import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ChevronLeft, Plus, ArrowUpRight, Ban, RefreshCw } from "lucide-react";
import type { Enrollment, Eligibility, Page, RecordData } from "./types";
import { useApi } from "./query";
import { EnrollmentConditions } from "./EnrollmentConditions";
import {
  Button,
  PageTitle,
  Loading,
  ErrorNotice,
  Journey,
  Notice,
  Badge,
  Empty,
  Pagination,
} from "./ui";
import { ActionForm, RecordForm } from "./forms";
import { enrollmentFields } from "./schema";
import { date, label, money, today } from "./format";
export function EnrollmentDetail() {
  const { id } = useParams();
  return <EnrollmentRecord key={id} id={id!} />;
}
function EnrollmentRecord({ id }: { id: string }) {
  const [chargePage, setChargePage] = useState(1);
  const enrollment = useApi<Enrollment>(`enrollments/${id}/`);
  const eligibility = useApi<Eligibility>(
    `enrollments/${id}/eligibility/?on=${today()}`,
  );
  const charges = useApi<Page<RecordData>>(
    `charges/?enrollment=${id}&page=${chargePage}&page_size=25`,
  );
  const [cancel, setCancel] = useState(false);
  const [notice, setNotice] = useState("");
  const [renewing, setRenewing] = useState(false);
  const [repairing, setRepairing] = useState(false);
  if (enrollment.isPending) return <Loading />;
  if (enrollment.error) return <ErrorNotice error={enrollment.error} />;
  if (!enrollment.data) return null;
  const value = enrollment.data;
  const state = eligibility.data ?? value.eligibility;
  return (
    <>
      <Link className="back-link" to="/matriculas">
        <ChevronLeft size={16} />
        Todas as matrículas
      </Link>
      <PageTitle
        eyebrow={`MATRÍCULA · #${id}`}
        title={value.student_name || `Aluno #${value.student}`}
        description={value.class_name || `Turma #${value.class_group}`}
        actions={
          <>
            <Link
              className="button button--secondary"
              to={`/alunos/${value.student}`}
            >
              Ver aluno <ArrowUpRight size={17} />
            </Link>
            {value.administrative_status !== "cancelled" && (
              <Button variant="secondary" onClick={() => setCancel(true)}>
                <Ban size={17} />
                Cancelar matrícula
              </Button>
            )}
          </>
        }
      />
      {notice && <Notice tone="success">{notice}</Notice>}
      {value.contract_version === 1 && <section className="sheet section-pad">
        <h2>Contrato e parcelas</h2>
        <p>Vigência: {date(value.start_date)} a {date(value.end_date)} · {String(value.installments)} parcelas · Total {money(value.amount)} · Taxa {money(value.fee_amount)}</p>
        <Notice>Vencimentos provisórios: primeira cobrança dia 15 ou último dia do mês; seguintes no dia original da matrícula.</Notice>
        <div className="contract-actions"><Button variant="secondary" onClick={() => setRepairing(true)}>Regularizar cobranças ausentes</Button>
        <Button variant="secondary" onClick={() => setRenewing(true)}>Renovar contrato</Button>
        </div>
      </section>}
      {repairing && <ActionForm title="Regularizar cobranças" description="Recria apenas obrigações ausentes do cronograma original, sem alterar datas ou duplicar parcelas."
        endpoint={`enrollments/${id}/repair_charges/`} fields={[]} onClose={() => setRepairing(false)} onSaved={() => setNotice('Cronograma conferido e cobranças ausentes geradas.')} />}
      {renewing && <RecordForm title="Renovar contrato" endpoint={`enrollments/${id}/renew/`}
        fields={enrollmentFields.filter(f => !['student', 'class_group'].includes(f.key))}
        onClose={() => setRenewing(false)} onSaved={row => setNotice(`Renovação registrada na matrícula #${row.id}.`)} />}
      <Journey step={state?.eligible ? 3 : 2} />
      <div className="detail-grid">
        <div className="detail-column">
          <section className="sheet">
            <div className="section-heading">
              <h2>Condições do vínculo</h2>
              <Badge value={value.administrative_status} />
            </div>
            <dl className="details-list">
              <div>
                <dt>Turma</dt>
                <dd>
                  <Link to={`/turmas/${value.class_group}`}>
                    {value.class_name}
                  </Link>
                </dd>
              </div>
              <div>
                <dt>Início</dt>
                <dd>{date(value.start_date)}</dd>
              </div>
              <div>
                <dt>Plano</dt>
                <dd>{label(value.plan)}</dd>
              </div>
              <div>
                <dt>Valor contratado</dt>
                <dd>{money(value.amount)}</dd>
              </div>
              <div>
                <dt>Tipo</dt>
                <dd>{label(value.kind)}</dd>
              </div>
            </dl>
            <div className="section-pad">
              <Notice tone="warning">
                {value.contract_version === 1 ? 'Valores e cronograma originais preservados. Suspensão e alterações contratuais exigem definição própria.' : 'Matrícula legada: vigência e cronograma não foram inferidos. Requer revisão das condições originais.'}
              </Notice>
            </div>
          </section>
          <EnrollmentConditions enrollmentId={id} />
        </div>
        <div>
          <section className="sheet eligibility-sheet">
            <div className="section-heading">
              <h2>Participação nas aulas</h2>
              <Button
                variant="ghost"
                onClick={() => void eligibility.refetch()}
                aria-label="Reavaliar participação"
              >
                <RefreshCw size={17} />
              </Button>
            </div>
            <div className="section-pad">
              {eligibility.isPending ? (
                <Loading />
              ) : eligibility.error ? (
                <ErrorNotice error={eligibility.error} />
              ) : (
                <>
                  <Badge value={state?.status || "pending"} />
                  <h3 className="eligibility-title">
                    {state?.reason ||
                      "A matrícula inicia pendente de liberação."}
                  </h3>
                  {state?.decisions?.length > 0 && (
                    <p className="muted">
                      Decisões necessárias: {state.decisions.join(", ")}
                    </p>
                  )}
                  <p className="period-note">
                    Avaliação em {date(today())}, horário de São Paulo. Cadastro
                    e pagamento isolados não comprovam participação.
                  </p>
                </>
              )}
            </div>
          </section>
          <section
            className="sheet charges-sheet"
            aria-label="Cobranças da matrícula"
          >
            <div className="section-heading">
              <h2>Cobranças da matrícula</h2>
              <Link className="text-link" to={`/financeiro?enrollment=${id}`}>
                <Plus size={16} />
                Gerir cobranças
              </Link>
            </div>
            {charges.isPending ? (
              <Loading />
            ) : charges.error ? (
              <div className="section-pad">
                <ErrorNotice error={charges.error} />
                <Button
                  variant="secondary"
                  onClick={() => void charges.refetch()}
                >
                  Tentar carregar cobranças novamente
                </Button>
                {chargePage > 1 && (
                  <Button variant="ghost" onClick={() => setChargePage(1)}>
                    Voltar à primeira página
                  </Button>
                )}
              </div>
            ) : !charges.data?.results.length ? (
              <Empty
                title="Nenhuma cobrança registrada"
                description="A geração automática depende das definições de plano e cobrança. Cobranças autorizadas podem ser registradas no financeiro."
                action={
                  <Link
                    className="button button--secondary"
                    to={`/financeiro?enrollment=${id}`}
                  >
                    Abrir financeiro <ArrowUpRight size={17} />
                  </Link>
                }
              />
            ) : (
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Finalidade</th>
                      <th>Vencimento</th>
                      <th>Valor</th>
                      <th>Situação</th>
                    </tr>
                  </thead>
                  <tbody>
                    {charges.data.results.map((charge) => (
                      <tr key={charge.id}>
                        <td>
                          <Link to={`/cobrancas/${charge.id}`}>
                            {label(charge.category)}
                          </Link>
                          <small>
                            {charge.competence ? date(charge.competence) : ""}
                          </small>
                        </td>
                        <td>{date(charge.due_date)}</td>
                        <td>{money(charge.amount)}</td>
                        <td>
                          <Badge value={charge.status} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            {!charges.isPending &&
              !charges.error &&
              charges.data &&
              (charges.data.count > 25 || chargePage > 1) && (
                <Pagination
                  page={chargePage}
                  count={charges.data.count}
                  onChange={setChargePage}
                />
              )}
          </section>
        </div>
      </div>
      {cancel && (
        <ActionForm
          title="Cancelar matrícula"
          endpoint={`enrollments/${id}/cancel/`}
          description="O cancelamento preserva dívidas e histórico. Não provoca devolução nem reativação automática por pagamento."
          fields={[
            {
              key: "reason",
              label: "Motivo do cancelamento",
              required: true,
              type: "textarea",
              wide: true,
            },
          ]}
          button="Confirmar cancelamento"
          onClose={() => setCancel(false)}
          onSaved={() =>
            setNotice(
              "Matrícula cancelada. Histórico e obrigações preservados.",
            )
          }
        />
      )}
    </>
  );
}
