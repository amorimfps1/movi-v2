from django.conf import settings
from django.db import models
from django.utils import timezone


class Order(models.Model):
    person = models.ForeignKey('core.Student', on_delete=models.PROTECT, related_name='ecowork_orders')
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

    class Meta:
        ordering = ['-id']
        constraints = [
            models.UniqueConstraint(fields=['person', 'request_key'], name='ecowork_order_request_unique'),
            models.CheckConstraint(condition=models.Q(total__gt=0, quantity__gte=1, installments__gte=1), name='ecowork_order_positive'),
        ]

    @property
    def coverage_status(self):
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

    class Meta:
        ordering = ['number', 'id']
        constraints = [
            models.UniqueConstraint(fields=['order', 'number'], name='ecowork_charge_number_unique'),
            models.CheckConstraint(condition=models.Q(amount__gt=0, number__gte=1), name='ecowork_charge_positive'),
        ]

    @property
    def status(self):
        if hasattr(self, 'payment'):
            return 'paid'
        return 'overdue' if self.due_date < timezone.localdate() else 'open'


class Payment(models.Model):
    charge = models.OneToOneField(Charge, on_delete=models.PROTECT, related_name='payment')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    paid_on = models.DateField()
    method = models.CharField(max_length=12, choices=[('pix', 'Pix'), ('cash', 'Dinheiro'), ('card', 'Cartão'), ('transfer', 'Transferência'), ('other', 'Outro')])
    reference = models.CharField(max_length=160, blank=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    request_key = models.UUIDField(unique=True)

    class Meta:
        ordering = ['-id']
        constraints = [models.CheckConstraint(condition=models.Q(amount__gt=0), name='ecowork_payment_positive')]
