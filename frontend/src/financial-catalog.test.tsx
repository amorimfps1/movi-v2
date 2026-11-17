import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { FinancialCatalog } from "./FinancialCatalog";
import { EcoCatalog } from "./EcoCatalog";

const service = vi.hoisted(() => ({ optionsFor: vi.fn(), post: vi.fn(), patch: vi.fn() }));
vi.mock("./api", () => ({ ...service, ApiError: class extends Error {} }));
afterEach(() => { cleanup(); vi.clearAllMocks(); });

it("impede conferir uma tabela com alterações ainda não salvas", async () => {
  service.optionsFor.mockResolvedValue([{ id: 5, version: 1, status: "draft", effective_from: "2026-01-01", effective_until: null,
    configuration: { plans: { quarterly: { months: 3, installments: [1, 2, 3] } }, prices: [], fees: { standard: { associated: "25.00", non_associated: "35.00" } } } }]);
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(<QueryClientProvider client={client}><FinancialCatalog /></QueryClientProvider>);
  const selector = await screen.findByLabelText("Versão da tabela");
  fireEvent.change(selector, { target: { value: "5" } });
  expect(screen.getByRole("button", { name: "Conferir rascunho salvo" })).not.toBeDisabled();
  fireEvent.change(screen.getByLabelText("Vigência a partir de"), { target: { value: "2026-02-01" } });
  expect(screen.getByRole("button", { name: "Conferir rascunho salvo" })).toBeDisabled();
  await waitFor(() => expect(screen.getByText("Salve as alterações antes de conferir.")).toBeInTheDocument());
});

it("permite remover e restaurar um preço sem perder seus dados", async () => {
  service.optionsFor.mockResolvedValue([{ id: 5, version: 1, status: "draft", effective_from: "2026-01-01", effective_until: null,
    configuration: { plans: { quarterly: { months: 3, installments: [1] } }, prices: [{ category: 2, plan: "quarterly", method: "card", associated: false, amount: "120.00" }], fees: {} } }]);
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(<QueryClientProvider client={client}><FinancialCatalog /></QueryClientProvider>);
  fireEvent.change(await screen.findByLabelText("Versão da tabela"), { target: { value: "5" } });
  fireEvent.click(screen.getByRole("button", { name: "Remover preço 1" }));
  expect(screen.getByText(/Nenhum preço cadastrado/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Desfazer remoção" }));
  expect(screen.getByLabelText("Valor total (R$)")).toHaveValue(120);
  expect(screen.getByLabelText("Categoria")).toHaveValue(2);
});

it("permite restaurar um produto EcoWork removido do rascunho", async () => {
  service.optionsFor.mockResolvedValue([{ id: 7, version: 1, status: "draft", effective_from: "2026-01-01", effective_until: null,
    configuration: { resident_discount_percent: 50, products: [{ code: "day", name: "Diária", price: "40.00", months: 0, hours: 8, max_installments: 1 }] } }]);
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(<QueryClientProvider client={client}><EcoCatalog /></QueryClientProvider>);
  fireEvent.change(await screen.findByLabelText("Versão"), { target: { value: "7" } });
  fireEvent.click(screen.getByRole("button", { name: "Remover Diária" }));
  expect(screen.getByText(/Nenhum produto cadastrado/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Desfazer remoção" }));
  expect(screen.getByLabelText("Nome")).toHaveValue("Diária");
  expect(screen.getByLabelText("Preço (R$)")).toHaveValue(40);
});
