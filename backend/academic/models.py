from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Lesson(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Agendada"
        COMPLETED = "completed", "Realizada"
        CANCELLED = "cancelled", "Cancelada"

    class_group = models.ForeignKey("core.ClassGroup", on_delete=models.PROTECT, related_name="lessons")
    date = models.DateField()
    assigned_instructor = models.ForeignKey(
        "core.Instructor", null=True, blank=True, on_delete=models.PROTECT,
        related_name="assigned_lessons",
    )
    replacement_for = models.ForeignKey('self', null=True, blank=True, on_delete=models.PROTECT, related_name='replacements')
    replacement_start = models.TimeField(null=True, blank=True)
    replacement_end = models.TimeField(null=True, blank=True)
    replacement_reason = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.SCHEDULED)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-id"]
        constraints = [
            models.UniqueConstraint(fields=["class_group", "date"], name="academic_unique_class_date"),
            models.CheckConstraint(
                condition=models.Q(status__in=["scheduled", "completed", "cancelled"]),
                name="academic_valid_lesson_status",
            ),
            models.CheckConstraint(condition=(models.Q(replacement_for__isnull=True, replacement_start__isnull=True, replacement_end__isnull=True, replacement_reason='') | models.Q(replacement_for__isnull=False, replacement_start__isnull=False, replacement_end__isnull=False, replacement_start__lt=models.F('replacement_end')) & ~models.Q(replacement_reason='')), name='academic_replacement_valid'),
        ]


class Attendance(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.PROTECT, related_name="attendance")
    enrollment = models.ForeignKey("billing.Enrollment", on_delete=models.PROTECT, related_name="attendance")
    present = models.BooleanField()
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="attendance_records")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["enrollment_id"]
        constraints = [
            models.UniqueConstraint(fields=["lesson", "enrollment"], name="academic_unique_lesson_enrollment"),
        ]

    def clean(self):
        if self.lesson_id and self.enrollment_id:
            if self.lesson.class_group_id != self.enrollment.class_group_id:
                raise ValidationError({"enrollment": "A matrícula não pertence à turma desta aula."})


class TrialParticipation(models.Model):
    person = models.ForeignKey('core.Person', on_delete=models.PROTECT, related_name='trials')
    modality = models.ForeignKey('core.Modality', on_delete=models.PROTECT, related_name='trials')
    lesson = models.ForeignKey(Lesson, on_delete=models.PROTECT, related_name='trials')
    guardian_authorization = models.BooleanField(default=False)
    status = models.CharField(max_length=12, choices=[('scheduled', 'Agendada'), ('completed', 'Registrada'), ('cancelled', 'Cancelada')], default='scheduled')
    present = models.BooleanField(null=True, blank=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'id']
        constraints = [
            models.UniqueConstraint(fields=['person', 'modality'], condition=~models.Q(status='cancelled'), name='academic_one_trial_per_modality'),
            models.CheckConstraint(condition=(models.Q(status='completed', present__isnull=False) | models.Q(status__in=['scheduled', 'cancelled'], present__isnull=True)), name='academic_trial_presence_consistent'),
        ]
