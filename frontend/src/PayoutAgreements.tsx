import type { ResourceSpec } from './schema';
import { date } from './format';
import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useApi } from './query';
import { RecordDetail } from './RecordDetail';
import { ActionForm } from './forms';
import { Button, Notice } from './ui';
import type { RecordData } from './types';

export const payoutAgreementSpec: ResourceSpec = {
  title: 'Acordos de repasse', singular: 'acordo', slug: 'acordos-repasse', endpoint: 'payout-agreements/',
  description: 'Registre o percentual e o critério de apropriação por instrutor, modalidade e vigência.', editable: false,
  fields: [
    { key: 'instructor', label: 'Instrutor', type: 'select', lookup: 'instructors/', required: true },
    { key: 'modality', label: 'Modalidade', type: 'select', lookup: 'modalities/', required: true },
    { key: 'effective_from', label: 'Início da vigência', type: 'date', required: true },
    { key: 'effective_until', label: 'Fim da vigência', type: 'date', required: true },
    { key: 'percentage', label: 'Percentual (%)', type: 'decimal', required: true },
    { key: 'allocation_method', label: 'Distribuição de pagamentos antecipados', type: 'select', required: true,
      options: [{ value: 'calendar_days', label: 'Proporcional aos dias de serviço' }, { value: 'equal_months', label: 'Meses iguais, com rateio por dias' }] },
    { key: 'reason', label: 'Justificativa ou referência do acordo', type: 'textarea', required: true, wide: true },
  ],
  columns: [{ key: 'instructor_name', label: 'Instrutor' }, { key: 'modality_name', label: 'Modalidade' },
    { key: 'effective_from', label: 'Início', render: row => date(row.effective_from) },
    { key: 'effective_until', label: 'Fim', render: row => date(row.effective_until) },
    { key: 'percentage', label: 'Percentual', render: row => `${String(row.percentage)}%` },
    { key: 'voided_at', label: 'Situação', render: row => row.voided_at ? 'Invalidado' : 'Vigente conforme datas' }],
};

export function PayoutAgreementDetail() {
  const { id } = useParams();
  const query = useApi<RecordData>(`payout-agreements/${id}/`);
  const [voiding, setVoiding] = useState(false);
  return <><RecordDetail spec={payoutAgreementSpec} />
    {query.data && (query.data.voided_at ? <Notice tone="warning">Acordo invalidado. Motivo: {String(query.data.void_reason)}</Notice> : <Button variant="secondary" onClick={() => setVoiding(true)}>Invalidar acordo</Button>)}
    {voiding && <ActionForm title="Invalidar acordo de repasse" endpoint={`payout-agreements/${id}/void/`} description="Use para corrigir um acordo registrado incorretamente. O histórico será preservado."
      fields={[{ key: 'reason', label: 'Motivo', type: 'textarea', required: true, wide: true }]} onClose={() => setVoiding(false)} />}
  </>;
}
