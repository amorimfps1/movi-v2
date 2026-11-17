import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { App } from "./App";

const session = vi.hoisted(() => ({ roles: ["instructor"] as string[] }));
vi.mock("./auth", () => ({
  useAuth: () => ({ user: { first_name: "Ana", email: "ana@example.test", access_status: "approved", roles: session.roles }, loading: false, logout: vi.fn() }),
  isAdmin: () => session.roles.includes("secretary") || session.roles.includes("coordinator"),
  Login: () => null,
}));
vi.mock("./query", () => ({ useApi: () => ({}) }));
vi.mock("./Academic", () => ({ AcademicList: () => <h1>Lista acadêmica</h1>, ClassDetail: () => <h1>Turma</h1>, LessonDetail: () => null }));
vi.mock("./Finance", () => ({ Finance: () => <h1>Financeiro</h1>, ChargeDetail: () => <h1>Cobrança</h1>, PaymentDetail: () => null }));

afterEach(() => { cleanup(); vi.restoreAllMocks(); session.roles = ["instructor"]; });

it("abre o grupo da rota, permite recolhê-lo e respeita as permissões", () => {
  vi.spyOn(window, "scrollTo").mockImplementation(() => {});
  render(<MemoryRouter initialEntries={["/turmas/12"]}><App /></MemoryRouter>);
  const nav = within(screen.getByRole("navigation", { name: "Navegação principal" }));
  const activities = nav.getByRole("button", { name: "ATIVIDADES" });
  expect(activities).toHaveAttribute("aria-expanded", "true");
  expect(nav.getByRole("link", { name: "Turmas" })).toHaveAttribute("aria-current", "page");
  expect(nav.queryByRole("link", { name: "Modalidades" })).not.toBeInTheDocument();
  fireEvent.click(activities);
  expect(activities).toHaveAttribute("aria-expanded", "false");
  expect(nav.queryByRole("link", { name: "Turmas" })).not.toBeInTheDocument();
  fireEvent.click(activities);
  expect(nav.getByRole("link", { name: "Aulas e chamada" }).querySelector("svg")).toBeNull();
  fireEvent.click(nav.getByRole("link", { name: "Aulas e chamada" }));
  expect(nav.getByRole("link", { name: "Aulas e chamada" })).toHaveAttribute("aria-current", "page");
});

it("organiza os módulos por área e abre o financeiro em detalhes de cobrança", () => {
  session.roles = ["coordinator"];
  vi.spyOn(window, "scrollTo").mockImplementation(() => {});
  render(<MemoryRouter initialEntries={["/cobrancas/12"]}><App /></MemoryRouter>);
  const nav = within(screen.getByRole("navigation", { name: "Navegação principal" }));
  const finance = nav.getByRole("button", { name: "FINANCEIRO" });
  expect(finance).toHaveAttribute("aria-expanded", "true");
  expect(nav.getByRole("link", { name: "Tabelas financeiras" })).toBeInTheDocument();
  fireEvent.click(nav.getByRole("button", { name: "ECOWORK" }));
  expect(nav.getByRole("link", { name: "Catálogo EcoWork" })).toBeInTheDocument();
  fireEvent.click(nav.getByRole("button", { name: "INDICADORES" }));
  expect(nav.getByRole("link", { name: "Relatórios" })).toBeInTheDocument();
  expect(nav.getByRole("button", { name: "ATIVIDADES" })).toBeInTheDocument();
});
