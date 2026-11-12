from django.conf import settings
from django.db import models
from django.utils import timezone


class CatalogVersion(models.Model):
    version = models.PositiveIntegerField(unique=True)
    status = models.CharField(max_length=12, choices=[('draft', 'Rascunho'), ('published', 'Publicado')], default='draft')
    effective_from = models.DateField()
    effective_until = models.DateField(null=True, blank=True)
    configuration = models.JSONField(default=dict)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    published_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name='+')
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-version']
        constraints = [
            models.CheckConstraint(condition=models.Q(effective_until__isnull=True) | models.Q(effective_until__gte=models.F('effective_from')), name='eco_catalog_valid_period'),
            models.CheckConstraint(condition=models.Q(status='draft', published_by__isnull=True, published_at__isnull=True) | models.Q(status='published', published_by__isnull=False, published_at__isnull=False), name='eco_catalog_publication_valid'),
        ]


class Order(models.Model):
    catalog = models.ForeignKey(CatalogVersion, null=True, blank=True, on_delete=models.PROTECT, related_name='orders', editable=False)
    benefit = models.ForeignKey('billing.BenefitAuthorization', null=True, blank=True, on_delete=models.PROTECT, related_name='ecowork_orders', editable=False)
    benefit_snapshot = models.JSONField(default=dict, editable=False)
    person = models.ForeignKey('core.Person', on_delete=models.PROTECT, related_name='ecowork_orders')
    product = models.CharField(max_length=20)
    product_name = models.CharField(max_length=100)
    months = models.PositiveSmallIntegerField(default=0)
    quantity = models.PositiveSmallIntegerField(default=1)
    base_price = models.DecimalField(max_digits=12, decimal_places=2)
    discount_percent = models.PositiveSmallIntegerField(default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    residence = models.ForeignKey('core.ResidenceVerification', null=True, on_delete=models.PROTECT)
    association = models.ForeignKey('core.CondominiumAssociation', null=True, on_delete=models.PROTECT)
    billing_mode = models.CharField(max_length=12, choices=[('cash', 'À vista'), ('office', 'Parcelas pela secretaria'), ('card', 'Cartão parcelado')])
    installments = models.PositiveSmallIntegerField(default=1)
    first_due = models.DateField()
    starts_on = models.DateField(null=True)
    ends_on = models.DateField(null=True)  # Exclusive end.
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    request_key = models.UUIDField()
    request_hash = models.CharField(max_length=64)
    cancelled_at = models.DateTimeField(null=True)
    cancelled_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT, related_name='+')
    cancellation_reason = models.TextField(blank=True)
    cancellation_mode = models.CharField(max_length=20, blank=True)

    class Meta:
        ordering = ['-id']
        constraints = [
            models.UniqueConstraint(fields=['person', 'request_key'], name='ecowork_order_request_unique'),
            models.CheckConstraint(condition=(models.Q(total__gt=0) | models.Q(total=0, months__gt=0, benefit__isnull=False) | models.Q(total=0, discount_percent=100, months__gt=0, association__isnull=False)) & models.Q(quantity__gte=1, installments__gte=1), name='ecowork_order_positive'),
        ]

    @property
    def coverage_status(self):
        if self.cancelled_at:
            return 'cancelled'
        if not self.starts_on:
            return 'awaiting_payment'
        if self.ends_on and timezone.localdate() >= self.ends_on:
            return 'expired'
        return 'active' if self.months else 'paid_use'


class Charge(models.Model):
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name='charges')
    number = models.PositiveSmallIntegerField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    due_date = models.DateField()
    cancelled_at = models.DateTimeField(null=True)

    class Meta:
        ordering = ['number', 'id']
        constraints = [
            models.UniqueConstraint(fields=['order', 'number'], name='ecowork_charge_number_unique'),
            models.CheckConstraint(condition=models.Q(amount__gt=0, number__gte=1), name='ecowork_charge_positive'),
        ]

    @property
    def payment(self):
        return next((payment for payment in self.payments.all() if payment.voided_at is None), None)

    @property
    def status(self):
        if self.cancelled_at:
            return 'cancelled'
        if self.payment:
            return 'paid'
        return 'overdue' if self.due_date < timezone.localdate() else 'open'


class Payment(models.Model):
    charge = models.ForeignKey(Charge, on_delete=models.PROTECT, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    paid_on = models.DateField()
    method = models.CharField(max_length=12, choices=[('pix', 'Pix'), ('cash', 'Dinheiro'), ('card', 'Cartão'), ('transfer', 'Transferência'), ('other', 'Outro')])
    reference = models.CharField(max_length=160, blank=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    request_key = models.UUIDField(unique=True)
    voided_at = models.DateTimeField(null=True)
    voided_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT, related_name='+')
    void_reason = models.TextField(blank=True)

    class Meta:
        ordering = ['-id']
        constraints = [
            models.CheckConstraint(condition=models.Q(amount__gt=0), name='ecowork_payment_positive'),
            models.UniqueConstraint(fields=['charge'], condition=models.Q(voided_at__isnull=True), name='ecowork_active_payment_unique'),
        ]


class Refund(models.Model):
    payment = models.ForeignKey(Payment, on_delete=models.PROTECT, related_name='refunds')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    refunded_on = models.DateField()
    method = models.CharField(max_length=12, choices=Payment._meta.get_field('method').choices)
    reference = models.CharField(max_length=160, blank=True)
    reason = models.TextField()
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    request_key = models.UUIDField(unique=True)

    class Meta:
        ordering = ['-id']
        constraints = [models.CheckConstraint(condition=models.Q(amount__gt=0), name='ecowork_refund_positive')]
