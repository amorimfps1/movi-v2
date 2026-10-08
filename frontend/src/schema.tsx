import type { ReactNode } from "react";
import type { RecordData } from "./types";
import type { FieldSpec, Option } from "./forms";
import { Badge } from "./ui";
import { date, money, label, today } from "./format";
export type Column = {
  key: string;
  label: string;
  render?: (row: RecordData) => ReactNode;
};
export type ResourceSpec = {
  searchPlaceholder?: string;
  title: string;
  singular: string;
  slug: string;
  endpoint: string;
  description: string;
  fields: FieldSpec[];
  columns: Column[];
  filters?: { key: string; label: string; options: Option[] }[];
  filterFields?: FieldSpec[];
  archive?: string;
  readOnly?: boolean;
  editable?: boolean;
};
export const studentSpec: ResourceSpec = {
  title: "Alunos",
  singular: "aluno",
  slug: "alunos",
  endpoint: "students/",
  description: "Cadastre alunos e acompanhe suas matrículas.",
  archive: "archived",
  fields: [
    { key: "name", label: "Nome completo", required: true, wide: true },
    { key: "cpf", label: "CPF", hint: "Opcional. Informe um CPF válido." },
    { key: "birth_date", label: "Data de nascimento", type: "date" },
    { key: "email", label: "E-mail", type: "email" },
    { key: "phone", label: "Telefone", type: "tel" },
    { key: "address", label: "Endereço", wide: true },
    { key: "notes", label: "Observações", type: "textarea", wide: true },
  ],
  columns: [
    { key: "name", label: "Aluno" },
    {
      key: "email",
      label: "Contato",
      render: (row) => (
        <span>
          {String(row.email || "E-mail não informado")}
          <small>{String(row.phone || "Telefone não informado")}</small>
        </span>
      ),
    },
    {
      key: "cpf",
      label: "CPF",
      render: (row) => String(row.cpf || "Não informado"),
    },
    {
      key: "archived",
      label: "Cadastro",
      render: (row) => (
        <Badge value={row.archived ? "cancelled" : "regular"}>
          {row.archived ? "Arquivado" : "Em acompanhamento"}
        </Badge>
      ),
    },
  ],
  filters: [
    {
      key: "archived",
      label: "Cadastro",
      options: [
        { value: "false", label: "Em acompanhamento" },
        { value: "true", label: "Arquivados" },
      ],
    },
  ],
};
export const enrollmentFields: FieldSpec[] = [
  {
    key: "student",
    label: "Aluno",
    type: "select",
    lookup: "students/",
    required: true,
    wide: true,
  },
  {
    key: "class_group",
    label: "Turma",
    type: "select",
    lookup: "classes/",
    required: true,
    wide: true,
  },
  {
    key: "start_date",
    label: "Início",
    type: "date",
    required: true,
    default: today(),
  },
  {
    key: "plan",
    label: "Plano",
    type: "select",
    required: true,
    default: "monthly",
    options: [
      { value: "monthly", label: "Mensal" },
      { value: "quarterly", label: "Trimestral" },
      { value: "yearly", label: "Anual" },
    ],
  },
  {
    key: "amount",
    label: "Valor contratado (R$)",
    type: "decimal",
    required: true,
    hint: "Periodicidade e cobertura dependem de política aprovada.",
  },
  {
    key: "kind",
    label: "Tipo",
    type: "select",
    default: "regular",
    required: true,
    options: [
      { value: "regular", label: "Regular" },
      { value: "trial", label: "Experimental · requer DN-013" },
    ],
  },
];
export const enrollmentSpec: ResourceSpec = {
  title: "Matrículas",
  singular: "matrícula",
  slug: "matriculas",
  endpoint: "enrollments/",
  filterFields: [
    { key: "class_group", label: "Turma", type: "select", lookup: "classes/" },
  ],
  description: "O vínculo com a turma e as condições de cada contrato.",
  editable: false,
  fields: enrollmentFields,
  columns: [
    { key: "student_name", label: "Aluno" },
    { key: "class_name", label: "Turma" },
    {
      key: "start_date",
      label: "Início",
      render: (row) => date(row.start_date),
    },
    { key: "plan", label: "Plano", render: (row) => label(row.plan) },
    { key: "amount", label: "Valor", render: (row) => money(row.amount) },
    {
      key: "eligibility",
      label: "Participação",
      render: (row) => (
        <Badge
          value={(row.eligibility as { status: string })?.status || "pending"}
        />
      ),
    },
  ],
  filters: [
    {
      key: "administrative_status",
      label: "Situação administrativa",
      options: [
        { value: "regular", label: "Regular" },
        { value: "cancelled", label: "Cancelada" },
      ],
    },
  ],
};
const activityOptions = [
  { value: "true", label: "Ativos" },
  { value: "false", label: "Inativos" },
];
export const weekdayOptions = [
  { value: 0, label: "Segunda" },
  { value: 1, label: "Terça" },
  { value: 2, label: "Quarta" },
  { value: 3, label: "Quinta" },
  { value: 4, label: "Sexta" },
  { value: 5, label: "Sábado" },
  { value: 6, label: "Domingo" },
];
export const leadSpec: ResourceSpec = {
  title: "Leads",
  singular: "lead",
  slug: "interessados",
  endpoint: "leads/",
  filterFields: [
    { key: "source", label: "Origem do contato" },
    {
      key: "interests",
      label: "Interesse em modalidade",
      type: "select",
      lookup: "modalities/",
    },
  ],
  description: "Acolha o primeiro contato e acompanhe cada próximo passo.",
  fields: [
    { key: "name", label: "Nome completo", required: true, wide: true },
    {
      key: "cpf",
      label: "CPF",
      hint: "Opcional. A identificação será validada na conversão.",
    },
    { key: "email", label: "E-mail", type: "email" },
    { key: "phone", label: "Telefone", type: "tel" },
    { key: "source", label: "Origem do contato" },
    {
      key: "status",
      label: "Acompanhamento",
      type: "select",
      default: "new",
      required: true,
      options: ["new", "contacting", "waiting", "not_converted"].map(
        (value) => ({ value, label: label(value) }),
      ),
    },
    {
      key: "interests",
      label: "Modalidades de interesse",
      type: "multi",
      lookup: "modalities/",
      wide: true,
    },
    {
      key: "notes",
      label: "Anotações de acompanhamento",
      type: "textarea",
      wide: true,
    },
  ],
  columns: [
    { key: "name", label: "Lead" },
    {
      key: "email",
      label: "Contato",
      render: (row) => (
        <span>
          {String(row.email || "E-mail não informado")}
          <small>{String(row.phone || "Telefone não informado")}</small>
        </span>
      ),
    },
    { key: "source", label: "Origem" },
    {
      key: "status",
      label: "Acompanhamento",
      render: (row) => <Badge value={row.status} />,
    },
  ],
  filters: [
    {
      key: "status",
      label: "Situação",
      options: [
        "new",
        "contacting",
        "waiting",
        "converted",
        "not_converted",
      ].map((value) => ({ value, label: label(value) })),
    },
  ],
};
export const modalitySpec: ResourceSpec = {
  title: "Modalidades",
  singular: "modalidade",
  slug: "modalidades",
  endpoint: "modalities/",
  description: "Modalidades disponíveis para as matrículas dos alunos.",
  archive: "active",
  fields: [
    { key: "name", label: "Nome da modalidade", required: true, wide: true },
    { key: "area", label: "Área" },
    {
      key: "default_price",
      label: "Valor padrão (R$)",
      type: "decimal",
      required: true,
    },
    { key: "active", label: "Modalidade ativa", type: "check", default: true },
  ],
  columns: [
    { key: "name", label: "Modalidade" },
    { key: "area", label: "Área" },
    {
      key: "default_price",
      label: "Valor padrão",
      render: (row) => money(row.default_price),
    },
    {
      key: "active",
      label: "Situação",
      render: (row) => (
        <Badge value={row.active ? "regular" : "cancelled"}>
          {row.active ? "Ativa" : "Inativa"}
        </Badge>
      ),
    },
  ],
  filters: [{ key: "active", label: "Situação", options: activityOptions }],
};
export const instructorSpec: ResourceSpec = {
  title: "Instrutores",
  singular: "instrutor",
  slug: "instrutores",
  endpoint: "instructors/",
  description: "Quem compartilha conhecimento e conduz os encontros.",
  archive: "active",
  fields: [
    { key: "name", label: "Nome completo", required: true, wide: true },
    { key: "email", label: "E-mail", type: "email" },
    { key: "phone", label: "Telefone", type: "tel" },
    {
      key: "specialties",
      label: "Especialidades",
      type: "multi",
      lookup: "modalities/",
      wide: true,
    },
    { key: "active", label: "Instrutor ativo", type: "check", default: true },
  ],
  columns: [
    { key: "name", label: "Instrutor" },
    {
      key: "email",
      label: "Contato",
      render: (row) => (
        <span>
          {String(row.email || "E-mail não informado")}
          <small>{String(row.phone || "Telefone não informado")}</small>
        </span>
      ),
    },
    {
      key: "user",
      label: "Conta vinculada",
      render: (row) => (row.user ? `Conta #${row.user}` : "Sem vínculo"),
    },
    {
      key: "active",
      label: "Situação",
      render: (row) => (
        <Badge value={row.active ? "regular" : "cancelled"}>
          {row.active ? "Ativo" : "Inativo"}
        </Badge>
      ),
    },
  ],
  filters: [{ key: "active", label: "Situação", options: activityOptions }],
};
export const classSpec: ResourceSpec = {
  title: "Turmas",
  singular: "turma",
  slug: "turmas",
  endpoint: "classes/",
  description: "Organize a oferta, os responsáveis e os horários de encontro.",
  archive: "active",
  fields: [
    { key: "name", label: "Nome da turma", required: true, wide: true },
    {
      key: "modality",
      label: "Modalidade",
      type: "select",
      lookup: "modalities/",
      required: true,
    },
    {
      key: "instructor",
      label: "Instrutor responsável",
      type: "select",
      lookup: "instructors/",
      required: true,
    },
    {
      key: "weekdays",
      label: "Dias da semana",
      type: "multi",
      options: weekdayOptions,
      wide: true,
    },
    {
      key: "start_time",
      label: "Horário de início",
      type: "time",
      required: true,
    },
    {
      key: "end_time",
      label: "Horário de término",
      type: "time",
      required: true,
    },
    { key: "room", label: "Sala / local" },
    { key: "age_range", label: "Faixa etária" },
    {
      key: "capacity",
      label: "Capacidade",
      type: "number",
      required: true,
      min: 1,
    },
    { key: "active", label: "Turma ativa", type: "check", default: true },
    {
      key: "allows_trial",
      label: "Permitir experimental",
      type: "check",
      hint: "A criação de matrícula experimental aguarda DN-013.",
    },
  ],
  columns: [
    {
      key: "name",
      label: "Turma",
      render: (row) => (
        <span>
          {String(row.name)}
          <small>{String(row.modality_name || "")}</small>
        </span>
      ),
    },
    { key: "instructor_name", label: "Instrutor" },
    {
      key: "weekdays",
      label: "Encontros",
      render: (row) => (
        <span>
          {(row.weekdays as number[])
            .map((day) => weekdayOptions[day]?.label.slice(0, 3))
            .join(" · ")}
          <small>
            {String(row.start_time).slice(0, 5)} –{" "}
            {String(row.end_time).slice(0, 5)}
          </small>
        </span>
      ),
    },
    { key: "room", label: "Local" },
    {
      key: "active",
      label: "Situação",
      render: (row) => (
        <Badge value={row.active ? "regular" : "cancelled"}>
          {row.active ? "Ativa" : "Inativa"}
        </Badge>
      ),
    },
  ],
  filters: [{ key: "active", label: "Situação", options: activityOptions }],
};
export const lessonSpec: ResourceSpec = {
  title: "Aulas e chamada",
  singular: "aula",
  slug: "aulas",
  endpoint: "lessons/",
  filterFields: [
    { key: "date", label: "Data da aula", type: "date" },
    { key: "class_group", label: "Turma", type: "select", lookup: "classes/" },
  ],
  description:
    "Cada encontro no calendário. Cada presença registrada com cuidado.",
  fields: [
    {
      key: "class_group",
      label: "Turma",
      type: "select",
      lookup: "classes/",
      required: true,
      wide: true,
    },
    {
      key: "date",
      label: "Data do encontro",
      type: "date",
      default: today(),
      required: true,
    },
    {
      key: "assigned_instructor",
      label: "Substituto (opcional)",
      type: "select",
      lookup: "instructors/",
      nullable: true,
      hint: "Sem substituto, o responsável é o instrutor da turma.",
    },
    {
      key: "status",
      label: "Situação da aula",
      type: "select",
      default: "scheduled",
      options: [
        { value: "scheduled", label: "Agendada" },
        { value: "cancelled", label: "Cancelada" },
      ],
    },
    { key: "notes", label: "Observações", type: "textarea", wide: true },
  ],
  columns: [
    { key: "class_name", label: "Turma" },
    { key: "date", label: "Encontro", render: (row) => date(row.date) },
    { key: "instructor_name", label: "Responsável" },
    {
      key: "status",
      label: "Situação",
      render: (row) => <Badge value={row.status} />,
    },
  ],
  filters: [
    {
      key: "status",
      label: "Situação",
      options: ["scheduled", "completed", "cancelled"].map((value) => ({
        value,
        label: label(value),
      })),
    },
  ],
};
export const chargeFields: FieldSpec[] = [
  {
    key: "enrollment",
    label: "Matrícula",
    type: "select",
    lookup: "enrollments/",
    optionLabel: (row) =>
      `${row.student_name} · ${row.class_name} (#${row.id})`,
    required: true,
    wide: true,
  },
  {
    key: "category",
    label: "Finalidade",
    type: "select",
    required: true,
    default: "tuition",
    options: ["tuition", "enrollment_fee", "extra"].map((value) => ({
      value,
      label: label(value),
    })),
  },
  {
    key: "competence",
    label: "Competência",
    type: "date",
    hint: "Para mensalidade, selecione o primeiro dia do mês.",
    default: `${today().slice(0, 7)}-01`,
    nullable: true,
  },
  {
    key: "due_date",
    label: "Vencimento",
    type: "date",
    required: true,
    default: today(),
  },
  {
    key: "amount",
    label: "Valor devido (R$)",
    type: "decimal",
    required: true,
  },
  { key: "description", label: "Descrição", type: "textarea", wide: true },
];
export const chargeSpec: ResourceSpec = {
  title: "Cobranças",
  singular: "cobrança",
  slug: "cobrancas",
  endpoint: "charges/",
  filterFields: [
    { key: "start", label: "Vencimento a partir de", type: "date" },
    { key: "end", label: "Vencimento até", type: "date" },
    { key: "competence", label: "Competência", type: "date" },
    { key: "enrollment", label: "Matrícula (número)", type: "number", min: 1 },
  ],
  description:
    "Obrigações registradas e seus recebimentos, sem confundir previsto com recebido.",
  editable: false,
  fields: chargeFields,
  columns: [
    {
      key: "student_name",
      label: "Aluno",
      render: (row) => (
        <span>
          {String(row.student_name)}
          <small>{String(row.class_name)}</small>
        </span>
      ),
    },
    {
      key: "category",
      label: "Finalidade",
      render: (row) => label(row.category),
    },
    {
      key: "due_date",
      label: "Vencimento",
      render: (row) => date(row.due_date),
    },
    { key: "amount", label: "Devido", render: (row) => money(row.amount) },
    {
      key: "received",
      label: "Recebido",
      render: (row) => money(row.received),
    },
    {
      key: "status",
      label: "Situação",
      render: (row) => <Badge value={row.status} />,
    },
  ],
  filters: [
    {
      key: "status",
      label: "Situação",
      options: ["open", "paid", "overdue"].map((value) => ({
        value,
        label: label(value),
      })),
    },
    {
      key: "category",
      label: "Finalidade",
      options: ["tuition", "enrollment_fee", "extra"].map((value) => ({
        value,
        label: label(value),
      })),
    },
  ],
};
export const paymentMethods = [
  { value: "pix", label: "Pix" },
  { value: "cash", label: "Dinheiro" },
  { value: "card", label: "Cartão" },
  { value: "transfer", label: "Transferência" },
  { value: "other", label: "Outra forma" },
];
export const paymentSpec: ResourceSpec = {
  title: "Recebimentos",
  singular: "recebimento",
  slug: "recebimentos",
  endpoint: "payments/",
  filterFields: [
    { key: "start", label: "Recebimento a partir de", type: "date" },
    { key: "end", label: "Recebimento até", type: "date" },
    {
      key: "charge__enrollment",
      label: "Matrícula (número)",
      type: "number",
      min: 1,
    },
  ],
  description: "Valores efetivamente registrados, pela data de recebimento.",
  readOnly: true,
  fields: [],
  columns: [
    { key: "student_name", label: "Aluno" },
    {
      key: "paid_on",
      label: "Recebimento em",
      render: (row) => date(row.paid_on),
    },
    {
      key: "category",
      label: "Finalidade",
      render: (row) => label(row.category),
    },
    { key: "amount", label: "Recebido", render: (row) => money(row.amount) },
    {
      key: "method",
      label: "Forma",
      render: (row) =>
        paymentMethods.find((method) => method.value === row.method)?.label ||
        String(row.method),
    },
  ],
  filters: [{ key: "method", label: "Forma", options: paymentMethods }],
};
