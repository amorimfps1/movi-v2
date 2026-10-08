from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Enrollment(models.Model):
    student = models.ForeignKey('core.Student', on_delete=models.PROTECT, related_name='enrollments')
    class_group = models.ForeignKey('core.ClassGroup', on_delete=models.PROTECT, related_name='enrollments')
    start_date = models.DateField()
    plan = models.CharField(max_length=12, choices=[('monthly', 'Mensal'), ('quarterly', 'Trimestral'), ('yearly', 'Anual')])
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    administrative_status = models.CharField(max_length=12, default='regular', choices=[('regular', 'Regular'), ('cancelled', 'Cancelada')])
    kind = models.CharField(max_length=10, default='regular', choices=[('regular', 'Comum'), ('trial', 'Experimental')])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-id']
        constraints = [models.CheckConstraint(condition=Q(amount__gt=0), name='enrollment_positive_amount')]


class CommercialCondition(models.Model):
    enrollment = models.ForeignKey(Enrollment, on_delete=models.PROTECT, related_name='conditions')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    effective_on = models.DateField()
    plan = models.CharField(max_length=12)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


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

    class Meta:
        ordering = ['due_date', 'id']
        constraints = [
            models.CheckConstraint(condition=Q(amount__gt=0), name='charge_positive_amount'),
            models.CheckConstraint(condition=~Q(category='tuition') | Q(competence__isnull=False), name='tuition_has_competence'),
        ]

    @property
    def received(self):
        return sum((p.amount for p in self.payments.all() if p.paid_on), Decimal('0.00'))

    @property
    def is_paid(self):
        return self.amount > 0 and self.received >= self.amount

    @property
    def status(self):
        if self.is_paid:
            return 'paid'
        return 'overdue' if self.due_date < timezone.localdate() else 'open'


class Payment(models.Model):
    charge = models.ForeignKey(Charge, on_delete=models.PROTECT, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    paid_on = models.DateField()
    method = models.CharField(max_length=20, choices=[('pix', 'Pix'), ('cash', 'Dinheiro'), ('card', 'Cartão'), ('transfer', 'Transferência'), ('other', 'Outro')])
    reference = models.CharField(max_length=160, blank=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-paid_on', '-id']
        constraints = [
            models.CheckConstraint(condition=Q(amount__gt=0), name='payment_positive_amount'),
            models.UniqueConstraint(fields=['charge'], name='one_full_settlement_per_charge'),
        ]
