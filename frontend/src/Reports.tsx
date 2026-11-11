import { useState } from "react";
import { Link } from "react-router-dom";
import { Download, ArrowUpRight, FileSpreadsheet } from "lucide-react";
import { useApi } from "./query";
import { useAuth, isAdmin } from "./auth";
import { downloadCsv } from "./api";
import { ActionForm } from "./forms";
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
      <ConversionReport start={period.start} end={period.end} />
      {admin && <AttritionReport start={period.start} end={period.end} />}
      {admin && <OccupancyReport />}
      {admin && <FrequencyReport />}
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

function AttritionReport({ start, end }: { start: string; end: string }) {
  const query = useApi<{ start: string; end: string; active_at_start: number; early_cancellations: number; normal_completions: number; unknown_end: number; unknown_cancellation: number; percent: string | null; definition: string }>(`reports/attrition/?${new URLSearchParams({ start, end })}`);
  return <section className="sheet section-pad"><h2>Evasão</h2>
    {query.isPending ? <Loading /> : query.error ? <ErrorNotice error={query.error} /> : typeof query.data?.active_at_start !== 'number' ? <Notice tone="error">Não foi possível interpretar a evasão recebida.</Notice> : query.data && <>
      <p>De {date(query.data.start)} a {date(query.data.end)}. {query.data.definition}</p>
      <p>Ativas no início: {query.data.active_at_start} · Cancelamentos antecipados: {query.data.early_cancellations} · Evasão: {query.data.percent === null ? 'Sem base definida' : `${Number(query.data.percent).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%`}</p>
      <p>Conclusões normais: {query.data.normal_completions} · Sem fim conhecido: {query.data.unknown_end} · Sem data conhecida de cancelamento: {query.data.unknown_cancellation}</p>
    </>}
  </section>;
}
function ConversionReport({ start, end }: { start: string; end: string }) {
  const query = useApi<{ start: string; end: string; leads: number; converted_people: number; converted_enrollments: number; person_percent: string | null; enrollment_percent: string | null; definition: string }>(`reports/conversion/?${new URLSearchParams({ start, end })}`);
  const percent = (value: string | null) => value === null ? 'Sem leads na coorte' : `${Number(value).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%`;
  return <section className="sheet section-pad"><h2>Conversão da coorte de leads</h2>
    {query.isPending ? <Loading /> : query.error ? <ErrorNotice error={query.error} /> : typeof query.data?.leads !== 'number' ? <Notice tone="error">Não foi possível interpretar a conversão recebida.</Notice> : query.data && <>
      <p>Leads cadastrados de {date(query.data.start)} a {date(query.data.end)}: {query.data.leads}. {query.data.definition}</p>
      <p>Pessoas vinculadas: {query.data.converted_people} · {percent(query.data.person_percent)}</p>
      <p>Leads com matrícula atribuída: {query.data.converted_enrollments} · {percent(query.data.enrollment_percent)}</p>
    </>}
  </section>;
}
function FrequencyReport() {
  type Window = { present: number; absent: number; percent: string | null };
  const { user } = useAuth();
  const [configuring, setConfiguring] = useState(false);
  const query = useApi<{ on: string; definition: string; short_days: number; long_days: number; absence_threshold: number; enrollments: { enrollment: number; person: string; class_name: string; short_window: Window; long_window: Window; consecutive_absences: number; alert: boolean }[] }>('reports/frequency/');
  const percent = (value: string | null) => value === null ? 'Sem registros' : `${Number(value).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%`;
  return <section className="sheet section-pad"><div className="section-heading"><h2>Frequência e faltas</h2>{user?.roles.includes('coordinator') && query.data && <Button variant="secondary" onClick={() => setConfiguring(true)}>Configurar indicador</Button>}</div>
    {query.isPending ? <Loading /> : query.error ? <ErrorNotice error={query.error} /> : !Array.isArray(query.data?.enrollments) ? <Notice tone="error">Não foi possível interpretar a frequência recebida.</Notice> : query.data && <>
      <p>Posição em {date(query.data.on)}. {query.data.definition} Alerta a partir de {query.data.absence_threshold} faltas consecutivas.</p>
      {!query.data.enrollments.length ? <p>Nenhuma matrícula regular vigente.</p> : <div className="table-wrap"><table><thead><tr><th>Aluno</th><th>Turma</th><th>{query.data.short_days} dias</th><th>{query.data.long_days} dias</th><th>Faltas consecutivas</th></tr></thead><tbody>
        {query.data.enrollments.map((row) => <tr key={row.enrollment}><td><Link to={`/matriculas/${row.enrollment}`}>{row.person}</Link></td><td>{row.class_name}</td><td>{percent(row.short_window.percent)}</td><td>{percent(row.long_window.percent)}</td><td>{row.consecutive_absences}{row.alert ? ' · Atenção' : ''}</td></tr>)}
      </tbody></table></div>}
    </>}
    {configuring && query.data && <ActionForm title="Configurar frequência" endpoint="reports/frequency-policy/" fields={[
      { key: 'short_days', label: 'Janela menor em dias', type: 'number', min: 1, max: 3650, required: true, default: query.data.short_days },
      { key: 'long_days', label: 'Janela maior em dias', type: 'number', min: 1, max: 3650, required: true, default: query.data.long_days },
      { key: 'absence_threshold', label: 'Faltas consecutivas para alerta', type: 'number', min: 1, max: 100, required: true, default: query.data.absence_threshold },
      { key: 'reason', label: 'Motivo da alteração', type: 'textarea', required: true, wide: true },
    ]} transform={(values) => ({ ...values, short_days: Number(values.short_days), long_days: Number(values.long_days), absence_threshold: Number(values.absence_threshold) })} onClose={() => setConfiguring(false)} />}
  </section>;
}
function OccupancyReport() {
  const query = useApi<{ on: string; definition: string; classes: { class_group: number; name: string; capacity: number; regular: number; experimental: number; waiting: number; percent: string }[] }>('reports/occupancy/');
  return <section className="sheet section-pad">
    <h2>Ocupação das turmas</h2>
    {query.isPending ? <Loading /> : query.error ? <ErrorNotice error={query.error} /> : !Array.isArray(query.data?.classes) ? <Notice tone="error">Não foi possível interpretar a ocupação recebida.</Notice> : query.data && <>
      <p>Posição em {date(query.data.on)}. {query.data.definition}</p>
      {!query.data.classes.length ? <p>Nenhuma turma ativa.</p> : <div className="table-wrap"><table><thead><tr><th>Turma</th><th>Matrículas</th><th>Capacidade</th><th>Ocupação</th><th>Experimentais</th><th>Espera</th></tr></thead><tbody>
        {query.data.classes.map((group) => <tr key={group.class_group}><td><Link to={`/turmas/${group.class_group}`}>{group.name}</Link></td><td>{group.regular}</td><td>{group.capacity}</td><td>{Number(group.percent).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%</td><td>{group.experimental}</td><td>{group.waiting}</td></tr>)}
      </tbody></table></div>}
    </>}
  </section>;
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
        description="Acompanhe as regras aprovadas e o andamento de sua implementação."
      />
      <Notice tone="warning">
        As propostas DN-001 a DN-022 foram aprovadas. Algumas funcionalidades ainda precisam ser implementadas ou homologadas.
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
                <Badge value="neutral">
                  {policy.id}
                </Badge>
                <div>
                  <h3>{policy.title}</h3>
                  <p>{policy.impact}</p>
                </div>
                <span className="policy-status">
                  Em acompanhamento
                </span>
              </article>
            ))}
          </div>
        )}
      </section>
      <p className="period-note">
        Fuso operacional: {data.timezone}.{" "}
        {data.demo ? "Ambiente de demonstração isolado." : ""}
      </p>
    </>
  );
}
