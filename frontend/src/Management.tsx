import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ShieldCheck,
  Plus,
  UserRoundMinus,
  ChevronLeft,
  Check,
  X,
} from "lucide-react";
import type { RecordData, User, Role } from "./types";
import type { ResourceSpec } from "./schema";
import { useAuth } from "./auth";
import { useApi } from "./query";
import { post, optionsFor } from "./api";
import { ResourceList } from "./resources";
import {
  PageTitle,
  Button,
  Notice,
  ErrorNotice,
  Loading,
  Badge,
  Modal,
  Field,
} from "./ui";
import { ActionForm } from "./forms";
import {
  roleNames,
  timestamp,
  auditActions,
  auditTargets,
  auditActionLabel,
  auditTargetLabel,
} from "./format";
const userSpec: ResourceSpec = {
  title: "Contas e perfis",
  singular: "conta",
  slug: "acessos",
  endpoint: "users/",
  description:
    "Autorizações revisadas por pessoas, com vínculo e histórico preservados.",
  readOnly: true,
  fields: [],
  columns: [
    {
      key: "email",
      label: "Conta",
      render: (row) => (
        <span>
          {String(row.first_name)} {String(row.last_name)}
          <small>{String(row.email)}</small>
        </span>
      ),
    },
    {
      key: "roles",
      label: "Funções",
      render: (row) => (
        <span>
          {(row.roles as string[]).map((role) => roleNames[role]).join(" · ") ||
            "Sem função atribuída"}
        </span>
      ),
    },
    {
      key: "access_status",
      label: "Situação",
      render: (row) => <Badge value={row.access_status} />,
    },
  ],
  filters: [
    {
      key: "access_status",
      label: "Autorização",
      options: [
        { value: "pending", label: "Pendentes" },
        { value: "approved", label: "Aprovadas" },
        { value: "rejected", label: "Rejeitadas" },
      ],
    },
  ],
};
export function AccessList() {
  return (
    <ResourceList
      spec={userSpec}
      beforeList={
        <Notice>
          Solicitações começam pendentes. Aprovação exige ao menos uma função.
          Alterações de autorização e vínculos profissionais ficam registradas
          no histórico.
        </Notice>
      }
    />
  );
}
export function AccessDetail() {
  const { id } = useParams();
  const { user: actor } = useAuth();
  const query = useApi<User>(`users/${id}/`);
  const [action, setAction] = useState<
    "approve" | "add-role" | "remove-role" | "reject" | null
  >(null);
  const [success, setSuccess] = useState("");
  if (query.isPending) return <Loading />;
  if (query.error) return <ErrorNotice error={query.error} />;
  if (!query.data) return null;
  const user = query.data;
  const self = user.id === actor?.id;
  return (
    <>
      <Link className="back-link" to="/acessos">
        <ChevronLeft size={16} />
        Todas as contas
      </Link>
      <PageTitle
        eyebrow={`ACESSO · CONTA #${id}`}
        title={`${user.first_name} ${user.last_name}`.trim() || user.email}
        description={user.email}
      />
      {success && <Notice tone="success">{success}</Notice>}
      {self && (
        <Notice>
          Você está consultando a própria conta. A alteração da própria
          autorização é impedida nas rotinas comuns.
        </Notice>
      )}
      <div className="detail-grid">
        <section className="sheet">
          <div className="section-heading">
            <h2>Autorização atual</h2>
            <Badge value={user.access_status} />
          </div>
          <dl className="details-list">
            <div>
              <dt>Funções atribuídas</dt>
              <dd>
                {user.roles.map((role) => roleNames[role]).join(" · ") ||
                  "Nenhuma função atribuída"}
              </dd>
            </div>
            <div>
              <dt>E-mail de acesso</dt>
              <dd>{user.email}</dd>
            </div>
            <div>
              <dt>Identificador da conta</dt>
              <dd>#{user.id}</dd>
            </div>
          </dl>
        </section>
        <section className="sheet">
          <div className="section-heading">
            <h2>Decisões de acesso</h2>
            <ShieldCheck size={20} />
          </div>
          <div className="access-actions">
            {user.access_status === "pending" && (
              <Button disabled={self} onClick={() => setAction("approve")}>
                <Check size={17} />
                Aprovar solicitação
              </Button>
            )}
            <Button
              variant="secondary"
              disabled={self}
              onClick={() => setAction("add-role")}
            >
              <Plus size={17} />
              Adicionar função
            </Button>
            {user.roles.length > 0 && (
              <Button
                variant="secondary"
                disabled={self}
                onClick={() => setAction("remove-role")}
              >
                <UserRoundMinus size={17} />
                Remover função
              </Button>
            )}
            <Button
              variant="secondary"
              disabled={self || user.access_status === "rejected"}
              onClick={() => setAction("reject")}
            >
              <X size={17} />
              Rejeitar acesso
            </Button>
            <p className="period-note">
              Aprovar substitui a lista de funções. Adicionar função é uma
              operação distinta. Remover a última função devolve a conta à
              situação pendente.
            </p>
            <Link
              className="text-link"
              to={`/auditoria?target_type=core.user&target_id=${user.id}`}
            >
              Consultar histórico desta conta
            </Link>
          </div>
        </section>
      </div>
      {action === "reject" && (
        <ActionForm
          title="Rejeitar acesso"
          endpoint={`users/${id}/reject/`}
          description="A conta ficará rejeitada e perderá as funções atuais. Registre o motivo da decisão."
          fields={[
            {
              key: "reason",
              label: "Motivo da rejeição",
              type: "textarea",
              required: true,
              wide: true,
            },
          ]}
          button="Confirmar rejeição"
          onClose={() => setAction(null)}
          onSaved={() =>
            setSuccess(
              "Acesso rejeitado. A decisão foi registrada no histórico.",
            )
          }
        />
      )}
      {action && action !== "reject" && (
        <AccessAction
          user={user}
          action={action}
          onClose={() => setAction(null)}
          onSaved={() =>
            setSuccess(
              "Autorização atualizada. A decisão foi registrada no histórico.",
            )
          }
        />
      )}
    </>
  );
}
function AccessAction({
  user,
  action,
  onClose,
  onSaved,
}: {
  user: User;
  action: "approve" | "add-role" | "remove-role";
  onClose: () => void;
  onSaved: () => void;
}) {
  const [roles, setRoles] = useState<Role[]>([]);
  const [role, setRole] = useState<Role | "">("");
  const [instructor, setInstructor] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<unknown>();
  const client = useQueryClient();
  const options = useQuery({
    queryKey: ["options", "instructors/"],
    queryFn: () => optionsFor("instructors/"),
    enabled: action !== "remove-role",
    retry: false,
  });
  const needsInstructor =
    action === "approve" ? roles.includes("instructor") : role === "instructor";
  const availableRoles = (
    action === "remove-role"
      ? user.roles
      : Object.keys(roleNames).filter(
          (value) =>
            action === "approve" || !user.roles.includes(value as Role),
        )
  ) as Role[];
  return (
    <Modal
      open
      title={
        action === "approve"
          ? "Aprovar solicitação"
          : action === "add-role"
            ? "Adicionar função"
            : "Remover função"
      }
      onClose={() => !pending && onClose()}
    >
      <form
        onSubmit={async (event) => {
          event.preventDefault();
          setPending(true);
          setError(undefined);
          try {
            await post(`users/${user.id}/${action}/`, {
              ...(action === "approve" ? { roles } : { role }),
              ...(needsInstructor && instructor
                ? { instructor_id: Number(instructor) }
                : {}),
            });
            await client.invalidateQueries();
            onSaved();
            onClose();
          } catch (err) {
            setError(err);
          } finally {
            setPending(false);
          }
        }}
      >
        <Notice tone={action === "remove-role" ? "warning" : "info"}>
          {action === "approve"
            ? "A aprovação atribui as funções selecionadas e libera somente as rotinas correspondentes."
            : action === "add-role"
              ? "Adicionar mantém as funções existentes e aprova a conta. Confirme a responsabilidade atribuída."
              : "Remover a última função revoga o acesso interno e devolve a conta à situação pendente."}
        </Notice>
        {action === "approve" ? (
          <fieldset className="role-choices">
            <legend>Funções autorizadas</legend>
            {availableRoles.map((value) => (
              <label className="check-option" key={value}>
                <input
                  type="checkbox"
                  checked={roles.includes(value)}
                  onChange={(event) =>
                    setRoles(
                      event.target.checked
                        ? [...roles, value]
                        : roles.filter((item) => item !== value),
                    )
                  }
                />
                {roleNames[value]}
              </label>
            ))}
          </fieldset>
        ) : (
          <Field label="Função">
            <select
              value={role}
              onChange={(event) => setRole(event.target.value as Role)}
              required
            >
              <option value="">Selecione…</option>
              {availableRoles.map((value) => (
                <option value={value} key={value}>
                  {roleNames[value]}
                </option>
              ))}
            </select>
          </Field>
        )}
        {needsInstructor && (
          <div className="instructor-binding">
            {options.isPending ? (
              <Loading />
            ) : options.error ? (
              <ErrorNotice error={options.error} />
            ) : (
              <Field
                label="Vínculo profissional"
                hint="Somente cadastro ativo e sem vínculo com outra conta. O servidor verifica a identidade novamente."
              >
                <select
                  value={instructor}
                  onChange={(event) => setInstructor(event.target.value)}
                  required={!options.data?.some((row) => row.user === user.id)}
                >
                  <option value="">
                    {options.data?.some((row) => row.user === user.id)
                      ? "Manter vínculo profissional existente"
                      : "Selecione o cadastro profissional…"}
                  </option>
                  {options.data
                    ?.filter(
                      (row) =>
                        row.active && (!row.user || row.user === user.id),
                    )
                    .map((row) => (
                      <option value={Number(row.id)} key={Number(row.id)}>
                        {String(row.name)} · {String(row.email || `#${row.id}`)}
                      </option>
                    ))}
                </select>
              </Field>
            )}
          </div>
        )}
        <ErrorNotice error={error} />
        <div className="form-actions">
          <Button
            variant="secondary"
            type="button"
            onClick={onClose}
            disabled={pending}
          >
            Voltar
          </Button>
          <Button
            type="submit"
            disabled={
              pending ||
              (action === "approve" ? !roles.length : !role) ||
              (needsInstructor && !!options.error)
            }
          >
            {pending ? "Salvando…" : "Confirmar decisão"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
const auditSpec: ResourceSpec = {
  title: "Histórico de ações",
  singular: "evento",
  slug: "auditoria",
  endpoint: "audit/",
  searchPlaceholder: "Pesquisar motivo registrado…",
  filterFields: [
    {
      key: "action",
      label: "Ação realizada",
      type: "select",
      options: Object.entries(auditActions).map(([value, label]) => ({
        value,
        label,
      })),
    },
    {
      key: "target_type",
      label: "Cadastro afetado",
      type: "select",
      options: Object.entries(auditTargets).map(([value, label]) => ({
        value,
        label,
      })),
    },
    { key: "target_id", label: "Número do registro", type: "number", min: 1 },
  ],
  description:
    "Responsável, momento e motivo das decisões que movem a operação.",
  readOnly: true,
  fields: [],
  columns: [
    {
      key: "action",
      label: "Ação",
      render: (row) => auditActionLabel(row.action),
    },
    { key: "actor_name", label: "Responsável" },
    {
      key: "target_type",
      label: "Registro",
      render: (row) => (
        <span>
          {auditTargetLabel(row.target_type)} #{String(row.target_id)}
        </span>
      ),
    },
    {
      key: "created_at",
      label: "Registrado em",
      render: (row) => timestamp(row.created_at),
    },
    {
      key: "reason",
      label: "Motivo",
      render: (row) => String(row.reason || "—"),
    },
  ],
};
export function AuditList() {
  return <ResourceList spec={auditSpec} />;
}
export function AuditDetail() {
  const { id } = useParams();
  const query = useApi<RecordData>(`audit/${id}/`);
  if (query.isPending) return <Loading />;
  if (query.error) return <ErrorNotice error={query.error} />;
  if (!query.data) return null;
  const row = query.data;
  return (
    <>
      <Link className="back-link" to="/auditoria">
        <ChevronLeft size={16} />
        Histórico de ações
      </Link>
      <PageTitle
        eyebrow={`EVENTO · #${id}`}
        title={auditActionLabel(row.action)}
        description={timestamp(row.created_at)}
      />
      <section className="sheet audit-detail">
        <dl className="details-list">
          <div>
            <dt>Responsável</dt>
            <dd>{String(row.actor_name || "Sistema")}</dd>
          </div>
          <div>
            <dt>Registro afetado</dt>
            <dd>
              {auditTargetLabel(row.target_type)} #{String(row.target_id)}
            </dd>
          </div>
          <div>
            <dt>Motivo</dt>
            <dd className="preserve-lines">
              {String(row.reason || "Não informado para esta ação.")}
            </dd>
          </div>
        </dl>
        <details className="audit-metadata">
          <summary>Conferir dados do evento</summary>
          <pre>{JSON.stringify(row.metadata, null, 2)}</pre>
        </details>
      </section>
    </>
  );
}
