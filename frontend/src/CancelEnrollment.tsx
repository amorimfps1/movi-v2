import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { optionsFor, post } from './api';
import { useAuth } from './auth';
import { Button, ErrorNotice, Field, Loading, Modal, Notice } from './ui';
import { date, money, today } from './format';

export function CancelEnrollment({ id, onClose, onSaved }: { id: string; onClose: () => void; onSaved: () => void }) {
  const { user } = useAuth();
  const client = useQueryClient();
  const charges = useQuery({ queryKey: ['cancel-charges', id], queryFn: () => optionsFor(`charges/?enrollment=${id}`), retry: false });
  const [selected, setSelected] = useState<number[]>([]);
  const [reason, setReason] = useState('');
  const [effectiveOn, setEffectiveOn] = useState(today());
  const [confirmed, setConfirmed] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<unknown>();
  return <Modal open title="Cancelar matrícula" onClose={() => !pending && onClose()}><form onSubmit={(event) => {
    event.preventDefault(); setPending(true); setError(undefined);
    void post(`enrollments/${id}/cancel/`, { reason, effective_on: effectiveOn, charge_ids: selected, service_unprovided_confirmed: confirmed })
      .then(async () => { await client.invalidateQueries(); onSaved(); onClose(); }).catch(setError).finally(() => setPending(false));
  }}>
    <Notice tone="warning">A matrícula permanece ativa até a data escolhida. Obrigações já vencidas, pagas e referentes a serviços prestados permanecem no histórico. Parcelas selecionadas não poderão receber pagamentos enquanto aguardam o cancelamento.</Notice>
    <Field label="Data de efeito"><input type="date" required min={today()} value={effectiveOn} onChange={(event) => { setEffectiveOn(event.target.value); setSelected([]); setConfirmed(false); }} /></Field>
    {charges.isPending ? <Loading /> : charges.error ? <ErrorNotice error={charges.error} /> : user?.roles.includes('coordinator') && <fieldset><legend>Parcelas futuras não pagas a cancelar</legend>
      {charges.data?.filter((charge) => charge.category === 'tuition' && String(charge.due_date) > effectiveOn && Number(charge.received || 0) === 0 && !charge.cancelled_on).map((charge) => <label className="check-option" key={Number(charge.id)}><input type="checkbox" checked={selected.includes(Number(charge.id))} onChange={(event) => setSelected(event.target.checked ? [...selected, Number(charge.id)] : selected.filter((item) => item !== Number(charge.id)))} />{date(charge.due_date)} · {money(charge.amount)}</label>)}
      {selected.length > 0 && <label className="check-option"><input type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} required />Confirmo que as parcelas selecionadas se referem a serviços não prestados.</label>}
    </fieldset>}
    <Field label="Justificativa"><textarea required rows={3} value={reason} onChange={(event) => setReason(event.target.value)} /></Field><ErrorNotice error={error} />
    <div className="form-actions"><Button type="button" variant="secondary" onClick={onClose} disabled={pending}>Voltar</Button><Button type="submit" disabled={pending || charges.isPending || !!charges.error || !reason.trim() || (selected.length > 0 && !confirmed)}>Confirmar cancelamento</Button></div>
  </form></Modal>;
}
