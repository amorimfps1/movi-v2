import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { FinancialCatalog } from "./FinancialCatalog";

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
