import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useApi } from './query';
import { post } from './api';
import { ActionForm } from './forms';
import { Button, Notice, ErrorNotice, Confirm } from './ui';
import { timestamp } from './format';

type Message = {id: number; recipient: string; phone: string; text: string; url: string;
  actor: number; created_at: string; sent_at: string | null; confirmed_by: number | null};

export function CollectionMessages({chargeId}: {chargeId: string}) {
  const query = useApi<Message[]>(`charges/${chargeId}/messages/`);
  const client = useQueryClient();
  const [preparing, setPreparing] = useState(false);
  const [confirming, setConfirming] = useState<number | null>(null);
  return <section className="sheet section-pad">
    <h2>Comunicação de cobrança</h2>
    <Notice>Confira o responsável financeiro e o texto antes de abrir o WhatsApp. O envio é manual. Registre a confirmação somente após enviar.</Notice>
    <Button variant="secondary" onClick={() => setPreparing(true)}>Preparar mensagem</Button>
    <ErrorNotice error={query.error} />
    {query.data?.map(message => <article key={message.id} className="section-pad">
      <strong>{message.recipient} · {message.phone}</strong>
      <p>{message.text}</p>
      <p>Preparada em {timestamp(message.created_at)} · Conta #{message.actor}</p>
      {message.sent_at ? <p>Envio manual confirmado em {timestamp(message.sent_at)} · Conta #{message.confirmed_by}</p> : <div className="contract-actions">
        <a className="button button--secondary" href={message.url} target="_blank" rel="noopener noreferrer">Revisar no WhatsApp</a>
        <Button variant="secondary" onClick={() => setConfirming(message.id)}>Registrar que enviei</Button>
      </div>}
    </article>)}
    {query.data?.length === 0 && <p>Nenhuma mensagem registrada para esta cobrança.</p>}
    {preparing && <ActionForm title="Preparar cobrança por WhatsApp" endpoint={`charges/${chargeId}/messages/`}
      fields={[{key: 'recipient', label: 'Nome do responsável financeiro', required: true},
        {key: 'phone', label: 'WhatsApp com código do país e DDD', hint: 'Somente números. Confira o destinatário antes de continuar.', required: true}]}
      onClose={() => setPreparing(false)} />}
    {confirming !== null && <Confirm title="Confirmar envio manual?" description="Registra que você enviou esta mensagem pelo WhatsApp. Não comprova entrega ou leitura." confirm="Sim, enviei"
      onClose={() => setConfirming(null)} action={async () => {
        await post(`charges/${chargeId}/confirm_message/`, {message: confirming});
        await client.invalidateQueries();
      }} />}
  </section>;
}
