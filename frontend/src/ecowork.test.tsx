import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { EcoWork } from './EcoWork';

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
const charge = { id: 1, number: 1, amount: '116.50', due_date: '2026-11-04', status: 'open', payment: null };
const order = { id: 1, person_name: 'Ana Moradora', product_name: 'Semestral', total: '699.00', billing_mode: 'office', installments: 6, discount_percent: 0, starts_on: null, ends_on: null, coverage_status: 'awaiting_payment', charges: [charge] };
function setup() {
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
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter><EcoWork /></MemoryRouter></QueryClientProvider>);
  return fetcher;
}

it('separa cobertura aguardando pagamento e saldo do cliente', async () => {
  setup();
  expect(await screen.findByText('Ana Moradora')).toBeInTheDocument();
  expect(screen.getByText('Aguardando pagamento')).toBeInTheDocument();
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
