import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { optionsFor, patch, post } from "./api";
import { Button, ErrorNotice, Field, Loading, Notice, PageTitle } from "./ui";

type Price = { category: number; plan: string; method: string; associated: boolean; amount: string };
type Plan = { name?: string; months: number; installments: number[] };
type Config = { plans: Record<string, Plan>; prices: Price[]; fees: Record<string, { associated: string; non_associated: string }>; due_rule?: string; due_day?: number; due_reference?: string };
type Catalog = { id: number; version: number; status: string; effective_from: string; effective_until: string | null; configuration: Config };
type Preview = { valid: boolean; errors: string[]; conflicting_versions: number[]; existing_contracts_preserved: number; scope: string; revision: string };
const initial = (): Config => ({ plans: { quarterly: { months: 3, installments: [1, 2, 3] }, yearly: { months: 12, installments: [3, 6, 10, 12] } }, prices: [], fees: { standard: { associated: "25.00", non_associated: "35.00" }, rhythmic: { associated: "35.00", non_associated: "70.00" } } });
const labels: Record<string, string> = { monthly: "Mensal", quarterly: "Trimestral", yearly: "Anual" };

export function FinancialCatalog() {
  const client = useQueryClient();
  const catalogs = useQuery({ queryKey: ["financial-catalogs"], queryFn: () => optionsFor("financial-catalogs/") });
  const [selected, setSelected] = useState<number | null>(null);
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [config, setConfig] = useState<Config>(initial);
  const [installmentText, setInstallmentText] = useState<Record<string, string>>({ quarterly: "1, 2, 3", yearly: "3, 6, 10, 12" });
  const [preview, setPreview] = useState<Preview | null>(null);
  const [reason, setReason] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<unknown>();
  const [notice, setNotice] = useState("");
  const [dirty, setDirty] = useState(false);
  const current = catalogs.data?.find((row) => Number(row.id) === selected) as Catalog | undefined;
  const editable = !current || current.status === "draft";
  async function run(action: () => Promise<void>) {
    setPending(true); setError(undefined); setNotice("");
    try { await action(); } catch (err) { setError(err); } finally { setPending(false); }
  }
  function choose(catalog?: Catalog) {
    setSelected(catalog?.id ?? null); setStart(catalog?.effective_from ?? ""); setEnd(catalog?.effective_until ?? "");
    const next = catalog ? structuredClone(catalog.configuration) : initial();
    setConfig(next); setInstallmentText(Object.fromEntries(Object.entries(next.plans).map(([key, plan]) => [key, plan.installments.join(", ")]))); setPreview(null); setReason(""); setDirty(false);
  }
  async function save() {
    const plans = Object.fromEntries(Object.entries(config.plans).map(([key, plan]) => [key, { ...plan, installments: (installmentText[key] || "").split(",").map((v) => Number(v.trim())) }]));
    const body = { effective_from: start, effective_until: end || null, configuration: { ...config, plans } };
    const result = selected ? await patch<Catalog>(`financial-catalogs/${selected}/`, body) : await post<Catalog>("financial-catalogs/", body);
    setSelected(result.id); setPreview(null); setDirty(false); await client.invalidateQueries({ queryKey: ["financial-catalogs"] }); setNotice("Rascunho salvo.");
  }
  if (catalogs.isPending) return <Loading />;
  if (catalogs.error) return <ErrorNotice error={catalogs.error} />;
  return <>
    <PageTitle eyebrow="COORDENAÇÃO" title="Tabelas financeiras" description="Organize planos, preços e taxas por período. Contratos anteriores preservam suas condições." />
    {notice && <Notice tone="success">{notice}</Notice>}<ErrorNotice error={error} />
    <section className="sheet">
      <Field label="Versão da tabela"><select value={selected ?? ""} onChange={(e) => choose(catalogs.data?.find((r) => Number(r.id) === Number(e.target.value)) as Catalog | undefined)}>
        <option value="">Novo rascunho</option>{catalogs.data?.map((row) => <option key={Number(row.id)} value={Number(row.id)}>Versão {String(row.version)} · {row.status === "published" ? "Publicada" : "Rascunho"} · {String(row.effective_from)}</option>)}
      </select></Field>
      <form onChangeCapture={() => { setPreview(null); setDirty(true); }} onSubmit={(event) => { event.preventDefault(); void run(save); }}>
        <fieldset disabled={!editable || pending}>
          <div className="form-grid"><Field label="Vigência a partir de"><input type="date" required value={start} onChange={(e) => setStart(e.target.value)} /></Field>
            <Field label="Vigência até (opcional)"><input type="date" value={end} min={start} onChange={(e) => setEnd(e.target.value)} /></Field></div>
          <h2>Vencimentos</h2>
          <div className="form-grid"><Field label="Primeiro vencimento"><select value={config.due_rule ?? "15_end"} onChange={(e) => setConfig({ ...config, due_rule: e.target.value })}><option value="15_end">Dia 15 ou último dia do mês</option><option value="start">Data de início do contrato</option><option value="fixed">Dia fixo</option></select></Field>
            {config.due_rule === "fixed" && <Field label="Dia fixo"><input type="number" min="1" max="31" required value={config.due_day ?? ""} onChange={(e) => setConfig({ ...config, due_day: Number(e.target.value) })} /></Field>}
            <Field label="Referência das parcelas seguintes"><select value={config.due_reference ?? "start"} onChange={(e) => setConfig({ ...config, due_reference: e.target.value })}><option value="start">Dia de início do contrato</option><option value="first_due">Dia do primeiro vencimento</option></select></Field></div>
          <h2>Planos e parcelamento</h2>
          {[...Object.entries(labels), ...Object.keys(config.plans).filter((key) => !(key in labels)).map((key): [string, string] => [key, config.plans[key].name || 'Plano personalizado'])].map(([key, label]) => <div className="form-grid" key={key}>
            <label className="check-option"><input type="checkbox" checked={!!config.plans[key]} onChange={(e) => { const plans = { ...config.plans }; if (e.target.checked) { plans[key] = { months: 1, installments: [1] }; setInstallmentText({ ...installmentText, [key]: "1" }); } else delete plans[key]; setConfig({ ...config, plans }); }} />{label}</label>
            {config.plans[key] && <><Field label={`Nome de ${label}`}><input required maxLength={120} value={config.plans[key].name ?? labels[key] ?? ''} onChange={(e) => setConfig({ ...config, plans: { ...config.plans, [key]: { ...config.plans[key], name: e.target.value } } })} /></Field>
              <Field label={`Duração de ${label} em meses`}><input type="number" min="1" max="120" required value={config.plans[key].months} onChange={(e) => setConfig({ ...config, plans: { ...config.plans, [key]: { ...config.plans[key], months: Number(e.target.value) } } })} /></Field>
              <Field label={`Parcelas permitidas para ${label}`} hint="Números separados por vírgula"><input required value={installmentText[key] ?? ""} onChange={(e) => setInstallmentText({ ...installmentText, [key]: e.target.value })} /></Field></>}
          </div>)}
          <Button type="button" variant="secondary" onClick={() => { const key = `p_${crypto.randomUUID().replaceAll('-', '').slice(0, 20)}`; setDirty(true); setPreview(null); setConfig({ ...config, plans: { ...config.plans, [key]: { name: '', months: 1, installments: [1] } } }); setInstallmentText({ ...installmentText, [key]: '1' }); }}>Adicionar plano personalizado</Button>
          <h2>Preços por categoria</h2>
          {config.prices.map((price, index) => <div className="form-grid" key={index}>
            <Field label="Categoria"><input type="number" min="1" max="7" value={price.category} onChange={(e) => setConfig({ ...config, prices: config.prices.map((p, i) => i === index ? { ...p, category: Number(e.target.value) } : p) })} /></Field>
            <Field label="Plano"><select value={price.plan} onChange={(e) => setConfig({ ...config, prices: config.prices.map((p, i) => i === index ? { ...p, plan: e.target.value } : p) })}>{Object.keys(config.plans).map((key) => <option key={key} value={key}>{config.plans[key].name || labels[key] || 'Plano personalizado'}</option>)}</select></Field>
            <Field label="Pagamento"><select value={price.method} onChange={(e) => setConfig({ ...config, prices: config.prices.map((p, i) => i === index ? { ...p, method: e.target.value } : p) })}><option value="card">Cartão</option><option value="boleto">Boleto</option></select></Field>
            <Field label="Associação"><select value={String(price.associated)} onChange={(e) => setConfig({ ...config, prices: config.prices.map((p, i) => i === index ? { ...p, associated: e.target.value === "true" } : p) })}><option value="false">Não associado</option><option value="true">Associado</option></select></Field>
            <Field label="Valor total (R$)"><input type="number" min="0.01" step="0.01" required value={price.amount} onChange={(e) => setConfig({ ...config, prices: config.prices.map((p, i) => i === index ? { ...p, amount: e.target.value } : p) })} /></Field>
            <Button type="button" variant="secondary" onClick={() => { setDirty(true); setPreview(null); setConfig({ ...config, prices: config.prices.filter((_, i) => i !== index) }); }}>Remover preço</Button>
          </div>)}
          <Button type="button" variant="secondary" disabled={!Object.keys(config.plans).length} onClick={() => { setDirty(true); setPreview(null); setConfig({ ...config, prices: [...config.prices, { category: 1, plan: Object.keys(config.plans)[0], method: "card", associated: false, amount: "" }] }); }}>Adicionar preço</Button>
          <h2>Taxas de matrícula</h2>
          {Object.entries(config.fees).map(([kind, fee]) => <div className="form-grid" key={kind}>{(["associated", "non_associated"] as const).map((key) => <Field key={key} label={`${kind === "standard" ? "Convencional" : "Rítmica"} · ${key === "associated" ? "associado" : "não associado"}`}><input type="number" min="0" step="0.01" required value={fee[key]} onChange={(e) => setConfig({ ...config, fees: { ...config.fees, [kind]: { ...fee, [key]: e.target.value } } })} /></Field>)}</div>)}
          <div className="form-actions"><Button type="submit">Salvar rascunho</Button></div>
        </fieldset>
      </form>
      {selected && editable && <div className="form-actions"><Button type="button" variant="secondary" disabled={pending || dirty} onClick={() => void run(async () => { setPreview(await post<Preview>(`financial-catalogs/${selected}/preview/`, {})); })}>Conferir rascunho salvo</Button>{dirty && <span>Salve as alterações antes de conferir.</span>}</div>}
      {preview && <><Notice tone={preview.valid ? "success" : "warning"}>{preview.valid ? "A verificação da tabela passou." : preview.errors.join(" ")} {preview.existing_contracts_preserved} contrato(s) existentes na vigência serão preservados.</Notice>
        {preview.valid && <><Field label="Motivo da publicação"><textarea value={reason} onChange={(e) => setReason(e.target.value)} /></Field><Button type="button" disabled={pending || !reason.trim()} onClick={() => void run(async () => { await post(`financial-catalogs/${selected}/publish/`, { reason, revision: preview.revision }); await client.invalidateQueries({ queryKey: ["financial-catalogs"] }); setPreview(null); setNotice("Tabela publicada."); })}>Publicar tabela salva</Button></>}</>}
    </section>
  </>;
}
