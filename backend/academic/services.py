"""Atomic diary operations.

Lock order: actor User -> ClassGroup (PK ascending) -> Lesson -> Instructor
(PK ascending) -> Enrollment (PK ascending) -> Charge (PK ascending) -> Payment (PK ascending). Billing
mutations must acquire ClassGroup before Enrollment, including creation, so a
new participant cannot appear between the final roster check and commit.
No joined select_for_update is used: nullable instructor joins are unsafe on PG.
"""
import hashlib
import json

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import APIException, NotFound, PermissionDenied, ValidationError

from billing.models import Charge, Enrollment, Payment
from billing.services import evaluate_eligibility
from core.audit import record
from core.models import ClassGroup, Instructor
from core.permissions import is_administrative, is_internal

from .models import Attendance, Lesson


class AcademicConflict(APIException):
    status_code = 409
    default_code = "academic_conflict"

    def __init__(self, detail, decisions=None):
        super().__init__({"detail": detail, "decisions": sorted(set(decisions or []))})


def _actor(actor_id):
    try:
        actor = get_user_model().objects.select_for_update().get(pk=actor_id)
    except get_user_model().DoesNotExist:
        raise PermissionDenied("A conta não possui mais autorização.")
    if not is_internal(actor):
        raise PermissionDenied("A autorização foi revogada. Entre em contato com a secretaria.")
    return actor


def _can_read(actor, lesson, class_group):
    if is_administrative(actor):
        return
    if "instructor" in actor.roles:
        instructor_id = Instructor.objects.filter(user_id=actor.pk, active=True).values_list("id", flat=True).first()
        if instructor_id and instructor_id in (class_group.instructor_id, lesson.assigned_instructor_id):
            return
    raise PermissionDenied("Esta aula não pertence ao seu diário autorizado.")


def _can_submit(actor, lesson, class_group):
    _can_read(actor, lesson, class_group)
    if is_administrative(actor):
        return
    instructor_id = Instructor.objects.filter(user_id=actor.pk, active=True).values_list("id", flat=True).first()
    responsible = lesson.assigned_instructor_id or class_group.instructor_id
    if responsible != instructor_id:
        raise PermissionDenied("A chamada cabe ao instrutor atribuído a esta aula.")


def _locked_lesson(actor_id, lesson_id):
    actor = _actor(actor_id)
    initial = Lesson.objects.filter(pk=lesson_id).values("class_group_id").first()
    if not initial:
        raise NotFound("Aula não encontrada.")
    class_group = ClassGroup.objects.select_for_update().get(pk=initial["class_group_id"])
    lesson = Lesson.objects.select_for_update().get(pk=lesson_id)
    if lesson.class_group_id != class_group.pk:
        raise AcademicConflict("A turma da aula mudou. Atualize o diário.")
    # Professional deactivation must also serialize for a substitute who has
    # no titular ClassGroup of their own. Core writes lock ClassGroup first,
    # then Instructor, so this keeps that order without joining nullable FKs.
    instructor_ids = {class_group.instructor_id, lesson.assigned_instructor_id} - {None}
    list(Instructor.objects.select_for_update().filter(pk__in=instructor_ids).order_by("pk").values_list("pk", flat=True))
    _can_read(actor, lesson, class_group)
    return actor, class_group, lesson


def _attendance_policy():
    approvals = getattr(settings, "BUSINESS_APPROVALS", [])
    policy = getattr(settings, "ATTENDANCE_POLICY", None)
    # The currently supported slice must be explicitly approved; an ID alone
    # does not decide retroactivity, evaluation date or empty lessons.
    required = {
        "marking": "presence_absence", "eligibility_date": "lesson_date",
        "allow_past": False, "allow_future": False, "allow_empty": False,
    }
    if "DN-014" not in approvals or not isinstance(policy, dict):
        raise AcademicConflict(
            "Chamada indisponível: a instituição precisa definir e aprovar a política de chamada.",
            ["DN-014"],
        )
    if set(policy) != set(required) or any(type(policy[key]) is not type(value) or policy[key] != value for key, value in required.items()):
        raise AcademicConflict("A política detalhada de chamada não está definida para este fluxo.", ["DN-014"])
    return policy


def _snapshot(actor, class_group, lesson):
    # Force evaluation while all rows are locked. The class mutex covers absent
    # rows and enrollments inserted concurrently through billing services.
    ids = list(Enrollment.objects.select_for_update().filter(class_group=class_group).order_by("pk").values_list("pk", flat=True))
    charge_ids = list(Charge.objects.select_for_update().filter(enrollment_id__in=ids).order_by("pk").values_list("pk", flat=True))
    list(Payment.objects.select_for_update().filter(charge_id__in=charge_ids).order_by("pk").values_list("pk", flat=True))
    enrollments = Enrollment.objects.filter(pk__in=ids).select_related("student", "class_group").order_by("pk")
    participants, excluded, raw, decisions = [], [], [], set()
    unresolved = False
    for enrollment in enrollments:
        result = evaluate_eligibility(enrollment, on=lesson.date)
        eligible = result.get("eligible")
        item_decisions = result.get("decisions", [])
        decisions.update(item_decisions)
        raw.append({"enrollment": enrollment.pk, "student": enrollment.student_id, "name": enrollment.student.name,
                    "start_date": str(enrollment.start_date), "kind": enrollment.kind,
                    "administrative_status": enrollment.administrative_status, "result": result})
        if eligible is True:
            participants.append({"enrollment": enrollment.pk, "student_name": enrollment.student.name})
        else:
            unresolved = unresolved or eligible is None
            excluded.append({
                "enrollment": enrollment.pk,
                "reason": result.get("reason", "Participação indisponível.") if is_administrative(actor)
                          else "Participação indisponível. Consulte a secretaria.",
                "decisions": item_decisions,
            })
    policy = getattr(settings, "ATTENDANCE_POLICY", None)
    state = {
        "actor": {"id": actor.pk, "roles": sorted(actor.roles), "access": actor.access_status,
                  "instructor": Instructor.objects.filter(user_id=actor.pk, active=True).values_list("id", flat=True).first()},
        "class": {"id": class_group.pk, "instructor": class_group.instructor_id, "trial": class_group.allows_trial},
        "lesson": {"id": lesson.pk, "date": str(lesson.date), "assigned": lesson.assigned_instructor_id, "status": lesson.status},
        "enrollments": raw, "policy": policy, "approvals": sorted(getattr(settings, "BUSINESS_APPROVALS", [])),
    }
    digest = hashlib.sha256(json.dumps(state, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()
    try:
        _attendance_policy()
    except AcademicConflict:
        decisions.add("DN-014")
    version = signing.dumps({"actor": actor.pk, "lesson": lesson.pk, "digest": digest}, salt="academic.roster.v1")
    return {"lesson": lesson.pk, "version": version, "participants": participants,
            "excluded": excluded, "decisions": sorted(decisions)}, digest, unresolved


@transaction.atomic
def roster(actor_id, lesson_id):
    actor, class_group, lesson = _locked_lesson(actor_id, lesson_id)
    payload, _, _ = _snapshot(actor, class_group, lesson)
    return payload


@transaction.atomic
def attendance_history(actor_id, lesson_id):
    # A completed diary reads immutable Attendance rows. Re-evaluating billing
    # here could erase the visible record of a participant's earlier attendance.
    _, _, lesson = _locked_lesson(actor_id, lesson_id)
    marks = [{
        "enrollment": attendance.enrollment_id,
        "student_name": attendance.enrollment.student.name,
        "present": attendance.present,
        "created_at": attendance.created_at,
    } for attendance in Attendance.objects.filter(lesson=lesson).select_related("enrollment__student").order_by("enrollment_id")]
    return {
        "lesson": lesson.pk,
        "status": lesson.status,
        "marks": marks,
        "definition": "Marcações gravadas na conclusão; não recalculadas pela elegibilidade atual.",
    }


@transaction.atomic
def submit_attendance(actor_id, lesson_id, version, marks):
    actor, class_group, lesson = _locked_lesson(actor_id, lesson_id)
    _can_submit(actor, lesson, class_group)
    _attendance_policy()
    if lesson.status != Lesson.Status.SCHEDULED or Attendance.objects.filter(lesson=lesson).exists():
        raise AcademicConflict("A chamada já foi concluída ou a aula foi cancelada. Correções dependem de política própria.", ["DN-014"])
    if lesson.date != timezone.localdate():
        raise AcademicConflict("A chamada fora da data atual depende de política institucional específica.", ["DN-014"])
    payload, digest, unresolved = _snapshot(actor, class_group, lesson)
    try:
        signed = signing.loads(version, salt="academic.roster.v1")
    except (signing.BadSignature, TypeError, ValueError):
        raise AcademicConflict("A lista da chamada é inválida. Atualize o diário.")
    if signed != {"actor": actor.pk, "lesson": lesson.pk, "digest": digest}:
        raise AcademicConflict("A lista ou a autorização mudou. Atualize a chamada antes de confirmar.", payload["decisions"])
    if unresolved:
        raise AcademicConflict("Existem matrículas cuja elegibilidade aguarda decisão institucional. Consulte a secretaria.", payload["decisions"])
    expected = {participant["enrollment"] for participant in payload["participants"]}
    submitted = [mark["enrollment"] for mark in marks]
    if len(submitted) != len(set(submitted)) or set(submitted) != expected:
        raise ValidationError({"marks": ["Envie exatamente uma marcação por matrícula elegível; atualize a lista se necessário."]})
    if not expected:
        raise AcademicConflict("Aula sem participantes exige política institucional específica.", ["DN-014"])
    Attendance.objects.bulk_create([
        Attendance(lesson=lesson, enrollment_id=mark["enrollment"], present=mark["present"], actor=actor)
        for mark in marks
    ])
    lesson.status = Lesson.Status.COMPLETED
    lesson.save(update_fields=["status"])
    record(actor, "attendance.completed", lesson, metadata={"enrollments": sorted(expected), "count": len(marks)})
    return lesson


@transaction.atomic
def save_lesson(actor_id, validated_data, lesson_id=None):
    actor = _actor(actor_id)
    if not is_administrative(actor):
        raise PermissionDenied("Somente Secretaria e Coordenação podem alterar aulas e atribuições.")
    existing = Lesson.objects.filter(pk=lesson_id).values("class_group_id").first() if lesson_id else None
    if lesson_id and not existing:
        raise NotFound("Aula não encontrada.")
    target = validated_data.get("class_group")
    class_ids = {existing["class_group_id"]} if existing else set()
    if target:
        class_ids.add(target.pk)
    list(ClassGroup.objects.select_for_update().filter(pk__in=class_ids).order_by("pk").values_list("pk", flat=True))
    lesson = Lesson.objects.select_for_update().get(pk=lesson_id) if lesson_id else None
    if lesson and lesson.class_group_id != existing["class_group_id"]:
        raise AcademicConflict("A aula mudou. Atualize antes de editar.")
    if lesson and (lesson.status == Lesson.Status.COMPLETED or Attendance.objects.filter(lesson=lesson).exists()):
        raise AcademicConflict("Uma aula realizada não pode ser alterada sem política de correção.", ["DN-014", "DN-015"])
    if validated_data.get("status") == Lesson.Status.COMPLETED:
        raise ValidationError({"status": "Confirme a chamada para realizar a aula."})
    # Reopening a cancellation could change historical participation rights.
    if lesson and lesson.status == Lesson.Status.CANCELLED and validated_data.get("status", lesson.status) != lesson.status:
        raise AcademicConflict("Reabrir uma aula cancelada depende de política institucional.", ["DN-015"])
    class_id = target.pk if target else lesson.class_group_id
    date = validated_data.get("date", lesson.date if lesson else None)
    duplicates = Lesson.objects.filter(class_group_id=class_id, date=date)
    if lesson:
        duplicates = duplicates.exclude(pk=lesson.pk)
    if duplicates.exists():
        raise ValidationError({"date": "Já existe uma aula para esta turma e data."})
    if lesson:
        for key, value in validated_data.items():
            setattr(lesson, key, value)
        lesson.save()
    else:
        lesson = Lesson.objects.create(**validated_data)
    record(actor, "lesson.updated" if lesson_id else "lesson.created", lesson,
           metadata={"class_group": lesson.class_group_id, "date": str(lesson.date),
                     "assigned_instructor": lesson.assigned_instructor_id, "status": lesson.status})
    return lesson
