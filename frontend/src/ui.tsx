import {
  useEffect,
  useRef,
  useId,
  useState,
  cloneElement,
  isValidElement,
} from "react";
import type {
  ReactNode,
  ReactElement,
  ButtonHTMLAttributes,
  InputHTMLAttributes,
} from "react";
import {
  AlertCircle,
  CheckCircle2,
  Inbox,
  LoaderCircle,
  X,
  ArrowRight,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { ApiError } from "./api";
import { label } from "./format";
export function Button({
  variant = "primary",
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost" | "danger";
}) {
  return (
    <button className={`button button--${variant} ${className}`} {...props} />
  );
}
export function Badge({
  value,
  children,
}: {
  value?: unknown;
  children?: ReactNode;
}) {
  return (
    <span className={`badge badge--${String(value ?? "neutral")}`}>
      {children ?? label(value)}
    </span>
  );
}
export function Notice({
  children,
  tone = "info",
}: {
  children: ReactNode;
  tone?: "info" | "error" | "success" | "warning";
}) {
  return (
    <div
      className={`notice notice--${tone}`}
      role={tone === "error" ? "alert" : "status"}
    >
      {tone === "success" ? (
        <CheckCircle2 size={19} />
      ) : (
        <AlertCircle size={19} />
      )}
      <div>{children}</div>
    </div>
  );
}
export function ErrorNotice({ error }: { error: unknown }) {
  if (!error) return null;
  const decisions =
    error instanceof ApiError ? error.data.decisions : undefined;
  return (
    <Notice tone="error">
      {error instanceof Error
        ? error.message
        : "Não foi possível concluir a operação."}
      {Array.isArray(decisions) && decisions.length > 0 && (
        <small>Decisões necessárias: {decisions.join(", ")}</small>
      )}
    </Notice>
  );
}
export function Empty({
  title = "Ainda não há registros",
  description = "Os registros cadastrados aparecerão aqui.",
  action,
}: {
  title?: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="empty">
      <span className="empty__icon">
        <Inbox size={28} />
      </span>
      <h3>{title}</h3>
      <p>{description}</p>
      {action}
    </div>
  );
}
export function Loading() {
  return (
    <div className="loading" role="status">
      <LoaderCircle size={22} className="spin" />
      Carregando registros…
    </div>
  );
}
export function PageTitle({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  actions?: ReactNode;
}) {
  return (
    <header className="page-heading">
      <div>
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <h1>{title}</h1>
        {description && <p className="page-description">{description}</p>}
      </div>
      {actions && <div className="page-actions">{actions}</div>}
    </header>
  );
}
export function Field({
  label: caption,
  hint,
  children,
  wide = false,
}: {
  label: string;
  hint?: string;
  children: ReactNode;
  wide?: boolean;
}) {
  const id = useId();
  return (
    <div className={`field ${wide ? "field--wide" : ""}`}>
      <label id={`${id}-label`} htmlFor={id}>
        {caption}
      </label>
      {isValidElement(children)
        ? cloneElement(
            children as ReactElement<{
              id?: string;
              "aria-describedby"?: string;
              "aria-labelledby"?: string;
            }>,
            {
              id,
              "aria-describedby": hint ? `${id}-hint` : undefined,
              "aria-labelledby": `${id}-label`,
            },
          )
        : children}
      {hint && <small id={`${id}-hint`}>{hint}</small>}
    </div>
  );
}
export function Input(props: InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} />;
}
export function Modal({
  open,
  onClose,
  title,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const id = useId();
  useEffect(() => {
    if (open && !dialog.current?.open) dialog.current?.showModal();
    if (!open && dialog.current?.open) dialog.current.close();
  }, [open]);
  return (
    <dialog
      ref={dialog}
      className="modal"
      aria-labelledby={id}
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      onClick={(event) => {
        if (event.target === dialog.current) onClose();
      }}
    >
      <div className="modal__heading">
        <h2 id={id}>{title}</h2>
        <Button variant="ghost" aria-label="Fechar diálogo" onClick={onClose}>
          <X size={20} />
        </Button>
      </div>
      <div className="modal__body">{children}</div>
    </dialog>
  );
}
export function Confirm({
  title,
  description,
  action,
  onClose,
  confirm = "Confirmar",
  danger = false,
  children,
}: {
  title: string;
  description: string;
  action: () => Promise<unknown>;
  onClose: () => void;
  confirm?: string;
  danger?: boolean;
  children?: ReactNode;
}) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<unknown>();
  return (
    <Modal open onClose={() => !pending && onClose()} title={title}>
      <p>{description}</p>
      {children}
      <ErrorNotice error={error} />
      <div className="form-actions">
        <Button variant="secondary" onClick={onClose} disabled={pending}>
          Voltar
        </Button>
        <Button
          variant={danger ? "danger" : "primary"}
          disabled={pending}
          onClick={async () => {
            setPending(true);
            try {
              await action();
              onClose();
            } catch (err) {
              setError(err);
            } finally {
              setPending(false);
            }
          }}
        >
          {pending ? "Salvando…" : confirm}
        </Button>
      </div>
    </Modal>
  );
}
export function Pagination({
  page,
  count,
  onChange,
}: {
  page: number;
  count: number;
  onChange: (page: number) => void;
}) {
  const pages = Math.max(1, Math.ceil(count / 25));
  return (
    <div className="pagination">
      <span>
        {count} {count === 1 ? "registro" : "registros"} · Página {page} de{" "}
        {pages}
      </span>
      <div>
        <Button
          variant="secondary"
          disabled={page <= 1}
          onClick={() => onChange(page - 1)}
          aria-label="Página anterior"
        >
          <ChevronLeft size={18} />
        </Button>
        <Button
          variant="secondary"
          disabled={page >= pages}
          onClick={() => onChange(page + 1)}
          aria-label="Próxima página"
        >
          <ChevronRight size={18} />
        </Button>
      </div>
    </div>
  );
}
export function Journey({ step = 1 }: { step?: number }) {
  return (
    <ol className="journey" aria-label="Etapas do vínculo do aluno">
      {["Lead", "Aluno", "Matrícula", "Participação"].map((title, index) => (
        <li className={index <= step ? "journey__reached" : ""} key={title}>
          <span>{String(index + 1).padStart(2, "0")}</span>
          {title}
          {index < 3 && <ArrowRight size={16} />}
        </li>
      ))}
    </ol>
  );
}
