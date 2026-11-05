import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { FinancialAction, FinancialHistory, type EcoPayment } from './EcoWorkFinancialActions';

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
const payment: EcoPayment = { id: 7, amount: '116.50', paid_on: '2026-01-01', method: 'pix', reference: '', actor: 1, voided_at: null, voided_by: null, void_reason: '', refunds: [] };
const order = { id: 3, person_name: 'Pessoa teste', product_name: 'Semestral', charges: [{ status: 'paid', amount: '116.50', payment }, { status: 'open', amount: '116.50', payment: null }] };
function setup(action: 'cancel' | 'void' | 'refund') {
  const fetcher = vi.fn(async (url: string) => url.includes('csrf') ? new Response(JSON.stringify({ csrfToken: 'test' })) : new Response(JSON.stringify({ detail: 'Confira os dados e tente novamente.' }), { status: 400 }));
  vi.stubGlobal('fetch', fetcher);
  render(<QueryClientProvider client={new QueryClient()}><FinancialAction action={action} order={order} payment={payment} onClose={vi.fn()} /></QueryClientProvider>);
  return fetcher;
}

it('exige escolha explícita do destino das parcelas e motivo antes do cancelamento', async () => {
  const fetcher = setup('cancel');
  const dialog = within(screen.getByRole('dialog'));
  const button = dialog.getByRole('button', { name: 'Cancelar contratação' });
  expect(button).toBeDisabled();
  fireEvent.change(dialog.getByLabelText('Motivo'), { target: { value: 'Encerramento solicitado' } });
  fireEvent.click(dialog.getByRole('checkbox'));
  expect(button).toBeDisabled();
  fireEvent.change(dialog.getByLabelText('Parcelas não pagas'), { target: { value: 'cancel_unpaid' } });
  expect(dialog.getByText('Saldo de cobranças que será cancelado')).toBeInTheDocument();
  expect(dialog.getByRole('checkbox')).not.toBeChecked();
  fireEvent.click(dialog.getByRole('checkbox'));
  fireEvent.click(button);
  expect(await dialog.findByText('Confira os dados e tente novamente.')).toBeInTheDocument();
  const call = fetcher.mock.calls.find(([url]) => url.includes('/cancel/'))!;
  expect(call[0]).toContain('/orders/3/cancel/');
});

it('devolução exige conferência e preserva o formulário após erro', async () => {
  setup('refund');
  const dialog = within(screen.getByRole('dialog'));
  const button = dialog.getByRole('button', { name: 'Registrar devolução' });
  expect(button).toBeDisabled();
  fireEvent.change(dialog.getByLabelText('Valor devolvido'), { target: { value: '20.00' } });
  fireEvent.change(dialog.getByLabelText('Motivo'), { target: { value: 'Devolução parcial conferida' } });
  fireEvent.click(dialog.getByRole('checkbox'));
  fireEvent.click(button);
  expect(await dialog.findByText('Confira os dados e tente novamente.')).toBeInTheDocument();
  expect(dialog.getByLabelText('Valor devolvido')).toHaveValue(20);
  expect(dialog.getByLabelText('Motivo')).toHaveValue('Devolução parcial conferida');
});

it('preserva autoria e motivo dos lançamentos invalidados e das devoluções', () => {
  render(<FinancialHistory payments={[{ ...payment, voided_at: '2026-11-05T10:00:00Z', voided_by: 2, void_reason: 'Lançamento duplicado' }, { ...payment, id: 8, refunds: [{ id: 2, amount: '20.00', refunded_on: '2026-11-05', method: 'pix', reference: 'DEV-123', reason: 'Devolução solicitada', actor: 3, created_at: '2026-11-05T10:00:00Z' }] }]} />);
  expect(screen.getByText(/Lançamento duplicado/)).toBeInTheDocument();
  expect(screen.getByText(/DEV-123/)).toHaveTextContent('operador #3');
});
