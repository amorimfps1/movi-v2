import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, within, waitFor } from '@testing-library/react';
import { MemoryRouter, useNavigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { EcoWork } from './EcoWork';
import { PersonOverview } from './PersonOverview';

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
const charge = { id: 1, number: 1, amount: '116.50', due_date: '2026-11-04', status: 'open', payment: null };
const order = { id: 1, person_name: 'Ana Moradora', product_name: 'Semestral', total: '699.00', billing_mode: 'office', installments: 6, discount_percent: 0, starts_on: null, ends_on: null, coverage_status: 'awaiting_payment', charges: [charge] };
function Back() {
  const navigate = useNavigate();
  return <button onClick={() => navigate(-1)}>Voltar consulta</button>;
}
function setup(initial = '/') {
  const fetcher = vi.fn(async (input: string, init?: RequestInit) => {
    let result: unknown = {};
    if (input.includes('/auth/csrf/')) result = { csrfToken: 'test' };
    else if (input.includes('/ecowork/orders/')) result = { results: [order], count: 1, next: null, previous: null };
    else if (input.includes('/people/')) result = { results: [{ id: 3, name: 'Ana Moradora', phone: '123' }], count: 1 };
    else if (input.includes('/ecowork/products/')) result = [{ code: 'monthly', name: 'Mensal', price: '169.00', months: 1, max_installments: 1 }];
    else if (input.includes('/ecowork/quote/')) result = { total: '84.50', base_price: '169.00', discount_percent: 50, reason: 'Desconto' };
    else if (input.includes('/receive/')) {
      expect(JSON.parse(String(init?.body)).amount).toBe('116.50');
      return new Response(JSON.stringify({ detail: 'Pagamento já registrado.' }), { status: 400 });
    }
    return new Response(JSON.stringify(result));
  });
  vi.stubGlobal('fetch', fetcher);
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter initialEntries={[initial]}><Back /><EcoWork /></MemoryRouter></QueryClientProvider>);
  return fetcher;
}

it('separa cobertura aguardando pagamento e saldo do cliente', async () => {
  setup();
  expect(await screen.findByText('Ana Moradora')).toBeInTheDocument();
  expect(within(screen.getByRole('article')).getByText('Aguardando pagamento')).toBeInTheDocument();
  expect(screen.getByText('Inicia no primeiro pagamento')).toBeInTheDocument();
  expect(screen.getByText('Saldo a pagar pelo cliente')).toBeInTheDocument();
});

it('exige conferência antes de enviar recebimento e mantém erro visível', async () => {
  const fetcher = setup();
  fireEvent.click(await screen.findByRole('button', { name: 'Registrar pagamento' }));
  const dialog = screen.getByRole('dialog');
  const confirm = within(dialog).getByRole('button', { name: 'Confirmar pagamento' });
  expect(confirm).toBeDisabled();
  fireEvent.click(within(dialog).getByRole('checkbox'));
  fireEvent.click(confirm);
  expect(await within(dialog).findByText('Pagamento já registrado.')).toBeInTheDocument();
  expect(fetcher.mock.calls.filter(([url]) => url.includes('/receive/'))).toHaveLength(1);
});

it('consulta desconto da pessoa antes de permitir contratação', async () => {
  setup();
  fireEvent.click(screen.getByRole('button', { name: 'Contratar plano ou avulso' }));
  const dialog = screen.getByRole('dialog');
  expect(within(dialog).getByRole('button', { name: 'Confirmar contratação' })).toBeDisabled();
  await within(dialog).findByRole('option', { name: 'Ana Moradora · 123' });
  fireEvent.change(within(dialog).getByLabelText('Pessoa', { exact: true }), { target: { value: '3' } });
  expect(await within(dialog).findByText('50% de desconto de associado')).toBeInTheDocument();
  expect(within(dialog).getByRole('button', { name: 'Confirmar contratação' })).toBeEnabled();
});

it('preserva pessoa, filtros e histórico sem encaminhar parâmetros desconhecidos', async () => {
  const fetcher = setup('/ecowork?person=3&status=overdue&page=2&unknown=value');
  await screen.findByText('Ana Moradora');
  expect(screen.getByLabelText('Situação da parcela')).toHaveValue('overdue');
  fireEvent.change(screen.getByLabelText('Cobertura'), { target: { value: 'active' } });
  await waitFor(() => expect(fetcher.mock.calls.some(([url]) => url.includes('coverage=active') && url.includes('person=3') && url.includes('page=1'))).toBe(true));
  expect(fetcher.mock.calls.every(([url]) => !url.includes('unknown'))).toBe(true);
  fireEvent.click(screen.getByText('Voltar consulta'));
  await waitFor(() => expect(screen.getByLabelText('Cobertura')).toHaveValue(''));
  expect(screen.getByLabelText('Situação da parcela')).toHaveValue('overdue');
  fireEvent.click(screen.getByText('Limpar filtros'));
  expect(screen.queryByText('Consulta da pessoa #3.')).not.toBeInTheDocument();
});

it('mostra dívida anterior no resumo e abre contratos da pessoa exata', async () => {
  vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ total: '868.00', paid: '169.00', balance: '699.00', overdue: '116.50', orders: 2 }))));
  render(<QueryClientProvider client={new QueryClient()}><MemoryRouter><PersonOverview id="3" /></MemoryRouter></QueryClientProvider>);
  expect(await screen.findByText(/699,00/)).toBeInTheDocument();
  expect(screen.getByText(/116,50/)).toBeInTheDocument();
  expect(screen.getByRole('link', { name: 'Contratações e parcelas EcoWork' })).toHaveAttribute('href', '/ecowork?person=3');
});
