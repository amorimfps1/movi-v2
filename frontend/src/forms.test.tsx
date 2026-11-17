import { afterEach, it, expect, vi } from "vitest";
import { render, screen, fireEvent, cleanup, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RecordForm } from "./forms";
import { enrollmentFields, leadSpec } from "./schema";
import { useState } from "react";
import { Field, SearchableSelect } from "./ui";
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});
it("busca registros pelo nome e exige uma opção válida, distinguindo nomes repetidos", () => {
  function Example() {
    const [value, setValue] = useState("");
    return <><Field label="Pessoa"><SearchableSelect value={value} onChange={setValue} required options={[
      { value: 1, label: "Ana Silva" }, { value: 2, label: "Ana Silva" }, { value: 3, label: "Bruno" },
    ]} /></Field><output>{value}</output></>;
  }
  render(<Example />);
  const input = screen.getByLabelText("Pessoa") as HTMLInputElement;
  fireEvent.focus(input);
  expect(screen.getAllByRole("option")).toHaveLength(3);
  fireEvent.change(input, { target: { value: "Ana" } });
  expect(input.validity.customError).toBe(true);
  expect(screen.getAllByRole("option")).toHaveLength(2);
  fireEvent.click(screen.getByRole("option", { name: "Ana Silva (#2)" }));
  expect(input.validity.valid).toBe(true);
  expect(screen.getByText("2", { selector: "output" })).toBeInTheDocument();
  fireEvent.change(input, { target: { value: "" } });
  expect(input.validity.valueMissing).toBe(true);
});
it("envia o lead e a aula experimental na mesma solicitação", async () => {
  const fetcher = vi.fn().mockImplementation((path: string, init?: RequestInit) => {
    if (path.includes('/csrf/')) return Promise.resolve(new Response(JSON.stringify({ csrfToken: 'token' })));
    if (init?.method === 'POST') return Promise.resolve(new Response(JSON.stringify({ id: 9, name: 'Ana' }), { status: 201 }));
    const rows = path.includes('lessons/') ? [{ id: 4, name: 'Turma A — 01/01/2099', date: '2099-01-01' }] : [];
    return Promise.resolve(new Response(JSON.stringify({ results: rows, next: null, count: rows.length })));
  });
  vi.stubGlobal('fetch', fetcher);
  const close = vi.fn();
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    <RecordForm title="Novo lead" endpoint="leads/" fields={leadSpec.fields} onClose={close} />
  </QueryClientProvider>);
  fireEvent.change(await screen.findByLabelText('Nome completo'), { target: { value: 'Ana' } });
  fireEvent.click(screen.getByLabelText('Agendar aula experimental'));
  const lesson = await screen.findByLabelText('Aula experimental');
  fireEvent.focus(lesson);
  fireEvent.click(screen.getByRole('option', { name: 'Turma A — 01/01/2099' }));
  fireEvent.change(screen.getByLabelText('Data de nascimento'), { target: { value: '2000-01-01' } });
  fireEvent.click(screen.getByRole('button', { name: 'Salvar cadastro' }));
  await waitFor(() => expect(close).toHaveBeenCalled());
  const request = fetcher.mock.calls.find(([path, init]) => path === '/api/leads/' && init?.method === 'POST');
  expect(JSON.parse(String(request?.[1]?.body))).toMatchObject({ name: 'Ana', trial: { lesson: 4, person: null, birth_date: '2000-01-01', guardian_authorization: false } });
});
it("solicita os dados do responsável ao ativar menor de idade e os envia com a matrícula", async () => {
  const fetcher = vi.fn().mockImplementation((path: string, init?: RequestInit) => {
    if (path.includes('/csrf/')) return Promise.resolve(new Response(JSON.stringify({ csrfToken: 'token' })));
    if (init?.method === 'POST') return Promise.resolve(new Response(JSON.stringify({ id: 10 }), { status: 201 }));
    if (path.includes('financial-options/')) return Promise.resolve(new Response(JSON.stringify({ plans: [{ code: 'quarterly', name: 'Trimestral', installments: [3] }], methods: ['card'] })));
    const rows = path.includes('students/') ? [{ id: 1, name: 'Aluno' }] : path.includes('classes/') ? [{ id: 2, name: 'Turma' }] : [];
    return Promise.resolve(new Response(JSON.stringify({ results: rows, next: null, count: rows.length })));
  });
  vi.stubGlobal('fetch', fetcher);
  const close = vi.fn();
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    <RecordForm title="Matrícula" endpoint="enrollments/" fields={enrollmentFields} onClose={close} />
  </QueryClientProvider>);
  fireEvent.change(await screen.findByLabelText('Aluno'), { target: { value: 'Aluno' } });
  fireEvent.change(screen.getByLabelText('Turma'), { target: { value: 'Turma' } });
  expect(screen.queryByLabelText('Nome do responsável')).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('switch', { name: 'Aluno é menor de idade' }));
  fireEvent.change(screen.getByLabelText('Nome do responsável'), { target: { value: 'Maria' } });
  fireEvent.change(screen.getByLabelText('Telefone do responsável'), { target: { value: '11999999999' } });
  fireEvent.click(screen.getByRole('button', { name: 'Salvar cadastro' }));
  await waitFor(() => expect(close).toHaveBeenCalled());
  const request = fetcher.mock.calls.find(([path, init]) => path === '/api/enrollments/' && init?.method === 'POST');
  expect(JSON.parse(String(request?.[1]?.body))).toMatchObject({ student: 1, class_group: 2, is_minor: true, guardian_data: { name: 'Maria', phone: '11999999999' } });
});
it("oferece apenas leads convertidos para o aluno selecionado e limpa o lead ao trocar de aluno", async () => {
  const fetcher = vi.fn().mockImplementation((path: string) => {
    const url = new URL(path, 'http://localhost');
    const rows = url.pathname.includes('/students/') ? [{ id: 1, name: 'Ana' }, { id: 2, name: 'Bruno' }]
      : url.pathname.includes('/leads/') ? (url.searchParams.get('student') === '1' ? [{ id: 11, name: 'Lead de Ana' }] : [{ id: 22, name: 'Lead de Bruno' }]) : [];
    return Promise.resolve(new Response(JSON.stringify({ results: rows, next: null, count: rows.length })));
  });
  vi.stubGlobal('fetch', fetcher);
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    <RecordForm title="Matrícula" endpoint="enrollments/" fields={enrollmentFields.filter((field) => ['student', 'source_lead'].includes(field.key))} onClose={() => {}} />
  </QueryClientProvider>);
  const student = await screen.findByLabelText('Aluno');
  expect(screen.getByLabelText('Lead de origem (opcional)')).toBeDisabled();
  expect(fetcher.mock.calls.some(([path]) => String(path).includes('/leads/'))).toBe(false);
  fireEvent.change(student, { target: { value: 'Ana' } });
  await waitFor(() => expect(screen.getByLabelText('Lead de origem (opcional)')).toBeEnabled());
  fireEvent.focus(screen.getByLabelText('Lead de origem (opcional)'));
  fireEvent.click(screen.getByRole('option', { name: 'Lead de Ana' }));
  fireEvent.change(student, { target: { value: 'Bruno' } });
  await waitFor(() => expect(screen.getByLabelText('Lead de origem (opcional)')).toHaveValue(''));
  await waitFor(() => expect(screen.getByLabelText('Lead de origem (opcional)')).toBeEnabled());
  fireEvent.focus(screen.getByLabelText('Lead de origem (opcional)'));
  expect(screen.getByRole('option', { name: 'Lead de Bruno' })).toBeInTheDocument();
  expect(screen.queryByRole('option', { name: 'Lead de Ana' })).not.toBeInTheDocument();
  expect(fetcher.mock.calls.some(([path]) => String(path).includes('student=2'))).toBe(true);
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
  fireEvent.change(screen.getByLabelText("Turma"), { target: { value: "Turma de teste A" } });
  expect(screen.queryByLabelText("Valor contratado (R$)")).not.toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Plano"), { target: { value: "yearly" } });
  fireEvent.change(screen.getByLabelText("Número de parcelas"), {
    target: { value: "12" },
  });
  fireEvent.change(screen.getByLabelText("Turma"), { target: { value: "Turma de teste B" } });
  expect(screen.getByLabelText("Número de parcelas")).toHaveValue(12);
  expect(screen.getByLabelText("Plano")).toHaveValue('yearly');
  expect(screen.queryByLabelText("Valor contratado (R$)")).not.toBeInTheDocument();
});
