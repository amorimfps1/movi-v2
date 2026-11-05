import { Link } from 'react-router-dom';
import { useApi } from './query';
import { money } from './format';
import { Button, ErrorNotice, Loading } from './ui';

type Summary = { total: string; paid: string; balance: string; overdue: string; orders: number; refunded: string; net_paid: string };

export function PersonOverview({ id }: { id: string }) {
  const query = useApi<Summary>(`ecowork/orders/summary/?person=${id}`);
  return <section className="sheet section-pad">
    <h2>Vínculos e financeiro</h2>
    <p>O resumo EcoWork considera todas as contratações desta pessoa, incluindo pendências anteriores.</p>
    <ErrorNotice error={query.error} />
    {query.isPending && <Loading />}
    {query.isError && <Button variant="secondary" onClick={() => void query.refetch()}>Tentar novamente</Button>}
    {query.data && <dl className="details-list">
      <div><dt>Contratações EcoWork</dt><dd>{query.data.orders}</dd></div>
      <div><dt>Total de cobran?as n?o canceladas</dt><dd>{money(query.data.total)}</dd></div>
      <div><dt>Pagamentos confirmados do cliente</dt><dd>{money(query.data.paid)}</dd></div>
      <div><dt>Devolu??es registradas</dt><dd>{money(query.data.refunded)}</dd></div>
      <div><dt>Recebido ap?s devolu??es</dt><dd>{money(query.data.net_paid)}</dd></div>
      <div><dt>Saldo total em aberto</dt><dd>{money(query.data.balance)}</dd></div>
      <div><dt>Do saldo, vencido</dt><dd>{money(query.data.overdue)}</dd></div>
    </dl>}
    <nav className="ecowork-links" aria-label="Vínculos da pessoa">
      <Link to={`/ecowork?person=${id}`}>Contratações e parcelas EcoWork</Link>
      <Link to={`/alunos/${id}`}>Matrículas e ficha acadêmica</Link>
    </nav>
  </section>;
}
