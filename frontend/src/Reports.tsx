import { useState } from "react";
import { Link } from "react-router-dom";
import { Download, ArrowUpRight, FileSpreadsheet } from "lucide-react";
import { useApi } from "./query";
import { useAuth, isAdmin } from "./auth";
import { downloadCsv } from "./api";
import type { Summary, Policies } from "./types";
import {
  PageTitle,
  Loading,
  ErrorNotice,
  Notice,
  Button,
  Field,
  Badge,
  Empty,
} from "./ui";
import { date, money, monthStart, today, label } from "./format";
export function Reports() {
  const { user } = useAuth();
  const admin = isAdmin(user);
  const [draft, setDraft] = useState({ start: monthStart(), end: today() });
  const [period, setPeriod] = useState(draft);
  const [resource, setResource] = useState("charges");
  const [exportError, setExportError] = useState<unknown>();
  const [success, setSuccess] = useState("");
  const [exporting, setExporting] = useState(false);
  const allowed = admin || user?.roles.includes("communication");
  const query = useApi<Summary>(
    `reports/summary/?start=${period.start}&end=${period.end}`,
    allowed,
  );
  if (!allowed)
    return (
      <Notice>
        Seu perfil não possui acesso aos relatórios institucionais. Consulte as
        turmas e aulas do diário autorizado.
      </Notice>
    );
  return (
    <>
      <PageTitle
        eyebrow="CONSULTA E ACOMPANHAMENTO"
        title="Relatórios"
        description="Números com período, população e origem identificados."
      />
      <form
        className="report-period sheet"
        onSubmit={(event) => {
          event.preventDefault();
          setPeriod({ ...draft });
          setSuccess("");
        }}
      >
        <Field label="Início do período">
          <input
            type="date"
            required
            value={draft.start}
            max={draft.end}
            onChange={(event) =>
              setDraft({ ...draft, start: event.target.value })
            }
          />
        </Field>
        <Field label="Fim do período">
          <input
            type="date"
            required
            value={draft.end}
            min={draft.start}
            onChange={(event) =>
              setDraft({ ...draft, end: event.target.value })
            }
          />
        </Field>
        <Button type="submit">Consultar período</Button>
        <span>Datas locais de São Paulo</span>
      </form>
      {query.isPending ? (
        <Loading />
      ) : query.error ? (
        <ErrorNotice error={query.error} />
      ) : (
        query.data && (
          <>
            <p className="report-caption">
              Consulta de <strong>{date(period.start)}</strong> a{" "}
              <strong>{date(period.end)}</strong>
            </p>
            {admin && (
              <div className="report-layout">
                <section className="sheet">
                  <div className="section-heading">
                    <div>
                      <p className="eyebrow">FINANCEIRO</p>
                      <h2>Obrigações e valores recebidos</h2>
                    </div>
                    <Link
                      className="text-link"
                      to={`/financeiro?${new URLSearchParams(period)}`}
                    >
                      Abrir cobranças <ArrowUpRight size={16} />
                    </Link>
                  </div>
                  <div className="report-financial-main">
                    <div>
                      <span>Recebido no período</span>
                      <strong>{money(query.data.received)}</strong>
                      <small>Recebimentos pela data de pagamento</small>
                      <Link
                        className="text-link"
                        to={`/recebimentos?${new URLSearchParams(period)}`}
                      >
                        Abrir recebimentos <ArrowUpRight size={16} />
                      </Link>
                    </div>
                    <dl>
                      <div>
                        <dt>Previsto</dt>
                        <dd>{money(query.data.expected)}</dd>
                      </div>
                      <div>
                        <dt>Saldo a receber</dt>
                        <dd>{money(query.data.outstanding)}</dd>
                      </div>
                      <div>
                        <dt>Saldo vencido</dt>
                        <dd className="text-warning">
                          {money(query.data.overdue)}
                        </dd>
                      </div>
                    </dl>
                  </div>
                  <p className="report-definition">
                    {String(
                      query.data.financial_definition ||
                        "Definição institucional pendente.",
                    )}
                  </p>
                  <div className="report-categories">
                    <h3>Recebido por finalidade</h3>
                    <table>
                      <thead>
                        <tr>
                          <th>Categoria</th>
                          <th>Valor recebido</th>
                        </tr>
                      </thead>
                      <tbody>
                        {Object.entries(
                          (query.data.categories ?? {}) as Record<
                            string,
                            string
                          >,
                        ).map(([category, value]) => (
                          <tr key={category}>
                            <td>{label(category)}</td>
                            <td>{money(value)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </section>
                <aside className="sheet">
                  <div className="section-heading">
                    <h2>Base cadastral atual</h2>
                  </div>
                  <dl className="report-counts">
                    <div>
                      <dt>Alunos em acompanhamento</dt>
                      <dd>{query.data.students}</dd>
                    </div>
                    <div>
                      <dt>Matrículas regulares</dt>
                      <dd>{query.data.enrollments}</dd>
                    </div>
                    <div>
                      <dt>Turmas ativas</dt>
                      <dd>{query.data.classes}</dd>
                    </div>
                    <div>
                      <dt>Acessos pendentes</dt>
                      <dd>{query.data.pending_users}</dd>
                    </div>
                  </dl>
                  <p className="report-definition">
                    Contagens refletem a situação atual do cadastro. Matrícula
                    regular não comprova elegibilidade para a aula.
                  </p>
                </aside>
              </div>
            )}
            <section className="sheet commercial-report">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">ACOLHIMENTO E CONVERSÃO</p>
                  <h2>Do primeiro contato ao vínculo</h2>
                </div>
              </div>
              <div className="commercial-flow">
                <div>
                  <span>Leads no período</span>
                  <strong>{query.data.leads ?? 0}</strong>
                  <small>População de origem</small>
                </div>
                <ArrowUpRight size={24} />
                <div>
                  <span>Convertidos em aluno</span>
                  <strong>{query.data.conversions ?? 0}</strong>
                  <small>Vínculo de conversão atual</small>
                </div>
                <ArrowUpRight size={24} />
                <div>
                  <span>Matrículas desses alunos</span>
                  <strong>
                    {String(query.data.converted_enrollments ?? "—")}
                  </strong>
                  <small>Vínculos distintos de cadastro</small>
                </div>
              </div>
              <p className="report-definition">
                {String(
                  query.data.commercial_definition ||
                    "Leads criados no período; vínculo de conversão e matrículas apresentados separadamente. Não representa taxa de conversão.",
                )}
              </p>
            </section>
            <Notice tone="warning">
              Metas, frequência, alertas de evasão, ocupação e repasse final
              aguardam definições institucionais. Não são apresentados como
              resultados aprovados. DN-016, DN-018 e DN-019.
            </Notice>
            {admin && (
              <section className="sheet export-section">
                <div>
                  <FileSpreadsheet size={25} />
                  <div>
                    <h2>Levar os registros para conferência</h2>
                    <p>
                      CSV inclui todos os resultados autorizados. Cobranças usam
                      vencimento; recebimentos usam pagamento. Alunos refletem o
                      cadastro atual.
                    </p>
                  </div>
                </div>
                <div className="export-controls">
                  <select
                    aria-label="Registros para exportar"
                    value={resource}
                    onChange={(event) => setResource(event.target.value)}
                  >
                    <option value="charges">Cobranças do período</option>
                    <option value="payments">Recebimentos do período</option>
                    <option value="students">Todos os alunos</option>
                  </select>
                  <Button
                    variant="secondary"
                    disabled={exporting}
                    onClick={async () => {
                      setExporting(true);
                      setExportError(undefined);
                      try {
                        await downloadCsv(
                          resource,
                          new URLSearchParams(
                            resource === "students" ? {} : period,
                          ),
                        );
                        setSuccess(
                          "Arquivo CSV exportado com todos os registros filtrados.",
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
                </div>
                <ErrorNotice error={exportError} />
                {success && <Notice tone="success">{success}</Notice>}
              </section>
            )}
          </>
        )
      )}
    </>
  );
}
export function PoliciesPage() {
  const query = useApi<Policies>("policies/");
  const [search, setSearch] = useState("");
  if (query.isPending) return <Loading />;
  if (query.error) return <ErrorNotice error={query.error} />;
  if (!query.data) return null;
  const data = query.data;
  const filtered = data.pending.filter((policy) =>
    `${policy.id} ${policy.title} ${policy.impact}`
      .toLocaleLowerCase("pt-BR")
      .includes(search.toLocaleLowerCase("pt-BR")),
  );
  return (
    <>
      <PageTitle
        eyebrow="REGRAS INSTITUCIONAIS"
        title="Decisões que orientam o MOVI+"
        description="As rotinas seguem as regras disponíveis. Uma decisão pendente não autoriza o sistema a inventar uma política."
      />
      <Notice tone="warning">
        Este registro indica pendências de negócio. A aprovação institucional
        precisa identificar a política detalhada, o responsável e a data antes
        de habilitar rotinas condicionadas.
      </Notice>
      <section className="sheet">
        <div className="policy-toolbar">
          <Field label="Pesquisar decisão">
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Código, assunto ou impacto…"
            />
          </Field>
          <div>
            <strong>{data.pending.length}</strong>
            <small>decisões registradas</small>
          </div>
        </div>
        {!filtered.length ? (
          <Empty
            title="Nenhuma decisão encontrada"
            description="Ajuste o termo de pesquisa."
          />
        ) : (
          <div className="policy-list">
            {filtered.map((policy) => (
              <article key={policy.id}>
                <Badge
                  value={
                    data.approved.includes(policy.id) ? "approved" : "pending"
                  }
                >
                  {policy.id}
                </Badge>
                <div>
                  <h3>{policy.title}</h3>
                  <p>{policy.impact}</p>
                </div>
                <span className="policy-status">
                  {data.approved.includes(policy.id)
                    ? "Aprovação registrada"
                    : "Pendente"}
                </span>
              </article>
            ))}
          </div>
        )}
      </section>
      <p className="period-note">
        Fuso operacional: {data.timezone}. Aprovações registradas:{" "}
        {data.approved.length ? data.approved.join(", ") : "nenhuma"}.{" "}
        {data.demo ? "Ambiente de demonstração isolado." : ""}
      </p>
    </>
  );
}
