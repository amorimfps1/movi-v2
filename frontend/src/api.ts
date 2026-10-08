import type { Page } from "./types";
export class ApiError extends Error {
  status: number;
  data: Record<string, unknown>;
  constructor(status: number, data: Record<string, unknown>) {
    super(
      status === 404
        ? "Registro não encontrado ou indisponível para seu perfil."
        : typeof data.detail === "string"
          ? data.detail
          : Object.entries(data)
              .map(
                ([key, value]) =>
                  `${key}: ${Array.isArray(value) ? value.join(" ") : String(value)}`,
              )
              .join(" · ") || "Não foi possível concluir a operação.",
    );
    this.status = status;
    this.data = data;
  }
}
let csrf: string | undefined;
export async function ensureCsrf() {
  const response = await fetch("/api/auth/csrf/", {
    credentials: "same-origin",
  });
  if (!response.ok)
    throw new Error(
      "Não foi possível iniciar uma sessão segura. Tente novamente.",
    );
  const data = await response.json();
  csrf =
    data.csrfToken ||
    data.csrf_token ||
    data.token ||
    document.cookie
      .split("; ")
      .find((item) => item.startsWith("csrftoken="))
      ?.split("=")[1];
}
export async function api<T>(
  path: string,
  options: RequestInit = {},
  csrfRetried = false,
): Promise<T> {
  const method = options.method || "GET";
  if (!["GET", "HEAD", "OPTIONS"].includes(method) && !csrf) await ensureCsrf();
  let response: Response;
  try {
    response = await fetch(`/api/${path}`, {
      ...options,
      credentials: "same-origin",
      headers: {
        ...(options.body ? { "Content-Type": "application/json" } : {}),
        ...(csrf ? { "X-CSRFToken": csrf } : {}),
        ...options.headers,
      },
    });
  } catch {
    throw new Error(
      "Não foi possível conectar ao MOVI+. Verifique a conexão e tente novamente.",
    );
  }
  if (response.status === 204) return undefined as T;
  const data = await response.json().catch(() => ({
    detail: "O serviço retornou uma resposta inesperada. Tente novamente.",
  }));
  if (!response.ok) {
    if (
      response.status === 403 &&
      !csrfRetried &&
      typeof data.detail === "string" &&
      data.detail.includes("CSRF") &&
      !["GET", "HEAD", "OPTIONS"].includes(method)
    ) {
      csrf = undefined;
      await ensureCsrf();
      return api<T>(path, options, true);
    }
    if (response.status === 401)
      window.dispatchEvent(new Event("movi:session-expired"));
    if (response.status === 403 && !path.startsWith("auth/"))
      window.dispatchEvent(new Event("movi:authorization-check"));
    throw new ApiError(response.status, data);
  }
  if (["auth/login/", "auth/logout/"].includes(path)) csrf = undefined;
  return data as T;
}
export const post = <T>(path: string, body: unknown) =>
  api<T>(path, { method: "POST", body: JSON.stringify(body) });
export const patch = <T>(path: string, body: unknown) =>
  api<T>(path, { method: "PATCH", body: JSON.stringify(body) });
export async function optionsFor(path: string) {
  const all: Record<string, unknown>[] = [];
  const [endpoint, query] = path.split("?");
  let page = 1;
  let hasNext = true;
  while (hasNext) {
    const params = new URLSearchParams(query);
    params.set("page_size", "100");
    params.set("page", String(page));
    const data = await api<Page<Record<string, unknown>>>(
      `${endpoint}?${params}`,
    );
    all.push(...data.results);
    hasNext = !!data.next;
    page++;
  }
  return all;
}
export async function downloadCsv(resource: string, params: URLSearchParams) {
  const response = await fetch(
    `/api/reports/export/?${new URLSearchParams({ ...Object.fromEntries(params), resource })}`,
    { credentials: "same-origin" },
  );
  if (!response.ok) {
    const data = await response.json();
    if (response.status === 403)
      window.dispatchEvent(new Event("movi:authorization-check"));
    throw new ApiError(response.status, data);
  }
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement("a");
  link.href = url;
  link.download = `movi-${resource}.csv`;
  link.click();
  URL.revokeObjectURL(url);
}
