import { afterEach, it, expect, vi } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RecordForm } from "./forms";
import { enrollmentFields } from "./schema";
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});
it("sugere o valor da modalidade e preserva o valor ajustado pelo operador", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockImplementation((path: string) => {
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
  fireEvent.change(screen.getByLabelText("Turma"), { target: { value: "1" } });
  expect(screen.getByLabelText("Valor contratado (R$)")).toHaveValue(150);
  fireEvent.change(screen.getByLabelText("Valor contratado (R$)"), {
    target: { value: "175" },
  });
  fireEvent.change(screen.getByLabelText("Turma"), { target: { value: "2" } });
  expect(screen.getByLabelText("Valor contratado (R$)")).toHaveValue(175);
});
