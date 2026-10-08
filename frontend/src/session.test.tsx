import { afterEach, it, expect, vi } from "vitest";
import {
  cleanup,
  render,
  screen,
  fireEvent,
  waitFor,
  act,
} from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider, useAuth } from "./auth";
import { api } from "./api";
import type { User } from "./types";
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});
const admin: User = {
  id: 1,
  email: "admin@example.test",
  first_name: "Administrativo de teste",
  last_name: "",
  access_status: "approved",
  roles: ["secretary"],
};
function SessionConsumer() {
  const { user, logout, refresh } = useAuth();
  return (
    <>
      <output>
        {user ? `${user.access_status}:${user.roles.join(",")}` : "sem sessão"}
      </output>
      <button onClick={() => void logout()}>Encerrar</button>
      <button onClick={() => void refresh()}>Revalidar</button>
    </>
  );
}
function setup(current: () => User) {
  const client = new QueryClient();
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockImplementation((path: string) =>
        Promise.resolve(
          new Response(
            JSON.stringify(
              path.includes("/csrf/")
                ? { csrfToken: "token" }
                : path.includes("/me/")
                  ? current()
                  : path.includes("/students/")
                    ? { detail: "Sem permissão operacional." }
                    : { detail: "Sessão encerrada." },
            ),
            { status: path.includes("/students/") ? 403 : 200 },
          ),
        ),
      ),
  );
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <AuthProvider>
          <SessionConsumer />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
  return client;
}
it("revalida uma revogação em 403 e descarta dados da autorização anterior", async () => {
  let value = admin;
  const client = setup(() => value);
  await screen.findByText("approved:secretary");
  client.setQueryData(["students"], { sensitive: "cadastro de teste" });
  value = { ...admin, access_status: "pending", roles: [] };
  await act(async () => {
    await api("students/").catch(() => {});
  });
  expect(await screen.findByText("pending:")).toBeInTheDocument();
  expect(client.getQueryData(["students"])).toBeUndefined();
});
it("preserva sessão aprovada em recusa operacional e limpa cache antes de outro perfil", async () => {
  let value = admin;
  const client = setup(() => value);
  await screen.findByText("approved:secretary");
  await act(async () => {
    await api("students/").catch(() => {});
  });
  expect(screen.getByText("approved:secretary")).toBeInTheDocument();
  client.setQueryData(["students"], { sensitive: "cadastro de teste" });
  fireEvent.click(screen.getByRole("button", { name: "Encerrar" }));
  await screen.findByText("sem sessão");
  expect(client.getQueryData(["students"])).toBeUndefined();
  value = {
    ...admin,
    id: 2,
    email: "instrutor@example.test",
    roles: ["instructor"],
  };
  fireEvent.click(screen.getByRole("button", { name: "Revalidar" }));
  await waitFor(() =>
    expect(screen.getByText("approved:instructor")).toBeInTheDocument(),
  );
  expect(client.getQueryData(["students"])).toBeUndefined();
});
