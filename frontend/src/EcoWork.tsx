import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { optionsFor, post } from './api';
import { useApi } from './query';
import { money, date, today } from './format';
import { Badge, Button, Empty, ErrorNotice, Field, Loading, Modal, Notice, PageTitle, Pagination } from './ui';
import type { Page } from './types';
import type { ResourceSpec } from './schema';
import { studentSpec } from './schema';
import './ecowork.css';
import { FinancialAction, FinancialHistory, type EcoPayment } from './EcoWorkFinancialActions';

type Person = { id: number; name: string; phone: string };
type Product = { code: string; name: string; price: string; months: number; max_installments: number };
type Quote = { total: string; base_price: string; discount_percent: number; reason: string; benefit_snapshot?: { discount?: string; after_resident?: string } };
type Charge = { id: number; number: number; amount: string; due_date: string; status: string; payment: EcoPayment | null; payments: EcoPayment[] };
type Order = { id: number; person: number; person_name: string; product_name: string; total: string; billing_mode: string; installments: number; discount_percent: number; benefit_snapshot?: { benefit?: number; discount?: string; after_resident?: string }; starts_on: string | null; ends_on: string | null; coverage_status: string; cancelled_at?: string | null; cancelled_by?: number; cancellation_reason?: string; cancellation_mode?: string; charges: Charge[] };
const coverage: Record<string, string> = { awaiting_payment: 'Aguardando pagamento', active: 'Plano vigente', expired: 'Plano encerrado', paid_use: 'Avulso pago', cancelled: 'Contrata??o cancelada' };

export const personSpec: ResourceSpec = {
  ...studentSpec, title: 'Pessoas', singular: 'pessoa', slug: 'pessoas', endpoint: 'people/',
  description: 'Cadastro compartilhado entre atividades acadêmicas e EcoWork.',
  columns: studentSpec.columns.map(c => c.key === 'name' ? { ...c, label: 'Pessoa' } : c),
  filters: [...(studentSpec.filters || []),
    { key: 'has_enrollments', label: 'Matrícula acadêmica', options: [{ value: 'true', label: 'Com matrícula' }, { value: 'false', label: 'Sem matrícula' }] },
    { key: 'has_ecowork', label: 'Contratação EcoWork', options: [{ value: 'true', label: 'Com contratação' }, { value: 'false', label: 'Sem contratação' }] },
  ],
};
export const condominiumSpec: ResourceSpec = {
  title: 'Condomínios', singular: 'condomínio', slug: 'condominios', endpoint: 'condominiums/',
  description: 'Cadastre o condomínio e mantenha seus períodos de associação separadamente.',
  fields: [{ key: 'name', label: 'Nome', required: true }, { key: 'active', label: 'Cadastro ativo', type: 'check', default: true }],
  columns: [{ key: 'name', label: 'Condomínio' }, { key: 'active', label: 'Cadastro ativo', render: row => row.active ? 'Sim' : 'Não' }],
};
export const associationSpec: ResourceSpec = {
  title: 'Associações', singular: 'período de associação', slug: 'associacoes', endpoint: 'condominium-associations/', editable: false,
  description: 'Períodos que habilitam o desconto dos moradores. A data final não está incluída.',
  fields: [{ key: 'condominium', label: 'Condomínio', type: 'select', lookup: 'condominiums/?active=true', required: true }, { key: 'starts_on', label: 'Início', type: 'date', required: true }, { key: 'ends_on', label: 'Fim (opcional)', type: 'date' }],
  columns: [{ key: 'condominium_name', label: 'Condomínio' }, { key: 'starts_on', label: 'Início', render: row => date(row.starts_on) }, { key: 'ends_on', label: 'Fim', render: row => date(row.ends_on) }],
};
export const residenceSpec: ResourceSpec = {
  title: 'Residências', singular: 'validação de residência', slug: 'residencias', endpoint: 'residence-verifications/', editable: false,
  description: 'Registre a declaração e a conferência do comprovante. Não é necessário anexar documentos.',
  fields: [{ key: 'person', label: 'Pessoa', type: 'select', lookup: 'people/?archived=false', required: true }, { key: 'condominium', label: 'Condomínio', type: 'select', lookup: 'condominiums/?active=true', required: true }, { key: 'declared', label: 'A pessoa declarou residência neste condomínio', type: 'check' }, { key: 'proof_checked', label: 'Conferi o comprovante de residência', type: 'check' }],
  columns: [{ key: 'person_name', label: 'Pessoa' }, { key: 'condominium_name', label: 'Condomínio' }, { key: 'verified_at', label: 'Conferido em', render: row => date(row.verified_at) }, { key: 'revoked_at', label: 'Situação', render: row => row.revoked_at ? 'Encerrada' : 'Validada' }],
};

export function EcoWork() {
  const [urlParams, setUrlParams] = useSearchParams();
  const allowed = ['search', 'person', 'coverage', 'status', 'due_from', 'due_to', 'page'];
  const params = new URLSearchParams([...urlParams].filter(([key]) => allowed.includes(key)));
  const rawPage = Number(params.get('page') || 1);
  const page = Number.isSafeInteger(rawPage) && rawPage > 0 ? rawPage : 1;
  params.set('page', String(page));
  function change(key: string, value: string) {
    const next = new URLSearchParams(params);
    next.delete('page');
    if (value) next.set(key, value); else next.delete(key);
    setUrlParams(next);
  }
  const setPage = (value: number) => change('page', String(value));
  const [financialAction, setFinancialAction] = useState<{ action: 'cancel' | 'void' | 'refund'; order: Order; payment?: EcoPayment }>();
  const [creating, setCreating] = useState(false);
  const [payment, setPayment] = useState<{ charge: Charge; order: Order }>();
  const query = useApi<Page<Order>>(`ecowork/orders/?${params}`);
  return <>
    <PageTitle eyebrow="ECOWORK" title="Planos e recebimentos" description="Consulte a cobertura e confira cada pagamento antes de registrar." actions={<Button onClick={() => setCreating(true)}>Contratar plano ou avulso</Button>} />
    <nav className="ecowork-links" aria-label="Cadastros EcoWork">
      <Link to="/pessoas">Pessoas</Link><Link to="/condominios">Condomínios</Link><Link to="/associacoes">Associações</Link><Link to="/residencias">Residências</Link>
    </nav>
    {params.get('person') && <Notice>Consulta da pessoa #{params.get('person')}. <Link to={`/pessoas/${params.get('person')}`}>Abrir cadastro e saldo total</Link></Notice>}
    <div className="ecowork-fields ecowork-filters">
      <Field label="Buscar por pessoa ou produto"><input type="search" placeholder="Nome do frequentador" value={params.get('search') || ''} onChange={e => change('search', e.target.value)} /></Field>
      <Field label="Cobertura"><select value={params.get('coverage') || ''} onChange={e => change('coverage', e.target.value)}><option value="">Todas</option>{Object.entries(coverage).map(([value, name]) => <option key={value} value={value}>{name}</option>)}</select></Field>
      <Field label="Situação da parcela"><select value={params.get('status') || ''} onChange={e => change('status', e.target.value)}><option value="">Todas</option><option value="paid">Paga</option><option value="open">A vencer</option><option value="overdue">Vencida</option><option value="cancelled">Cancelada</option></select></Field>
      <Field label="Vencimento a partir de"><input type="date" value={params.get('due_from') || ''} onChange={e => change('due_from', e.target.value)} /></Field>
      <Field label="Vencimento até"><input type="date" value={params.get('due_to') || ''} onChange={e => change('due_to', e.target.value)} /></Field>
    </div>
    <p>Os filtros de parcela e vencimento encontram contratações com ao menos uma parcela correspondente. Todas as parcelas do contrato permanecem visíveis.</p>
    {[...params.keys()].some(key => key !== 'page') && <Button variant="secondary" onClick={() => setUrlParams({})}>Limpar filtros</Button>}
    <ErrorNotice error={query.error} />
    {query.isError && <Button variant="secondary" onClick={() => void query.refetch()}>Tentar novamente</Button>}
    {query.isError && page > 1 && <Button variant="secondary" onClick={() => setPage(1)}>Voltar à primeira página</Button>}
    {query.isPending && <Loading />}
    {query.data && !query.data.results.length && <Empty title="Nenhuma contratação encontrada" description="Cadastre a pessoa e registre o plano ou o uso avulso." />}
    <div className="ecowork-orders">{query.data?.results.map(order => {
      const open = order.charges.filter(c => ['open', 'overdue'].includes(c.status));
      const overdue = open.some(c => c.status === 'overdue');
      return <article className="ecowork-order" key={order.id}>
        <header><div><h2><Link to={`/pessoas/${order.person}`}>{order.person_name}</Link></h2><p>{order.product_name} · contratação #{order.id}</p></div><Badge value={order.coverage_status === 'active' ? 'regular' : 'neutral'}>{coverage[order.coverage_status]}</Badge></header>
        {order.cancelled_at ? <Notice>Cancelada em {date(order.cancelled_at)} por #{order.cancelled_by}. {order.cancellation_mode === 'keep_unpaid' ? 'Cobran?as n?o pagas mantidas.' : 'Cobran?as n?o pagas canceladas.'} Motivo: {order.cancellation_reason}</Notice> : <Button variant="secondary" onClick={() => setFinancialAction({ action: 'cancel', order })}>Cancelar contrato</Button>}
        <dl className="ecowork-facts">
          <div><dt>Total contratado</dt><dd>{money(order.total)}</dd></div>
          <div><dt>Desconto de associado</dt><dd>{order.discount_percent}%</dd></div>
          {order.benefit_snapshot?.benefit && <div><dt>Benefício individual #{order.benefit_snapshot.benefit}</dt><dd>{money(order.benefit_snapshot.discount)} sobre {money(order.benefit_snapshot.after_resident)} após desconto de morador</dd></div>}
          <div><dt>Vigência</dt><dd>{order.starts_on ? `Início: ${date(order.starts_on)}${order.ends_on ? ` · encerra em ${date(order.ends_on)}` : ''}` : order.cancelled_at ? 'Contrata??o cancelada' : 'Inicia no primeiro pagamento'}</dd></div>
          <div><dt>Saldo a pagar pelo cliente</dt><dd>{money(open.reduce((sum, c) => sum + Number(c.amount), 0))}{overdue && <Badge value="overdue">Há vencimentos em atraso</Badge>}</dd></div>
        </dl>
        {order.billing_mode === 'card' && <p>Compra no cartão em {order.installments}x. A confirmação abaixo registra a compra aprovada, não os repasses da operadora.</p>}
        <div className="table-scroll" tabIndex={0} role="region" aria-label={`Parcelas de ${order.person_name}`}><table><thead><tr><th>Cobrança</th><th>Vencimento</th><th>Valor</th><th>Situação</th><th>Recebimento</th></tr></thead><tbody>{order.charges.map(charge => <tr key={charge.id}>
          <td>{order.billing_mode === 'card' ? 'Compra no cartão' : `Parcela ${charge.number}/${order.charges.length}`}</td><td>{date(charge.due_date)}</td><td>{money(charge.amount)}</td><td><Badge value={charge.status} /></td>
          <td>{charge.payment ? <span>Confirmado em {date(charge.payment.paid_on)}<small>Operador #{charge.payment.actor} · {charge.payment.reference || charge.payment.method}</small></span> : charge.status === 'cancelled' ? <span>Cobran?a cancelada</span> : <Button variant="secondary" disabled={charge.number > 1 && !order.charges.some(c => c.number === 1 && c.payment)} onClick={() => setPayment({ order, charge })}>Registrar pagamento</Button>}
          {charge.payment && <div className="ecowork-financial-buttons">
            {!(charge.payment.refunds?.length) && <Button variant="secondary" onClick={() => setFinancialAction({ action: 'void', order, payment: charge.payment! })}>Corrigir lan?amento</Button>}
            {Math.round(Number(charge.payment.amount) * 100) > (charge.payment.refunds || []).reduce((sum, refund) => sum + Math.round(Number(refund.amount) * 100), 0) && <Button variant="secondary" onClick={() => setFinancialAction({ action: 'refund', order, payment: charge.payment! })}>Registrar devolu??o</Button>}
          </div>}
          </td>
        </tr>)}</tbody></table></div>
        <FinancialHistory payments={order.charges.flatMap(c => c.payments || [])} />
      </article>;
    })}</div>
    {query.data && <Pagination page={page} count={query.data.count} onChange={setPage} />}
    {financialAction && <FinancialAction {...financialAction} onClose={() => setFinancialAction(undefined)} />}
    {creating && <CreateOrder onClose={() => setCreating(false)} />}
    {payment && <ReceivePayment {...payment} onClose={() => setPayment(undefined)} />}
  </>;
}

function CreateOrder({ onClose }: { onClose: () => void }) {
  const cache = useQueryClient();
  const [search, setSearch] = useState('');
  const [person, setPerson] = useState<Person>();
  const [product, setProduct] = useState('monthly');
  const [benefit, setBenefit] = useState('');
  const [mode, setMode] = useState('cash');
  const [installments, setInstallments] = useState(1);
  const [due, setDue] = useState(today());
  const [key, setKey] = useState(() => crypto.randomUUID());
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<unknown>();
  const people = useApi<Page<Person>>(`people/?archived=false&search=${encodeURIComponent(search)}`);
  const products = useApi<Product[]>('ecowork/products/');
  useEffect(() => {
    if (products.data && !products.data.some((item) => item.code === product)) {
      setProduct(products.data[0]?.code || '');
      setMode('cash'); setInstallments(1); setKey(crypto.randomUUID());
    }
  }, [products.data, product]);
  const selected = products.data?.find(p => p.code === product);
  const benefits = useQuery({ queryKey: ['eco-benefits', person?.id], queryFn: () => optionsFor(`benefits/?person=${person!.id}&scope=ecowork&status=approved`), enabled: !!person, retry: false });
  const pricing = useQuery({ queryKey: ['ecowork-quote', person?.id, product, benefit], queryFn: () => post<Quote>('ecowork/quote/', { person: person!.id, product, ...(benefit ? { benefit: Number(benefit) } : {}) }), enabled: !!person && !!selected, retry: false });
  const change = () => { setKey(crypto.randomUUID()); setError(undefined); };
  return <Modal open title="Contratar plano ou avulso" onClose={() => !pending && onClose()}>
    <form onSubmit={async e => { e.preventDefault(); if (!person || !pricing.data || pending) return; setPending(true); setError(undefined); try {
      const waived = Number(pricing.data.total) === 0;
      await post('ecowork/orders/', { person: person.id, product, quantity: 1, billing_mode: waived ? 'cash' : mode, installments: waived ? 1 : installments, first_due: waived ? today() : due, expected_total: pricing.data.total, request_key: key, ...(benefit ? { benefit: Number(benefit) } : {}) });
      await cache.invalidateQueries(); onClose();
    } catch (err) { setError(err); } finally { setPending(false); } }}>
      <fieldset disabled={pending} className="ecowork-fields">
        <Field label="Buscar pessoa"><input value={search} onChange={e => setSearch(e.target.value)} placeholder="Digite o nome" /></Field>
        <ErrorNotice error={people.error} />
        <Field label="Pessoa"><select required value={person?.id || ''} onChange={e => { setPerson(people.data?.results.find(p => p.id === Number(e.target.value))); setBenefit(''); change(); }}><option value="">Selecione uma pessoa</option>{person && !people.data?.results.some(p => p.id === person.id) && <option value={person.id}>{person.name}</option>}{people.data?.results.map(p => <option key={p.id} value={p.id}>{p.name} · {p.phone || `#${p.id}`}</option>)}</select></Field>
        <Link to="/pessoas">Cadastrar uma pessoa</Link>
        <ErrorNotice error={products.error} />
        <Field label="Produto"><select value={product} onChange={e => { setProduct(e.target.value); setBenefit(''); setMode('cash'); setInstallments(1); change(); }}>{products.data?.map(p => <option key={p.code} value={p.code}>{p.name} · {money(p.price)}</option>)}</select></Field>
        {!!selected?.months && person && <Field label="Benefício individual aprovado"><select value={benefit} onChange={e => { setBenefit(e.target.value); change(); }}><option value="">Nenhum</option>{benefits.data?.map(item => <option key={Number(item.id)} value={String(item.id)}>#{String(item.id)} · {String(item.value)}{item.kind === 'percent' ? '%' : ' reais'} · até {date(item.ends_on)}</option>)}</select></Field>}
        <ErrorNotice error={benefits.error} />
        {(!pricing.data || Number(pricing.data.total) !== 0) && <><Field label="Forma de cobrança"><select value={mode} onChange={e => { setMode(e.target.value); setInstallments(1); change(); }}><option value="cash">À vista</option>{!!selected && selected.max_installments > 1 && <><option value="office">Parcelas pela secretaria</option><option value="card">Cartão parcelado</option></>}</select></Field>
        {mode !== 'cash' && <Field label="Número de parcelas"><input type="number" required min={1} max={selected?.max_installments || 1} value={installments} onChange={e => { setInstallments(Number(e.target.value)); change(); }} /></Field>}
        <Field label="Primeiro vencimento"><input type="date" required value={due} onChange={e => { setDue(e.target.value); change(); }} /></Field></>}
        <ErrorNotice error={pricing.error} />
        {pricing.isFetching && person && <Loading />}
        {pricing.data && <div className="ecowork-price"><span>Total contratado</span><strong>{money(pricing.data.total)}</strong><small>{pricing.data.discount_percent ? `${pricing.data.discount_percent}% de desconto de associado` : pricing.data.reason}</small></div>}
        {pricing.data?.benefit_snapshot?.discount && <p>Benefício individual: {money(pricing.data.benefit_snapshot.discount)} sobre {money(pricing.data.benefit_snapshot.after_resident)} após o desconto de morador.</p>}
        <Notice>{pricing.data && Number(pricing.data.total) === 0 ? 'O plano começa na contratação, sem cobrança ou pagamento.' : selected?.months ? 'A vigência começa na confirmação do primeiro pagamento. Contratar ainda não significa pagar.' : 'Confirme o pagamento integral antes do uso do espaço.'}</Notice>
        <ErrorNotice error={error} />
        <div className="form-actions"><Button type="button" variant="secondary" onClick={onClose}>Cancelar</Button><Button disabled={!person || !pricing.data || pricing.isFetching || pricing.isError || !selected} type="submit">{pending ? 'Registrando…' : 'Confirmar contratação'}</Button></div>
      </fieldset>
    </form>
  </Modal>;
}

function ReceivePayment({ charge, order, onClose }: { charge: Charge; order: Order; onClose: () => void }) {
  const cache = useQueryClient();
  const [paidOn, setPaidOn] = useState(today());
  const [method, setMethod] = useState(order.billing_mode === 'card' ? 'card' : 'pix');
  const [reference, setReference] = useState('');
  const [confirmed, setConfirmed] = useState(false);
  const [key, setKey] = useState(() => crypto.randomUUID());
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<unknown>();
  const change = () => setKey(crypto.randomUUID());
  return <Modal open title="Confirmar recebimento" onClose={() => !pending && onClose()}><form onSubmit={async e => { e.preventDefault(); if (!confirmed || pending) return; setPending(true); setError(undefined); try {
    await post(`ecowork/charges/${charge.id}/receive/`, { amount: charge.amount, paid_on: paidOn, method, reference, request_key: key });
    await cache.invalidateQueries(); onClose();
  } catch (err) { setError(err); } finally { setPending(false); } }}><fieldset disabled={pending} className="ecowork-fields">
    <p>{order.person_name} · {order.product_name}</p><div className="ecowork-price"><span>Valor integral desta cobrança</span><strong>{money(charge.amount)}</strong></div>
    <Field label="Data do pagamento"><input type="date" value={paidOn} max={today()} required onChange={e => { setPaidOn(e.target.value); change(); }} /></Field>
    <Field label="Meio de pagamento"><select value={method} onChange={e => { setMethod(e.target.value); change(); }}>{(order.billing_mode === 'card' ? [['card', 'Cartão']] : [['pix', 'Pix'], ['cash', 'Dinheiro'], ['card', 'Cartão'], ['transfer', 'Transferência'], ['other', 'Outro']]).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></Field>
    <Field label="Referência do pagamento" hint={order.billing_mode === 'card' ? 'Informe a referência da compra aprovada no cartão.' : 'Opcional.'}><input maxLength={160} required={order.billing_mode === 'card'} value={reference} onChange={e => { setReference(e.target.value); change(); }} /></Field>
    <label className="ecowork-check"><input type="checkbox" required checked={confirmed} onChange={e => setConfirmed(e.target.checked)} />{order.billing_mode === 'card' ? 'Conferi a aprovação da compra no cartão.' : 'Conferi o recebimento integral deste valor.'}</label>
    <ErrorNotice error={error} /><div className="form-actions"><Button type="button" variant="secondary" onClick={onClose}>Cancelar</Button><Button type="submit" disabled={!confirmed}>{pending ? 'Registrando…' : 'Confirmar pagamento'}</Button></div>
  </fieldset></form></Modal>;
}
