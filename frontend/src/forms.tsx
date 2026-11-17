import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useQueries, useQuery, useQueryClient } from "@tanstack/react-query";
import type { RecordData } from "./types";
import { api, optionsFor, post, patch } from "./api";
import { Button, Field, ErrorNotice, Modal, Loading, Notice, SearchableSelect } from "./ui";
import { today } from "./format";
export type Option = { value: string | number; label: string };
export type FieldSpec = {
  key: string;
  label: string;
  type?:
    | "text"
    | "email"
    | "tel"
    | "date"
    | "time"
    | "number"
    | "decimal"
    | "textarea"
    | "select"
    | "lookup"
    | "multi"
    | "check";
  required?: boolean;
  hint?: string;
  options?: Option[];
  lookup?: string;
  optionLabel?: (row: Record<string, unknown>) => string;
  wide?: boolean;
  default?: unknown;
  min?: number;
  max?: number;
  readOnly?: boolean;
  nullable?: boolean;
};
export function RecordForm({
  title,
  endpoint,
  fields,
  record,
  onClose,
  onSaved,
  initial = {},
}: {
  title: string;
  endpoint: string;
  fields: FieldSpec[];
  record?: RecordData;
  onClose: () => void;
  onSaved?: (row: RecordData) => void;
  initial?: Record<string, unknown>;
}) {
  const client = useQueryClient();
  const [values, setValues] = useState<Record<string, unknown>>(() =>
    Object.fromEntries(
      fields.map((field) => [
        field.key,
        record?.[field.key] ??
          initial[field.key] ??
          field.default ??
          (field.type === "check" ? false : field.type === "multi" ? [] : ""),
      ]),
    ),
  );
  const [error, setError] = useState<unknown>();
  const [pending, setPending] = useState(false);
  const [priceTouched, setPriceTouched] = useState(false);
  const [priceSuggested, setPriceSuggested] = useState(false);
  const [scheduleTrial, setScheduleTrial] = useState(false);
  const [trialLesson, setTrialLesson] = useState("");
  const [trialPerson, setTrialPerson] = useState("");
  const [trialBirthDate, setTrialBirthDate] = useState("");
  const [trialGuardian, setTrialGuardian] = useState(false);
  const [isMinor, setIsMinor] = useState(initial.is_minor === true);
  const [guardianMode, setGuardianMode] = useState<"new" | "existing">(initial.guardian ? "existing" : "new");
  const [guardianId, setGuardianId] = useState(String(initial.guardian || ""));
  const [guardianName, setGuardianName] = useState("");
  const [guardianCpf, setGuardianCpf] = useState("");
  const [guardianEmail, setGuardianEmail] = useState("");
  const [guardianPhone, setGuardianPhone] = useState("");
  const trialLessons = useQuery({ queryKey: ['options', 'lessons/?trial_available=true'], queryFn: () => optionsFor('lessons/?trial_available=true'), enabled: scheduleTrial, retry: false });
  const trialPeople = useQuery({ queryKey: ['options', 'people/'], queryFn: () => optionsFor('people/'), enabled: scheduleTrial, retry: false });
  const contractForm = endpoint === 'enrollments/' || /^enrollments\/\d+\/renew\/$/.test(endpoint);
  const guardianPeople = useQuery({ queryKey: ['options', 'people/?archived=false'], queryFn: () => optionsFor('people/?archived=false'), enabled: contractForm && isMinor && guardianMode === 'existing', retry: false });
  const benefitForm = endpoint === 'benefits/';
  const planForm = contractForm || (benefitForm && values.scope !== 'ecowork');
  const ecoBenefit = benefitForm && values.scope === 'ecowork';
  const ecoProducts = useQuery({ queryKey: ['eco-benefit-products'], queryFn: () => api<{ code: string; name: string; months: number }[]>('ecowork/products/'), enabled: ecoBenefit, retry: false });
  const contractDate = String((benefitForm ? values.starts_on : values.start_date) || '');
  const financialOptions = useQuery({
    queryKey: ['financial-options', contractDate],
    queryFn: async () => {
      const data = await api<{ plans: { code: string; name: string; installments: number[] }[]; methods: string[] }>(`financial-options/?${new URLSearchParams({ on: contractDate })}`);
      if (!Array.isArray(data.plans) || !Array.isArray(data.methods)) throw new Error('Não foi possível interpretar as opções da tabela financeira.');
      return data;
    },
    enabled: planForm && !!contractDate,
    retry: false,
  });
  useEffect(() => {
    if (!planForm || !financialOptions.data) return;
    setValues((previous) => ({ ...previous,
      plan: financialOptions.data.plans.some((plan) => plan.code === previous.plan) ? previous.plan : '',
      ...(contractForm ? { payment_method: financialOptions.data.methods.includes(String(previous.payment_method)) ? previous.payment_method : '' } : {}),
    }));
  }, [contractForm, planForm, financialOptions.data]);
  const enrollmentStudent = String(('student' in values ? values.student : initial.student) || "");
  const sourceLeadPath = contractForm && enrollmentStudent ? `leads/?status=converted&student=${encodeURIComponent(enrollmentStudent)}` : undefined;
  const lookupPath = (field: FieldSpec) => contractForm && field.key === 'source_lead' ? sourceLeadPath : field.lookup;
  const paths = [
    ...new Set(
      [
        ...fields.map(lookupPath),
        ...(endpoint === "enrollments/" ? ["modalities/"] : []),
      ].filter((value): value is string => !!value),
    ),
  ];
  const lookupQueries = useQueries({
    queries: paths.map((path) => ({
      queryKey: ["options", path],
      queryFn: () => optionsFor(path),
      retry: false,
    })),
  });
  const sourceLeadQuery = sourceLeadPath ? lookupQueries[paths.indexOf(sourceLeadPath)] : undefined;
  const lookupError = lookupQueries.find((query, index) => paths[index] !== sourceLeadPath && query.error)?.error || (planForm ? financialOptions.error : undefined) || (ecoBenefit ? ecoProducts.error : undefined) || (scheduleTrial ? trialLessons.error || trialPeople.error : undefined);
  const loading = lookupQueries.some((query, index) => paths[index] !== sourceLeadPath && query.isPending) || (planForm && !!contractDate && financialOptions.isPending) || (ecoBenefit && ecoProducts.isPending) || (scheduleTrial && (trialLessons.isPending || trialPeople.isPending));
  const guardianUnavailable = contractForm && isMinor && guardianMode === 'existing' && (guardianPeople.isPending || guardianPeople.isError);
  const options = (field: FieldSpec): Option[] =>
    (ecoBenefit && field.key === 'plan' && ecoProducts.data ? ecoProducts.data.filter((item) => item.months > 0).map((item) => ({ value: item.code, label: item.name })) : undefined) ??
    (planForm && field.key === 'plan' && financialOptions.data ? financialOptions.data.plans.map((plan) => ({ value: plan.code, label: plan.name })) : undefined) ??
    (contractForm && field.key === 'payment_method' && financialOptions.data ? financialOptions.data.methods.map((method) => ({ value: method, label: method === 'card' ? 'Cartão' : method === 'boleto' ? 'Boleto' : method })) : undefined) ??
    field.options ??
    (lookupQueries[paths.indexOf(lookupPath(field) ?? "")]?.data ?? []).map(
      (row) => ({
        value: Number(row.id),
        label:
          field.optionLabel?.(row) ??
          String(row.name || row.email || `#${row.id}`),
      }),
    );
  function change(field: FieldSpec, value: unknown) {
    if (contractForm && field.key === 'student') {
      setValues((previous) => ({ ...previous, student: value, source_lead: String(previous.student ?? '') === String(value) ? previous.source_lead : '' }));
      return;
    }
    if (field.key === "amount") {
      setPriceTouched(true);
      setPriceSuggested(false);
    }
    if (
      endpoint === "enrollments/" &&
      fields.some((item) => item.key === 'amount') &&
      field.key === "class_group" &&
      !priceTouched &&
      !record
    ) {
      const classPath = paths.find((path) => path.startsWith("classes/"))!;
      const selected = lookupQueries[paths.indexOf(classPath)]?.data?.find(
        (row) => String(row.id) === String(value),
      );
      const modality = lookupQueries[paths.indexOf("modalities/")]?.data?.find(
        (row) => row.id === selected?.modality,
      );
      if (modality?.default_price !== undefined) {
        setValues((previous) => ({
          ...previous,
          [field.key]: value,
          amount: String(modality.default_price),
        }));
        setPriceSuggested(true);
        return;
      }
    }
    setValues((previous) => ({ ...previous, [field.key]: value }));
  }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError(undefined);
    const payload = Object.fromEntries(
      fields
        .filter((field) => !field.readOnly)
        .map((field) => {
          const value = values[field.key];
          return [
            field.key,
            (field.type === "date" && value === "") ||
            (field.nullable && value === "")
              ? null
              : field.type === "number" ||
                  (field.lookup && (field.type === "select" || field.type === "lookup"))
                ? value === ""
                  ? ""
                  : Number(value)
                : field.type === "decimal"
                  ? String(value).replace(",", ".")
                  : value,
          ];
        }),
    );
    if (scheduleTrial && endpoint === 'leads/' && !record) {
      payload.trial = { lesson: Number(trialLesson), person: trialPerson ? Number(trialPerson) : null, birth_date: trialBirthDate, guardian_authorization: trialGuardian };
    }
    if (contractForm) {
      payload.is_minor = isMinor;
      if (isMinor) payload.guardian_data = guardianMode === 'existing' ? { id: Number(guardianId) } : { name: guardianName, cpf: guardianCpf, email: guardianEmail, phone: guardianPhone };
    }
    try {
      const row = record
        ? await patch<RecordData>(`${endpoint}${record.id}/`, payload)
        : await post<RecordData>(endpoint, payload);
      await client.invalidateQueries();
      onSaved?.(row);
      onClose();
    } catch (err) {
      setError(err);
    } finally {
      setPending(false);
    }
  }
  return (
    <Modal open title={title} onClose={() => !pending && onClose()}>
      <form onSubmit={submit}>
        {contractForm && financialOptions.data && !financialOptions.data.plans.length && <Notice tone="warning">Não há tabela financeira publicada para a data escolhida.</Notice>}
        {endpoint === 'leads/' && !record && <label className="check-option lead-trial-toggle"><input className="toggle" role="switch" type="checkbox" checked={scheduleTrial} onChange={(event) => setScheduleTrial(event.target.checked)} /> Agendar aula experimental</label>}
        {loading ? (
          <Loading />
        ) : lookupError ? (
          <>
            <ErrorNotice error={lookupError} />
            <Button
              variant="secondary"
              onClick={() =>
                { lookupQueries.forEach((query) => void query.refetch()); if (planForm && contractDate) void financialOptions.refetch(); if (scheduleTrial) { void trialLessons.refetch(); void trialPeople.refetch(); } if (contractForm && isMinor && guardianMode === 'existing') void guardianPeople.refetch(); }
              }
            >
              Tentar carregar opções novamente
            </Button>
          </>
        ) : (
          <div className="form-grid">
            {fields.map((field) => (
              <Field
                key={field.key}
                label={field.label}
                hint={
                  contractForm && field.key === 'source_lead' && !enrollmentStudent
                    ? "Selecione o aluno primeiro."
                    : contractForm && field.key === 'source_lead' && sourceLeadQuery?.isPending
                      ? "Carregando leads vinculados…"
                      : contractForm && field.key === 'source_lead' && sourceLeadQuery?.error
                        ? "Não foi possível carregar os leads vinculados. Tente novamente."
                  : field.key === "amount" && priceSuggested
                    ? "Valor sugerido pela modalidade. Confira as condições antes de salvar."
                    : field.hint
                }
                wide={field.wide}
              >
                {field.type === "textarea" ? (
                  <textarea
                    value={String(values[field.key] ?? "")}
                    onChange={(event) => change(field, event.target.value)}
                    required={field.required}
                    rows={4}
                  />
                ) : (field.type === "lookup" || field.type === "select") && field.lookup ? (
                  <SearchableSelect value={String(values[field.key] ?? "")} options={options(field)}
                    onChange={(value) => change(field, value)} required={field.required} disabled={field.readOnly || (contractForm && field.key === 'source_lead' && (!enrollmentStudent || sourceLeadQuery?.isPending || !!sourceLeadQuery?.error))} />
                ) : field.type === "select" ? (
                  <select
                    value={String(values[field.key] ?? "")}
                    onChange={(event) => change(field, event.target.value)}
                    required={field.required}
                    disabled={
                      field.readOnly ||
                      (field.key === "status" && record?.status === "converted")
                    }
                  >
                    <option value="">Selecione…</option>
                    {field.key === "status" &&
                      record?.status === "converted" && (
                        <option value="converted">Convertido</option>
                      )}
                    {options(field).map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                ) : field.type === "multi" ? (
                  <div className="choice-group" role="group">
                    {options(field).length ? (
                      options(field).map((option) => (
                        <label className="check-option" key={option.value}>
                          <input
                            type="checkbox"
                            checked={(
                              values[field.key] as (string | number)[]
                            ).includes(option.value)}
                            onChange={(event) => {
                              const previous = values[field.key] as (
                                string | number
                              )[];
                              change(
                                field,
                                event.target.checked
                                  ? [...previous, option.value]
                                  : previous.filter(
                                      (value) => value !== option.value,
                                    ),
                              );
                            }}
                          />
                          {option.label}
                        </label>
                      ))
                    ) : (
                      <span className="muted">Nenhuma opção cadastrada.</span>
                    )}
                  </div>
                ) : field.type === "check" ? (
                  <input
                    className="toggle"
                    role="switch"
                    type="checkbox"
                    checked={!!values[field.key]}
                    onChange={(event) => change(field, event.target.checked)}
                  />
                ) : (
                  <input
                    value={String(values[field.key] ?? "")}
                    onChange={(event) => change(field, event.target.value)}
                    type={
                      field.type === "decimal" ? "number" : field.type || "text"
                    }
                    inputMode={field.type === "decimal" ? "decimal" : undefined}
                    step={
                      field.type === "decimal"
                        ? "0.01"
                        : field.type === "time"
                          ? 60
                          : undefined
                    }
                    min={
                      field.min ?? (field.type === "decimal" ? 0.01 : undefined)
                    }
                    max={field.max}
                    required={field.required}
                    disabled={field.readOnly}
                    maxLength={field.type === "text" ? 1000 : undefined}
                  />
                )}
              </Field>
            ))}
            {sourceLeadQuery?.error && <div className="field--wide"><ErrorNotice error={sourceLeadQuery.error} /><Button type="button" variant="secondary" onClick={() => void sourceLeadQuery.refetch()}>Tentar carregar leads novamente</Button></div>}
            {contractForm && <>
              <label className="check-option field--wide"><input className="toggle" role="switch" type="checkbox" checked={isMinor} onChange={(event) => setIsMinor(event.target.checked)} /> Aluno é menor de idade</label>
              {isMinor && <>
                <Field label="Responsável" wide><select value={guardianMode} onChange={(event) => setGuardianMode(event.target.value as "new" | "existing")}><option value="new">Cadastrar responsável</option><option value="existing">Selecionar pessoa cadastrada</option></select></Field>
                {guardianMode === 'existing' && guardianPeople.isPending ? <div className="field--wide"><Loading /></div> : guardianMode === 'existing' && guardianPeople.isError ? <div className="field--wide"><ErrorNotice error={guardianPeople.error} /><Button type="button" variant="secondary" onClick={() => void guardianPeople.refetch()}>Tentar novamente</Button></div> : guardianMode === 'existing' ? <Field label="Pessoa responsável" wide><SearchableSelect required value={guardianId} onChange={setGuardianId}
                  options={(guardianPeople.data ?? []).filter((person) => !person.archived && String(person.id) !== String(values.student || initial.student || '')).map((person) => ({ value: Number(person.id), label: String(person.name) }))} /></Field>
                  : <>
                    <Field label="Nome do responsável" wide><input required maxLength={200} value={guardianName} onChange={(event) => setGuardianName(event.target.value)} /></Field>
                    <Field label="CPF do responsável"><input value={guardianCpf} onChange={(event) => setGuardianCpf(event.target.value)} /></Field>
                    <Field label="E-mail do responsável"><input type="email" value={guardianEmail} onChange={(event) => setGuardianEmail(event.target.value)} /></Field>
                    <Field label="Telefone do responsável"><input type="tel" value={guardianPhone} onChange={(event) => setGuardianPhone(event.target.value)} /></Field>
                  </>}
              </>}
            </>}
            {endpoint === 'leads/' && !record && <>
              {scheduleTrial && <>
                <Field label="Aula experimental" wide><SearchableSelect required value={trialLesson} onChange={setTrialLesson}
                  options={(trialLessons.data ?? []).filter((row) => String(row.date) >= today()).map((row) => ({ value: Number(row.id), label: String(row.name || `${row.class_name} — ${row.date}`) }))} /></Field>
                <Field label="Pessoa já cadastrada (opcional)" wide hint="Selecione o cadastro existente se o CPF ou e-mail já estiver em uso."><SearchableSelect value={trialPerson} onChange={setTrialPerson}
                  options={(trialPeople.data ?? []).filter((row) => !row.archived).map((row) => ({ value: Number(row.id), label: String(row.name) }))} /></Field>
                <Field label="Data de nascimento"><input type="date" required max={today()} value={trialBirthDate} onChange={(event) => setTrialBirthDate(event.target.value)} /></Field>
                <label className="check-option field--wide"><input className="toggle" role="switch" type="checkbox" checked={trialGuardian} onChange={(event) => setTrialGuardian(event.target.checked)} /> Autorização do responsável conferida</label>
                <p className="field--wide muted">A autorização é obrigatória para menores de idade.</p>
              </>}
            </>}
          </div>
        )}
        <ErrorNotice error={error} />
        <div className="form-actions">
          <Button
            variant="secondary"
            type="button"
            onClick={onClose}
            disabled={pending}
          >
            Cancelar
          </Button>
          <Button type="submit" disabled={pending || loading || !!lookupError || guardianUnavailable}>
            {pending
              ? "Salvando…"
              : record
                ? "Salvar alterações"
                : "Salvar cadastro"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
export function ActionForm({
  transform,
  title,
  description,
  endpoint,
  fields,
  onClose,
  onSaved,
  button = "Confirmar",
}: {
  transform?: (values: Record<string, unknown>) => Record<string, unknown>;
  title: string;
  description?: string;
  endpoint: string;
  fields: FieldSpec[];
  onClose: () => void;
  onSaved?: () => void;
  button?: string;
}) {
  const [values, setValues] = useState<Record<string, unknown>>(() =>
    Object.fromEntries(fields.map((field) => [field.key, field.default ?? (field.type === "check" ? false : "")])),
  );
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<unknown>();
  const client = useQueryClient();
  return (
    <Modal open title={title} onClose={() => !pending && onClose()}>
      <form
        onSubmit={async (event) => {
          event.preventDefault();
          setPending(true);
          setError(undefined);
          try {
            await post(endpoint, transform ? transform(values) : values);
            await client.invalidateQueries();
            onSaved?.();
            onClose();
          } catch (err) {
            setError(err);
          } finally {
            setPending(false);
          }
        }}
      >
        {description && <Notice tone="warning">{description}</Notice>}
        <div className="form-grid">
          {fields.map((field) => (
            <Field
              key={field.key}
              label={field.label}
              hint={field.hint}
              wide={field.wide}
            >
              {field.type === "textarea" ? (
                <textarea
                  value={String(values[field.key])}
                  onChange={(event) =>
                    setValues({ ...values, [field.key]: event.target.value })
                  }
                  required={field.required}
                  rows={3}
                />
              ) : field.type === "check" ? (
                <input className="toggle" role="switch" type="checkbox" checked={!!values[field.key]}
                  onChange={(event) => setValues({ ...values, [field.key]: event.target.checked })} />
              ) : field.type === "select" ? (
                <select
                  value={String(values[field.key])}
                  onChange={(event) =>
                    setValues({ ...values, [field.key]: event.target.value })
                  }
                  required={field.required}
                >
                  <option value="">Selecione…</option>
                  {field.options?.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  type={
                    field.type === "decimal" ? "number" : field.type || "text"
                  }
                  step={field.type === "decimal" ? "0.01" : undefined}
                  min={field.type === "decimal" ? 0.01 : undefined}
                  required={field.required}
                  value={String(values[field.key])}
                  onChange={(event) =>
                    setValues({ ...values, [field.key]: event.target.value })
                  }
                />
              )}
            </Field>
          ))}
        </div>
        <ErrorNotice error={error} />
        <div className="form-actions">
          <Button
            variant="secondary"
            type="button"
            onClick={onClose}
            disabled={pending}
          >
            Voltar
          </Button>
          <Button type="submit" disabled={pending}>
            {pending ? "Salvando…" : button}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
