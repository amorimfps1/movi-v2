# Plano de implementação das DN-001 a DN-022

Base: `docs/MOVIV2_Decisoes_de_Negocio_DN001_DN022.md` (consolidação de 11/11/2026).

## Princípios de execução

- Preservar regras já confirmadas e snapshots de contratos/transações existentes.
- Implementar propostas com status explícito de **proposta implementada**; não confundir com aprovação ou homologação institucional.
- Enquanto não houver aprovação institucional registrada, manter desabilitadas as operações ou parâmetros que o próprio documento condiciona a aprovação.
- Parametrização comercial usual será persistida, versionada, auditada e administrável no site; preço/regra hardcoded deixa de ser fonte de verdade.
- Mudanças financeiras e acadêmicas sensíveis são transacionais, idempotentes quando aplicável e registram autor, data, motivo e antes/depois.

## Fases e dependências

### 0. Base comum e rastreabilidade

- Atualizar `docs/decisions.md` para refletir o documento consolidado, registrando por DN: regra anterior confirmada, proposta, estado de aprovação, implementação e aceite.
- Definir versionamento/configuração efetiva e serviço comum de auditoria para publicações de políticas e exceções.
- Criar trilha de migração compatível com dados legados; nenhuma alteração retroativa automática.

### 1. Acesso, contas e identidade — DN-001 a DN-003

- Separar permissões de Secretaria e Coordenação no backend e interface; limitar aprovação/rejeição/reabertura, funções e desativação à Coordenação.
- Adicionar motivo obrigatório para rejeição, reabertura e mudanças críticas; suportar múltiplas funções, sem autoalteração.
- Implementar desativação/revogação de sessão preservando histórico.
- Tornar CPF opcional, normalizado e único quando informado; manter e-mail de pessoa não exclusivo.
- Conversão de lead detecta correspondências CPF/e-mail; bloquear conflitos/múltiplos resultados e exigir resolução manual auditada.

### 2. Catálogo e configuração comercial no site — DN-004 a DN-007, base de DN-009/011

- Persistir versões de planos, preços por modalidade/categoria/ano/associação/meio, parcelamento, vencimentos, taxas, descontos/bolsas e política de inadimplência.
- Criar interface de Administração > Configurações Financeiras para Coordenação, com rascunho, validação, simulação de impacto e publicação com vigência.
- Migrar regras/preços de `backend/billing/contracts.py` e `backend/ecowork/catalog.py` para dados versionados; preservar catálogo e snapshots históricos.
- Implementar planos personalizados e configuração de elegibilidade, incluindo obrigação dispensada por bolsa integral sem pagamento fictício.
- Limites e exceções de descontos ficam configuráveis; fluxo de solicitação/aprovação separado.
- Manter configurações propostas inativas até aprovação institucional registrada.

### 3. Ciclo financeiro e contratos — DN-005 a DN-011

- Geração de obrigações transacional e idempotente, corrigindo ausências apenas por ação autorizada e auditada.
- Suportar pagamentos parciais/múltiplos, saldo derivado, impedir excedente inicialmente e preservar recebimentos imutáveis; criar estorno/ajuste explícito.
- Aplicar inadimplência com os defaults conservadores documentados (sem carência, multa ou juros automáticos); deixar parâmetros opcionais configuráveis e inativos.
- Criar suspensão/trancamento com autorização da Coordenação, período, motivo e efeito explícito, sem retroatividade automática.
- Implementar cancelamento por data efetiva; não calcular reembolso automaticamente.
- Renovação explícita ligada ao contrato anterior, sequencial por padrão, sem taxa e sem apagar dívida anterior.

### 4. Turmas, experimentais e aulas — DN-012 a DN-015

- Validar capacidade, conflito de instrutor/sala/horário e especialidade na criação/matrícula; exceção de lotação somente por Coordenação com justificativa.
- Criar lista de espera com ordenação estável e promoção auditada quando surgir vaga.
- Implementar experimental separado da matrícula, limite de uma por pessoa/modalidade, sem cobrança quando permitido, duração da aula regular e registro de autorização de responsável quando aplicável.
- Aplicar regras de chamada confirmadas e corrigir interfaces/mensagens conforme a política documentada.
- Modelar reposição como nova aula vinculada à original; cancelamento excluído da frequência, sem reescrever chamada concluída.

### 5. Repasses e indicadores — DN-016 a DN-019

- Modelar acordos de repasse versionados por contrato/instrutor/modalidade/período, atribuição de aula e base elegível; fechamento mensal, aprovação e reabertura auditada.
- Exibir caixa e competência em indicadores separados; reconciliar recebido, contratado, previsto, saldo, atraso, descontos, taxas e estornos.
- Calcular frequência em janelas de 30/90 dias e alertar três faltas consecutivas; excluir canceladas e separar experimentais.
- Calcular evasão com fórmula e período explícitos; separar encerramentos antecipados de conclusões normais.
- Separar conversão para pessoa de conversão para matrícula; ocupação usa matrículas regulares ativas/capacidade e apresenta experimentais/lista de espera em indicadores distintos.

### 6. Dados, histórico e operação — DN-020 a DN-022

- Aplicar acesso mínimo por função; preparar suporte a dados sensíveis com autorização e auditoria de leitura. Não criar campos médicos sem finalidade e aprovação definidas.
- Registrar preferências/finalidades de comunicação; preservar WhatsApp manual; sem disparo automático.
- Definir ferramentas e política de retenção por categoria antes de eliminar dados reais; respeitar obrigações legais aplicáveis.
- Preservar cobranças, pagamentos, contratos, frequência e auditoria ao arquivar/transferir; registrar vínculos e data de efeito sem recálculo histórico.
- Documentar arquitetura para 1 unidade, 5.000 pessoas, 50 usuários simultâneos; implementar métricas e ensaio de carga para p95 de 2s.
- Configurar backups compatíveis com RPO 4h/RTO 8h e executar restauração mensal documentada; backup diário isolado não atende ao RPO.

### 7. Aceite integrado

- Por DN, registrar separadamente: decisão aprovada, entrega técnica, testes automatizados, validação integrada por perfil e homologação institucional.
- Cobrir migrações não destrutivas, dados legados, concorrência, idempotência, auditoria, limites de acesso, valores em centavos, bloqueios e fluxos de exceção.
- Não declarar conclusão de operação sem exercício de backup/restauração e homologação dos fluxos institucionais.

## Ordem de execução

1. Fase 0 e DN-001–003 (fundação de acesso e identidade).
2. DN-004–007 (catálogo/configuração persistida e interface administrativa).
3. DN-008–011 (saldo, políticas financeiras, suspensão/cancelamento/renovação).
4. DN-012–015 (capacidade, experimental, chamada e reposição).
5. DN-016–019 (repasse e indicadores).
6. DN-020–022 (privacidade, retenção, escala e recuperação).
7. Aceite integrado e atualização dos documentos de progresso/decisões.

## Marco inicial identificado

O repositório já possui contas com funções JSON e proteção de acesso, CPF normalizado, contratos acadêmicos 2026, pagamentos integrais, chamada/correção sob política, base de modelos EcoWork e auditoria. Ainda há diferenças entre essas entregas e o documento novo: papéis administrativos atualmente agrupados, desativação/reabertura ausentes, configurações financeiras hardcoded, pagamentos parciais ausentes, funções de suspensão/transferência/reposição e relatórios de repasse ainda incompletos. Cada fase começa com inspeção dessas implementações existentes para estender sem duplicar domínio ou quebrar compatibilidade.
