from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from rest_framework.exceptions import APIException


class DecisionRequired(APIException):
    status_code = 409
    default_code = 'decision_required'

    def __init__(self, detail, decisions):
        super().__init__({'detail': detail, 'decisions': decisions})


def evaluate_eligibility(enrollment, on=None):
    """Never infer temporal coverage from historical cash receipts (DN-004)."""
    on = on or timezone.localdate()
    result = {'eligible': False, 'status': 'pending', 'reason': '', 'decisions': []}
    if enrollment.administrative_status != 'regular':
        return {**result, 'status': 'cancelled', 'reason': 'Matrícula cancelada; pagamento não reativa o vínculo.'}
    if enrollment.start_date > on:
        return {**result, 'reason': 'A matrícula ainda não iniciou.'}
    if enrollment.student.archived:
        return {**result, 'eligible': None, 'status': 'decision_required', 'reason': 'Aluno arquivado; efeito sobre participação depende de decisão.', 'decisions': ['DN-021']}
    if not enrollment.class_group.active:
        return {**result, 'reason': 'Turma inativa.'}
    if enrollment.kind == 'trial':
        if not enrollment.class_group.allows_trial:
            return {**result, 'status':'blocked', 'reason':'A turma não permite participação experimental.'}
        return {**result, 'eligible': None, 'status': 'decision_required', 'reason': 'Duração, quantidade e condições experimentais aguardam política detalhada; aprovação por ID isolado não define participação.', 'decisions': ['DN-013']}
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
    ('DN-001', 'Permissões finais', 'Matriz final e concessão de funções.'),
    ('DN-002', 'Múltiplas funções', 'Aprovação substitui funções na Base; reabertura e desativação definitiva pendentes.'),
    ('DN-003', 'Identificação', 'CPF, e-mail compartilhado e resolução de identidade.'),
    ('DN-004', 'Planos e cobertura', 'Geração automática, vigência e liberação acadêmica indisponíveis.'),
    ('DN-005', 'Geração de cobranças', 'Sem periodicidade, horizonte ou proporcionalidade arbitrária.'),
    ('DN-006', 'Cobrança esperada ausente', 'Elegibilidade indeterminada e pendência explícita.'),
    ('DN-007', 'Bolsas e descontos', 'Valor zero e benefícios indisponíveis.'),
    ('DN-008', 'Pagamentos divergentes', 'Somente baixa integral exata; parciais e excedentes indisponíveis.'),
    ('DN-009', 'Inadimplência', 'Base sem carência; multas, juros e exceções não definidos.'),
    ('DN-010', 'Suspensão e trancamento', 'Transições indisponíveis.'),
    ('DN-011', 'Cancelamento e renovação', 'Somente cancelamento presente; devolução, reativação e renovação indisponíveis.'),
    ('DN-012', 'Capacidade e conflitos', 'Sem homologação da oferta/capacidade ou exceções automáticas.'),
    ('DN-013', 'Experimental', 'Participação experimental depende de política.'),
    ('DN-014', 'Chamada', 'Gravação, retroatividade e reabertura dependem de política.'),
    ('DN-015', 'Reposições', 'Uma aula por turma/data na Base; reposições indisponíveis.'),
    ('DN-016', 'Repasse', 'Sem cálculo final nem atribuição de base por substituições.'),
    ('DN-017', 'Indicadores financeiros', 'Extratos identificam data de recebimento/vencimento; homologação do regime pendente.'),
    ('DN-018', 'Frequência e evasão', 'Sem metas, percentuais ou alertas arbitrários.'),
    ('DN-019', 'Conversão e ocupação', 'Contagens brutas separadas; taxas e ocupação dependem de definição.'),
    ('DN-020', 'Dados e comunicação', 'Dados sensíveis e automação de contato indisponíveis.'),
    ('DN-021', 'Arquivamento e transferência', 'Transferências indisponíveis; arquivamento exige proposta aprovada.'),
    ('DN-022', 'Capacidade operacional', 'Carga, recuperação e homologação institucional pendentes.'),
]
