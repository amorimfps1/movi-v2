# Decisões institucionais pendentes

Data: 07/10/2026. Fonte: especificação v1.0, seção 13. **Responsável institucional não informado; nenhuma decisão homologada.** Base é referência histórica candidata a aceite, não aprovação. Todas as decisões abaixo continuam pendentes.

`BUSINESS_APPROVALS` inicia vazio. O registro de uma aprovação deve conter ID, decisão detalhada, responsável, data, alcance, exceções e critérios de validação. A configuração só pode mudar por instrução expressa do usuário; ID isolado não substitui política detalhada. Overrides de teste não são aprovação e não devem ser usados como configuração operacional.

| ID | Decisão necessária | Resultado a aprovar | Estado | Impactos rastreáveis | Comportamento conservador atual | Responsável / data de decisão |
|---|---|---|---|---|---|---|
| DN-001 | Secretaria e coordenação | Matriz final de permissões e quem pode conceder cada função. | Pendente | RN-001 a RN-010; RF-001 a RF-004; RF-029/RF-032 | Base: secretaria e coordenação equivalentes; comunicação só indicadores Base. Nenhuma ampliação tácita. | Não definido / não decidida |
| DN-002 | Aprovação e múltiplas funções | Substituição ou acumulação de funções; reabertura de rejeição; desativação definitiva. | Pendente | RN-003 a RN-009; RF-003/RF-004 | Preservar referência Base: aprovar substitui funções, adicionar é distinto; sem desativação definitiva/reabertura inventada. | Não definido / não decidida |
| DN-003 | Identificação de alunos | CPF obrigatório ou opcional, exceções, correspondência por e-mail e tratamento de cadastros sem documento. | Pendente | RN-011 a RN-017; RF-005/RF-007; CA-003/CA-004 | CPF opcional válido; RN-013 unicidade proposta default desativada. Email familiar não vira identidade única. | Não definido / não decidida |
| DN-004 | Plano e cobrança | Duração, periodicidade, valor por período, cobertura temporal e vencimento. Plano trimestral não implica por si só três cobranças mensais. | Pendente | RN-029 a RN-046; RF-012/RF-013/RF-015/RF-019; UC-003/004 | Nenhuma cobertura eterna ou duração de cobrança presumida; eligible null quando cobertura indefinida. | Não definido / não decidida |
| DN-005 | Geração de obrigações | Momento de geração, horizonte, proporcionalidade, primeiro vencimento, mudança de contrato e períodos sem obrigação. | Pendente | RN-037/RN-045/RN-046; RF-015/RF-031; UC-004 | POST geração retorna 409 sem criar obrigação enquanto política incompleta. | Não definido / não decidida |
| DN-006 | Cobrança esperada ausente | Impedir participação, exigir resolução administrativa ou aplicar outra política expressa; definir responsável e prazo. | Pendente | RN-040/RN-044/RN-046; RF-019/RF-031; CA-011 | Expor decision_required/eligible null e decisões; ausência não prova adimplência. | Não definido / não decidida |
| DN-007 | Bolsas e descontos | Quem concede, limites, vigência, valor zero e efeito sobre participação e repasse. | Pendente | RN-032/RN-035; RF-012/RF-015/RF-019 | Não conceder bolsa/desconto ou elegibilidade por valor zero. | Não definido / não decidida |
| DN-008 | Pagamento parcial e excedente | Quitação, saldo, crédito, múltiplos recebimentos, rateio e efeito sobre elegibilidade. | Pendente | RN-038/RN-047/RN-048; RF-017/RF-018; CA-008 | Baixa integral somente exata e positiva; insuficiente/excesso recusados; sem estorno/credito inventado. | Não definido / não decidida |
| DN-009 | Inadimplência | Confirmar ausência de carência; regras de multa, juros, renegociação, anistia e exceções de acesso. | Pendente | RN-041 a RN-044; RF-019; CA-007 | Regra Base vencimento: dia seguinte local, sem inventar carência/multa/juros. | Não definido / não decidida |
| DN-010 | Suspensão e trancamento | Quem autoriza; prazo; cobrança durante o período; ajuste de vigência; retorno; eventual retroatividade. | Pendente | RN-034/RN-036; RF-013/RF-014 | Sem suspensão/trancamento automático ou prorrogação de trinta dias. | Não definido / não decidida |
| DN-011 | Cancelamento e renovação | Data de efeito, dívida remanescente, devolução, renovação e prevenção de matrícula duplicada na mesma oferta. | Pendente | RN-034/RN-035; RF-014; CA-009; matrícula duplicada | Cancelamento presente auditado não elimina dívida; sem devolução/renovação automática. | Não definido / não decidida |
| DN-012 | Capacidade e agenda | Bloqueio, lista de espera, exceções, conflito de sala ou instrutor e compatibilidade de especialidade. | Pendente | RN-026/RN-027/RN-028; RF-010/RF-012 | Cadastro registra capacidade/agenda, sem regra proposta de bloqueio/exceção operante. | Não definido / não decidida |
| DN-013 | Aula experimental | Duração, quantidade permitida, necessidade de cobrança e restrições por aluno ou modalidade. | Pendente | RN-024/RN-050; RF-020/RF-021; CA-013 | Experimental indisponível por padrão; flag turma isolada não define direitos de trial. | Não definido / não decidida |
| DN-014 | Chamada | Marcação permitida, falta justificada, chamada retroativa, data de elegibilidade, prazo de correção e aula sem participantes. | Pendente | RN-049 a RN-056; RF-021/RF-022; UC-006; CA-014/015 | Chamada default indisponível (409), inclusive retroativa/vazia. Motor só exercitado sob override técnico; zero decisão homologada. | Não definido / não decidida |
| DN-015 | Aulas e reposições | Uma ou várias sessões por turma e dia; reposição como tipo ou situação; efeitos de cancelamento. | Pendente | RN-025; RF-011; aula cancelada/reposição | Uma aula por turma/data Base; sem reposição ou efeito temporal inventado. | Não definido / não decidida |
| DN-016 | Repasse | Percentual ou fórmula, titular e substituto, período, bolsas, estornos, descontos, aprovação e reabertura. | Pendente | RN-058/RN-059; RF-025/RF-026; CA-016 | Sem percentual, base atribuída ou cálculo de repasse final; indicadores retornam null/pendência. | Não definido / não decidida |
| DN-017 | Indicadores financeiros | Regime de caixa ou competência, valores bruto e líquido, categorias, estornos e política de arredondamento. | Pendente | RN-057 a RN-061; RF-023 a RF-026; RNF-014 | Consultas técnicas mostram definições de recebido por data e obrigação por vencimento, sem declarar regime institucional homologado. | Não definido / não decidida |
| DN-018 | Frequência e evasão | Fórmula, período, aulas incluídas, metas e limiar de alertas; definir consecutivas ou acumuladas. | Pendente | RN-061/RN-063; RF-027; RNF-015 | Sem meta fixa, mínimo 75/80%, alerta por duas/três faltas ou fórmula assumida. | Não definido / não decidida |
| DN-019 | Conversão e ocupação | Denominadores, coortes ou períodos, matrículas consideradas e experimental no cálculo de vagas. | Pendente | RN-060/RN-061/RN-062; RF-023/RF-028 | Contagens identificadas; sem taxa/coorte ou ocupação presumida. | Não definido / não decidida |
| DN-020 | Dados e comunicação | Finalidades, canais, preferências, menores, dados médicos, retenção, acesso e atendimento aos titulares. | Pendente | RN-018/RN-019; RF-005/RF-006/RF-020/RF-029/RF-030; RNF-004/005/006 | Sem dados médicos/responsáveis ou disparo de mensagem; sem afirmar conformidade legal/retencão. | Não definido / não decidida |
| DN-021 | Arquivamento e transferência | Efeito de arquivar aluno; mudar turma ou modalidade; preservar cobranças e frequência anteriores. | Pendente | RN-019/RN-035/RN-056; RF-005/RF-014/RF-022 | Preservação técnica do histórico; nenhuma transferência com efeitos retroativos presumidos. | Não definido / não decidida |
| DN-022 | Escopo e capacidade operacional | Unidades atendidas, volume inicial, usuários simultâneos, disponibilidade e objetivos de recuperação. | Pendente | RNF-010/RNF-011/RNF-012; capacidade operacional e escopo | Setup reproduzível entregue; carga/SLA/RPO/RTO dependem definição e exercício externo. | Não definido / não decidida |

## Perguntas objetivas para a instituição

1. DN-001/DN-002: confirmar secretaria e coordenação equivalentes? Quais funções cada uma pode conceder, e aprovar deve substituir as funções atuais?
2. DN-003: CPF continuará opcional? Aprova RN-013? Como resolver conversão quando CPF e email apontarem pessoas diferentes e quando email for compartilhado?
3. DN-004/DN-005/DN-006: qual período cada plano cobre, quando nasce a obrigação, qual vencimento/horizonte e qual decisão para uma cobrança esperada ausente?
4. DN-008/DN-009/DN-011: como tratar parcial/excesso, carência e cancelamento (data de efeito, dívida e devolução)?
5. DN-013/DN-014/DN-015: qual duração/limite de experimental, marcação permitida, data de elegibilidade, autorização de retroativa/correção e aula sem participantes?
6. DN-016/DN-017/DN-018/DN-019: quais fórmula, atribuição e período de repasse; regime financeiro; denominadores de frequência, conversão e ocupação?
7. DN-020/DN-021/DN-022: quais dados cada função pode consultar, retenção/transferência e objetivos de carga/recuperação?

## Decisões técnicas reversíveis

- JSON/DRF, IDs inteiros, decimal de centavos, paginação 25 e filtros explícitos conforme CONTRACT.md.
- SessionAuthentication + CSRF; valores reais são persistidos e dados demo só são habilitados explicitamente em desenvolvimento.
- Aulas e matrículas de chamada são protegidas por transação, constraints e locks em ordem documentada no domínio acadêmico. Token assinado de roster detecta alterações antes de confirmar.
- Status técnico de motor sob teste não concede direito operacional nem encerra DN-014. PostgreSQL e homologação por perfil continuam necessários para aceite final.

## Recorte técnico do motor de chamada

`academic.services` aceita uma política detalhada somente depois de decisão expressa DN-014. O recorte suportado exige exatamente `marking=presence_absence`, `eligibility_date=lesson_date`, `allow_past=false`, `allow_future=false` e `allow_empty=false`. Uma política diferente ou ausente devolve 409. Esse recorte é uma capacidade técnica exercitada via override nos testes, **não uma recomendação homologada ou configuração operacional aprovada**. Antes de operação, a instituição ainda precisa decidir marcação, data de elegibilidade, retroativa, correção e aulas vazias. O backend não fornece endpoint para habilitar decisões.

O snapshot é assinado e vinculado ao usuário, à aula, à atribuição e às matrículas/decisões de elegibilidade. A confirmação adquire locks na ordem `User -> ClassGroup (PK) -> Lesson -> Instructor (PK) -> Enrollment (PK) -> Charge (PK) -> Payment (PK)`. Criação e alterações financeiras devem adquirir o mesmo ClassGroup antes de Enrollment. Operações cadastrais de aluno usam adicionalmente o mutex de identidade e locks das turmas antes de Student, para serializar arquivamento que afeta a elegibilidade. O teste concorrente tem skip explícito fora do PostgreSQL.

## Evidência técnica sem homologação — 07/10/2026

A suíte final em PostgreSQL concluiu 87 testes em 49,808s, sem skips e com exit code 0, incluindo sete cenários concorrentes e criação/destruição completas do banco isolado. Foram 29 testes core, 22 billing e 36 academic, incluindo a consulta de marcações persistidas. Esse resultado verifica o código e os bloqueios descritos; **não aprova nenhuma RN proposta nem encerra qualquer DN**. BUSINESS_APPROVALS permanece vazio. O ciclo integral de matrícula/cobrança/cobertura/chamada continua dependendo das decisões institucionais; os testes positivos de conversão, unicidade proposta e motor de chamada usam overrides isolados. O detalhe das verificações consta de requirements.md.

## Consulta de chamada anterior

A leitura Base do diário inclui as marcações persistidas em `GET lessons/{id}/attendance/`, dentro do vínculo atual autorizado. Ela não depende de nova aprovação DN-014 porque não grava ou corrige frequência. O histórico não é recalculado pela elegibilidade financeira atual; não expõe dados financeiros ou informações adicionais do autor. Gravação, reabertura/correção e fórmulas acadêmicas continuam bloqueadas ou condicionadas. Essa separação preserva a observação original sem inventar uma regra de frequência ou retroatividade.
