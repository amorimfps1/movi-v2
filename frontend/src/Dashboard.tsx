import { Link } from "react-router-dom";
import {
  ArrowUpRight,
  Plus,
  CalendarDays,
  Clock3,
  ArrowRight,
  UsersRound,
  ClipboardList,
} from "lucide-react";
import { useAuth, isAdmin } from "./auth";
import { useApi } from "./query";
import type { Summary, Page, RecordData, Policies } from "./types";
import { date, money, today, monthStart } from "./format";
import { PageTitle, Loading, ErrorNotice, Empty, Badge, Notice } from "./ui";
export function Dashboard() {
  const { user } = useAuth();
  const admin = isAdmin(user);
  const instructor = user?.roles.includes("instructor");
  const summary = useApi<Summary>(
    `reports/summary/?start=${monthStart()}&end=${today()}`,
    admin || !!user?.roles.includes("communication"),
  );
  const lessons = useApi<Page<RecordData>>(
    `lessons/?date=${today()}&ordering=date`,
    admin || instructor === true,
  );
  const policies = useApi<Policies>("policies/");
  const fullDate = new Intl.DateTimeFormat("pt-BR", {
    weekday: "long",
    day: "numeric",
    month: "long",
    timeZone: "America/Sao_Paulo",
  }).format(new Date());
  return (
    <>
      <PageTitle
        eyebrow="SEU PONTO DE PARTIDA"
        title={`Olá, ${user?.first_name || "equipe"}.`}
        description={
          admin
            ? "Acompanhe alunos, matrículas e leads."
            : instructor
              ? "Consulte suas turmas e aulas."
              : "Acompanhe os leads e as conversões."
        }
        actions={
          admin && (
            <Link className="button button--primary" to="/alunos">
              <Plus size={18} />
              Cadastrar aluno
            </Link>
          )
        }
      />
      <div className="dashboard-date">
        <span>
          <CalendarDays size={17} />
          {fullDate}
        </span>
        <span>Horário de São Paulo</span>
      </div>
      {summary.error && <ErrorNotice error={summary.error} />}
      {summary.data && (
        <section className="overview-strip" aria-label="Resumo do período">
          <div className="overview-leading">
            <p className="eyebrow">
              {admin ? "ALUNOS CADASTRADOS" : "LEADS CADASTRADOS"}
            </p>
            <strong>
              {admin ? summary.data.students : summary.data.leads}
            </strong>
            <span>
              {admin
                ? "cadastros de alunos em acompanhamento"
                : "contatos em acompanhamento"}
            </span>
          </div>
          <div>
            <span>
              {admin ? "Matrículas registradas" : "Conversões em aluno"}
            </span>
            <strong>
              {admin ? summary.data.enrollments : summary.data.conversions}
            </strong>
            <small>Cadastro não indica participação</small>
          </div>
          {admin ? (
            <>
              <div>
                <span>Recebido no período</span>
                <strong>{money(summary.data.received)}</strong>
                <small>Por data de recebimento</small>
              </div>
              <div>
                <span>Saldo vencido</span>
                <strong className="text-warning">
                  {money(summary.data.overdue)}
                </strong>
                <small>Até {date(today())}</small>
              </div>
            </>
          ) : (
            <div>
              <span>Conversões em matrícula</span>
              <strong>
                {String(summary.data.converted_enrollments ?? "—")}
              </strong>
              <small>Indicador distinto de conversão em aluno</small>
            </div>
          )}
        </section>
      )}
      {summary.isPending &&
        (admin || user?.roles.includes("communication")) && <Loading />}
      <div className="dashboard-grid">
        <section className="sheet agenda-sheet">
          <div className="section-heading">
            <div>
              <p className="eyebrow">ROTINA DE AULAS</p>
              <h2>Agenda de hoje</h2>
            </div>
            {(admin || instructor) && (
              <Link className="text-link" to="/aulas">
                Ver aulas <ArrowUpRight size={17} />
              </Link>
            )}
          </div>
          {!(admin || instructor) ? (
            <Empty
              title="Seu foco está nas conexões"
              description="Acompanhe os indicadores comerciais nos relatórios disponíveis ao seu perfil."
              action={
                <Link className="button button--secondary" to="/relatorios">
                  Consultar indicadores
                </Link>
              }
            />
          ) : lessons.isPending ? (
            <Loading />
          ) : lessons.error ? (
            <div className="section-pad">
              <ErrorNotice error={lessons.error} />
              <button
                className="button button--secondary"
                onClick={() => void lessons.refetch()}
              >
                Tentar novamente
              </button>
            </div>
          ) : !lessons.data?.results.length ? (
            <Empty
              title="Um dia para preparar os próximos encontros"
              description="Nenhuma aula foi agendada para hoje. Consulte as turmas e organize a agenda."
              action={
                <Link className="button button--secondary" to="/aulas">
                  {admin ? "Organizar aulas" : "Consultar meu diário"}{" "}
                  <ArrowRight size={17} />
                </Link>
              }
            />
          ) : (
            <div className="daily-lessons">
              {lessons.data.results.map((lesson) => (
                <Link
                  className="daily-lesson"
                  key={lesson.id}
                  to={`/aulas/${lesson.id}`}
                >
                  <span className="lesson-clock">
                    <Clock3 size={18} />
                    {String(lesson.start_time || "").slice(0, 5) || "Hoje"}
                  </span>
                  <div>
                    <h3>
                      {String(
                        lesson.class_name || `Turma #${lesson.class_group}`,
                      )}
                    </h3>
                    <p>
                      {String(lesson.instructor_name || "Responsável da turma")}
                    </p>
                  </div>
                  <Badge value={lesson.status} />
                  <ArrowUpRight size={18} />
                </Link>
              ))}
            </div>
          )}
        </section>
        <aside className="operational-column">
          {admin && (
            <section className="operation-note">
              <p className="eyebrow">CUIDADOS DA SECRETARIA</p>
              <h2>O que pede atenção</h2>
              <Link
                to="/acessos?access_status=pending"
                className="pending-link"
              >
                <span className="pending-icon">
                  <UsersRound size={19} />
                </span>
                <div>
                  <strong>Solicitações de acesso</strong>
                  <p>
                    {summary.data
                      ? `${summary.data.pending_users} pendente${summary.data.pending_users === 1 ? "" : "s"} de aprovação`
                      : "Consultar solicitações pendentes"}
                  </p>
                </div>
                <ArrowUpRight size={18} />
              </Link>
              <Link to="/financeiro" className="pending-link">
                <span className="pending-icon">
                  <ClipboardList size={19} />
                </span>
                <div>
                  <strong>Cobranças e recebimentos</strong>
                  <p>Conferir compromissos financeiros</p>
                </div>
                <ArrowUpRight size={18} />
              </Link>
            </section>
          )}
          <section className="policy-note">
            <span className="eyebrow">REGRAS INSTITUCIONAIS</span>
            <h3>Decisões que orientam a operação</h3>
            <p>
              Algumas rotinas aguardam definições da instituição. Cada
              impedimento informa a decisão necessária.
            </p>
            {policies.error ? (
              <ErrorNotice error={policies.error} />
            ) : (
              <Link to="/politicas" className="text-link">
                {policies.data
                  ? `${policies.data.pending.length} decisões pendentes`
                  : "Consultar decisões"}
                <ArrowUpRight size={17} />
              </Link>
            )}
          </section>
        </aside>
      </div>
      {summary.data && (
        <p className="period-note">
          Indicadores consultados de {date(monthStart())} a {date(today())}.{" "}
          {typeof summary.data.financial_definition === "string"
            ? summary.data.financial_definition
            : ""}{" "}
          <Link to="/relatorios">Ver definições e relatórios</Link>
        </p>
      )}
      {instructor && !admin && (
        <Notice>
          Seu diário mostra somente turmas e aulas autorizadas. A liberação e a
          conclusão da chamada dependem das políticas institucionais.
        </Notice>
      )}
    </>
  );
}
