from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone


class FinancialCatalogVersion(models.Model):
    """Versioned catalog storage; publication rules belong to the service layer."""

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Rascunho'
        PUBLISHED = 'published', 'Publicado'

    version = models.PositiveIntegerField(unique=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    effective_from = models.DateField()
    effective_until = models.DateField(null=True, blank=True)
    configuration = models.JSONField(default=dict)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    published_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name='+')
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-version']
        constraints = [
            models.CheckConstraint(condition=Q(effective_until__isnull=True) | Q(effective_until__gte=models.F('effective_from')), name='financial_catalog_valid_period'),
            models.CheckConstraint(condition=Q(status='draft', published_by__isnull=True, published_at__isnull=True) | Q(status='published', published_by__isnull=False, published_at__isnull=False), name='financial_catalog_publish_metadata'),
        ]


class InstructorPayoutAgreement(models.Model):
    instructor = models.ForeignKey('core.Instructor', on_delete=models.PROTECT, related_name='payout_agreements')
    modality = models.ForeignKey('core.Modality', on_delete=models.PROTECT, related_name='payout_agreements')
    effective_from = models.DateField()
    effective_until = models.DateField()
    percentage = models.DecimalField(max_digits=5, decimal_places=2)
    allocation_method = models.CharField(max_length=16, choices=[('calendar_days', 'Dias de serviço'), ('equal_months', 'Meses de contrato')])
    reason = models.TextField()
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    voided_at = models.DateTimeField(null=True, blank=True, editable=False)
    voided_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name='+')
    void_reason = models.TextField(blank=True, editable=False)

    class Meta:
        ordering = ['-effective_from', '-id']
        constraints = [
            models.CheckConstraint(condition=Q(effective_until__gte=models.F('effective_from'), percentage__gte=0, percentage__lte=100), name='payout_agreement_valid'),
            models.CheckConstraint(condition=Q(voided_at__isnull=True, voided_by__isnull=True, void_reason='') | (Q(voided_at__isnull=False, voided_by__isnull=False) & ~Q(void_reason='')), name='payout_agreement_void_consistent'),
        ]


class FrequencyPolicy(models.Model):
    short_days = models.PositiveSmallIntegerField(default=30)
    long_days = models.PositiveSmallIntegerField(default=90)
    absence_threshold = models.PositiveSmallIntegerField(default=3)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT, related_name='+')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=Q(short_days__gte=1, long_days__gte=models.F('short_days'), long_days__lte=3650, absence_threshold__gte=1, absence_threshold__lte=100), name='frequency_policy_valid')]


class BenefitAuthorization(models.Model):
    scope = models.CharField(max_length=10, choices=[('academic', 'Acadêmico'), ('ecowork', 'EcoWork')], default='academic')
    person = models.ForeignKey('core.Person', on_delete=models.PROTECT, related_name='benefits')
    modality = models.ForeignKey('core.Modality', null=True, blank=True, on_delete=models.PROTECT, related_name='benefits')
    plan = models.CharField(max_length=40, blank=True)
    starts_on = models.DateField()
    ends_on = models.DateField()
    kind = models.CharField(max_length=10, choices=[('percent', 'Percentual'), ('fixed', 'Valor fixo')])
    value = models.DecimalField(max_digits=12, decimal_places=2)
    fee_waiver = models.BooleanField(default=False)
    reason = models.TextField()
    status = models.CharField(max_length=10, choices=[('pending', 'Pendente'), ('approved', 'Aprovada'), ('rejected', 'Rejeitada')], default='pending')
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name='+')
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_reason = models.TextField(blank=True)
    institutional_reference = models.CharField(max_length=250, blank=True)
    approval_limit_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']
        constraints = [
            models.CheckConstraint(condition=Q(ends_on__gte=models.F('starts_on')) & (Q(value__gt=0) | Q(value=0, fee_waiver=True)) & (~Q(kind='percent') | Q(value__lte=100)), name='benefit_valid_values'),
            models.CheckConstraint(condition=Q(status='pending', decided_by__isnull=True, decided_at__isnull=True) | Q(status__in=['approved', 'rejected'], decided_by__isnull=False, decided_at__isnull=False), name='benefit_decision_consistent'),
        ]


class Enrollment(models.Model):
    financial_catalog = models.ForeignKey(FinancialCatalogVersion, null=True, blank=True, on_delete=models.PROTECT, related_name='enrollments', editable=False)
    source_lead = models.ForeignKey('core.Lead', null=True, blank=True, on_delete=models.PROTECT, related_name='origin_enrollments')
    benefit = models.ForeignKey(BenefitAuthorization, null=True, blank=True, on_delete=models.PROTECT, related_name='enrollments')
    benefit_snapshot = models.JSONField(default=dict, editable=False)
    contract_version = models.PositiveSmallIntegerField(default=0, editable=False)
    end_date = models.DateField(null=True, blank=True, editable=False)
    associated = models.BooleanField(default=False)
    payment_method = models.CharField(max_length=12, blank=True)
    installments = models.PositiveSmallIntegerField(default=1)
    fee_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)
    renewed_from = models.OneToOneField('self', null=True, blank=True, on_delete=models.PROTECT, related_name='renewal', editable=False)
    schedule = models.JSONField(default=list, editable=False)
    student = models.ForeignKey('core.Person', on_delete=models.PROTECT, related_name='enrollments')
    class_group = models.ForeignKey('core.ClassGroup', on_delete=models.PROTECT, related_name='enrollments')
    start_date = models.DateField()
    plan = models.CharField(max_length=40)
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0'))])
    administrative_status = models.CharField(max_length=12, default='regular', choices=[('regular', 'Regular'), ('cancelled', 'Cancelada')])
    cancelled_on = models.DateField(null=True, blank=True, editable=False)
    kind = models.CharField(max_length=10, default='regular', choices=[('regular', 'Comum'), ('trial', 'Experimental')])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-id']
        constraints = [models.CheckConstraint(condition=Q(amount__gt=0) | Q(amount=0, benefit__isnull=False), name='enrollment_amount_valid')]


class CommercialCondition(models.Model):
    enrollment = models.ForeignKey(Enrollment, on_delete=models.PROTECT, related_name='conditions')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    effective_on = models.DateField()
    plan = models.CharField(max_length=40)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class EnrollmentSuspension(models.Model):
    enrollment = models.ForeignKey(Enrollment, on_delete=models.PROTECT, related_name='suspensions')
    starts_on = models.DateField()
    ends_on = models.DateField()
    reason = models.TextField()
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-starts_on', '-id']
        constraints = [models.CheckConstraint(condition=Q(ends_on__gte=models.F('starts_on')), name='suspension_valid_period')]


class WaitingListEntry(models.Model):
    class_group = models.ForeignKey('core.ClassGroup', on_delete=models.PROTECT, related_name='waiting_list')
    person = models.ForeignKey('core.Person', on_delete=models.PROTECT, related_name='waiting_list')
    status = models.CharField(max_length=12, choices=[('waiting', 'Aguardando'), ('cancelled', 'Cancelada'), ('enrolled', 'Matriculada')], default='waiting')
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    enrollment = models.OneToOneField(Enrollment, null=True, blank=True, on_delete=models.PROTECT, related_name='waiting_entry')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'id']
        constraints = [
            models.UniqueConstraint(fields=['class_group', 'person'], condition=Q(status='waiting'), name='waiting_person_class_active_unique'),
            models.CheckConstraint(condition=(Q(status='enrolled', enrollment__isnull=False) | Q(status__in=['waiting', 'cancelled'], enrollment__isnull=True)), name='waiting_enrollment_consistent'),
        ]


class Charge(models.Model):
    enrollment = models.ForeignKey(Enrollment, on_delete=models.PROTECT, related_name='charges')
    category = models.CharField(max_length=20, choices=[('tuition', 'Mensalidade'), ('enrollment_fee', 'Taxa de matrícula'), ('extra', 'Outra receita')])
    competence = models.DateField(null=True, blank=True)
    due_date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    description = models.CharField(max_length=240, blank=True)
    # Identity technical key; does not schedule or invent recurring obligations.
    idempotency_key = models.CharField(max_length=120, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    cancelled_on = models.DateField(null=True, blank=True, editable=False)
    cancelled_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name='+')
    cancellation_reason = models.TextField(blank=True, editable=False)

    class Meta:
        ordering = ['due_date', 'id']
        constraints = [
            models.CheckConstraint(condition=Q(amount__gt=0), name='charge_positive_amount'),
            models.CheckConstraint(condition=~Q(category='tuition') | Q(competence__isnull=False), name='tuition_has_competence'),
        ]

    @property
    def received(self):
        return sum((p.amount for p in self.payments.all() if p.paid_on and not p.voided_at), Decimal('0.00'))

    @property
    def is_paid(self):
        return self.amount > 0 and self.received >= self.amount

    @property
    def status(self):
        if self.cancelled_on and self.cancelled_on <= timezone.localdate():
            return 'cancelled'
        if self.is_paid:
            return 'paid'
        return 'overdue' if self.due_date < timezone.localdate() else 'open'


class Payment(models.Model):
    request_key = models.UUIDField(null=True, blank=True, unique=True, editable=False)
    charge = models.ForeignKey(Charge, on_delete=models.PROTECT, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    paid_on = models.DateField()
    method = models.CharField(max_length=20, choices=[('pix', 'Pix'), ('cash', 'Dinheiro'), ('card', 'Cartão'), ('transfer', 'Transferência'), ('other', 'Outro')])
    reference = models.CharField(max_length=160, blank=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    voided_at = models.DateTimeField(null=True, blank=True, editable=False)
    voided_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name='+')
    void_reason = models.TextField(blank=True, editable=False)

    class Meta:
        ordering = ['-paid_on', '-id']
        constraints = [
            models.CheckConstraint(condition=Q(amount__gt=0), name='payment_positive_amount'),
            models.CheckConstraint(condition=Q(voided_at__isnull=True, voided_by__isnull=True, void_reason='') | (Q(voided_at__isnull=False, voided_by__isnull=False) & ~Q(void_reason='')), name='payment_void_consistent'),
        ]


class PaymentRefund(models.Model):
    payment = models.ForeignKey(Payment, on_delete=models.PROTECT, related_name='refunds')
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    refunded_on = models.DateField()
    method = models.CharField(max_length=20, choices=Payment._meta.get_field('method').choices)
    reference = models.CharField(max_length=160, blank=True)
    reason = models.TextField()
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    request_key = models.UUIDField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-refunded_on', '-id']
        constraints = [models.CheckConstraint(condition=Q(amount__gt=0), name='academic_refund_positive')]


class CollectionMessage(models.Model):
    charge = models.ForeignKey(Charge, on_delete=models.PROTECT, related_name='messages')
    recipient = models.CharField(max_length=160)
    phone = models.CharField(max_length=15)
    text = models.TextField()
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    confirmed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT, related_name='+')

    class Meta:
        ordering = ['-id']
