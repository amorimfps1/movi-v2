import { useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { Pencil, ChevronLeft, ArrowUpRight, UserRoundPlus } from "lucide-react";
import { useQueries, useQueryClient, useQuery } from "@tanstack/react-query";
import { useApi } from "./query";
import type { ResourceSpec } from "./schema";
import type { RecordData, Page } from "./types";
import { optionsFor, post } from "./api";
import { RecordForm } from "./forms";
import {
  Button,
  PageTitle,
  Loading,
  ErrorNotice,
  Notice,
  Modal,
  Field,
  Journey,
  Badge,
  Empty,
} from "./ui";
import { date, money, label } from "./format";
import { useAuth, isAdmin } from "./auth";
export function RecordDetail({ spec }: { spec: ResourceSpec }) {
  const { user } = useAuth();
  const admin = isAdmin(user);
  const { id } = useParams();
  const query = useApi<RecordData>(`${spec.endpoint}${id}/`);
  const [editing, setEditing] = useState(false);
  const [converting, setConverting] = useState(false);
  const [success, setSuccess] = useState("");
  const paths = [
    ...new Set(
      spec.fields
        .map((field) => field.lookup)
        .filter((value): value is string => !!value),
    ),
  ];
  const lookups = useQueries({
    queries: (admin ? paths : []).map((path) => ({
      queryKey: ["options", path],
      queryFn: () => optionsFor(path),
      retry: false,
    })),
  });
  const classes = useApi<Page<RecordData>>(
    `lessons/?class_group=${id}`,
    spec.endpoint === "classes/",
  );
  if (query.isPending) return <Loading />;
  if (query.error) return <ErrorNotice error={query.error} />;
  if (!query.data) return null;
  const row = query.data;
  const show = (key: string) => {
    const field = spec.fields.find((item) => item.key === key)!;
    const value = row[key];
    if (key === "modality" && row.modality_name)
      return String(row.modality_name);
    if (key === "instructor" && row.instructor_name)
      return String(row.instructor_name);
    if (value === null || value === undefined || value === "")
      return "Não informado";
    if (field.type === "date") return date(value);
    if (field.type === "time") return String(value).slice(0, 5);
    if (field.type === "decimal") return money(value);
    if (field.type === "check") return value ? "Sim" : "Não";
    if (field.lookup || field.options) {
      const options =
        field.options ??
        (lookups[paths.indexOf(field.lookup ?? "")]?.data ?? []).map(
          (item) => ({
            value: Number(item.id),
            label: field.optionLabel?.(item) ?? String(item.name || item.email),
          }),
        );
      const values = Array.isArray(value) ? value : [value];
      return (
        values
          .map(
            (item) =>
              options.find((option) => String(option.value) === String(item))
                ?.label || `#${item}`,
          )
          .join(", ") || "Nenhuma seleção"
      );
    }
    return label(value);
  };
  return (
    <>
      <Link className="back-link" to={`/${spec.slug}`}>
        <ChevronLeft size={16} />
        {spec.title}
      </Link>
      <PageTitle
        eyebrow={`FICHA · #${id}`}
        title={String(row.name || row.student_name || spec.title)}
        description={
          spec.endpoint === "classes/"
            ? String(row.modality_name || "")
            : spec.description
        }
        actions={
          !spec.readOnly &&
          spec.editable !== false && (
            <Button variant="secondary" onClick={() => setEditing(true)}>
              <Pencil size={17} />
              Editar {spec.singular}
            </Button>
          )
        }
      />
      {success && <Notice tone="success">{success}</Notice>}
      {spec.endpoint === "leads/" && <Journey step={row.student ? 1 : 0} />}
      <div className="detail-grid">
        <section className="sheet">
          <div className="section-heading">
            <h2>Informações do cadastro</h2>
            {"active" in row && (
              <Badge value={row.active ? "regular" : "cancelled"}>
                {row.active ? "Ativo" : "Inativo"}
              </Badge>
            )}
          </div>
          <dl className="details-list">
            {spec.fields.map((field) => (
              <div key={field.key}>
                <dt>{field.label.replace(" (R$)", "")}</dt>
                <dd
                  className={field.type === "textarea" ? "preserve-lines" : ""}
                >
                  {show(field.key)}
                </dd>
              </div>
            ))}
          </dl>
          {lookups.some((item) => item.error) && (
            <div className="section-pad">
              <ErrorNotice error={lookups.find((item) => item.error)?.error} />
            </div>
          )}
        </section>
        <div>
          {spec.endpoint === "leads/" && (
            <section className="sheet">
              <div className="section-heading">
                <h2>Próximo passo</h2>
                <Badge value={row.status} />
              </div>
              {row.student ? (
                <div className="section-pad">
                  <Notice tone="success">
                    Lead vinculado a um aluno. A matrícula e a participação
                    continuam etapas distintas.
                  </Notice>
                  <Link
                    className="button button--primary"
                    to={`/alunos/${row.student}`}
                  >
                    Abrir cadastro do aluno <ArrowUpRight size={17} />
                  </Link>
                </div>
              ) : (
                <Empty
                  title="Do lead ao cadastro do aluno"
                  description="A conversão identifica um aluno existente ou cria seu cadastro. Não cria matrícula nem libera participação."
                  action={
                    <Button onClick={() => setConverting(true)}>
                      <UserRoundPlus size={18} />
                      Converter em aluno
                    </Button>
                  }
                />
              )}
            </section>
          )}
          {spec.endpoint === "classes/" && (
            <section className="sheet">
              <div className="section-heading">
                <h2>Encontros desta turma</h2>
                <Link className="text-link" to={`/aulas?class_group=${id}`}>
                  Consultar agenda <ArrowUpRight size={17} />
                </Link>
              </div>
              {classes.isPending ? (
                <Loading />
              ) : classes.error ? (
                <ErrorNotice error={classes.error} />
              ) : !classes.data?.results.length ? (
                <Empty
                  title="O próximo encontro começa aqui"
                  description="Agende as aulas na rotina de aulas e chamada."
                />
              ) : (
                <div className="enrollment-list">
                  {classes.data.results.map((lesson) => (
                    <Link
                      className="enrollment-item"
                      key={lesson.id}
                      to={`/aulas/${lesson.id}`}
                    >
                      <div>
                        <h3>{date(lesson.date)}</h3>
                        <p>{String(lesson.instructor_name)}</p>
                      </div>
                      <Badge value={lesson.status} />
                    </Link>
                  ))}
                </div>
              )}
              <div className="section-pad">
                <Notice tone="warning">
                  Capacidade, conflitos de sala e de instrutor seguem políticas
                  institucionais ainda pendentes. DN-012.
                </Notice>
              </div>
            </section>
          )}
          {spec.endpoint === "modalities/" && (
            <section className="operation-note">
              <p className="eyebrow">DA MODALIDADE AO ENCONTRO</p>
              <h2>Organize uma oferta</h2>
              <p className="muted">
                O valor padrão pode orientar novas matrículas. Contratos
                existentes preservam suas condições.
              </p>
              <Link className="button button--secondary" to="/turmas">
                Consultar turmas <ArrowUpRight size={17} />
              </Link>
            </section>
          )}
          {spec.endpoint === "instructors/" && (
            <section className="operation-note">
              <p className="eyebrow">VÍNCULO PROFISSIONAL</p>
              <h2>
                {row.user ? "Conta vinculada" : "Acesso ainda não vinculado"}
              </h2>
              <p className="muted">
                A função de instrutor exige vínculo inequívoco entre a conta e
                este cadastro profissional.
              </p>
              <Link className="button button--secondary" to="/acessos">
                Gerir contas e perfis <ArrowUpRight size={17} />
              </Link>
            </section>
          )}
        </div>
      </div>
      {editing && (
        <RecordForm
          title={`Editar ${spec.singular}`}
          endpoint={spec.endpoint}
          fields={spec.fields}
          record={row}
          onClose={() => setEditing(false)}
          onSaved={() => setSuccess("Cadastro atualizado com sucesso.")}
        />
      )}
      {converting && (
        <LeadConversion lead={row} onClose={() => setConverting(false)} />
      )}
    </>
  );
}
function LeadConversion({
  lead,
  onClose,
}: {
  lead: RecordData;
  onClose: () => void;
}) {
  const [student, setStudent] = useState("");
  const [reason, setReason] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<unknown>();
  const options = useQuery({
    queryKey: ["options", "students/"],
    queryFn: () => optionsFor("students/"),
    retry: false,
  });
  const navigate = useNavigate();
  const client = useQueryClient();
  return (
    <Modal
      open
      title="Converter lead em aluno"
      onClose={() => !pending && onClose()}
    >
      <form
        onSubmit={async (event) => {
          event.preventDefault();
          setPending(true);
          setError(undefined);
          try {
            const result = await post<RecordData>(
              `leads/${lead.id}/convert/`,
              student ? { student_id: Number(student), reason } : {},
            );
            await client.invalidateQueries();
            onClose();
            if (result.student) navigate(`/alunos/${result.student}`);
          } catch (err) {
            setError(err);
          } finally {
            setPending(false);
          }
        }}
      >
        <Notice>
          Confira a identidade de <strong>{String(lead.name)}</strong>. O
          sistema verifica CPF e e-mail antes de criar outro cadastro. Conflitos
          exigem resolução explícita.
        </Notice>
        {options.isPending ? (
          <Loading />
        ) : options.error ? (
          <ErrorNotice error={options.error} />
        ) : (
          <div className="form-grid">
            <Field label="Identificação do aluno" wide>
              <select
                value={student}
                onChange={(event) => setStudent(event.target.value)}
              >
                <option value="">
                  Verificar correspondência automaticamente
                </option>
                {options.data?.map((row) => (
                  <option key={Number(row.id)} value={Number(row.id)}>
                    {String(row.name)} ·{" "}
                    {String(row.cpf || row.email || `#${row.id}`)}
                  </option>
                ))}
              </select>
            </Field>
            {student && (
              <Field
                label="Justificativa da identidade selecionada"
                wide
                hint="A resolução é registrada e pode depender de aprovação institucional."
              >
                <textarea
                  value={reason}
                  onChange={(event) => setReason(event.target.value)}
                  required
                  rows={3}
                />
              </Field>
            )}
          </div>
        )}
        <p className="period-note">
          Esta confirmação cria ou vincula somente o aluno. Matrícula, cobrança
          e participação são etapas separadas.
        </p>
        <ErrorNotice error={error} />
        <div className="form-actions">
          <Button
            type="button"
            variant="secondary"
            onClick={onClose}
            disabled={pending}
          >
            Voltar
          </Button>
          <Button
            type="submit"
            disabled={pending || options.isPending || !!options.error}
          >
            {pending ? "Convertendo…" : "Confirmar conversão"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
