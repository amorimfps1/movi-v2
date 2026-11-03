import { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import {
  Plus,
  Search,
  ArrowUpRight,
  Pencil,
  Archive,
  Download,
  ChevronLeft,
} from "lucide-react";
import { useQueryClient, useQueries } from "@tanstack/react-query";
import type { Page, RecordData, Student, Enrollment } from "./types";
import { useApi } from "./query";
import { patch, downloadCsv, optionsFor } from "./api";
import type { ResourceSpec } from "./schema";
import { studentSpec, enrollmentFields } from "./schema";
import { RecordForm } from "./forms";
import {
  Button,
  PageTitle,
  Loading,
  ErrorNotice,
  Empty,
  Pagination,
  Confirm,
  Badge,
  Journey,
  Notice,
  Field,
} from "./ui";
import { date, money, label } from "./format";
export function ResourceList({
  spec,
  extraActions,
  beforeList,
  eyebrow = "ROTINA DA SECRETARIA",
}: {
  spec: ResourceSpec;
  extraActions?: (row: RecordData) => React.ReactNode;
  beforeList?: React.ReactNode;
  eyebrow?: string;
}) {
  const feminine =
    spec.singular.endsWith("a") || spec.singular === "modalidade";
  const [urlParams, setUrlParams] = useSearchParams();
  const filterKeys = [
    "ordering",
    ...(spec.filters?.map((filter) => filter.key) ?? []),
    ...(spec.filterFields?.map((field) => field.key) ?? []),
    ...(spec.endpoint === "enrollments/" ? ["student"] : []),
  ];
  const filters = Object.fromEntries(
    filterKeys
      .filter((key) => urlParams.get(key))
      .map((key) => [key, urlParams.get(key)!]),
  );
  const search = urlParams.get("search") || "";
  const rawPage = Number(urlParams.get("page") || 1);
  const page = Number.isSafeInteger(rawPage) && rawPage > 0 ? rawPage : 1;
  const [searchDraft, setSearchDraft] = useState(search);
  useEffect(() => setSearchDraft(search), [search]);
  function changeQuery(changes: Record<string, string>, resetPage = true) {
    const next = new URLSearchParams(
      Object.fromEntries(
        [...filterKeys, "search", "page"]
          .filter((key) => urlParams.get(key))
          .map((key) => [key, urlParams.get(key)!]),
      ),
    );
    if (resetPage) next.delete("page");
    Object.entries(changes).forEach(([key, value]) => {
      if (value) next.set(key, value);
      else next.delete(key);
    });
    setUrlParams(next);
  }
  const setPage = (value: number) =>
    changeQuery({ page: String(value) }, false);
  const filtered =
    !!search ||
    Object.entries(filters).some(
      ([key, value]) => key !== "ordering" && !!value,
    );
  const [form, setForm] = useState<RecordData | "new" | null>(null);
  const [archive, setArchive] = useState<RecordData | null>(null);
  const [notice, setNotice] = useState("");
  const [exportError, setExportError] = useState<unknown>();
  const [exporting, setExporting] = useState(false);
  const client = useQueryClient();
  const filterPaths = [
    ...new Set(
      spec.filterFields
        ?.map((field) => field.lookup)
        .filter((value): value is string => !!value),
    ),
  ];
  const filterQueries = useQueries({
    queries: filterPaths.map((path) => ({
      queryKey: ["options", path],
      queryFn: () => optionsFor(path),
      retry: false,
    })),
  });
  const params = new URLSearchParams({
    page: String(page),
    page_size: "25",
    search,
    ...filters,
  });
  const query = useApi<Page<RecordData>>(`${spec.endpoint}?${params}`);
  const canExport = ["students/", "charges/", "payments/"].includes(
    spec.endpoint,
  );
  return (
    <>
      <PageTitle
        eyebrow={eyebrow}
        title={spec.title}
        description={spec.description}
        actions={
          <>
            {canExport && (
              <Button
                variant="secondary"
                disabled={exporting}
                onClick={async () => {
                  setExporting(true);
                  setExportError(undefined);
                  try {
                    await downloadCsv(spec.endpoint.replace("/", ""), params);
                    setNotice(
                      "Exportação concluída: todos os registros filtrados.",
                    );
                  } catch (err) {
                    setExportError(err);
                  } finally {
                    setExporting(false);
                  }
                }}
              >
                <Download size={17} />
                {exporting ? "Exportando…" : "Exportar CSV"}
              </Button>
            )}
            {!spec.readOnly && (
              <Button onClick={() => setForm("new")}>
                <Plus size={18} />
                Nov{feminine ? "a" : "o"} {spec.singular}
              </Button>
            )}
          </>
        }
      />
      {notice && <Notice tone="success">{notice}</Notice>}
      <ErrorNotice error={exportError} />
      {beforeList}
      <section className="sheet">
        <div className="list-toolbar">
          <form
            className="search-field"
            onSubmit={(event) => {
              event.preventDefault();
              changeQuery({ search: searchDraft });
            }}
          >
            <Search size={19} />
            <input
              aria-label={`Pesquisar ${spec.title.toLowerCase()}`}
              placeholder={
                spec.searchPlaceholder ??
                `Pesquisar ${spec.title.toLowerCase()}…`
              }
              value={searchDraft}
              onChange={(event) => setSearchDraft(event.target.value)}
            />
            <Button variant="ghost" type="submit">
              Buscar
            </Button>
          </form>
          <div className="list-filters">
            {spec.filters?.map((filter) => (
              <select
                aria-label={filter.label}
                key={filter.key}
                value={filters[filter.key] || ""}
                onChange={(event) => {
                  changeQuery({ [filter.key]: event.target.value });
                }}
              >
                <option value="">{filter.label}: todos</option>
                {filter.options.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            ))}
            <select
              aria-label="Ordenação"
              value={filters.ordering || ""}
              onChange={(event) => {
                changeQuery({ ordering: event.target.value });
              }}
            >
              <option value="">Ordenação padrão</option>
              <option value={spec.endpoint === "students/" ? "name" : "id"}>
                Ordem crescente
              </option>
              <option value={spec.endpoint === "students/" ? "-name" : "-id"}>
                Ordem decrescente
              </option>
            </select>
            {(filtered || filters.ordering) && (
              <Button
                variant="ghost"
                onClick={() => {
                  setSearchDraft("");
                  setUrlParams({});
                }}
              >
                Limpar filtros
              </Button>
            )}
          </div>
        </div>
        {spec.filterFields && (
          <div className="additional-filters">
            {spec.filterFields.map((field) => (
              <Field key={field.key} label={field.label}>
                {field.type === "select" ? (
                  <select
                    value={filters[field.key] || ""}
                    onChange={(event) => {
                      changeQuery({ [field.key]: event.target.value });
                    }}
                    disabled={
                      filterQueries[filterPaths.indexOf(field.lookup!)]
                        ?.isPending
                    }
                  >
                    <option value="">Todas</option>
                    {(
                      field.options ??
                      filterQueries[
                        filterPaths.indexOf(field.lookup!)
                      ]?.data?.map((row) => ({
                        value: Number(row.id),
                        label: String(row.name || row.email),
                      }))
                    )?.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    type={field.type || "text"}
                    min={field.min}
                    value={filters[field.key] || ""}
                    onChange={(event) => {
                      changeQuery({ [field.key]: event.target.value });
                    }}
                  />
                )}
              </Field>
            ))}
          </div>
        )}
        {filterQueries.some((item) => item.error) && (
          <div className="section-pad">
            <ErrorNotice
              error={filterQueries.find((item) => item.error)?.error}
            />
          </div>
        )}
        {query.isPending ? (
          <Loading />
        ) : query.error ? (
          <div className="section-pad">
            <ErrorNotice error={query.error} />
            <Button variant="secondary" onClick={() => void query.refetch()}>
              Tentar novamente
            </Button>
          </div>
        ) : !query.data?.results.length ? (
          <Empty
            title={
              filtered
                ? "Nenhum resultado encontrado"
                : `Nenhum${feminine ? "a" : "o"} ${spec.singular} por aqui`
            }
            description={
              spec.readOnly
                ? "Nenhum registro disponível no escopo ou nos filtros selecionados."
                : filtered
                  ? "Tente outro termo ou ajuste os filtros."
                  : `Cadastre ${feminine ? "a primeira" : "o primeiro"} ${spec.singular} para iniciar o acompanhamento.`
            }
            action={
              !spec.readOnly && (
                <Button onClick={() => setForm("new")}>
                  <Plus size={17} />
                  Adicionar {spec.singular}
                </Button>
              )
            }
          />
        ) : (
          <>
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    {spec.columns.map((column) => (
                      <th key={column.key} scope="col">
                        {column.label}
                      </th>
                    ))}
                    <th scope="col">
                      <span className="sr-only">Ações</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {query.data.results.map((row) => (
                    <tr key={row.id}>
                      {spec.columns.map((column, index) => (
                        <td key={column.key}>
                          {index === 0 ? (
                            <Link
                              className="table-name"
                              to={`/${spec.slug}/${row.id}`}
                            >
                              {column.render?.(row) ??
                                String(row[column.key] ?? "—")}
                              <ArrowUpRight size={15} />
                            </Link>
                          ) : (
                            (column.render?.(row) ??
                            String(row[column.key] ?? "—"))
                          )}
                        </td>
                      ))}
                      <td>
                        <div className="row-actions">
                          {extraActions?.(row)}
                          {!spec.readOnly && spec.editable !== false && (
                            <Button
                              variant="ghost"
                              aria-label={`Editar ${String(row.name || row.id)}`}
                              onClick={() => setForm(row)}
                            >
                              <Pencil size={17} />
                            </Button>
                          )}
                          {spec.archive &&
                            !spec.readOnly &&
                            (spec.archive === "active"
                              ? !!row.active
                              : !row[spec.archive]) && (
                              <Button
                                variant="ghost"
                                aria-label={`Arquivar ${String(row.name || row.id)}`}
                                onClick={() => setArchive(row)}
                              >
                                <Archive size={17} />
                              </Button>
                            )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination
              page={page}
              count={query.data.count}
              onChange={setPage}
            />
          </>
        )}
      </section>
      {form && (
        <RecordForm
          title={`${form === "new" ? "Cadastrar" : "Editar"} ${spec.singular}`}
          endpoint={spec.endpoint}
          fields={spec.fields}
          record={form === "new" ? undefined : form}
          initial={Object.fromEntries(
            ["enrollment", "class_group"]
              .filter((key) => filters[key])
              .map((key) => [key, Number(filters[key])]),
          )}
          onClose={() => setForm(null)}
          onSaved={() =>
            setNotice(
              `${spec.singular[0].toUpperCase() + spec.singular.slice(1)} ${form === "new" ? "cadastrad" + (feminine ? "a" : "o") : "atualizad" + (feminine ? "a" : "o")} com sucesso.`,
            )
          }
        />
      )}
      {archive && (
        <Confirm
          title={`Arquivar ${spec.singular}?`}
          description="O histórico e os vínculos existentes serão preservados."
          danger
          confirm="Confirmar arquivamento"
          onClose={() => setArchive(null)}
          action={async () => {
            await patch(`${spec.endpoint}${archive.id}/`, {
              [spec.archive!]: spec.archive === "active" ? false : true,
            });
            await client.invalidateQueries();
            setNotice("Cadastro arquivado com histórico preservado.");
          }}
        />
      )}
    </>
  );
}
export function StudentDetail() {
  const { id } = useParams();
  return <StudentRecord key={id} id={id!} />;
}
function StudentRecord({ id }: { id: string }) {
  const [enrollmentPage, setEnrollmentPage] = useState(1);
  const student = useApi<Student>(`students/${id}/`);
  const enrollments = useApi<Page<Enrollment>>(
    `enrollments/?student=${id}&page=${enrollmentPage}&page_size=25`,
  );
  const [editing, setEditing] = useState(false);
  const [enrolling, setEnrolling] = useState(false);
  const [success, setSuccess] = useState("");
  if (student.isPending) return <Loading />;
  if (student.error) return <ErrorNotice error={student.error} />;
  if (!student.data) return null;
  const value = student.data;
  return (
    <>
      <Link className="back-link" to="/alunos">
        <ChevronLeft size={16} />
        Todos os alunos
      </Link>
      <PageTitle
        eyebrow={`CADASTRO · #${value.id}`}
        title={value.name}
        description={
          value.archived
            ? "Cadastro arquivado · histórico preservado"
            : "Cadastro do aluno e matrículas vinculadas."
        }
        actions={
          <>
            <Button variant="secondary" onClick={() => setEditing(true)}>
              <Pencil size={17} />
              Editar cadastro
            </Button>
            <Button
              disabled={value.archived}
              onClick={() => setEnrolling(true)}
            >
              <Plus size={18} />
              Nova matrícula
            </Button>
          </>
        }
      />
      {success && <Notice tone="success">{success}</Notice>}
      <Journey step={enrollments.data?.count ? 2 : 1} />
      <div className="detail-grid">
        <section className="sheet participant-details">
          <div className="section-heading">
            <h2>Sobre o aluno</h2>
            <Badge value={value.archived ? "cancelled" : "regular"}>
              {value.archived ? "Arquivado" : "Em acompanhamento"}
            </Badge>
          </div>
          <dl className="details-list">
            <div>
              <dt>E-mail</dt>
              <dd>{value.email || "Não informado"}</dd>
            </div>
            <div>
              <dt>Telefone</dt>
              <dd>{value.phone || "Não informado"}</dd>
            </div>
            <div>
              <dt>CPF</dt>
              <dd>{value.cpf || "Não informado"}</dd>
            </div>
            <div>
              <dt>Nascimento</dt>
              <dd>{date(value.birth_date)}</dd>
            </div>
            <div>
              <dt>Endereço</dt>
              <dd>{value.address || "Não informado"}</dd>
            </div>
            <div>
              <dt>Observações</dt>
              <dd className="preserve-lines">
                {value.notes || "Sem observações."}
              </dd>
            </div>
          </dl>
        </section>
        <section className="sheet" aria-label="Matrículas e participação">
          <div className="section-heading">
            <div>
              <p className="eyebrow">PRÓXIMO PASSO</p>
              <h2>Matrículas e participação</h2>
            </div>
            <span className="count-label">
              {enrollments.data?.count ?? "—"}
            </span>
          </div>
          {enrollments.isPending ? (
            <Loading />
          ) : enrollments.error ? (
            <div className="section-pad">
              <ErrorNotice error={enrollments.error} />
              <Button
                variant="secondary"
                onClick={() => void enrollments.refetch()}
              >
                Tentar carregar matrículas novamente
              </Button>
              {enrollmentPage > 1 && (
                <Button variant="ghost" onClick={() => setEnrollmentPage(1)}>
                  Voltar à primeira página
                </Button>
              )}
            </div>
          ) : !enrollments.data?.results.length ? (
            <Empty
              title="Pronto para uma nova atividade"
              description="O cadastro não cria uma matrícula. Escolha uma turma para dar o próximo passo."
              action={
                <Button
                  disabled={value.archived}
                  onClick={() => setEnrolling(true)}
                >
                  Matricular aluno <ArrowUpRight size={17} />
                </Button>
              }
            />
          ) : (
            <div className="enrollment-list">
              {enrollments.data.results.map((enrollment) => (
                <Link
                  key={enrollment.id}
                  to={`/matriculas/${enrollment.id}`}
                  className="enrollment-item"
                >
                  <div>
                    <h3>{enrollment.class_name}</h3>
                    <p>
                      {label(enrollment.plan)} · início em{" "}
                      {date(enrollment.start_date)}
                    </p>
                    <strong>{money(enrollment.amount)}</strong>
                  </div>
                  <div>
                    <Badge
                      value={enrollment.eligibility?.status || "pending"}
                    />
                    <ArrowUpRight size={19} />
                  </div>
                </Link>
              ))}
            </div>
          )}
          {!enrollments.isPending &&
            !enrollments.error &&
            enrollments.data &&
            (enrollments.data.count > 25 || enrollmentPage > 1) && (
              <Pagination
                page={enrollmentPage}
                count={enrollments.data.count}
                onChange={setEnrollmentPage}
              />
            )}
        </section>
      </div>
      {editing && (
        <RecordForm
          title="Editar aluno"
          endpoint="students/"
          fields={studentSpec.fields}
          record={value}
          onClose={() => setEditing(false)}
          onSaved={() => setSuccess("Cadastro atualizado com sucesso.")}
        />
      )}
      {enrolling && (
        <RecordForm
          title={`Matricular ${value.name.split(" ")[0]}`}
          endpoint="enrollments/"
          fields={enrollmentFields}
          initial={{ student: value.id }}
          onClose={() => setEnrolling(false)}
          onSaved={() =>
            setSuccess(
              "Matrícula registrada. Consulte as condições de participação e cobranças.",
            )
          }
        />
      )}
    </>
  );
}
