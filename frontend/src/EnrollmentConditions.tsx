import { Link } from "react-router-dom";
import { useApi } from "./query";
import { Button, Empty, ErrorNotice, Loading } from "./ui";
import { date, label, money, timestamp } from "./format";

type CommercialCondition = {
  id: number;
  enrollment: number;
  amount: string;
  effective_on: string;
  plan: string;
  actor: number;
  reason: string;
  created_at: string;
};

export function EnrollmentConditions({
  enrollmentId,
}: {
  enrollmentId: string;
}) {
  const history = useApi<CommercialCondition[]>(
    `enrollments/${enrollmentId}/conditions/`,
  );

  return (
    <section className="sheet" aria-label="Histórico das condições comerciais">
      <div className="section-heading">
        <h2>Histórico das condições comerciais</h2>
      </div>
      <div className="section-pad">
        <p className="period-note">
          Valores e planos registrados para esta matrícula, com suas datas de
          efeito. Mudanças no preço da modalidade preservam este histórico.
        </p>
        <Link
          className="text-link"
          to={`/auditoria?target_type=billing.enrollment&target_id=${enrollmentId}`}
        >
          Consultar ações desta matrícula
        </Link>
      </div>
      {history.isPending ? (
        <Loading />
      ) : history.error ? (
        <div className="section-pad">
          <ErrorNotice error={history.error} />
          <Button variant="secondary" onClick={() => void history.refetch()}>
            Tentar carregar histórico novamente
          </Button>
        </div>
      ) : !history.data?.length ? (
        <Empty
          title="Nenhuma condição comercial registrada"
          description="Esta matrícula ainda não possui registros de condições comerciais no histórico."
        />
      ) : (
        history.data.map((condition) => (
          <article key={condition.id} aria-label={`Condição #${condition.id}`}>
            <div className="section-heading">
              <h3>A partir de {date(condition.effective_on)}</h3>
              <span className="count-label">#{condition.id}</span>
            </div>
            <dl className="details-list">
              <div>
                <dt>Plano registrado</dt>
                <dd>{label(condition.plan)}</dd>
              </div>
              <div>
                <dt>Valor registrado</dt>
                <dd>{money(condition.amount)}</dd>
              </div>
              <div>
                <dt>Responsável pelo registro</dt>
                <dd>
                  <Link to={`/acessos/${condition.actor}`}>
                    Conta #{condition.actor}
                  </Link>
                </dd>
              </div>
              <div>
                <dt>Registrado em</dt>
                <dd>{timestamp(condition.created_at)}</dd>
              </div>
              <div>
                <dt>Motivo</dt>
                <dd className="preserve-lines">
                  {condition.reason || "Não informado"}
                </dd>
              </div>
            </dl>
          </article>
        ))
      )}
    </section>
  );
}
