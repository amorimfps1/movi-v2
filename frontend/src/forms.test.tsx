import { afterEach, it, expect, vi } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RecordForm } from "./forms";
import { enrollmentFields } from "./schema";
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});
it("mantém o contrato escolhido ao trocar turma e não usa o preço legado como total", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockImplementation((path: string) => {
      if (path.includes('financial-options/')) return Promise.resolve(new Response(JSON.stringify({ plans: [{ code: 'quarterly', name: 'Trimestral', installments: [1, 2, 3] }, { code: 'yearly', name: 'Anual', installments: [3, 6, 10, 12] }, { code: 'p_custom', name: 'Plano personalizado', installments: [6] }], methods: ['card'] })));
      const rows = path.includes("classes/")
        ? [
            { id: 1, name: "Turma de teste A", modality: 11 },
            { id: 2, name: "Turma de teste B", modality: 12 },
          ]
        : path.includes("modalities/")
          ? [
              {
                id: 11,
                name: "Modalidade de teste A",
                default_price: "150.00",
              },
              {
                id: 12,
                name: "Modalidade de teste B",
                default_price: "200.00",
              },
            ]
          : [{ id: 1, name: "Aluno de teste" }];
      return Promise.resolve(
        new Response(
          JSON.stringify({ results: rows, next: null, count: rows.length }),
        ),
      );
    }),
  );
  render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <RecordForm
        title="Matrícula de teste"
        endpoint="enrollments/"
        fields={enrollmentFields}
        onClose={() => {}}
      />
    </QueryClientProvider>,
  );
  await screen.findByLabelText("Turma");
  expect(screen.getByRole('option', { name: 'Plano personalizado' })).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Turma"), { target: { value: "1" } });
  expect(screen.queryByLabelText("Valor contratado (R$)")).not.toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Plano"), { target: { value: "yearly" } });
  fireEvent.change(screen.getByLabelText("Número de parcelas"), {
    target: { value: "12" },
  });
  fireEvent.change(screen.getByLabelText("Turma"), { target: { value: "2" } });
  expect(screen.getByLabelText("Número de parcelas")).toHaveValue(12);
  expect(screen.getByLabelText("Plano")).toHaveValue('yearly');
  expect(screen.queryByLabelText("Valor contratado (R$)")).not.toBeInTheDocument();
});
