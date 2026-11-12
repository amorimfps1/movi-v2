from decimal import Decimal
from datetime import timedelta, date
from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import APIException, ValidationError


class DecisionRequired(APIException):
    status_code = 409
    default_code = 'decision_required'

    def __init__(self, detail, decisions):
        super().__init__({'detail': detail, 'decisions': decisions})


def active_on_q(on, prefix=''):
    return Q(**{f'{prefix}administrative_status': 'regular'}) | Q(**{f'{prefix}administrative_status': 'cancelled', f'{prefix}cancelled_on__gt': on})


def ensure_class_capacity(group, start, end, person_id=None, limit=None):
    """Caller holds the group lock; check every date where occupancy can change."""
    from .models import Enrollment
    periods = Enrollment.objects.filter(class_group=group, kind='regular').filter(active_on_q(start))
    if end:
        periods = periods.filter(start_date__lte=end)
    periods = periods.filter(Q(end_date__isnull=True) | Q(end_date__gte=start))
    changes = {}
    for begins, finishes, status, cancellation in periods.values_list('start_date', 'end_date', 'administrative_status', 'cancelled_on'):
        if status == 'cancelled' and cancellation:
            cancellation_end = cancellation - timedelta(days=1)
            finishes = min(finishes, cancellation_end) if finishes else cancellation_end
        begins = max(begins, start)
        if finishes and begins > finishes:
            continue
        changes[begins] = changes.get(begins, 0) + 1
        if finishes and finishes < date.max and (end is None or finishes < end):
            after = finishes + timedelta(days=1)
            changes[after] = changes.get(after, 0) - 1
    from academic.models import TrialParticipation
    trials = TrialParticipation.objects.filter(lesson__class_group=group, lesson__date__gte=start).filter(Q(status='scheduled') | Q(status='completed', present=True)).exclude(lesson__status='cancelled')
    if person_id is not None:
        trials = trials.exclude(person_id=person_id)
    if end:
        trials = trials.filter(lesson__date__lte=end)
    for trial_date in trials.values_list('lesson__date', flat=True):
        changes[trial_date] = changes.get(trial_date, 0) + 1
        if trial_date < date.max and (end is None or trial_date < end):
            after = trial_date + timedelta(days=1)
            changes[after] = changes.get(after, 0) - 1
    occupancy = 0
    for day in sorted(changes):
        occupancy += changes[day]
        if occupancy >= (group.capacity if limit is None else limit):
            raise ValidationError({'class_group': f'Turma sem vaga em {day:%d/%m/%Y}.'})


def evaluate_eligibility(enrollment, on=None):
    """Never infer temporal coverage from historical cash receipts (DN-004)."""
    on = on or timezone.localdate()
    result = {'eligible': False, 'status': 'pending', 'reason': '', 'decisions': []}
    if enrollment.administrative_status != 'regular' and (not enrollment.cancelled_on or on >= enrollment.cancelled_on):
        return {**result, 'status': 'cancelled', 'reason': 'Matrícula cancelada; pagamento não reativa o vínculo.'}
    if enrollment.start_date > on:
        return {**result, 'reason': 'A matrícula ainda não iniciou.'}
    if enrollment.suspensions.filter(starts_on__lte=on, ends_on__gte=on).exists():
        return {**result, 'status': 'suspended', 'reason': 'Matrícula suspensa nesta data.'}
    if enrollment.student.archived:
        return {**result, 'eligible': None, 'status': 'decision_required', 'reason': 'Aluno arquivado; efeito sobre participação depende de decisão.', 'decisions': ['DN-021']}
    if not enrollment.class_group.active:
        return {**result, 'reason': 'Turma inativa.'}
    if enrollment.kind == 'trial':
        if not enrollment.class_group.allows_trial:
            return {**result, 'status':'blocked', 'reason':'A turma não permite participação experimental.'}
        return {**result, 'eligible': None, 'status': 'decision_required', 'reason': 'Duração, quantidade e condições experimentais aguardam política detalhada; aprovação por ID isolado não define participação.', 'decisions': ['DN-013']}
    if enrollment.contract_version == 1:
        from .contracts import contract_eligibility
        return contract_eligibility(enrollment, on)
    charges = list(enrollment.charges.filter(category='tuition').prefetch_related('payments'))
    overdue = [c for c in charges if c.due_date < on and not c.is_paid]
    if overdue:
        return {**result, 'status': 'blocked', 'reason': 'Existe mensalidade vencida sem quitação integral.'}
    if not charges:
        return {**result, 'eligible': None, 'status': 'decision_required', 'reason': 'Nenhuma mensalidade registrada. Ausência de cobrança não comprova adimplência.', 'decisions': ['DN-004', 'DN-005', 'DN-006']}
    if not any(c.is_paid for c in charges):
        return {**result, 'reason': 'Pendente de mensalidade integralmente quitada. Taxa de matrícula não libera participação.'}
    return {**result, 'eligible': None, 'status': 'decision_required', 'reason': 'Recebimento confirmado; cobertura temporal do pagamento aguarda política institucional.', 'decisions': ['DN-004', 'DN-006']}


PENDING_DECISIONS = [
    ('DN-001', 'Permissões finais', 'Gestão de contas restrita à Coordenação; revisão dos demais acessos por perfil em andamento.'),
    ('DN-002', 'Múltiplas funções', 'Aprovação, reabertura e desativação disponíveis; validação integrada dos perfis em andamento.'),
    ('DN-003', 'Identificação', 'CPF único e resolução de identidade disponíveis; migração e validação operacional pendentes.'),
    ('DN-004', 'Tabela e vencimentos', 'Cartão 2026 parametrizado; conferir categorias, Karatê, boleto e vencimentos provisórios.'),
    ('DN-005', 'Contratos legados', 'Novos contratos têm cronograma; vínculos antigos exigem revisão antes de gerar obrigações.'),
    ('DN-006', 'Cobrança esperada ausente', 'Novos contratos bloqueiam participação e permitem regularização auditada; legados exigem revisão.'),
    ('DN-007', 'Bolsas e descontos', 'Solicitação, aprovação e aplicação acadêmica disponíveis; alterações posteriores e EcoWork ainda precisam ser concluídos.'),
    ('DN-008', 'Pagamentos e correções', 'Recebimentos parciais, invalidação auditada e devolução separada estão disponíveis; homologação e concorrência em PostgreSQL pendentes.'),
    ('DN-009', 'Inadimplência', 'Base sem carência; multas, juros e exceções não definidos.'),
    ('DN-010', 'Suspensão e trancamento', 'Suspensão por até 30 dias autorizada pela Coordenação; ajustes contratuais e prorrogações exigem novos procedimentos.'),
    ('DN-011', 'Cancelamento e renovação', 'Renovação explícita sem taxa disponível para contratos parametrizados; devolução e reativação não definidas.'),
    ('DN-012', 'Capacidade e conflitos', 'Lotação, fila, conflitos e exceção dentro do limite físico são verificados; validação operacional permanece pendente.'),
    ('DN-013', 'Experimental', 'Agendamento, presença e correção auditada separados estão disponíveis; validação operacional permanece pendente.'),
    ('DN-015', 'Reposições', 'Reposições são novas aulas vinculadas, com horário e conflitos verificados; validação operacional permanece pendente.'),
    ('DN-016', 'Repasse', 'Sem cálculo final nem atribuição de base por substituições.'),
    ('DN-017', 'Indicadores financeiros', 'Extratos identificam data de recebimento/vencimento; homologação do regime pendente.'),
    ('DN-018', 'Frequência e evasão', 'Frequência e alerta são configuráveis; evasão separa registros sem datas históricas conhecidas.'),
    ('DN-019', 'Conversão e ocupação', 'Ocupação e conversão por coorte disponíveis; matrícula conta mediante vínculo explícito ao lead.'),
    ('DN-020', 'Dados e comunicação', 'Preferências por canal e finalidade registradas; retenção e acesso a dados sensíveis ainda requerem procedimentos.'),
    ('DN-021', 'Arquivamento e transferência', 'Arquivamento preserva histórico; transferências ainda não estão disponíveis.'),
    ('DN-022', 'Capacidade operacional', 'Carga, recuperação e homologação institucional pendentes.'),
]
