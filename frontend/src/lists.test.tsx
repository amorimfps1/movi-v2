import type { ReactNode } from "react";
import { afterEach, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import {
  MemoryRouter,
  Route,
  Routes,
  useLocation,
  useNavigate,
} from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ResourceList } from "./resources";
import { chargeSpec } from "./schema";
import { Finance } from "./Finance";
import { Reports } from "./Reports";
import { AccessList } from "./Management";
import { downloadCsv } from "./api";

vi.mock("./auth", () => ({
  useAuth: () => ({ user: { roles: ["secretary"] } }),
  isAdmin: () => true,
}));
vi.mock("./api", async (original) => ({
  ...(await original<typeof import("./api")>()),
  downloadCsv: vi.fn().mockResolvedValue(undefined),
}));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  vi.unstubAllGlobals();
});

function LocationControls() {
  const location = useLocation();
  const navigate = useNavigate();
  return (
    <>
      <output aria-label="Endereço atual">
        {location.pathname}
        {location.search}
      </output>
      <button onClick={() => navigate(-1)}>Voltar na navegação</button>
    </>
  );
}

function show(path: string, children: ReactNode) {
  render(
    <QueryClientProvider
      client={
        new QueryClient({
          defaultOptions: { queries: { retry: false, gcTime: 0 } },
        })
      }
    >
      <MemoryRouter initialEntries={[path]}>
        <LocationControls />
        {children}
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function setupFetch(empty = false) {
  const fetcher = vi.fn((path: string) => {
    const url = new URL(path, "http://localhost");
    const payload =
      url.pathname === "/api/reports/summary/"
        ? {
            received: "100.00",
            expected: "120.00",
            outstanding: "20.00",
            overdue: "20.00",
            categories: {},
            pending_decisions: [],
            students: 2,
            enrollments: 2,
            classes: 1,
            pending_users: 1,
          }
        : {
            count: empty ? 0 : 26,
            next: null,
            previous: null,
            results: empty
              ? []
              : [
                  {
                    id: Number(url.searchParams.get("page") || 1),
                    student_name: "Aluno de teste",
                    class_name: "Música",
                    category: "tuition",
                    amount: "120.00",
                    received: "0.00",
                    due_date: "2026-09-10",
                    status: "overdue",
                    email: "conta@example.test",
                    first_name: "Conta",
                    last_name: "de teste",
                    access_status: "pending",
                    roles: [],
                  },
                ],
          };
    return Promise.resolve(new Response(JSON.stringify(payload)));
  });
  vi.stubGlobal("fetch", fetcher);
  return fetcher;
}

function currentQuery() {
  return new URL(
    screen.getByLabelText("Endereço atual").textContent!,
    "http://localhost",
  ).searchParams;
}

it("restaura busca, filtros e página pelo endereço e mantém o contexto ao navegar", async () => {
  const fetcher = setupFetch();
  show(
    "/financeiro?start=2026-09-01&end=2026-09-30&status=overdue&search=Maria&page=2",
    <ResourceList spec={chargeSpec} />,
  );
  await screen.findByText("26 registros · Página 2 de 2");
  expect(screen.getByLabelText("Pesquisar cobranças")).toHaveValue("Maria");
  expect(screen.getByLabelText("Vencimento a partir de")).toHaveValue(
    "2026-09-01",
  );
  expect(screen.getByLabelText("Situação")).toHaveValue("overdue");

  fireEvent.change(screen.getByLabelText("Finalidade"), {
    target: { value: "extra" },
  });
  await screen.findByText("26 registros · Página 1 de 2");
  expect(currentQuery().get("category")).toBe("extra");
  expect(currentQuery().get("start")).toBe("2026-09-01");
  expect(currentQuery().get("search")).toBe("Maria");
  expect(currentQuery().has("page")).toBe(false);

  fireEvent.change(screen.getByLabelText("Pesquisar cobranças"), {
    target: { value: "Ana" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Buscar" }));
  await waitFor(() => expect(currentQuery().get("search")).toBe("Ana"));
  fireEvent.click(screen.getByRole("button", { name: "Voltar na navegação" }));
  await waitFor(() =>
    expect(screen.getByLabelText("Pesquisar cobranças")).toHaveValue("Maria"),
  );
  fireEvent.click(screen.getByRole("button", { name: "Voltar na navegação" }));
  await screen.findByText("26 registros · Página 2 de 2");
  expect(screen.getByLabelText("Finalidade")).toHaveValue("");
  expect(
    fetcher.mock.calls.some(([path]) => {
      const params = new URL(path, "http://localhost").searchParams;
      return (
        params.get("category") === "extra" &&
        params.get("start") === "2026-09-01" &&
        params.get("end") === "2026-09-30" &&
        params.get("status") === "overdue" &&
        params.get("page") === "1"
      );
    }),
  ).toBe(true);
});

it("exporta os mesmos filtros aplicados e permite limpar a consulta", async () => {
  setupFetch();
  show(
    "/financeiro?enrollment=8&status=overdue&start=2026-09-01&page=2",
    <ResourceList spec={chargeSpec} />,
  );
  await screen.findByText("26 registros · Página 2 de 2");
  fireEvent.click(screen.getByRole("button", { name: "Exportar CSV" }));
  await screen.findByText(
    "Exportação concluída: todos os registros filtrados.",
  );
  const [resource, params] = vi.mocked(downloadCsv).mock.calls[0];
  expect(resource).toBe("charges");
  expect(params.get("enrollment")).toBe("8");
  expect(params.get("status")).toBe("overdue");
  expect(params.get("start")).toBe("2026-09-01");
  fireEvent.click(screen.getByRole("button", { name: "Limpar filtros" }));
  await screen.findByText("26 registros · Página 1 de 2");
  expect(currentQuery().size).toBe(0);
  expect(screen.getByLabelText("Matrícula (número)")).toHaveValue(null);
});

it("trata página inválida e filtros desconhecidos sem encaminhá-los à consulta", async () => {
  const fetcher = setupFetch(true);
  show(
    "/financeiro?page=-4&desconhecido=1&status=paid",
    <ResourceList spec={chargeSpec} />,
  );
  expect(
    await screen.findByText("Nenhum resultado encontrado"),
  ).toBeInTheDocument();
  const params = new URL(fetcher.mock.calls[0][0], "http://localhost")
    .searchParams;
  expect(params.get("page")).toBe("1");
  expect(params.has("desconhecido")).toBe(false);
  expect(params.get("status")).toBe("paid");
});

it("aplica o filtro de solicitações pendentes recebido pelo endereço", async () => {
  const fetcher = setupFetch();
  show("/acessos?access_status=pending", <AccessList />);
  await screen.findByText("conta@example.test");
  expect(screen.getByLabelText("Autorização")).toHaveValue("pending");
  expect(
    new URL(fetcher.mock.calls[0][0], "http://localhost").searchParams.get(
      "access_status",
    ),
  ).toBe("pending");
});

it.each([
  {
    link: "Abrir cobranças",
    endpoint: "charges",
    startLabel: "Vencimento a partir de",
    endLabel: "Vencimento até",
  },
  {
    link: "Abrir recebimentos",
    endpoint: "payments",
    startLabel: "Recebimento a partir de",
    endLabel: "Recebimento até",
  },
])(
  "abre $endpoint com o período efetivamente consultado no relatório",
  async ({ link, endpoint, startLabel, endLabel }) => {
    const fetcher = setupFetch();
    show(
      "/relatorios",
      <Routes>
        <Route path="/relatorios" element={<Reports />} />
        <Route path="/financeiro" element={<Finance />} />
        <Route path="/recebimentos" element={<Finance payments />} />
      </Routes>,
    );
    await screen.findByRole("link", { name: link });
    fireEvent.change(screen.getByLabelText("Início do período"), {
      target: { value: "2026-09-01" },
    });
    fireEvent.change(screen.getByLabelText("Fim do período"), {
      target: { value: "2026-09-30" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Consultar período" }));
    fireEvent.click(await screen.findByRole("link", { name: link }));
    expect(await screen.findByLabelText(startLabel)).toHaveValue("2026-09-01");
    expect(screen.getByLabelText(endLabel)).toHaveValue("2026-09-30");
    await waitFor(() =>
      expect(
        fetcher.mock.calls.some(([path]) => {
          const url = new URL(path, "http://localhost");
          return (
            url.pathname === `/api/${endpoint}/` &&
            url.searchParams.get("start") === "2026-09-01" &&
            url.searchParams.get("end") === "2026-09-30"
          );
        }),
      ).toBe(true),
    );
    expect(
      screen.getByText(/Indicadores gerais de 01\/09\/2026 a 30\/09\/2026/),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", {
        name: endpoint === "charges" ? "Recebimentos" : "Cobranças",
      }),
    ).toHaveAttribute(
      "href",
      `${endpoint === "charges" ? "/recebimentos" : "/financeiro"}?start=2026-09-01&end=2026-09-30`,
    );
  },
);
