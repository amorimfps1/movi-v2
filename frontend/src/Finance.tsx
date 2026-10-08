import { useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import {
  ChevronLeft,
  Wallet,
  ArrowUpRight,
  ReceiptText,
  Check,
} from "lucide-react";
import { useApi } from "./query";
import type { RecordData, Page, Summary } from "./types";
import { chargeSpec, paymentSpec, paymentMethods } from "./schema";
import { ResourceList } from "./resources";
import { ActionForm } from "./forms";
import {
  PageTitle,
  Button,
  Notice,
  ErrorNotice,
  Loading,
  Badge,
  Empty,
} from "./ui";
import { date, money, label, today, monthStart, timestamp } from "./format";
export function ReceiveForm({
  charge,
  onClose,
  onSaved,
}: {
  charge: RecordData;
  onClose: () => void;
  onSaved: () => void;
}) {
  return (
    <ActionForm
      title="Confirmar recebimento"
      endpoint={`charges/${charge.id}/receive/`}
      description={`Confira o recebimento de ${String(charge.student_name)}. Devido: ${money(charge.amount)}. Enquanto DN-008 estiver pendente, a baixa exige valor exato. O registro preserva a situação administrativa da matrícula.`}
      fields={[
        {
          key: "amount",
          label: "Valor efetivamente recebido (R$)",
          type: "decimal",
          required: true,
          default: String(charge.amount),
        },
        {
          key: "paid_on",
          label: "Data do recebimento",
          type: "date",
          required: true,
          default: today(),
        },
        {
          key: "method",
          label: "Forma de recebimento",
          type: "select",
          required: true,
          options: paymentMethods,
        },
        {
          key: "reference",
          label: "Referência / comprovante",
          hint: "Identificação do recebimento, quando houver.",
        },
      ]}
      button="Registrar recebimento"
      onClose={onClose}
      onSaved={onSaved}
    />
  );
}
export function Finance({ payments = false }: { payments?: boolean }) {
  const [urlParams] = useSearchParams();
  const summaryStart = urlParams.get("start") || monthStart();
  const summaryEnd = urlParams.get("end") || today();
  const periodQuery = new URLSearchParams(
    ["start", "end"]
      .filter((key) => urlParams.get(key))
      .map((key) => [key, urlParams.get(key)!]),
  ).toString();
  const [receiving, setReceiving] = useState<RecordData | null>(null);
  const [success, setSuccess] = useState("");
  const summary = useApi<Summary>(
    `reports/summary/?${new URLSearchParams({ start: summaryStart, end: summaryEnd })}`,
  );
  return (
    <>
      {success && <Notice tone="success">{success}</Notice>}
      <ResourceList
        key={payments ? "payments" : "charges"}
        spec={payments ? paymentSpec : { ...chargeSpec, title: "Financeiro" }}
        extraActions={
          payments
            ? undefined
            : (row) =>
                row.status !== "paid" && (
                  <Button
                    variant="ghost"
                    onClick={() => setReceiving(row)}
                    aria-label={`Receber cobrança de ${row.student_name}`}
                  >
                    <Wallet size={17} />
                    <span className="row-action-label">Receber</span>
                  </Button>
                )
        }
        beforeList={
          <>
            <nav className="section-tabs" aria-label="Rotinas financeiras">
              <Link
                to={`/financeiro${periodQuery ? `?${periodQuery}` : ""}`}
                className={
                  !payments ? "section-tab section-tab--active" : "section-tab"
                }
              >
                Cobranças
              </Link>
              <Link
                to={`/recebimentos${periodQuery ? `?${periodQuery}` : ""}`}
                className={
                  payments ? "section-tab section-tab--active" : "section-tab"
                }
              >
                Recebimentos
              </Link>
            </nav>
            <section className="finance-overview">
              <div>
                <span>Recebido no período</span>
                <strong>
                  {summary.data ? money(summary.data.received) : "—"}
                </strong>
                <small>Data de recebimento</small>
              </div>
              <div>
                <span>Previsto no período</span>
                <strong>
                  {summary.data ? money(summary.data.expected) : "—"}
                </strong>
                <small>Data de vencimento</small>
              </div>
              <div>
                <span>Saldo a receber</span>
                <strong>
                  {summary.data ? money(summary.data.outstanding) : "—"}
                </strong>
                <small>Das cobranças do período</small>
              </div>
              <div>
                <span>Saldo vencido</span>
                <strong className="text-warning">
                  {summary.data ? money(summary.data.overdue) : "—"}
                </strong>
                <small>Das cobranças do período</small>
              </div>
            </section>
            <p className="period-note finance-period">
              Indicadores gerais de {date(summaryStart)} a {date(summaryEnd)}. A
              lista abaixo usa os filtros selecionados.{" "}
              <Link to="/relatorios">Consultar outras datas e definições</Link>
            </p>
            <ErrorNotice error={summary.error} />
            {!payments && (
              <Notice tone="warning">
                <strong>Geração automática indisponível.</strong> Periodicidade,
                cobertura e horizonte de cobranças aguardam decisão: DN-004,
                DN-005 e DN-006. Os lançamentos abaixo são obrigações
                registradas.
              </Notice>
            )}
          </>
        }
      />
      {receiving && (
        <ReceiveForm
          charge={receiving}
          onClose={() => setReceiving(null)}
          onSaved={() =>
            setSuccess(
              "Recebimento registrado. Consulte a elegibilidade da matrícula para verificar participação.",
            )
          }
        />
      )}
    </>
  );
}
export function ChargeDetail() {
  const { id } = useParams();
  const query = useApi<RecordData>(`charges/${id}/`);
  const payments = useApi<Page<RecordData>>(`payments/?charge=${id}`);
  const [receiving, setReceiving] = useState(false);
  const [success, setSuccess] = useState("");
  if (query.isPending) return <Loading />;
  if (query.error) return <ErrorNotice error={query.error} />;
  if (!query.data) return null;
  const row = query.data;
  return (
    <>
      <Link className="back-link" to="/financeiro">
        <ChevronLeft size={16} />
        Todas as cobranças
      </Link>
      <PageTitle
        eyebrow={`COBRANÇA · #${id}`}
        title={String(row.student_name)}
        description={`${label(row.category)} · ${String(row.class_name)}`}
        actions={
          row.status !== "paid" && (
            <Button onClick={() => setReceiving(true)}>
              <Wallet size={17} />
              Registrar recebimento
            </Button>
          )
        }
      />
      {success && <Notice tone="success">{success}</Notice>}
      <section className="charge-summary">
        <div>
          <span>Valor devido</span>
          <strong>{money(row.amount)}</strong>
        </div>
        <div>
          <span>Valor recebido</span>
          <strong>{money(row.received)}</strong>
        </div>
        <div>
          <span>Situação da obrigação</span>
          <Badge value={row.status} />
        </div>
        <div>
          <span>Vencimento</span>
          <strong className="charge-date">{date(row.due_date)}</strong>
        </div>
      </section>
      <div className="detail-grid">
        <section className="sheet">
          <div className="section-heading">
            <h2>Origem da obrigação</h2>
            <ReceiptText size={20} />
          </div>
          <dl className="details-list">
            <div>
              <dt>Matrícula</dt>
              <dd>
                <Link to={`/matriculas/${row.enrollment}`}>
                  Matrícula #{String(row.enrollment)} <ArrowUpRight size={14} />
                </Link>
              </dd>
            </div>
            <div>
              <dt>Finalidade</dt>
              <dd>{label(row.category)}</dd>
            </div>
            <div>
              <dt>Competência</dt>
              <dd>{date(row.competence)}</dd>
            </div>
            <div>
              <dt>Descrição</dt>
              <dd className="preserve-lines">
                {String(row.description || "Sem descrição.")}
              </dd>
            </div>
            <div>
              <dt>Registro</dt>
              <dd>{timestamp(row.created_at)}</dd>
            </div>
          </dl>
        </section>
        <div>
          <Notice tone="warning">
            <strong>Recebimento não equivale à liberação.</strong> Taxa de
            matrícula isolada não libera participação. A cobertura temporal de
            mensalidades e cobranças esperadas depende de DN-004 e DN-006.{" "}
            <Link to={`/matriculas/${row.enrollment}`}>
              Consultar elegibilidade da matrícula
            </Link>
            .
          </Notice>
          <section className="sheet">
            <div className="section-heading">
              <h2>Recebimentos registrados</h2>
            </div>
            {payments.isPending ? (
              <Loading />
            ) : payments.error ? (
              <ErrorNotice error={payments.error} />
            ) : !payments.data?.results.length ? (
              <Empty
                title="Ainda sem recebimento"
                description="Registre somente um valor efetivamente recebido e confira a data e a forma de pagamento."
              />
            ) : (
              <div className="enrollment-list">
                {payments.data.results.map((payment) => (
                  <Link
                    key={payment.id}
                    className="enrollment-item"
                    to={`/recebimentos/${payment.id}`}
                  >
                    <div>
                      <h3>{money(payment.amount)}</h3>
                      <p>
                        {date(payment.paid_on)} ·{" "}
                        {paymentMethods.find(
                          (method) => method.value === payment.method,
                        )?.label || String(payment.method)}
                      </p>
                      <small>
                        {String(
                          payment.reference || "Sem referência informada",
                        )}
                      </small>
                    </div>
                    <Check size={20} />
                  </Link>
                ))}
              </div>
            )}
          </section>
          <p className="period-note">
            Correções, estornos e pagamentos parciais ou excedentes aguardam
            política aprovada. DN-008 e RN-048. O histórico é preservado.
          </p>
        </div>
      </div>
      {receiving && (
        <ReceiveForm
          charge={row}
          onClose={() => setReceiving(false)}
          onSaved={() =>
            setSuccess(
              "Recebimento registrado com sucesso. A situação administrativa da matrícula foi preservada.",
            )
          }
        />
      )}
    </>
  );
}
export function PaymentDetail() {
  const { id } = useParams();
  const query = useApi<RecordData>(`payments/${id}/`);
  if (query.isPending) return <Loading />;
  if (query.error) return <ErrorNotice error={query.error} />;
  if (!query.data) return null;
  const row = query.data;
  return (
    <>
      <Link className="back-link" to="/recebimentos">
        <ChevronLeft size={16} />
        Todos os recebimentos
      </Link>
      <PageTitle
        eyebrow={`RECEBIMENTO · #${id}`}
        title={money(row.amount)}
        description={`Recebido de ${String(row.student_name)} em ${date(row.paid_on)}.`}
      />
      <div className="detail-grid">
        <section className="sheet">
          <div className="section-heading">
            <h2>Comprovante do registro</h2>
            <Badge value="paid">Registrado</Badge>
          </div>
          <dl className="details-list">
            <div>
              <dt>Cobrança de origem</dt>
              <dd>
                <Link to={`/cobrancas/${row.charge}`}>
                  Cobrança #{String(row.charge)} <ArrowUpRight size={14} />
                </Link>
              </dd>
            </div>
            <div>
              <dt>Categoria</dt>
              <dd>{label(row.category)}</dd>
            </div>
            <div>
              <dt>Forma</dt>
              <dd>
                {paymentMethods.find((method) => method.value === row.method)
                  ?.label || String(row.method)}
              </dd>
            </div>
            <div>
              <dt>Referência</dt>
              <dd>{String(row.reference || "Não informada")}</dd>
            </div>
            <div>
              <dt>Responsável pelo registro</dt>
              <dd>Conta #{String(row.actor)}</dd>
            </div>
            <div>
              <dt>Registrado em</dt>
              <dd>{timestamp(row.created_at)}</dd>
            </div>
          </dl>
        </section>
        <Notice tone="warning">
          Este registro é preservado no histórico. Correção ou estorno requer
          política institucional definida: RN-048 e DN-008.
        </Notice>
      </div>
    </>
  );
}
