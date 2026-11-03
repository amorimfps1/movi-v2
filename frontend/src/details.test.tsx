import { afterEach, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import { Link, MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StudentDetail } from "./resources";
import { EnrollmentDetail } from "./EnrollmentDetail";
import { RecordDetail } from "./RecordDetail";
import { classSpec } from "./schema";
import { timestamp } from "./format";

vi.mock("./auth", () => ({
  useAuth: () => ({ user: { roles: ["secretary"] } }),
  isAdmin: () => true,
}));

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const eligibility = {
  eligible: null,
  status: "decision_required",
  reason: "Cobertura pendente de definição.",
  decisions: ["DN-004"],
};
const condition = {
  id: 7,
  enrollment: 1,
  amount: "120.50",
  effective_on: "2026-09-01",
  plan: "monthly",
  actor: 4,
  reason: "Condição original preservada.",
  created_at: "2026-08-28T15:30:00Z",
};

function json(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), { status });
}

function responseFor(path: string) {
  const url = new URL(path, "http://localhost");
  if (url.pathname.endsWith("/conditions/")) return json([condition]);
  if (url.pathname.endsWith("/eligibility/")) return json(eligibility);
  if (/\/students\/\d+\/$/.test(url.pathname)) {
    return json({
      id: Number(url.pathname.split("/").at(-2)),
      name: "Aluno de teste",
      archived: false,
    });
  }
  if (/\/enrollments\/\d+\/$/.test(url.pathname)) {
    return json({
      id: Number(url.pathname.split("/").at(-2)),
      student: 1,
      student_name: "Aluno de teste",
      class_group: 1,
      class_name: "Turma de teste",
      start_date: "2026-10-01",
      amount: "900.00",
      plan: "yearly",
      kind: "regular",
      administrative_status: "cancelled",
      eligibility,
    });
  }
  if (/\/classes\/\d+\/$/.test(url.pathname)) {
    return json({
      id: Number(url.pathname.split("/").at(-2)),
      name: "Turma de teste",
      modality: 1,
      modality_name: "Música",
      instructor: 1,
      instructor_name: "Instrutor de teste",
      weekdays: [1],
      start_time: "10:00:00",
      end_time: "11:00:00",
      active: true,
    });
  }
  if (
    ["/api/enrollments/", "/api/charges/", "/api/lessons/"].includes(
      url.pathname,
    )
  ) {
    const page = Number(url.searchParams.get("page") || 1);
    const parent = Number(
      url.searchParams.get("student") ||
        url.searchParams.get("enrollment") ||
        url.searchParams.get("class_group"),
    );
    const count = parent === 1 ? 26 : 1;
    const first = (page - 1) * 25;
    const results = Array.from(
      { length: Math.max(0, Math.min(25, count - first)) },
      (_, index) => ({
        id: first + index + 1,
        class_name: `Vínculo ${first + index + 1}`,
        start_date: "2026-10-01",
        plan: "monthly",
        amount: "120.00",
        category: "tuition",
        due_date: "2026-10-10",
        date: "2026-10-08",
        instructor_name: "Instrutor de teste",
        status: "scheduled",
        eligibility,
      }),
    );
    return json({
      count,
      next: page * 25 < count ? "?page=2" : null,
      previous: page > 1 ? "?page=1" : null,
      results,
    });
  }
  if (["/api/modalities/", "/api/instructors/"].includes(url.pathname)) {
    return json({
      count: 1,
      next: null,
      previous: null,
      results: [{ id: 1, name: "Cadastro de teste" }],
    });
  }
  throw new Error(`Consulta inesperada: ${path}`);
}

const cases = [
  {
    route: "alunos",
    endpoint: "enrollments",
    filter: "student",
    region: "Matrículas e participação",
    childRoute: "matriculas",
    element: <StudentDetail />,
  },
  {
    route: "matriculas",
    endpoint: "charges",
    filter: "enrollment",
    region: "Cobranças da matrícula",
    childRoute: "cobrancas",
    element: <EnrollmentDetail />,
  },
  {
    route: "turmas",
    endpoint: "lessons",
    filter: "class_group",
    region: "Encontros desta turma",
    childRoute: "aulas",
    element: <RecordDetail spec={classSpec} />,
  },
];

function show(detail: (typeof cases)[number]) {
  render(
    <QueryClientProvider
      client={
        new QueryClient({
          defaultOptions: { queries: { retry: false, gcTime: 0 } },
        })
      }
    >
      <MemoryRouter initialEntries={[`/${detail.route}/1`]}>
        <Link to={`/${detail.route}/2`}>Abrir outro cadastro</Link>
        <Routes>
          <Route path={`/${detail.route}/:id`} element={detail.element} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

it.each(cases)(
  "consulta todos os vínculos de $route e reinicia a página ao mudar de cadastro",
  async (detail) => {
    const fetcher = vi.fn((path: string) => Promise.resolve(responseFor(path)));
    vi.stubGlobal("fetch", fetcher);
    show(detail);

    const section = within(
      await screen.findByRole("region", { name: detail.region }),
    );
    await section.findByText("26 registros · Página 1 de 2");
    expect(
      section.getByRole("button", { name: "Página anterior" }),
    ).toBeDisabled();
    expect(
      section
        .getAllByRole("link")
        .filter((link) =>
          link.getAttribute("href")?.startsWith(`/${detail.childRoute}/`),
        ),
    ).toHaveLength(25);

    fireEvent.click(section.getByRole("button", { name: "Próxima página" }));
    await section.findByText("26 registros · Página 2 de 2");
    expect(
      section
        .getAllByRole("link")
        .filter(
          (link) => link.getAttribute("href") === `/${detail.childRoute}/26`,
        ),
    ).toHaveLength(1);
    expect(
      section.getByRole("button", { name: "Próxima página" }),
    ).toBeDisabled();
    const secondPagePath = `/api/${detail.endpoint}/?${detail.filter}=1&page=2&page_size=25`;
    expect(fetcher).toHaveBeenCalledWith(secondPagePath, expect.anything());

    fireEvent.click(section.getByRole("button", { name: "Página anterior" }));
    await section.findByText("26 registros · Página 1 de 2");
    fireEvent.click(section.getByRole("button", { name: "Próxima página" }));
    await section.findByText("26 registros · Página 2 de 2");
    fireEvent.click(screen.getByRole("link", { name: "Abrir outro cadastro" }));
    const newSection = within(
      await screen.findByRole("region", { name: detail.region }),
    );
    await newSection.findByRole("link", {
      name:
        detail.route === "alunos"
          ? /Vínculo 1/
          : detail.route === "matriculas"
            ? "Mensalidade"
            : /08\/10\/2026/,
    });
    expect(fetcher).toHaveBeenCalledWith(
      `/api/${detail.endpoint}/?${detail.filter}=2&page=1&page_size=25`,
      expect.anything(),
    );
    expect(
      fetcher.mock.calls.some(([path]) =>
        path.includes(`${detail.filter}=2&page=2`),
      ),
    ).toBe(false);
    expect(
      newSection.queryByRole("button", { name: "Próxima página" }),
    ).not.toBeInTheDocument();
  },
);

it("mostra as condições originais e sua autoria mesmo para matrícula cancelada com valor atual diferente", async () => {
  const fetcher = vi.fn((path: string, _options?: RequestInit) =>
    Promise.resolve(responseFor(path)),
  );
  vi.stubGlobal("fetch", fetcher);
  show(cases[1]);
  const history = within(
    await screen.findByRole("region", {
      name: "Histórico das condições comerciais",
    }),
  );
  expect(await history.findByText(/R\$\s120,50/)).toBeInTheDocument();
  expect(history.getByText("A partir de 01/09/2026")).toBeInTheDocument();
  expect(history.getByText("Mensal")).toBeInTheDocument();
  expect(
    history.getByText(timestamp(condition.created_at)),
  ).toBeInTheDocument();
  expect(history.getByText(condition.reason)).toBeInTheDocument();
  expect(history.getByRole("link", { name: "Conta #4" })).toHaveAttribute(
    "href",
    "/acessos/4",
  );
  expect(
    history.getByRole("link", { name: "Consultar ações desta matrícula" }),
  ).toHaveAttribute(
    "href",
    "/auditoria?target_type=billing.enrollment&target_id=1",
  );
  expect(history.queryByText(/R\$\s900,00/)).not.toBeInTheDocument();
  expect(screen.getByText("Cancelada")).toBeInTheDocument();
  expect(
    fetcher.mock.calls.every(
      ([, options]) => !options || !options.method || options.method === "GET",
    ),
  ).toBe(true);
});

it("informa histórico ausente sem criar condições a partir do contrato atual", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn((path: string) =>
      Promise.resolve(
        path.endsWith("/conditions/") ? json([]) : responseFor(path),
      ),
    ),
  );
  show(cases[1]);
  const history = within(
    await screen.findByRole("region", {
      name: "Histórico das condições comerciais",
    }),
  );
  expect(
    await history.findByText("Nenhuma condição comercial registrada"),
  ).toBeInTheDocument();
  expect(history.queryByRole("article")).not.toBeInTheDocument();
});

it("exibe recusa de acesso ao histórico e permite tentar novamente sem ocultar a matrícula", async () => {
  let attempts = 0;
  vi.stubGlobal(
    "fetch",
    vi.fn((path: string) =>
      Promise.resolve(
        path.endsWith("/conditions/") && ++attempts === 1
          ? json(
              { detail: "Sem autorização para consultar este histórico." },
              403,
            )
          : responseFor(path),
      ),
    ),
  );
  show(cases[1]);
  const history = within(
    await screen.findByRole("region", {
      name: "Histórico das condições comerciais",
    }),
  );
  expect(await history.findByRole("alert")).toHaveTextContent(
    "Sem autorização",
  );
  expect(
    history.queryByText("Nenhuma condição comercial registrada"),
  ).not.toBeInTheDocument();
  expect(
    screen.getByRole("heading", { name: "Aluno de teste" }),
  ).toBeInTheDocument();
  fireEvent.click(
    history.getByRole("button", {
      name: "Tentar carregar histórico novamente",
    }),
  );
  expect(await history.findByText(condition.reason)).toBeInTheDocument();
  expect(history.queryByRole("alert")).not.toBeInTheDocument();
});

it("permite voltar ao início se a página de cobranças deixar de existir", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn((path: string) =>
      Promise.resolve(
        path.includes("charges/?enrollment=1&page=2")
          ? json({ detail: "Página inválida." }, 404)
          : responseFor(path),
      ),
    ),
  );
  show(cases[1]);
  const charges = within(
    await screen.findByRole("region", { name: "Cobranças da matrícula" }),
  );
  fireEvent.click(
    await charges.findByRole("button", { name: "Próxima página" }),
  );
  expect(await charges.findByRole("alert")).toBeInTheDocument();
  fireEvent.click(
    charges.getByRole("button", { name: "Voltar à primeira página" }),
  );
  expect(
    await charges.findByText("26 registros · Página 1 de 2"),
  ).toBeInTheDocument();
});
