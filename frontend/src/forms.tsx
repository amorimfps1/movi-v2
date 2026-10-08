import { useState } from "react";
import type { FormEvent } from "react";
import { useQueries, useQueryClient } from "@tanstack/react-query";
import type { RecordData } from "./types";
import { optionsFor, post, patch } from "./api";
import { Button, Field, ErrorNotice, Modal, Loading, Notice } from "./ui";
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
  const paths = [
    ...new Set(
      [
        ...fields.map((field) => field.lookup),
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
  const lookupError = lookupQueries.find((query) => query.error)?.error;
  const loading = lookupQueries.some((query) => query.isPending);
  const options = (field: FieldSpec): Option[] =>
    field.options ??
    (lookupQueries[paths.indexOf(field.lookup ?? "")]?.data ?? []).map(
      (row) => ({
        value: Number(row.id),
        label:
          field.optionLabel?.(row) ??
          String(row.name || row.email || `#${row.id}`),
      }),
    );
  function change(field: FieldSpec, value: unknown) {
    if (field.key === "amount") {
      setPriceTouched(true);
      setPriceSuggested(false);
    }
    if (
      endpoint === "enrollments/" &&
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
                  (field.lookup && field.type === "select")
                ? value === ""
                  ? ""
                  : Number(value)
                : field.type === "decimal"
                  ? String(value).replace(",", ".")
                  : value,
          ];
        }),
    );
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
        {loading ? (
          <Loading />
        ) : lookupError ? (
          <>
            <ErrorNotice error={lookupError} />
            <Button
              variant="secondary"
              onClick={() =>
                lookupQueries.forEach((query) => void query.refetch())
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
                  field.key === "amount" && priceSuggested
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
                    className="field-checkbox"
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
          <Button type="submit" disabled={pending || loading || !!lookupError}>
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
  title,
  description,
  endpoint,
  fields,
  onClose,
  onSaved,
  button = "Confirmar",
}: {
  title: string;
  description?: string;
  endpoint: string;
  fields: FieldSpec[];
  onClose: () => void;
  onSaved?: () => void;
  button?: string;
}) {
  const [values, setValues] = useState<Record<string, unknown>>(() =>
    Object.fromEntries(fields.map((field) => [field.key, field.default ?? ""])),
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
            await post(endpoint, values);
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
