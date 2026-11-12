import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { optionsFor, patch, post } from './api';
import { Button, ErrorNotice, Field, Loading, Notice, PageTitle } from './ui';
import { ActionForm } from './forms';

type Product = { code: string; name: string; price: string; months: number; hours: number | null; max_installments: number };
type Config = { products: Product[]; resident_discount_percent: number; discount_limit_percent?: number };
type Catalog = { id: number; version: number; status: string; effective_from: string; effective_until: string | null; configuration: Config };
type Preview = { valid: boolean; errors: string[]; revision: string; existing_orders_preserved: number };
const empty = (): Config => ({ products: [], resident_discount_percent: 50, discount_limit_percent: 20 });

export function EcoCatalog() {
  const client = useQueryClient();
  const catalogs = useQuery({ queryKey: ['eco-catalogs'], queryFn: () => optionsFor('ecowork/catalogs/'), retry: false });
  const [id, setId] = useState<number | null>(null);
  const [start, setStart] = useState(''); const [end, setEnd] = useState('');
  const [config, setConfig] = useState<Config>(empty);
  const [dirty, setDirty] = useState(false); const [pending, setPending] = useState(false);
  const [preview, setPreview] = useState<Preview | null>(null); const [reason, setReason] = useState('');
  const [error, setError] = useState<unknown>(); const [success, setSuccess] = useState('');
  const [ending, setEnding] = useState(false);
  const selected = catalogs.data?.find((row) => Number(row.id) === id) as Catalog | undefined;
  const editable = !selected || selected.status === 'draft';
  function choose(catalog?: Catalog) { setId(catalog?.id ?? null); setStart(catalog?.effective_from ?? ''); setEnd(catalog?.effective_until ?? ''); setConfig(catalog ? structuredClone(catalog.configuration) : empty()); setDirty(false); setPreview(null); setReason(''); }
  async function run(action: () => Promise<void>) { setPending(true); setError(undefined); setSuccess(''); try { await action(); } catch (err) { setError(err); } finally { setPending(false); } }
  function edit(index: number, update: Partial<Product>) { setDirty(true); setPreview(null); setConfig({ ...config, products: config.products.map((product, i) => i === index ? { ...product, ...update } : product) }); }
  if (catalogs.isPending) return <Loading />;
  if (catalogs.error) return <ErrorNotice error={catalogs.error} />;
  return <><PageTitle eyebrow="COORDENAÇÃO · ECOWORK" title="Catálogo EcoWork" description="Configure produtos, preços e desconto de morador por vigência. Contratações anteriores preservam suas condições." />
    {success && <Notice tone="success">{success}</Notice>}<ErrorNotice error={error} />
    <section className="sheet section-pad"><Field label="Versão"><select value={id ?? ''} onChange={(event) => choose(catalogs.data?.find((row) => Number(row.id) === Number(event.target.value)) as Catalog | undefined)}><option value="">Novo rascunho</option>{catalogs.data?.map((row) => <option key={Number(row.id)} value={Number(row.id)}>Versão {String(row.version)} · {row.status === 'published' ? 'Publicada' : 'Rascunho'} · {String(row.effective_from)}</option>)}</select></Field>
      {selected?.status === 'published' && <div className="form-actions"><Button type="button" variant="secondary" onClick={() => { const copy = structuredClone(config); choose(); setConfig(copy); setDirty(true); }}>Criar nova versão com estes dados</Button><Button type="button" variant="secondary" onClick={() => setEnding(true)}>Encerrar vigência</Button></div>}
      {ending && selected && <ActionForm title="Encerrar vigência do catálogo" endpoint={`ecowork/catalogs/${selected.id}/end/`} description="O fim não pode ser retroativo. Contratações existentes preservam suas condições."
        fields={[{ key: 'effective_until', label: 'Último dia de vigência', type: 'date', required: true }, { key: 'reason', label: 'Justificativa', type: 'textarea', required: true, wide: true }]}
        onClose={() => setEnding(false)} onSaved={() => setSuccess('Vigência atualizada.')} />}
      <form onChangeCapture={() => { setDirty(true); setPreview(null); }} onSubmit={(event) => { event.preventDefault(); void run(async () => { const body = { effective_from: start, effective_until: end || null, configuration: config }; const result = id ? await patch<Catalog>(`ecowork/catalogs/${id}/`, body) : await post<Catalog>('ecowork/catalogs/', body); setId(result.id); setDirty(false); setPreview(null); await client.invalidateQueries({ queryKey: ['eco-catalogs'] }); setSuccess('Rascunho salvo.'); }); }}>
        <fieldset disabled={!editable || pending}><div className="form-grid"><Field label="Vigência a partir de"><input type="date" required value={start} onChange={(event) => setStart(event.target.value)} /></Field><Field label="Vigência até (opcional)"><input type="date" min={start} value={end} onChange={(event) => setEnd(event.target.value)} /></Field><Field label="Desconto de morador em planos (%)"><input type="number" min="0" max="100" required value={config.resident_discount_percent} onChange={(event) => setConfig({ ...config, resident_discount_percent: Number(event.target.value) })} /></Field></div>
          <Field label="Limite de aprovação de benefício individual (%)"><input type="number" min="0" max="100" required value={config.discount_limit_percent ?? 20} onChange={(event) => setConfig({ ...config, discount_limit_percent: Number(event.target.value) })} /></Field>
          <h2>Produtos e planos</h2>{config.products.map((item, index) => <section className="sheet section-pad" key={item.code}><h3>{item.name || 'Novo produto'}</h3><div className="form-grid">
            <Field label="Nome"><input required maxLength={100} value={item.name} onChange={(event) => edit(index, { name: event.target.value })} /></Field>
            <Field label="Tipo"><select value={item.months === 0 ? 'single' : 'plan'} onChange={(event) => edit(index, event.target.value === 'single' ? { months: 0, hours: 1, max_installments: 1 } : { months: 1, hours: null })}><option value="single">Avulso</option><option value="plan">Plano</option></select></Field>
            <Field label="Preço (R$)"><input type="number" min="0.01" step="0.01" required value={item.price} onChange={(event) => edit(index, { price: event.target.value })} /></Field>
            {item.months === 0 ? <Field label="Horas"><input type="number" min="1" required value={item.hours ?? ''} onChange={(event) => edit(index, { hours: Number(event.target.value) })} /></Field> : <Field label="Duração em meses"><input type="number" min="1" max="120" required value={item.months} onChange={(event) => edit(index, { months: Number(event.target.value) })} /></Field>}
            <Field label="Máximo de parcelas"><input type="number" min="1" max="12" required disabled={item.months === 0} value={item.max_installments} onChange={(event) => edit(index, { max_installments: Number(event.target.value) })} /></Field>
          </div><Button type="button" variant="secondary" onClick={() => { setDirty(true); setPreview(null); setConfig({ ...config, products: config.products.filter((_, i) => i !== index) }); }}>Remover produto</Button></section>)}
          <Button type="button" variant="secondary" onClick={() => { setDirty(true); setPreview(null); setConfig({ ...config, products: [...config.products, { code: `p_${crypto.randomUUID().replaceAll('-', '').slice(0, 16)}`, name: '', price: '', months: 0, hours: 1, max_installments: 1 }] }); }}>Adicionar produto</Button>
          <div className="form-actions"><Button type="submit">Salvar rascunho</Button></div>
        </fieldset>
      </form>
      {id && editable && <div className="form-actions"><Button type="button" variant="secondary" disabled={pending || dirty} onClick={() => void run(async () => setPreview(await post<Preview>(`ecowork/catalogs/${id}/preview/`, {})))}>Conferir rascunho salvo</Button>{dirty && <span>Salve as alterações antes de conferir.</span>}</div>}
      {preview && <><Notice tone={preview.valid ? 'success' : 'warning'}>{preview.valid ? 'A verificação passou.' : preview.errors.join(' ')} {preview.existing_orders_preserved} contratação(ões) existentes serão preservadas.</Notice>{preview.valid && <><Field label="Motivo da publicação"><textarea value={reason} onChange={(event) => setReason(event.target.value)} /></Field><Button disabled={pending || !reason.trim()} onClick={() => void run(async () => { await post(`ecowork/catalogs/${id}/publish/`, { reason, revision: preview.revision }); await client.invalidateQueries({ queryKey: ['eco-catalogs'] }); setPreview(null); setSuccess('Catálogo publicado.'); })}>Publicar catálogo salvo</Button></>}</>}
    </section></>;
}
