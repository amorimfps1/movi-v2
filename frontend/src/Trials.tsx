import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { optionsFor, post } from "./api";
import { ActionForm } from "./forms";
import { Button, ErrorNotice, Field, Loading, Modal, Notice } from "./ui";

export function Trials({ lessonId, lessonStatus, admin }: { lessonId: string; lessonStatus: string; admin: boolean }) {
  const client = useQueryClient();
  const [adding, setAdding] = useState(false);
  const [person, setPerson] = useState("");
  const [guardian, setGuardian] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<unknown>();
  const [cancel, setCancel] = useState<number | null>(null);
  const [mark, setMark] = useState<{ id: number; present: boolean } | null>(null);
  const [correct, setCorrect] = useState<number | null>(null);
  const trials = useQuery({ queryKey: ['trials', lessonId], queryFn: () => optionsFor(`trials/?lesson=${lessonId}`), retry: false });
  const people = useQuery({ queryKey: ['options', 'people/'], queryFn: () => optionsFor('people/'), enabled: adding, retry: false });
  return <section className="sheet section-pad"><div className="section-heading"><h2>Aulas experimentais</h2>
    {admin && lessonStatus === 'scheduled' && <Button variant="secondary" onClick={() => { setError(undefined); setAdding(true); }}>Agendar experimental</Button>}</div>
    <p>As participações experimentais ficam separadas das matrículas regulares.</p>
    {trials.isPending ? <Loading /> : trials.error ? <ErrorNotice error={trials.error} /> : !trials.data?.length ? <p>Nenhuma experimental registrada nesta aula.</p> :
      <ul>{trials.data.map((trial) => <li key={Number(trial.id)}>{String(trial.person_name)} · {trial.status === 'cancelled' ? 'Cancelada' : trial.status === 'completed' ? (trial.present ? 'Presente' : 'Ausente') : 'Agendada'}{' '}
        {trial.status === 'scheduled' && lessonStatus === 'completed' && <><Button variant="ghost" onClick={() => setMark({ id: Number(trial.id), present: true })}>Marcar presença</Button><Button variant="ghost" onClick={() => setMark({ id: Number(trial.id), present: false })}>Marcar falta</Button></>}
        {trial.status === 'completed' && lessonStatus === 'completed' && <Button variant="ghost" onClick={() => setCorrect(Number(trial.id))}>Corrigir marcação</Button>}
        {admin && trial.status === 'scheduled' && lessonStatus !== 'completed' && <Button variant="ghost" onClick={() => setCancel(Number(trial.id))}>Cancelar</Button>}</li>)}</ul>}
    {adding && <Modal open title="Agendar aula experimental" onClose={() => !pending && setAdding(false)}><form onSubmit={(event) => { event.preventDefault(); setPending(true); setError(undefined); void post('trials/', { lesson: Number(lessonId), person: Number(person), guardian_authorization: guardian }).then(async () => { await client.invalidateQueries(); setAdding(false); setPerson(''); setGuardian(false); }).catch(setError).finally(() => setPending(false)); }}>
      <Notice>Para menores, registre a autorização do responsável antes de agendar.</Notice>
      {people.isPending ? <Loading /> : people.error ? <ErrorNotice error={people.error} /> : <Field label="Pessoa"><select required value={person} onChange={(event) => setPerson(event.target.value)}><option value="">Selecione…</option>{people.data?.filter((row) => !row.archived).map((row) => <option key={Number(row.id)} value={Number(row.id)}>{String(row.name)} · #{String(row.id)}</option>)}</select></Field>}
      <label className="check-option"><input type="checkbox" checked={guardian} onChange={(event) => setGuardian(event.target.checked)} />Autorização do responsável conferida</label>
      <ErrorNotice error={error} /><div className="form-actions"><Button type="submit" disabled={pending || !person}>Agendar experimental</Button></div>
    </form></Modal>}
    {cancel !== null && <ActionForm title="Cancelar experimental" endpoint={`trials/${cancel}/cancel/`} fields={[{ key: 'reason', label: 'Motivo', type: 'textarea', required: true, wide: true }]} onClose={() => setCancel(null)} />}
    {mark && <ActionForm title={mark.present ? 'Confirmar presença experimental' : 'Confirmar falta experimental'} endpoint={`trials/${mark.id}/mark/`} fields={[]} transform={() => ({ present: mark.present })} onClose={() => setMark(null)} />}
    {correct !== null && <ActionForm title="Corrigir marcação experimental" endpoint={`trials/${correct}/correct/`} fields={[{ key: 'present', label: 'Marcação correta', type: 'select', required: true, options: [{ value: 'true', label: 'Presente' }, { value: 'false', label: 'Ausente' }] }, { key: 'reason', label: 'Motivo da correção', type: 'textarea', required: true, wide: true }]} transform={(values) => ({ ...values, present: values.present === 'true' })} onClose={() => setCorrect(null)} />}
  </section>;
}
