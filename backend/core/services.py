from django.db import transaction
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from .audit import record
from .models import Instructor, Lead, OperationLock, Person, User
from .permissions import is_administrative
from .policies import DecisionRequired


def lock_admin(actor, target_user_id=None):
    """First lock User rows in primary-key order; revalidate authority while locked."""
    ids = {actor.pk}
    if target_user_id is not None:
        ids.add(target_user_id)
    users = {user.pk: user for user in User.objects.select_for_update().filter(pk__in=ids).order_by("pk")}
    current = users.get(actor.pk)
    if not is_administrative(current):
        raise PermissionDenied("Sua autorização administrativa não está mais ativa.")
    if target_user_id is not None:
        if actor.pk == target_user_id:
            raise PermissionDenied("Você não pode alterar sua própria autorização.")
        if target_user_id not in users:
            raise NotFound("Conta não encontrada.")
        return current, users[target_user_id]
    return current


def lock_student_identities():
    # This database row serializes both matching and creation, even when there is
    # no existing CPF row to lock. All API student writers acquire it.
    OperationLock.objects.get_or_create(key="student-identities")
    return OperationLock.objects.select_for_update().get(key="student-identities")


def bind_instructor(user, instructor_id=None):
    existing = Instructor.objects.filter(user=user).first()
    if instructor_id is None and existing:
        instructor_id = existing.pk
    if instructor_id is None:
        raise ValidationError({"instructor_id": "Informe o vínculo profissional para conceder acesso de instrutor."})
    instructor = Instructor.objects.select_for_update().filter(pk=instructor_id).first()
    if not instructor or not instructor.active:
        raise ValidationError({"instructor_id": "O cadastro profissional deve existir e estar ativo."})
    if instructor.user_id not in (None, user.pk) or (existing and existing.pk != instructor.pk):
        raise ValidationError({"instructor_id": "O vínculo profissional é conflitante ou já pertence a outra conta."})
    instructor.user = user
    instructor.save(update_fields=["user"])
    return instructor


@transaction.atomic
def change_access(actor, target_id, operation, data):
    actor, target = lock_admin(actor, target_id)
    if "coordinator" not in actor.roles:
        raise PermissionDenied("Somente a Coordenação pode alterar autorizações de acesso.")
    if operation in {'reject', 'reopen', 'deactivate', 'add_role', 'remove_role'} and (not isinstance(data.get('reason'), str) or not data['reason'].strip()):
        raise ValidationError({'reason': 'Informe a justificativa da alteração.'})
    before = {"roles": list(target.roles), "access_status": target.access_status, "is_active": target.is_active}
    if operation == "approve":
        if not target.is_active:
            raise ValidationError("Uma conta desativada não pode ser aprovada.")
        if target.access_status != "pending":
            raise DecisionRequired("A solicitação já foi decidida. Use a atribuição distinta de função quando autorizada.", ["DN-002"])
        roles = data["roles"]
        if "instructor" in roles:
            bind_instructor(target, data.get("instructor_id"))
        target.roles, target.access_status = roles, "approved"
    elif operation == "reject":
        target.roles, target.access_status = [], "rejected"
    elif operation == "reopen":
        if target.access_status != "rejected" or not target.is_active:
            raise ValidationError("Somente solicitações rejeitadas de contas ativas podem ser reabertas.")
        target.roles, target.access_status = [], "pending"
    elif operation == "deactivate":
        if not target.is_active:
            raise ValidationError("Esta conta já está desativada.")
        target.is_active = False
    elif operation == "add_role":
        if target.access_status != "approved" or not target.is_active:
            raise ValidationError("A conta precisa estar ativa e aprovada para receber funções.")
        if data["role"] == "instructor":
            bind_instructor(target, data.get("instructor_id"))
        target.roles = sorted(set(target.roles) | {data["role"]})
        target.access_status = "approved"
    elif operation == "remove_role":
        if data["role"] not in target.roles:
            raise ValidationError({"role": "A conta não possui esta função."})
        target.roles = [role for role in target.roles if role != data["role"]]
        if not target.roles:
            target.access_status = "pending"
    else:
        raise ValueError("Operação de acesso desconhecida.")
    target.save(update_fields=["roles", "access_status", "is_active"])
    record(actor, f"access.{operation}", target, reason=data.get("reason", ""), metadata={"before": before, "after": {"roles": target.roles, "access_status": target.access_status, "is_active": target.is_active}})
    return target


@transaction.atomic
def convert_lead(actor, lead_id, data):
    actor = lock_admin(actor)
    lock_student_identities()
    lead = Lead.objects.select_for_update().filter(pk=lead_id).first()
    if lead is None:
        raise NotFound("Interessado não encontrado.")
    if lead.student_id:
        if data.get("student_id") not in (None, lead.student_id):
            raise ValidationError({"student_id": "Este interessado já foi convertido para outro aluno."})
        return lead, False
    cpf_ids = set(Person.objects.filter(cpf=lead.cpf).values_list("id", flat=True)) if lead.cpf else set()
    email_ids = set(Person.objects.filter(email__iexact=lead.email).values_list("id", flat=True)) if lead.email else set()
    candidate_ids = cpf_ids | email_ids
    cpf_conflict = bool(lead.cpf and Person.objects.filter(pk__in=email_ids).exclude(cpf__in=["", lead.cpf]).exists())
    conflict = len(candidate_ids) > 1 or cpf_conflict
    selected_id = data.get("student_id")
    if conflict and selected_id is None:
        raise DecisionRequired("CPF ou e-mail correspondem a mais de um aluno. Confira os cadastros e informe student_id e reason para resolver a identidade.", ["RN-015", "DN-003"])
    if selected_id is not None:
        if conflict and not data.get("reason"):
            raise ValidationError({"reason": "Registre a justificativa da resolução de identidade."})
        student = Person.objects.select_for_update().filter(pk=selected_id).first()
        if student is None or student.archived:
            raise ValidationError({"student_id": "Selecione um aluno existente e não arquivado."})
        if candidate_ids and selected_id not in candidate_ids:
            raise ValidationError({"student_id": "O aluno selecionado não corresponde ao CPF ou e-mail encontrado."})
    elif candidate_ids:
        student = Person.objects.select_for_update().get(pk=next(iter(candidate_ids)))
        if student.archived:
            raise DecisionRequired("O cadastro correspondente está arquivado. Resolva a identidade e os efeitos do arquivamento antes de converter.", ["DN-003", "DN-021"])
    else:
        student = Person.objects.create(name=lead.name, cpf=lead.cpf, email=lead.email, phone=lead.phone)
    lead.student, lead.status = student, "converted"
    lead.save(update_fields=["student", "status"])
    record(actor, "lead.convert", lead, reason=data.get("reason", ""), metadata={"student_id": student.pk, "identity_resolved": conflict, "candidate_ids": sorted(candidate_ids), "enrollment_created": False})
    return lead, True
