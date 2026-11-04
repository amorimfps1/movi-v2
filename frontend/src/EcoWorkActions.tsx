import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import type { RecordData } from './types';
import { post } from './api';
import { today } from './format';
import { Button, ErrorNotice, Field, Modal, Notice } from './ui';

export function EcoWorkActions({ endpoint, row }: { endpoint: string; row: RecordData }) {
  const cache = useQueryClient();
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState('');
  const [endsOn, setEndsOn] = useState(today());
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<unknown>();
  const residence = endpoint === 'residence-verifications/';
  if (!residence && endpoint !== 'condominium-associations/') return null;
  if (residence ? row.revoked_at : row.ends_on) return <Notice>Este registro possui encerramento registrado. O histórico foi preservado.</Notice>;
  return <section className="sheet section-pad">
    <h2>Manutenção do vínculo</h2>
    <p>{residence ? 'Ao mudar de endereço, encerre esta validação antes de conferir a nova residência.' : 'O encerramento impede novos descontos após a data informada. Contratos existentes preservam suas condições.'}</p>
    <Button variant="secondary" onClick={() => setOpen(true)}>{residence ? 'Encerrar validação' : 'Encerrar associação'}</Button>
    {open && <Modal open title={residence ? 'Encerrar validação de residência' : 'Encerrar associação'} onClose={() => !pending && setOpen(false)}><form onSubmit={async event => {
      event.preventDefault(); if (pending) return; setPending(true); setError(undefined);
      try { await post(`${endpoint}${row.id}/${residence ? 'revoke' : 'end'}/`, { reason, ...(!residence ? { ends_on: endsOn } : {}) }); await cache.invalidateQueries(); setOpen(false); }
      catch (err) { setError(err); } finally { setPending(false); }
    }}><fieldset className="ecowork-fields" disabled={pending}>
      {!residence && <Field label="Fim da associação" hint="Nesta data o condomínio já não concede novos descontos."><input type="date" required value={endsOn} onChange={e => setEndsOn(e.target.value)} /></Field>}
      <Field label="Justificativa"><textarea required maxLength={2000} value={reason} onChange={e => setReason(e.target.value)} /></Field>
      <ErrorNotice error={error} /><div className="form-actions"><Button type="button" variant="secondary" onClick={() => setOpen(false)}>Voltar</Button><Button type="submit">Confirmar encerramento</Button></div>
    </fieldset></form></Modal>}
  </section>;
}
