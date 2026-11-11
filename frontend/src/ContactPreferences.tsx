import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { optionsFor } from './api';
import { ActionForm } from './forms';
import { Button, ErrorNotice, Loading } from './ui';
import { timestamp } from './format';

export function ContactPreferences({ kind, id }: { kind: 'lead' | 'person'; id: string }) {
  const [editing, setEditing] = useState(false);
  const query = useQuery({ queryKey: ['contact-preferences', kind, id], queryFn: () => optionsFor(`contact-preferences/?${kind}=${id}`), retry: false });
  const channels: Record<string, string> = { email: 'E-mail', phone: 'Telefone', whatsapp: 'WhatsApp' };
  const purposes: Record<string, string> = { commercial: 'Comercial', administrative: 'Administrativa' };
  return <section className="sheet section-pad"><div className="section-heading"><h2>Preferências de contato</h2><Button variant="secondary" onClick={() => setEditing(true)}>Registrar preferência</Button></div>
    <p>O registro mais recente de cada canal e finalidade determina a preferência. Comunicação consulta apenas contatos comerciais autorizados.</p>
    {query.isPending ? <Loading /> : query.error ? <ErrorNotice error={query.error} /> : !query.data?.length ? <p>Nenhuma preferência registrada.</p> : <ul>{query.data.map((item) => <li key={Number(item.id)}>{channels[String(item.channel)]} · {purposes[String(item.purpose)]} · {item.allowed ? 'Autorizado' : 'Não autorizado'} · {timestamp(item.created_at)} · Conta #{String(item.actor)}</li>)}</ul>}
    {editing && <ActionForm title="Registrar preferência de contato" endpoint="contact-preferences/" fields={[
      { key: 'channel', label: 'Canal', type: 'select', required: true, options: [{ value: 'email', label: 'E-mail' }, { value: 'phone', label: 'Telefone' }, { value: 'whatsapp', label: 'WhatsApp' }] },
      { key: 'purpose', label: 'Finalidade', type: 'select', required: true, options: [{ value: 'commercial', label: 'Comercial' }, { value: 'administrative', label: 'Administrativa' }] },
      { key: 'allowed', label: 'Preferência', type: 'select', required: true, options: [{ value: 'true', label: 'Autoriza contato' }, { value: 'false', label: 'Não autoriza contato' }] },
    ]} transform={(values) => ({ ...values, [kind]: Number(id), allowed: values.allowed === 'true' })} onClose={() => setEditing(false)} />}
  </section>;
}
