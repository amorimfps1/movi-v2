import hashlib
from decimal import Decimal

from django.contrib.auth.models import AbstractUser, UserManager as DjangoUserManager
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.functions import Lower

from .validators import normalize_cpf, validate_weekdays


class UserManager(DjangoUserManager):
    def create_user(self, username=None, email=None, password=None, **extra_fields):
        if not email:
            raise ValueError("O e-mail é obrigatório.")
        email = email.strip().lower()
        generated_username = "movi_" + hashlib.sha256(email.encode("utf-8")).hexdigest()
        return super().create_user(username or generated_username, email, password, **extra_fields)

    def create_superuser(self, username=None, email=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("access_status", "approved")
        extra_fields.setdefault("roles", ["coordinator"])
        return self.create_user(username, email, password, **extra_fields)


class User(AbstractUser):
    class AccessStatus(models.TextChoices):
        PENDING = "pending", "Pendente"
        APPROVED = "approved", "Aprovado"
        REJECTED = "rejected", "Rejeitado"

    email = models.EmailField(unique=True)
    access_status = models.CharField(max_length=10, choices=AccessStatus.choices, default=AccessStatus.PENDING)
    roles = models.JSONField(default=list, blank=True)
    objects = UserManager()
    REQUIRED_FIELDS = ["email"]

    class Meta:
        constraints = [models.UniqueConstraint(Lower("email"), name="core_user_email_case_unique")]
        ordering = ["id"]


class Student(models.Model):
    name = models.CharField(max_length=200)
    cpf = models.CharField(max_length=11, blank=True, db_index=True, validators=[normalize_cpf])
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    address = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name", "id"]

    def save(self, *args, **kwargs):
        self.cpf = normalize_cpf(self.cpf)
        self.email = self.email.strip().lower()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Modality(models.Model):
    name = models.CharField(max_length=120)
    area = models.CharField(max_length=120, blank=True)
    default_price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0"))])
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name", "id"]

    def __str__(self):
        return self.name


class Instructor(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    active = models.BooleanField(default=True)
    specialties = models.ManyToManyField(Modality, related_name="instructors", blank=True)
    user = models.OneToOneField(User, null=True, blank=True, related_name="instructor", on_delete=models.PROTECT)

    class Meta:
        ordering = ["name", "id"]

    def __str__(self):
        return self.name


class ClassGroup(models.Model):
    name = models.CharField(max_length=150)
    modality = models.ForeignKey(Modality, related_name="classes", on_delete=models.PROTECT)
    instructor = models.ForeignKey(Instructor, related_name="classes", on_delete=models.PROTECT)
    weekdays = models.JSONField(default=list, validators=[validate_weekdays])
    start_time = models.TimeField()
    end_time = models.TimeField()
    room = models.CharField(max_length=120)
    age_range = models.CharField(max_length=120, blank=True)
    capacity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    active = models.BooleanField(default=True)
    allows_trial = models.BooleanField(default=False)

    class Meta:
        ordering = ["name", "id"]
        constraints = [
            models.CheckConstraint(condition=models.Q(start_time__lt=models.F("end_time")), name="core_class_valid_times"),
            models.CheckConstraint(condition=models.Q(capacity__gte=1), name="core_class_positive_capacity"),
        ]

    def __str__(self):
        return self.name


class Lead(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "Novo"
        CONTACTING = "contacting", "Em atendimento"
        WAITING = "waiting", "Aguardando retorno"
        CONVERTED = "converted", "Convertido"
        NOT_CONVERTED = "not_converted", "Não convertido"

    name = models.CharField(max_length=200)
    cpf = models.CharField(max_length=11, blank=True, validators=[normalize_cpf])
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    source = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.NEW)
    interests = models.ManyToManyField(Modality, related_name="leads", blank=True)
    notes = models.TextField(blank=True)
    student = models.ForeignKey(Student, null=True, blank=True, related_name="leads", on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=(models.Q(status="converted", student__isnull=False) | (~models.Q(status="converted") & models.Q(student__isnull=True))),
                name="core_lead_conversion_consistent",
            )
        ]

    def save(self, *args, **kwargs):
        self.cpf = normalize_cpf(self.cpf)
        self.email = self.email.strip().lower()
        return super().save(*args, **kwargs)


class AuditEvent(models.Model):
    actor = models.ForeignKey(User, null=True, on_delete=models.PROTECT, related_name="audit_events")
    action = models.CharField(max_length=100)
    target_type = models.CharField(max_length=100)
    target_id = models.CharField(max_length=50)
    reason = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]


class OperationLock(models.Model):
    """Stable mutex rows serialize identity checks, including absent student matches."""
    key = models.CharField(max_length=150, primary_key=True)
