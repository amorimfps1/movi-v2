import { afterEach, describe, it, expect, vi } from "vitest";
import {
  cleanup,
  render,
  screen,
  fireEvent,
  waitFor,
} from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider, Login } from "./auth";
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});
function renderLogin(register = false) {
  return render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <MemoryRouter>
        <AuthProvider>
          <Login register={register} />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}
function json(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}
describe("acesso", () => {
  it("mostra impedimento de conta pendente sem acesso interno", async () => {
    const fetcher = vi.fn().mockImplementation((path: string) =>
      path.endsWith("/me/")
        ? Promise.resolve(json({ detail: "Não autenticado" }, 403))
        : path.endsWith("/csrf/")
          ? Promise.resolve(json({ csrfToken: "token" }))
          : Promise.resolve(
              json(
                {
                  detail: "Sua conta ainda não possui autorização interna.",
                  access_status: "pending",
                },
                403,
              ),
            ),
    );
    vi.stubGlobal("fetch", fetcher);
    renderLogin();
    await screen.findByLabelText("E-mail");
    fireEvent.change(screen.getByLabelText("E-mail"), {
      target: { value: "solicitante@exemplo.com" },
    });
    fireEvent.change(screen.getByLabelText("Senha"), {
      target: { value: "SenhaSecreta123" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Entrar no MOVI+" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "ainda não possui autorização",
    );
    expect(
      screen.getByRole("button", { name: "Entrar no MOVI+" }),
    ).toBeEnabled();
  });
  it("confirma solicitação como pendente, sem afirmar aprovação", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockImplementation((path: string) =>
          Promise.resolve(
            path.endsWith("/me/")
              ? json({ detail: "Não autenticado" }, 403)
              : path.endsWith("/csrf/")
                ? json({ csrfToken: "token" })
                : json({ access_status: "pending" }, 201),
          ),
        ),
    );
    renderLogin(true);
    await screen.findByLabelText("Nome");
    fireEvent.change(screen.getByLabelText("Nome"), {
      target: { value: "Maria" },
    });
    fireEvent.change(screen.getByLabelText("Sobrenome"), {
      target: { value: "Silva" },
    });
    fireEvent.change(screen.getByLabelText("E-mail"), {
      target: { value: "maria@exemplo.com" },
    });
    fireEvent.change(screen.getByLabelText("Senha"), {
      target: { value: "SenhaSecreta123" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Solicitar acesso" }));
    await waitFor(() =>
      expect(screen.getByRole("status")).toHaveTextContent(
        "Sua conta está pendente",
      ),
    );
    expect(
      screen.queryByRole("button", { name: "Salvar cadastro" }),
    ).not.toBeInTheDocument();
  });
});
