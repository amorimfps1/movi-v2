import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { post } from './api';
import { date, money, timestamp, today } from './format';
import { Button, ErrorNotice, Field, Modal, Notice } from './ui';

export type EcoPayment = { id: number; amount: string; paid_on: string; method: string; reference: string; actor: number; voided_at: string | null; voided_by: number | null; void_reason: string; refunds: { id: number; amount: string; refunded_on: string; method: string; reference: string; reason: string; actor: number; created_at: string }[] };
type ActionOrder = { id: number; person_name: string; product_name: string; cancelled_at?: string | null; cancellation_mode?: string; charges: { status: string; amount: string; payment: EcoPayment | null }[] };
const cents = (value: string) => Math.round(Number(value) * 100);

export function FinancialHistory({ payments }: { payments: EcoPayment[] }) {
  return <details className="ecowork-history"><summary>Histórico financeiro ({payments.length} recebimentos)</summary>
    {payments.map(payment => <div key={payment.id}>
      <p><strong>Recebimento #{payment.id} · {money(payment.amount)}</strong> · {date(payment.paid_on)} · operador #{payment.actor}</p>
      {payment.voided_at && <p>Lançamento invalidado em {timestamp(payment.voided_at)} por #{payment.voided_by}: {payment.void_reason}</p>}
      {payment.refunds?.map(refund => <p key={refund.id}>Devolução #{refund.id}: {money(refund.amount)} em {date(refund.refunded_on)} · {refund.method} · {refund.reference || 'Sem referência'} · operador #{refund.actor}. Motivo: {refund.reason}</p>)}
    </div>)}
  </details>;
}

export function FinancialAction({ action, order, payment, onClose }: { action: 'cancel' | 'void' | 'refund'; order: ActionOrder; payment?: EcoPayment; onClose: () => void }) {
  const cache = useQueryClient();
  const [reason, setReason] = useState('');
  const [mode, setMode] = useState('');
  const available = payment ? cents(payment.amount) - (payment.refunds || []).reduce((sum, item) => sum + cents(item.amount), 0) : 0;
  const [amount, setAmount] = useState((available / 100).toFixed(2));
  const [refundedOn, setRefundedOn] = useState(today());
  const [method, setMethod] = useState('pix');
  const [reference, setReference] = useState('');
  const [confirmed, setConfirmed] = useState(false);
  const [key, setKey] = useState(() => crypto.randomUUID());
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<unknown>();
  const title = { cancel: 'Cancelar contratação', void: 'Corrigir lançamento', refund: 'Registrar devolução' }[action];
  const openAmount = order.charges.filter(c => ['open', 'overdue'].includes(c.status)).reduce((sum, c) => sum + cents(c.amount), 0) / 100;
  const change = () => { setKey(crypto.randomUUID()); setConfirmed(false); };
  return <Modal open title={title} onClose={() => !pending && onClose()}>
    <form onSubmit={async event => {
      event.preventDefault(); if (pending || !confirmed || !reason.trim() || (action === 'cancel' && !mode)) return;
      setPending(true); setError(undefined);
      try {
        const endpoint = action === 'cancel' ? `ecowork/orders/${order.id}/cancel/` : `ecowork/payments/${payment!.id}/${action}/`;
        await post(endpoint, { reason, ...(action === 'cancel' ? { mode } : action === 'refund' ? { amount, refunded_on: refundedOn, method, reference, request_key: key } : {}) });
        await cache.invalidateQueries(); onClose();
      } catch (err) { setError(err); } finally { setPending(false); }
    }}><fieldset disabled={pending} className="ecowork-fields">
      <p>{order.person_name} · {order.product_name} · contratação #{order.id}</p>
      {action === 'cancel' && <>
        <Field label="Parcelas não pagas"><select required value={mode} onChange={e => { setMode(e.target.value); change(); }}><option value="">Escolha o efeito financeiro</option><option value="keep_unpaid">Manter as cobranças</option><option value="cancel_unpaid">Cancelar as cobranças</option></select></Field>
        <Notice>A contratação será encerrada agora. Pagamentos e histórico serão preservados. Devoluções devem ser registradas separadamente.</Notice>
        {mode && <div className="ecowork-price"><span>{mode === 'keep_unpaid' ? 'Saldo que continuará a pagar' : 'Saldo de cobranças que será cancelado'}</span><strong>{money(openAmount)}</strong></div>}
      </>}
      {action === 'void' && <Notice>Use apenas para um recebimento lançado por engano. O lançamento original será preservado e a cobrança voltará a ficar pendente{order.cancelled_at && order.cancellation_mode === 'cancel_unpaid' ? ', sendo cancelada pela decisão já registrada no contrato' : ''}. Não registra devolução de dinheiro. Corrigir a primeira parcela remove o início da vigência e exige corrigir antes os pagamentos das demais parcelas.</Notice>}
      {action === 'refund' && <>
        <div className="ecowork-price"><span>Disponível para devolver</span><strong>{money(available / 100)}</strong></div>
        <Field label="Valor devolvido"><input type="number" min="0.01" max={(available / 100).toFixed(2)} step="0.01" required value={amount} onChange={e => { setAmount(e.target.value); change(); }} /></Field>
        <Field label="Data da devolução"><input type="date" min={payment?.paid_on} max={today()} required value={refundedOn} onChange={e => { setRefundedOn(e.target.value); change(); }} /></Field>
        <Field label="Meio da devolução"><select value={method} onChange={e => { setMethod(e.target.value); change(); }}>{[['pix', 'Pix'], ['cash', 'Dinheiro'], ['card', 'Cartão'], ['transfer', 'Transferência'], ['other', 'Outro']].map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></Field>
        <Field label="Referência da devolução"><input maxLength={160} value={reference} onChange={e => { setReference(e.target.value); change(); }} /></Field>
        <Notice>Registre somente o valor já devolvido. A cobrança continuará quitada e a cobertura do plano não será alterada. Esta ação não transfere dinheiro.</Notice>
      </>}
      <Field label="Motivo"><textarea required maxLength={2000} value={reason} onChange={e => { setReason(e.target.value); change(); }} /></Field>
      <label className="ecowork-check"><input type="checkbox" required checked={confirmed} onChange={e => setConfirmed(e.target.checked)} />{action === 'refund' ? 'Conferi a devolução efetiva deste valor.' : 'Conferi o motivo e o efeito desta operação.'}</label>
      <ErrorNotice error={error} />
      <div className="form-actions"><Button type="button" variant="secondary" onClick={onClose}>Voltar</Button><Button type="submit" disabled={!confirmed || !reason.trim() || (action === 'cancel' && !mode)}>{pending ? 'Registrando…' : title}</Button></div>
    </fieldset></form>
  </Modal>;
}
