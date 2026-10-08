export const money = (value: unknown) =>
  value === null || value === undefined
    ? "—"
    : new Intl.NumberFormat("pt-BR", {
        style: "currency",
        currency: "BRL",
      }).format(Number(value));
export const date = (value: unknown) => {
  if (!value) return "—";
  const text = String(value).slice(0, 10);
  const parts = text.split("-");
  return parts.length === 3 ? `${parts[2]}/${parts[1]}/${parts[0]}` : text;
};
export const today = () =>
  new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/Sao_Paulo",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());
export const monthStart = () => `${today().slice(0, 7)}-01`;
export const timestamp = (value: unknown) =>
  value
    ? new Intl.DateTimeFormat("pt-BR", {
        dateStyle: "short",
        timeStyle: "short",
        timeZone: "America/Sao_Paulo",
      }).format(new Date(String(value)))
    : "—";
export const roleNames: Record<string, string> = {
  secretary: "Secretaria",
  coordinator: "Coordenação",
  instructor: "Instrutor",
  communication: "Comunicação",
};
export const labels: Record<string, string> = {
  pending: "Pendente",
  approved: "Aprovado",
  rejected: "Rejeitado",
  new: "Novo",
  contacting: "Em atendimento",
  waiting: "Aguardando retorno",
  converted: "Convertido",
  not_converted: "Não convertido",
  regular: "Regular",
  cancelled: "Cancelada",
  monthly: "Mensal",
  quarterly: "Trimestral",
  yearly: "Anual",
  trial: "Experimental",
  tuition: "Mensalidade",
  enrollment_fee: "Taxa de matrícula",
  extra: "Extra",
  open: "Em aberto",
  paid: "Quitada",
  overdue: "Vencida",
  scheduled: "Agendada",
  completed: "Realizada",
  eligible: "Liberada",
  blocked: "Bloqueada",
  decision_required: "Decisão pendente",
};
export const label = (value: unknown) =>
  labels[String(value)] || String(value ?? "—");

// Codes emitted by core.audit.record; transport and filtering keep these keys.
export const auditActions: Record<string, string> = {
  "access.request": "Solicitação de acesso",
  "access.approve": "Acesso aprovado",
  "access.reject": "Acesso rejeitado",
  "access.add_role": "Função adicionada",
  "access.remove_role": "Função removida",
  "session.login": "Entrada no sistema",
  "student.create": "Aluno cadastrado",
  "student.update": "Cadastro de aluno atualizado",
  "lead.create": "Lead cadastrado",
  "lead.update": "Lead atualizado",
  "lead.convert": "Lead convertido em aluno",
  "modality.create": "Modalidade cadastrada",
  "modality.update": "Modalidade atualizada",
  "instructor.create": "Instrutor cadastrado",
  "instructor.update": "Cadastro de instrutor atualizado",
  "classgroup.create": "Turma cadastrada",
  "classgroup.update": "Turma atualizada",
  "enrollment.created": "Matrícula registrada",
  "enrollment.cancelled": "Matrícula cancelada",
  "charge.created": "Cobrança registrada",
  "payment.received": "Recebimento registrado",
  "attendance.completed": "Chamada concluída",
  "lesson.created": "Aula agendada",
  "lesson.updated": "Aula atualizada",
};
export const auditTargets: Record<string, string> = {
  "core.user": "Conta de acesso",
  "core.student": "Aluno",
  "core.lead": "Lead",
  "core.modality": "Modalidade",
  "core.instructor": "Instrutor",
  "core.classgroup": "Turma",
  "billing.enrollment": "Matrícula",
  "billing.charge": "Cobrança",
  "billing.payment": "Recebimento",
  "academic.lesson": "Aula",
};
export const auditActionLabel = (value: unknown) =>
  auditActions[String(value)] || "Evento registrado";
export const auditTargetLabel = (value: unknown) =>
  auditTargets[String(value)] || "Registro";
