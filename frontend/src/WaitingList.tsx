import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { optionsFor, post } from "./api";
import { ActionForm } from "./forms";
import { Button, ErrorNotice, Field, Loading, Modal, Notice } from "./ui";
import { timestamp } from "./format";

export function WaitingList({ groupId }: { groupId: string }) {
  const client = useQueryClient();
  const [adding, setAdding] = useState(false);
  const [person, setPerson] = useState("");
  const [cancel, setCancel] = useState<number | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<unknown>();
  const entries = useQuery({ queryKey: ['waiting-list', groupId], queryFn: () => optionsFor(`waiting-list/?class_group=${groupId}&status=waiting`), retry: false });
  const people = useQuery({ queryKey: ['options', 'people/'], queryFn: () => optionsFor('people/'), enabled: adding, retry: false });
  return <section className="sheet section-pad">
    <div className="section-heading"><h2>Lista de espera</h2><Button variant="secondary" onClick={() => { setAdding(true); setError(undefined); }}>Adicionar pessoa</Button></div>
    <p>A ordem de solicitação é respeitada ao efetivar a matrícula.</p>
    {entries.isPending ? <Loading /> : entries.error ? <ErrorNotice error={entries.error} /> : !entries.data?.length ? <p>Nenhuma pessoa aguardando.</p> :
      <ol>{entries.data.map((entry) => <li key={Number(entry.id)}>{String(entry.person_name)} · {timestamp(entry.created_at)}{" "}<Button variant="ghost" onClick={() => setCancel(Number(entry.id))}>Retirar da lista</Button></li>)}</ol>}
    {adding && <Modal open title="Adicionar à lista de espera" onClose={() => !pending && setAdding(false)}>
      <form onSubmit={(event) => { event.preventDefault(); setPending(true); setError(undefined); void post('waiting-list/', { class_group: Number(groupId), person: Number(person) }).then(async () => { await client.invalidateQueries(); setAdding(false); setPerson(""); }).catch(setError).finally(() => setPending(false)); }}>
        <Notice>A primeira pessoa da lista tem prioridade quando houver vaga.</Notice>
        {people.isPending ? <Loading /> : people.error ? <ErrorNotice error={people.error} /> : <Field label="Pessoa"><select required value={person} onChange={(event) => setPerson(event.target.value)}><option value="">Selecione…</option>{people.data?.filter((row) => !row.archived).map((row) => <option key={Number(row.id)} value={Number(row.id)}>{String(row.name)} · #{String(row.id)}</option>)}</select></Field>}
        <ErrorNotice error={error} /><div className="form-actions"><Button type="submit" disabled={pending || !person}>Adicionar à lista</Button></div>
      </form></Modal>}
    {cancel !== null && <ActionForm title="Retirar da lista de espera" endpoint={`waiting-list/${cancel}/cancel/`} description="Informe o motivo para preservar o histórico."
      fields={[{ key: 'reason', label: 'Motivo', type: 'textarea', required: true, wide: true }]} onClose={() => setCancel(null)} />}
  </section>;
}
