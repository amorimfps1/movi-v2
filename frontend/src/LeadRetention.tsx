import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useApi } from './query';
import { ActionForm } from './forms';
import { Button, ErrorNotice, Loading, Notice, PageTitle } from './ui';
import { date, label } from './format';

export function LeadRetention() {
  const query = useApi<{ results: { id: number; name: string; status: string; last_activity: string; review_due: string }[] }>('leads/retention-review/');
  const [reviewing, setReviewing] = useState<number | null>(null);
  const [success, setSuccess] = useState(false);
  return <><PageTitle eyebrow="CONTATOS" title="Revisão de contatos" description="Leads sem atividade há 12 meses são apresentados para revisão. Os registros são preservados." />
    {success && <Notice tone="success">Revisão registrada.</Notice>}
    <section className="sheet section-pad">{query.isPending ? <Loading /> : query.error ? <ErrorNotice error={query.error} /> : !Array.isArray(query.data?.results) ? <Notice tone="error">Não foi possível interpretar a lista de revisão.</Notice> : !query.data.results.length ? <p>Nenhum contato aguardando revisão.</p> :
      <div className="table-wrap"><table><thead><tr><th>Lead</th><th>Situação</th><th>Última atividade</th><th>Revisão desde</th><th>Ação</th></tr></thead><tbody>{query.data.results.map((row) => <tr key={row.id}><td><Link to={`/interessados/${row.id}`}>{row.name}</Link></td><td>{label(row.status)}</td><td>{date(row.last_activity)}</td><td>{date(row.review_due)}</td><td><Button variant="secondary" onClick={() => setReviewing(row.id)}>Registrar revisão</Button></td></tr>)}</tbody></table></div>}
    </section>
    {reviewing !== null && <ActionForm title="Registrar revisão do contato" endpoint={`leads/${reviewing}/review-retention/`} description="A revisão mantém o contato e registra a justificativa no histórico."
      fields={[{ key: 'reason', label: 'Resultado e motivo da revisão', type: 'textarea', required: true, wide: true }]} onClose={() => setReviewing(null)} onSaved={() => setSuccess(true)} />}
  </>;
}
