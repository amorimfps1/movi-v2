import { useState } from 'react';
import { useParams } from 'react-router-dom';
import type { ResourceSpec } from './schema';
import type { RecordData } from './types';
import { useAuth } from './auth';
import { useApi } from './query';
import { RecordDetail } from './RecordDetail';
import { ActionForm } from './forms';
import { Button, Notice } from './ui';
import { date, label } from './format';

export const benefitSpec: ResourceSpec = {
  title: 'Bolsas e descontos', singular: 'benefício', slug: 'beneficios', endpoint: 'benefits/', editable: false,
  description: 'Solicite benefícios e acompanhe a decisão da Coordenação.',
  fields: [
    { key: 'scope', label: 'Área', type: 'select', required: true, default: 'academic', options: [{ value: 'academic', label: 'Acadêmico' }, { value: 'ecowork', label: 'EcoWork' }] },
    { key: 'person', label: 'Pessoa', type: 'select', lookup: 'people/', required: true },
    { key: 'modality', label: 'Modalidade acadêmica (opcional)', type: 'select', lookup: 'modalities/', nullable: true, hint: 'Deixe em branco para EcoWork.' },
    { key: 'starts_on', label: 'Início da vigência', type: 'date', required: true },
    { key: 'ends_on', label: 'Fim da vigência', type: 'date', required: true },
    { key: 'plan', label: 'Plano (opcional)', type: 'select', options: [], hint: 'Selecione a data inicial primeiro; deixe em branco para permitir qualquer plano.' },
    { key: 'kind', label: 'Tipo', type: 'select', required: true, options: [{ value: 'percent', label: 'Percentual' }, { value: 'fixed', label: 'Valor fixo' }] },
    { key: 'value', label: 'Valor ou percentual', type: 'decimal', required: true },
    { key: 'fee_waiver', label: 'Isentar taxa de matrícula', type: 'check', default: false },
    { key: 'reason', label: 'Justificativa da solicitação', type: 'textarea', required: true, wide: true },
  ],
  columns: [{ key: 'person_name', label: 'Pessoa' }, { key: 'status', label: 'Situação', render: row => label(row.status) },
    { key: 'starts_on', label: 'Início', render: row => date(row.starts_on) }, { key: 'ends_on', label: 'Fim', render: row => date(row.ends_on) },
    { key: 'value', label: 'Valor', render: row => `${String(row.value)}${row.kind === 'percent' ? '%' : ' reais'}` }],
};

export function BenefitDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const query = useApi<RecordData>(`benefits/${id}/`);
  const [decision, setDecision] = useState<'approve' | 'reject' | null>(null);
  return <><RecordDetail spec={benefitSpec} />
    {query.data?.status === 'pending' && user?.roles.includes('coordinator') && <div className="form-actions"><Button onClick={() => setDecision('approve')}>Aprovar benefício</Button><Button variant="secondary" onClick={() => setDecision('reject')}>Rejeitar benefício</Button></div>}
    {query.data?.status === 'approved' && <Notice tone="success">Benefício aprovado. {String(query.data.decision_reason || '')}</Notice>}
    {decision && <ActionForm title={decision === 'approve' ? 'Aprovar benefício' : 'Rejeitar benefício'} endpoint={`benefits/${id}/${decision}/`} fields={[
      { key: 'reason', label: 'Justificativa da decisão', type: 'textarea', required: true, wide: true },
      ...(decision === 'approve' ? [{ key: 'institutional_reference', label: 'Referência da autorização institucional', hint: 'Obrigatória acima do limite e em bolsa integral.' }] : []),
    ]} onClose={() => setDecision(null)} />}
  </>;
}
