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
