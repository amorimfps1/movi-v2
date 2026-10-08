# Rastreabilidade MOVI+

Fonte funcional: [especificação v1.0](../MOVI_Regras_de_Negocio_e_Requisitos.md), lida integralmente. Contratos técnicos: [CONTRACT.md](CONTRACT.md). Data: 07/10/2026.

**Base é referência do levantamento, não homologação institucional.** Nenhum estado técnico deste documento constitui aceite de negócio. As classificações originais são preservadas. Propostas ficam desativadas por padrão: `BUSINESS_APPROVALS = []`; ativação exige decisão expressa registrada em decisions.md e, quando necessário, política detalhada. Aprovar um ID não define fórmula, período, cobertura ou direitos por si só.

Estados: **implementado** = código entregue, testes ainda não demonstrados; **verificado** = teste indicado executado; **parcial** = parte entregue/em desenvolvimento ou verificação incompleta; **bloqueado** = implementação/aceite depende de decisão ou ambiente. A matriz não declara verificações inexistentes. Todo aceite institucional continua pendente. Linhas verificadas indicam o alcance técnico das evidências de servidor/API abaixo; cobertura visual completa e homologação por representantes não são presumidas.

## Regras de negócio

| ID | Regra original | Classificação | Estado técnico | Entrega | Dependências | Verificação necessária |
|---|---|---|---|---|---|---|
| RN-001 | Uma solicitação de conta deve iniciar pendente de aprovação. | Base | verificado | core — Acesso | DN-001, DN-002 | cadastro produz pending |
| RN-002 | Conta pendente ou rejeitada não pode acessar funcionalidades internas. | Base | verificado | core — Acesso | DN-001, DN-002 | pending/rejected/sem função: 403 |
| RN-003 | A aprovação deve atribuir ao menos uma função autorizada e registrar o responsável e a data da decisão. | Base | verificado | core — Acesso | DN-001, DN-002 | aprovar sem função recusa; evento auditado |
| RN-004 | A rejeição de uma solicitação deve exigir motivo e impedir o acesso interno. | Base | verificado | core — Acesso | DN-001, DN-002 | motivo obrigatório e 403 após rejeição |
| RN-005 | A remoção da última função deve suspender a autorização e devolver a conta à situação pendente. | Base | verificado | core — Acesso | DN-001, DN-002 | remover última função revoga sessão ativa |
| RN-006 | A atribuição administrativa de uma função deve colocar a conta na situação aprovada. | Base | verificado | core — Acesso | DN-001, DN-002 | adicionar função muda autorização |
| RN-007 | Um administrador não pode alterar a própria autorização por meio das rotinas comuns de gestão de acesso. | Base | verificado | core — Acesso | DN-001, DN-002 | autoalteração recusada |
| RN-008 | Alterações de função, aprovação e rejeição devem preservar ator, alvo, data, ação e motivo quando aplicável. | Base | verificado | core — Acesso | DN-001, DN-002 | ator/alvo/momento/motivo imutáveis |
| RN-009 | Uma conta de instrutor deve possuir vínculo profissional inequívoco; vínculos ambíguos impedem a concessão desse acesso. | Base | verificado | core — Acesso | DN-001, DN-002 | vínculo OneToOne e conflito recusado |
| RN-010 | O usuário somente pode executar ações e consultar dados permitidos por sua função e pelo vínculo com o registro. | Base | verificado | core — Acesso | DN-001, DN-002 | testes por perfil e acesso direto por ID |
| RN-011 | O cadastro de aluno e o cadastro de interessado devem possuir nome. | Base | verificado | core — Alunos/interessados | DN-003, DN-019, DN-020, DN-021 | nome vazio recusado |
| RN-012 | O CPF, quando informado, deve ser válido. Sua obrigatoriedade não está estabelecida. | Base | verificado | core — Alunos/interessados | DN-003, DN-019, DN-020, DN-021 | CPF inválido recusado; normalização de dígitos |
| RN-013 | Não deve ser permitido cadastrar dois alunos com o mesmo CPF informado, considerando apenas seus dígitos. | Proposta | bloqueado | core — Alunos/interessados | DN-003, DN-019, DN-020, DN-021 | unicidade proposta desativada no default; cenário com aprovação testa CPF concorrente |
| RN-014 | Na conversão, o sistema deve procurar um aluno existente por CPF ou e-mail antes de criar outro cadastro. | Base | parcial | core — Alunos/interessados | DN-003, DN-019, DN-020, DN-021 | CPF/email inequívoco reutiliza aluno |
| RN-015 | Quando CPF e e-mail apontarem para alunos diferentes ou houver múltiplas correspondências, a conversão deve exigir resolução da identidade. | Proposta | bloqueado | core — Alunos/interessados | DN-003, DN-019, DN-020, DN-021 | conflito CPF/email interrompe conversão |
| RN-016 | A conversão deve concluir com aluno identificado, interessado marcado como convertido e vínculo preservado entre os dois registros. | Base quanto à conversão; vínculo é Proposta | parcial | core — Alunos/interessados | DN-003, DN-019, DN-020, DN-021 | conversão atômica/idempotente, vínculo sujeito RN-016 |
| RN-017 | Converter um interessado não cria automaticamente uma matrícula nem comprova pagamento ou participação. | Base | parcial | core — Alunos/interessados | DN-003, DN-019, DN-020, DN-021 | conversão deixa zero matrícula criada |
| RN-018 | O contato comercial deve respeitar a política institucional aplicável ao canal, à finalidade e às preferências registradas. | Proposta; política A definir | bloqueado | core — Alunos/interessados | DN-003, DN-019, DN-020, DN-021 | sem envio automático; política pendente |
| RN-019 | Cadastros com histórico acadêmico ou financeiro devem ser encerrados ou arquivados sem apagar os registros relacionados. | Proposta | bloqueado | core — Alunos/interessados | DN-003, DN-019, DN-020, DN-021 | sem DELETE físico; histórico permanece |
| RN-020 | Uma turma deve identificar sua modalidade; uma aula deve identificar sua turma e sua data. | Base | verificado | core + academic — Oferta/agenda | DN-012, DN-013, DN-015 | FK e data obrigatórias |
| RN-021 | A especialidade atribuída ao instrutor deve corresponder a uma modalidade cadastrada. | Base | implementado | core + academic — Oferta/agenda | DN-012, DN-013, DN-015 | especialidade FK modalidade válida |
| RN-022 | O instrutor pode consultar turmas sob sua responsabilidade e aulas para as quais recebeu atribuição específica. | Base | verificado | core + academic — Oferta/agenda | DN-012, DN-013, DN-015 | titular e substituto: acesso por aula |
| RN-023 | O instrutor não pode transferir uma aula para outro instrutor nem alterar sua turma por conta própria. | Base | verificado | core + academic — Oferta/agenda | DN-012, DN-013, DN-015 | instrutor PATCH/criação atribuição recusados |
| RN-024 | Uma turma pode permitir ou impedir a participação de matrículas experimentais. | Base | parcial | core + academic — Oferta/agenda | DN-012, DN-013, DN-015 | flag turma preservada; elegibilidade trial depende DN-013 |
| RN-025 | Deve existir uma única aula por turma e data. Permitir duas sessões no mesmo dia exige revisão dessa regra. | Base | verificado | core + academic — Oferta/agenda | DN-012, DN-013, DN-015 | UniqueConstraint turma/data e erro API |
| RN-026 | A matrícula acima da capacidade deve ser impedida ou exigir uma exceção autorizada, conforme política aprovada. | Proposta; exceções A definir | bloqueado | core + academic — Oferta/agenda | DN-012, DN-013, DN-015 | bloqueada até DN-012 |
| RN-027 | Agendas incompatíveis de sala ou instrutor devem impedir a confirmação da turma ou exigir exceção autorizada. | Proposta; política A definir | bloqueado | core + academic — Oferta/agenda | DN-012, DN-013, DN-015 | bloqueada até DN-012 |
| RN-028 | A compatibilidade entre especialidade do instrutor e modalidade da turma deve seguir a política institucional. | A definir | bloqueado | core + academic — Oferta/agenda | DN-012, DN-013, DN-015 | bloqueada até DN-012 |
| RN-029 | Uma nova matrícula deve iniciar pendente de liberação. | Base | verificado | billing — Matrículas | DN-004, DN-007, DN-010, DN-011 | nova matrícula sem liberação |
| RN-030 | O cadastro da matrícula deve identificar aluno, oferta, início e condições comerciais aplicáveis. | Base | verificado | billing — Matrículas | DN-004, DN-007, DN-010, DN-011 | FK/início/plano/valor validados |
| RN-031 | Na base, os planos mensal, trimestral e anual correspondem a durações de um, três e doze meses. A relação com cobrança deve ser confirmada. | Base; semântica A definir | bloqueado | billing — Matrículas | DN-004, DN-007, DN-010, DN-011 | não gerar cobertura/duração presumida |
| RN-032 | O valor padrão da modalidade pode sugerir o valor da matrícula. Valores zero, bolsas e descontos devem seguir política própria. | Base quanto à sugestão; exceções A definir | bloqueado | billing — Matrículas | DN-004, DN-007, DN-010, DN-011 | sugestão não altera matrícula anterior |
| RN-033 | Situações de liberação e bloqueio financeiro devem resultar das regras de cobrança e pagamento, sem edição manual comum. | Base | verificado | billing — Matrículas | DN-004, DN-007, DN-010, DN-011 | estado financeiro derivado, readonly |
| RN-034 | Cancelamento, suspensão, trancamento e demais situações administrativas não devem ser revertidos automaticamente por um pagamento. | Base | verificado | billing — Matrículas | DN-004, DN-007, DN-010, DN-011 | recebimento preserva cancelled |
| RN-035 | Alterações de condições comerciais devem preservar sua data de efeito e o histórico das condições anteriores. | Proposta | bloqueado | billing — Matrículas | DN-004, DN-007, DN-010, DN-011 | alteração comercial bloqueada até histórico/política |
| RN-036 | Os efeitos de suspensão e trancamento sobre vigência, cobrança e participação devem ser aprovados antes da implementação. Não se assume prorrogação fixa de trinta dias. | A definir | bloqueado | billing — Matrículas | DN-004, DN-007, DN-010, DN-011 | sem extensão arbitrária de prazo |
| RN-037 | Uma cobrança de mensalidade deve identificar matrícula, aluno correspondente, competência, vencimento e valor devido. | Base; unicidade por competência é Proposta | parcial | billing — Financeiro/elegibilidade | DN-004 a DN-011, DN-017 | mensalidade identifica matrícula/competência/vencimento/valor |
| RN-038 | Uma mensalidade somente pode ser considerada quitada integralmente quando possui data de pagamento, valor devido positivo e valor recebido suficiente. | Base | verificado | billing — Financeiro/elegibilidade | DN-004 a DN-011, DN-017 | sem data/insuficiente/zero não quita |
| RN-039 | O pagamento apenas da taxa de matrícula não libera o aluno para participar das aulas. | Base | verificado | billing — Financeiro/elegibilidade | DN-004 a DN-011, DN-017 | taxa paga isolada não libera |
| RN-040 | Na base, uma mensalidade integralmente paga e a ausência de mensalidades vencidas permitem a liberação financeira, respeitando a situação administrativa. | Base | parcial | billing — Financeiro/elegibilidade | DN-004 a DN-011, DN-017 | paga antiga gera decisão, nunca cobertura eterna |
| RN-041 | Uma mensalidade não quitada fica vencida no dia seguinte ao vencimento, considerando a data de Brasília/São Paulo. Não há carência na base. | Base | verificado | billing — Financeiro/elegibilidade | DN-004 a DN-011, DN-017 | due_date hoje não vence; amanhã local vence |
| RN-042 | Uma mensalidade vencida deve bloquear financeiramente a matrícula elegível à automação financeira. | Base | verificado | billing — Financeiro/elegibilidade | DN-004 a DN-011, DN-017 | vencida bloqueia |
| RN-043 | Após a quitação de todas as obrigações vencidas, a liberação deve ser reavaliada sem restaurar situações administrativas encerradas ou suspensas. | Base | parcial | billing — Financeiro/elegibilidade | DN-004 a DN-011, DN-017 | regularização reavalia, não reativa administrativo |
| RN-044 | A situação apresentada e a elegibilidade para aula devem considerar a data vigente, mesmo sem uma edição manual dos registros. | Base | verificado | billing — Financeiro/elegibilidade | DN-004 a DN-011, DN-017 | clock/date muda cálculo sem editar banco |
| RN-045 | As cobranças previstas no contrato devem ser geradas de forma confiável; repetir a geração não pode duplicar uma mesma obrigação. | Proposta | bloqueado | billing — Financeiro/elegibilidade | DN-004 a DN-011, DN-017 | geração default 409 sem side effects; cenário idempotente após aprovação |
| RN-046 | A inexistência de uma cobrança esperada não deve, por si só, comprovar adimplência. O tratamento dessa ausência precisa ser aprovado. | Proposta; efeito A definir | bloqueado | billing — Financeiro/elegibilidade | DN-004 a DN-011, DN-017 | ausência retorna decision_required/eligible null |
| RN-047 | Uma baixa integral deve registrar o valor efetivamente recebido e a data, e satisfazer o critério de quitação. | Base quanto à quitação; confirmação do recebido é Proposta | parcial | billing — Financeiro/elegibilidade | DN-004 a DN-011, DN-017 | recebimento integral exato, auditado |
| RN-048 | Correções, cancelamentos e estornos de recebimentos devem preservar o histórico e provocar nova avaliação financeira da matrícula. | Proposta; políticas A definir | bloqueado | billing — Financeiro/elegibilidade | DN-004 a DN-011, DN-017 | estorno/correção bloqueados sem DN-008 |
| RN-049 | Uma matrícula comum somente deve aparecer na chamada quando sua situação acadêmica e financeira permitir participação. | Base | parcial | academic — Chamada | DN-013, DN-014, DN-015, DN-018 | elegibilidade true somente; null explícito em excluded |
| RN-050 | Uma matrícula experimental pode aparecer na chamada quando a turma permitir essa participação. | Base | parcial | academic — Chamada | DN-013, DN-014, DN-015, DN-018 | trial default 409 DN-013 |
| RN-051 | A chamada deve conter exatamente uma marcação para cada matrícula elegível. | Base | parcial | academic — Chamada | DN-013, DN-014, DN-015, DN-018 | conjunto exato, incompleto/duplicado/extra recusados |
| RN-052 | A mesma matrícula não pode possuir duas marcações ativas para a mesma turma e data. | Base | parcial | academic — Chamada | DN-013, DN-014, DN-015, DN-018 | constraint aula/matrícula e confirmação repetida recusa |
| RN-053 | A autorização do instrutor e a elegibilidade dos participantes devem ser verificadas novamente ao confirmar a chamada. | Base | parcial | academic — Chamada | DN-013, DN-014, DN-015, DN-018 | revogar/reatribuir entre roster e POST recusa |
| RN-054 | Se a lista elegível mudar durante o preenchimento, o sistema deve impedir confirmação silenciosa e solicitar atualização da lista. | Base | parcial | academic — Chamada | DN-013, DN-014, DN-015, DN-018 | version muda para matrícula/financeiro/atribuição alterados |
| RN-055 | A conclusão da chamada e a indicação de aula realizada devem ocorrer juntas; uma falha não pode deixar apenas parte do resultado registrada. | Base | parcial | academic — Chamada | DN-013, DN-014, DN-015, DN-018 | falha injetada faz rollback presença/status/audit |
| RN-056 | Correções de chamada devem identificar responsável, momento e justificativa conforme a política de reabertura. | Proposta; política A definir | bloqueado | academic — Chamada | DN-013, DN-014, DN-015, DN-018 | reabrir/corrigir indisponível sem DN-014 |
| RN-057 | Receita recebida deve considerar os recebimentos reconhecidos no período, com separação entre mensalidades, taxas e outras categorias. | Base; regime temporal A definir | bloqueado | billing + frontend — Indicadores/repasse | DN-016 a DN-019 | recebido por paid_on e categorias, definição explícita |
| RN-058 | A base de repasse do instrutor deve considerar mensalidades quitadas elegíveis; taxas e extras ficam fora dessa base. | Base | bloqueado | billing + frontend — Indicadores/repasse | DN-016 a DN-019 | taxa/extra nunca base; cálculo pendente DN-016/017 |
| RN-059 | Base de repasse e valor final de repasse são conceitos distintos. O valor final depende de política aprovada. | Base | parcial | billing + frontend — Indicadores/repasse | DN-016 a DN-019 | base e repasse final separados/null enquanto pendente |
| RN-060 | Previsão, valor contratado, valor a receber e valor recebido devem ser apresentados como indicadores distintos. | Proposta | bloqueado | billing + frontend — Indicadores/repasse | DN-016 a DN-019 | não misturar recebido/esperado/outstanding |
| RN-061 | Um mesmo indicador deve ter a mesma definição em todos os relatórios, incluindo período, população e critérios de inclusão. | Proposta | bloqueado | billing + frontend — Indicadores/repasse | DN-016 a DN-019 | mesmos filtros/totais conciliam com origem |
| RN-062 | Conversão em aluno deve ser medida pelo vínculo entre interessado e aluno; conversão em matrícula deve ser um indicador distinto. | Proposta | bloqueado | billing + frontend — Indicadores/repasse | DN-016 a DN-019 | conversão aluno/matrícula separadas |
| RN-063 | Metas de alunos, frequência e alertas de evasão devem ser parâmetros aprovados, com critérios e vigência identificados. | Proposta; valores A definir | bloqueado | billing + frontend — Indicadores/repasse | DN-016 a DN-019 | sem meta/frequência/evasão arbitrárias |

## Requisitos funcionais

| ID | Nome / prioridade | Regras vinculadas | Estado técnico | Dependências | Critério de aceite a verificar |
|---|---|---|---|---|---|
| RF-001 | Solicitar acesso — Essencial | RN-001 e RN-002 | verificado | DN-001/DN-002 | ao concluir um cadastro válido, a conta fica pendente; a tentativa de acesso interno é impedida; falhas de cadastro são apresentadas sem indicar aprovação inexistente. |
| RF-002 | Autenticar e encerrar sessão — Essencial | RN-002 e RN-010 | verificado | DN-001 | credenciais válidas de usuário aprovado liberam somente os recursos autorizados; conta pendente, rejeitada ou sem função não obtém acesso interno; após sair, ações protegidas exigem nova autenticação. |
| RF-003 | Aprovar ou rejeitar acesso — Essencial | RN-003, RN-004, RN-007 e RN-008 | verificado | DN-001/DN-002 | aprovar exige função válida; rejeitar exige motivo; a decisão registra o responsável e a data; uma falha mantém a solicitação e a autorização em condição consistente. |
| RF-004 | Gerenciar funções e vínculos profissionais — Essencial | RN-005 a RN-010 | verificado | DN-001/DN-002 | remover a última função impede o acesso; a alteração da própria autorização é recusada; atribuição de instrutor com vínculo ambíguo é recusada; alterações ficam registradas no histórico. |
| RF-005 | Gerenciar alunos — Essencial | RN-011 a RN-013 e RN-019 | parcial | DN-003/DN-020/DN-021; RN-013 | nome é obrigatório; CPF informado inválido é recusado; conforme aprovação da RN-013, CPFs equivalentes não geram dois alunos, inclusive com cadastros simultâneos; arquivamento preserva histórico. |
| RF-006 | Gerenciar interessados — Essencial | RN-011 e RN-018 | implementado | DN-020; comunicação CRUD proposto | nome é obrigatório; é possível filtrar por situação, origem e interesse; o cadastro não é contado como aluno ou matrícula antes da conversão correspondente. |
| RF-007 | Converter interessado em aluno — Essencial | RN-014 a RN-017 | parcial | DN-003; RN-015/RN-016 | correspondência inequívoca reutiliza o aluno; conflito de identidade exige resolução; repetir a conversão não cria outro aluno; uma falha não deixa conversão concluída sem aluno identificado. |
| RF-008 | Gerenciar modalidades — Essencial | RN-020, RN-021 e RN-032 | implementado | DN-007 | a modalidade fica disponível para os vínculos permitidos; inativar preserva seu histórico; o valor padrão pode sugerir condições para uma nova matrícula sem alterar contratos anteriores. |
| RF-009 | Gerenciar instrutores — Essencial | RN-009 e RN-021 a RN-023 | parcial | DN-001/DN-012 | especialidade deve referir-se a modalidade válida; a conta profissional possui vínculo inequívoco; o instrutor não consulta cadastros profissionais de terceiros sem autorização adicional. |
| RF-010 | Gerenciar turmas e agenda — Essencial | RN-020, RN-024 e RN-026 a RN-028 | parcial | DN-012/DN-013 | vínculos e horários são válidos; conflitos e capacidade seguem a política aprovada; eventual exceção identifica responsável e justificativa. Enquanto a política não for aprovada, não se presume autorização de exceção. |
| RF-011 | Gerenciar aulas e substituições — Essencial | RN-022, RN-023 e RN-025 | parcial | DN-015 | não existe duplicação de aula na mesma turma e data conforme a regra base; uma atribuição específica libera apenas a aula correspondente; o instrutor não altera sua própria atribuição. |
| RF-012 | Cadastrar matrícula — Essencial | RN-029 a RN-032 | verificado | DN-004/DN-007/DN-012 | aluno e oferta são identificados; a matrícula inicia pendente de liberação; o valor sugerido pode ser ajustado conforme permissão e política; o cadastro isolado não comprova pagamento. |
| RF-013 | Consultar e calcular vigência — Condicionado | RN-031 e RN-036 | bloqueado | DN-004/DN-010 | plano e data inicial determinam o término segundo convenção aprovada; casos de fim de mês e ano bissexto possuem resultado definido; suspensão não acrescenta prazo arbitrário. |
| RF-014 | Alterar situação administrativa da matrícula — Essencial para cancelamento; demais transições Condicionadas | RN-033 a RN-036 | parcial | DN-010/DN-011 | uma transição não permitida é recusada; pagamento não reativa matrícula cancelada ou suspensa; alteração retroativa e reativação seguem política expressa. |
| RF-015 | Gerar cobranças por competência — Essencial após validação da política | RN-037, RN-045 e RN-046 | bloqueado | DN-004/DN-005/DN-006 | repetir a execução não duplica a obrigação; cada cobrança identifica contrato e competência; períodos cancelados ou suspensos seguem a política definida; falhas e cobranças esperadas ausentes ficam visíveis para resolução. |
| RF-016 | Registrar cobranças avulsas — Essencial | RN-037 e RN-039 | verificado | DN-004/DN-007 | mensalidade identifica matrícula e aluno correspondente; taxa de matrícula não é confundida com mensalidade para liberação; categoria, valor e vencimento seguem sua política. |
| RF-017 | Registrar recebimento e baixa — Essencial | RN-038 e RN-047 | parcial | DN-008 | mensalidade sem data ou com recebimento insuficiente não é declarada integralmente quitada; o valor registrado corresponde ao recebido confirmado; pagamentos parciais e excedentes seguem a política aprovada. |
| RF-018 | Corrigir ou estornar recebimento — Condicionado | RN-048 | bloqueado | DN-008/DN-017 | são preservados valor original, alteração, responsável e motivo; o valor líquido dos relatórios reflete a operação; a elegibilidade é recalculada; estorno não apaga silenciosamente o recebimento original. |
| RF-019 | Avaliar situação financeira e liberação — Essencial | RN-033, RN-034 e RN-038 a RN-046 | parcial | DN-004/DN-006/DN-009/DN-011 | taxa isolada não libera; obrigação vencida bloqueia segundo a regra base; quitação reavalia o acesso; situação administrativa é preservada; ausência de cobrança esperada recebe tratamento aprovado e visível. |
| RF-020 | Consultar diário do instrutor — Essencial | RN-010, RN-022, RN-049 e RN-050 | parcial | DN-013/DN-014/DN-020 | o instrutor vê apenas seu escopo; uma substituição libera a aula atribuída; dados pessoais adicionais só são mostrados quando autorizados para aquela finalidade. |
| RF-021 | Registrar chamada — Essencial | RN-049 a RN-055 | parcial | DN-014 + elegibilidade billing | lista incompleta ou duplicada é recusada; a autorização e a lista são reavaliadas ao confirmar; mudanças relevantes exigem atualização; a chamada concluída registra a aula como realizada; falha não deixa conclusão parcial. |
| RF-022 | Corrigir chamada — Condicionado | RN-056 | bloqueado | DN-014 | alteração identifica registro anterior, novo valor, responsável e justificativa; nenhuma duplicidade é criada; a correção repercute nos indicadores correspondentes. |
| RF-023 | Consultar indicadores gerais — Complementar | RN-060 a RN-063 | parcial | DN-017/DN-018/DN-019 | cada indicador identifica definição e período; filtros equivalentes produzem valores compatíveis com os relatórios de origem; metas não aprovadas não aparecem como parâmetro institucional obrigatório. |
| RF-024 | Consultar financeiro — Essencial para extratos e inadimplência; gráficos Complementares | RN-057, RN-060 e RN-061 | parcial | DN-017 | recebido e previsto são separados; totais permitem consultar registros que os compõem; categorias e períodos equivalentes produzem totais consistentes; estornos e correções seguem a definição aprovada. |
| RF-025 | Consultar base de repasse — Complementar | RN-058 e RN-059 | bloqueado | DN-016/DN-017 | taxas e extras ficam fora; o instrutor não vê a base de terceiros; a tela não apresenta a base como remuneração final; titular, substituto e período seguem critérios aprovados. |
| RF-026 | Calcular e fechar repasse — Condicionado | RN-059 | bloqueado | DN-016 | percentual ou fórmula, competência, descontos e substituições são conhecidos; é possível explicar o cálculo; um fechamento aprovado só é alterado por procedimento autorizado. Não implementar o cálculo final antes dessas definições. |
| RF-027 | Consultar frequência e alertas acadêmicos — Complementar | RN-061 e RN-063 | bloqueado | DN-018 | numerador, denominador, período e tratamento de aulas canceladas são identificados; percentual com denominador zero não é exibido como resultado válido; alerta de evasão usa o parâmetro aprovado. |
| RF-028 | Consultar indicadores comerciais — Complementar | RN-061 e RN-062 | parcial | DN-019/DN-020 | converter cadastro não implica matricular; o período e a população de cada taxa são identificados; o usuário pode verificar os registros que compõem o indicador dentro de suas permissões. |
| RF-029 | Pesquisar filtrar e exportar — Essencial para consultas; exportação Complementar | RN-010 e RN-061 | verificado | DN-001/DN-020 | a exportação declara se cobre a página ou todos os resultados filtrados; filtros e permissões são respeitados; nenhum campo restrito é incluído por meio da exportação. |
| RF-030 | Iniciar contato por WhatsApp — Complementar | RN-018 | bloqueado | DN-020 | telefone inválido recebe orientação; a ação respeita a política aprovada; abrir o contato não é registrado automaticamente como mensagem enviada ou entregue. |
| RF-031 | Notificar pendências operacionais — Complementar | RN-001, RN-045 e RN-046 | parcial | DN-005/DN-006 | a notificação identifica a pendência e sua situação atual; concluir a pendência atualiza o aviso; usuários sem permissão não recebem detalhes restritos. |
| RF-032 | Consultar histórico de ações críticas — Essencial para acesso e financeiro; extensão Complementar | RN-008, RN-019, RN-035, RN-048 e RN-056 | parcial | DN-001/DN-020 | cada evento identifica responsável, momento, alvo e ação; motivo é preservado quando obrigatório; a consulta respeita as permissões; editar o registro operacional não apaga o evento histórico. |

## Requisitos não funcionais

| ID | Resultado | Estado técnico | Verificação / dependência |
|---|---|---|---|
| RNF-001 | Controle de acesso | verificado | Tentativas de consultar ou alterar registros fora da função ou do vínculo são recusadas, inclusive por acesso direto aos serviços da aplicação. |
| RNF-002 | Consistência das operações | verificado | Falhas em conversão, aprovação e chamada não deixam resultados parciais apresentados como concluídos. |
| RNF-003 | Controle de concorrência | parcial | Ações simultâneas não geram aluno com CPF duplicado, obrigação duplicada ou chamada duplicada conforme as regras aprovadas. |
| RNF-004 | Privacidade | verificado | Cada perfil recebe apenas os dados autorizados para sua finalidade, inclusive nas exportações. |
| RNF-005 | Preservação de histórico | parcial | Arquivamento e correções mantêm registros acadêmicos e financeiros necessários segundo a política de retenção aprovada. |
| RNF-006 | Tratamento de dados pessoais | bloqueado | Finalidades, categorias de dados, permissões e procedimentos de atendimento aos titulares devem ser definidos pela instituição antes da operação. |
| RNF-007 | Clareza operacional | parcial | Mensagens informam o resultado da ação e, em caso de impedimento, o motivo e o caminho de resolução. |
| RNF-008 | Usabilidade | parcial | Proposta de homologação: secretaria e instrutor conseguem concluir os fluxos principais com dados representativos, sem auxílio do desenvolvedor. |
| RNF-009 | Acessibilidade | parcial | Proposta: fluxos essenciais atendem WCAG 2.2 nível AA, com navegação por teclado, foco perceptível e identificação de erros. |
| RNF-010 | Compatibilidade | parcial | Proposta: fluxos principais funcionam nas versões estáveis homologadas de Chrome, Edge e Firefox e nos dispositivos móveis definidos pelo projeto. |
| RNF-011 | Desempenho | parcial | Proposta: 95% das consultas principais respondem em até dois segundos, em ambiente, volume e carga simultânea previamente definidos; exportações são avaliadas separadamente. |
| RNF-012 | Recuperação de falhas | bloqueado | Proposta: perda máxima tolerada de dados e prazo de recuperação são definidos pela instituição e verificados em exercício de restauração. Não há valor aprovado neste documento. |
| RNF-013 | Consistência temporal | verificado | Datas de vencimento e inadimplência usam America/Sao_Paulo; competência, data da aula e data de recebimento possuem significados distintos. |
| RNF-014 | Correção financeira | parcial | Cálculos preservam centavos e usam política aprovada de arredondamento; totais equivalentes conciliam entre relatórios. |
| RNF-015 | Homologação por perfil | parcial | Cada fluxo essencial possui cenário positivo e de impedimento validado pelo perfil responsável. |

## Casos de uso

| ID | Fluxo | Estado técnico | Dependências | Pós-condição / teste |
|---|---|---|---|---|
| UC-001 | Aprovar acesso | verificado | DN-001/DN-002; core approval tests | a decisão e a autorização estão consistentes. Nenhuma decisão é confirmada parcialmente. |
| UC-002 | Converter interessado | parcial | DN-003/RN-015/RN-016; core conversion tests | interessado convertido com aluno identificado. A matrícula permanece um caso de uso separado. |
| UC-003 | Matricular e liberar participação | parcial | DN-004 a DN-013; billing eligibility tests | matrícula registrada, obrigações identificadas e participação liberada ou impedida segundo regra aprovada. |
| UC-004 | Gerar cobranças do período | bloqueado | DN-004/DN-005/DN-006; geração permanece 409 | cada obrigação prevista foi gerada uma única vez ou ficou identificada como pendência. |
| UC-005 | Regularizar inadimplência | parcial | DN-008/DN-009/DN-011; billing receive tests | financeiro atualizado e elegibilidade coerente. Quitar dívida não implica reativação administrativa automática. |
| UC-006 | Registrar chamada | parcial | DN-014 + billing eligibility; academic attendance tests | chamada completa e aula realizada, ou nenhuma conclusão parcial. |

## Cenários de aceitação

| ID | Cenário | Estado técnico | Verificação reproduzível / dependência |
|---|---|---|---|
| CA-001 | Conta pendente | verificado | core tests: pending/rejected recusados |
| CA-002 | Revogação de acesso | verificado | core tests: última função removida recusa próxima request |
| CA-003 | CPF repetido | bloqueado | condicionado RN-013; normalização e concorrência PostgreSQL |
| CA-004 | Conversão com conflito de identidade | parcial | core conversion: CPF e email conflitantes |
| CA-005 | Conversão sem matrícula | parcial | conversion não cria enrollment; reports contam vínculos |
| CA-006 | Taxa sem mensalidade | verificado | billing eligibility: enrollment_fee paga não libera |
| CA-007 | Vencimento e mudança de data | verificado | billing eligibility com on em dois dias consecutivos locais |
| CA-008 | Quitação insuficiente | verificado | billing receive: 60 em 100 recusa integral sem pagamento |
| CA-009 | Regularização de matrícula cancelada | verificado | billing receive: cancelled permanece cancelled |
| CA-010 | Geração repetida de cobrança | bloqueado | geração bloqueada DN-004/DN-005; corrida somente após política |
| CA-011 | Competência esperada ausente | parcial | eligible null + DN-004/DN-006; sem promessa de adimplência |
| CA-012 | Instrutor substituto | verificado | academic: substituto acessa só aula; titular não confirma atribuída |
| CA-013 | Experimental | bloqueado | bloqueado DN-013; flag permite trial não define duração |
| CA-014 | Mudança durante a chamada | parcial | academic: token antigo ou conjunto alterado produz 409 |
| CA-015 | Falha ao concluir chamada | parcial | academic: falha injetada faz rollback Attendance + Lesson |
| CA-016 | Separação da base de repasse | bloqueado | bloqueado DN-016/DN-017; receita categorias não é repasse |

## Entregas, limites e atualização

- core: autenticação, acesso, cadastros, conversão, oferta e auditoria. billing: matrículas, recebimentos, elegibilidade central, relatórios. academic: aula, substituição, roster e motor transacional de chamada. frontend: jornadas e estados explícitos. Coordenador: configuração global, PostgreSQL, execução, documentação e integração.
- Preservação técnica usa PROTECT e ausência de DELETE físico; política institucional de retenção não foi aprovada (DN-020/DN-021).
- Dados médicos/responsáveis, fórmulas de frequência/evasão, reposição, retroativa, regras de trial, capacidade/exceção e repasse não são inventados.
- PostgreSQL é a persistência alvo. Um teste SQLite não comprova concorrência ou locks PostgreSQL. Homologação manual por perfil, recuperação, carga e WCAG exigem evidência própria.
- Atualizar cada linha para implementado/verificado somente após inspecionar a entrega e registrar o comando/resultados em seção de evidências. Aprovações institucionais ficam separadas em decisions.md.

## Evidências finais de backend — 07/10/2026
Resultados executados e comunicados pelo coordenador:

- Suíte Django em PostgreSQL 16.15: **87 testes, OK, 49,808s, sem skips, exit code 0**, com remoção do banco de testes concluída. Core: 29; billing: 22; academic: 36. Os sete testes concorrentes usam conexões separadas e PostgreSQL real.
- `manage.py check`: exit code 0, sem problemas.
- `manage.py makemigrations --check --dry-run`: sem alterações pendentes.
- `manage.py spectacular --validate --fail-on-warn`: exit code 0, sem erros ou avisos. O contrato textual foi revisado contra o código e sincronizado pelo coordenador.

| Regras / requisitos / cenários | Evidência executada | Resultado e limite |
|---|---|---|
| RN-001/RN-002/RN-010; RF-001/RF-002; CA-001 | core: register_pending_and_sensitive_access_fields_ignored; login_requires_csrf_and_pending_cannot_enter; session_login_rejection_and_logout; pending_rejected_and_roleless_accounts_blocked | Cadastro pendente, CSRF, autenticação, logout e impedimento de acesso interno |
| RN-003 a RN-009; RF-003/RF-004; UC-001; CA-002 | core: approval_add_remove_and_last_role_revocation; self_mutation_refused; rejection_requires_reason_and_invalidates_existing_session; instructor_requires_unambiguous_binding; access_audit_failure_rolls_back_authorization | Decisão autorizada e auditada, vínculo inequívoco, última função revogada e rollback |
| RN-011/RN-012; RF-005 | core: valid_optional_and_normalized_cpf | Nome vazio e CPF inválido recusados; CPF opcional, normalizado |
| RN-013/RN-019; CA-003 | core: duplicate_proposal_not_assumed_approved; approved_duplicate_rule_blocks_equivalent_cpfs; delete_absent_and_archiving_pending_approval; concurrent_cpf_creation_has_one_winner | Propostas desativadas no default. Unicidade e arquivamento exercitados somente sob override técnico; decisões continuam pendentes |
| RN-014 a RN-017; RF-007; UC-002; CA-004/CA-005 | core: conversion_waits_for_link_proposal; conversion_is_idempotent_does_not_enroll_and_preserves_history; unique_match_reuses_student; identity_conflict_requires_explicit_student_and_reason; shared_email_is_not_unique_identity; failed_audit_rolls_back_student_and_conversion; cannot_bypass_conversion_by_patching_status | Default bloqueia vínculo proposto RN-016. Motor sob fixture preserva identidade, idempotência, histórico e nenhuma matrícula automática |
| RN-022/RN-023; RF-009/RF-010; RNF-001 | core: instructor_only_sees_own_classes_and_cannot_reassign; valid_schedule_required; communication_cannot_manage_leads_or_students | Escopo e horários verificados; capacidade, conflitos e especialidade institucional seguem pendentes DN-012 |
| RN-029/RN-030/RN-033/RN-034; RF-012/RF-014 | billing: new_enrollment_pending; payment_preserves_cancelled_enrollment; cancel_requires_reason | Matrícula sem liberação, cancelamento exige motivo, recebimento preserva cancelamento. Vigência/suspensão/renovação seguem bloqueadas |
| RN-038 a RN-044; RF-017/RF-019; UC-005; CA-006 a CA-009 | billing: enrollment_fee_does_not_release; underpaid_not_settled_and_no_partial_write; excess_not_recorded_without_policy; local_date_rollover_changes_eligibility_without_write; paid_month_does_not_imply_eternal_coverage; payment_preserves_cancelled_enrollment | Centavos/baixa integral, vencimento local e preservação administrativa. Cobertura temporal permanece indeterminada DN-004/DN-006 |
| RN-037/RN-045/RN-046; RF-015/RF-016; UC-004; CA-010/CA-011 | billing: expected_absence_is_explicit_not_adimplente; generation_repeated_is_blocked_without_arbitrary_obligations; duplicate_manual_competence_under_proposed_uniqueness; simultaneous_proposed_competence_is_not_duplicated | Geração automática bloqueada, sem obrigações arbitrárias. Unicidade manual por competência testada com aprovação simulada RN-037; não equivale a gerador concluído |
| DN-013; RN-024/RN-050; CA-013 | billing: trial_id_alone_never_grants_unlimited_participation | Flag da turma não concede duração experimental ilimitada; aprovação por ID isolado não libera |
| RN-047; RNF-002/RNF-003 | billing: receipt_retry_cannot_duplicate; audit_failure_rolls_back_receipt; simultaneous_receipts_record_once | Uma baixa integral por cobrança, repetição recusada, rollback e concorrência reais |
| RN-057/RN-059; RF-023/RF-024; CA-016 | billing: reports_conciliate_receipts_categories_and_charge_totals; charge_status_filters_include_rows_without_payments | Receita de R$ 130,00 conciliada por categorias, esperado e saldo. Filtros incluem cobranças sem pagamentos. Base e repasse retornam null enquanto DN-016/DN-017 pendentes |
| RN-010; RF-028/RF-029; RNF-004 | core: search_filters_order_and_pagination; billing: report_filters_and_export_safe_csv; instructor_no_financial_access_even_direct; communication_summary_does_not_leak_finance; revoked_role_rechecked | Pesquisa/paginação/exportação filtradas; CSV protege fórmulas; perfis sem acesso financeiro não recebem dados restritos |
| RNF-003 | core: concurrent_cpf_creation_has_one_winner; concurrent_conversion_creates_one_student; concurrent_approval_cannot_silently_replace_decision; concurrent_partial_updates_preserve_distinct_fields; billing: simultaneous_receipts_record_once; simultaneous_proposed_competence_is_not_duplicated; academic: simultaneous_submissions_create_one_complete_set | Sete corridas PostgreSQL aprovadas. Overrides técnicos de propostas não alteram BUSINESS_APPROVALS operacional |

Os testes institucionais de políticas de cobrança/cobertura, aula experimental, chamada operacional, reabertura, frequência/evasão, repasse, retenção, capacidade/agenda e metas continuam bloqueados ou parciais. Requisitos de carga, recuperação, compatibilidade completa, WCAG e homologação por representantes não foram declarados aprovados.

## Evidências acadêmicas incluídas na suíte final

A suíte final PostgreSQL inclui **36 testes acadêmicos, sem skips**, cobrindo escrita transacional sob fixture técnica e leitura do histórico sob autorização atual.

| Requisito / cenário | Evidência em backend/academic/tests.py | Alcance técnico |
|---|---|---|
| RN-022/RN-023; CA-012; RF-011/RF-020 | substitution_grants_only_specific_lesson; instructor_cannot_transfer_or_create_lesson; assignment_is_revalidated_and_titular_cannot_confirm_substitution | Instrutor substituto só acessa aula atribuída; titular não confirma substituição; sem expansão de acesso à turma |
| RN-025 | lesson_unique_class_date_in_api_and_database | Duplicata recusada por API e UniqueConstraint |
| RN-010; RNF-001/RNF-004; CA-001/CA-002 | pending_rejected_and_revoked_users_have_no_access; communication_cannot_read_diary; instructor_receives_no_personal_or_financial_exclusion_details | Escopo acadêmico, revogação da conta e privacidade de excluídos |
| RN-049; CA-011 | unknown_eligibility_is_explicit_and_does_not_enter_roster; paid_tuition_does_not_become_eternal_coverage_in_roster; unresolved_financial_eligibility_blocks_even_technical_policy | Consumo real de billing: elegibilidade desconhecida fica explícita, não entra como participante nem permite confirmar |
| RN-051/RN-052; RF-021 | incomplete_duplicate_and_extra_marks_are_refused; mark_values_require_explicit_booleans; database_attendance_uniqueness; repeated_submission_and_edits_to_completed_lesson_are_refused | Motor sob fixtures técnicas; não habilita chamada operacional |
| RN-053/RN-054; CA-014 | new_enrollment_requires_roster_refresh; eligibility_change_requires_roster_refresh; revoked_role_is_revalidated; tampered_or_other_actor_roster_token_is_refused | Snapshot assinado, conjunto e autorização revalidados |
| RN-055; RNF-002; CA-015 | failure_after_insert_rolls_back_attendance_lesson_and_audit; exact_attendance_and_completion_are_recorded_together | Rollback real após insert, inclusive status/auditoria; fixtures técnicas |
| DN-014; RF-022 | default_attendance_is_blocked_even_empty_or_retroactive; approval_id_without_detailed_policy_does_not_unblock; cancelled_past_future_and_empty_lessons_remain_unavailable | Bloqueios operacionais explícitos. Fixtures não constituem aprovação |
| RNF-003 | simultaneous_submissions_create_one_complete_set | Executado com PostgreSQL na suíte final: duas confirmações simultâneas produzem um conjunto completo e recusa da segunda |

A política `TECHNICAL_POLICY` e o retorno `ELIGIBLE` simulado só existem nos testes do motor. O default continua sem nenhuma aprovação. `BUSINESS_APPROVALS` com DN-014 isolado não habilita a chamada; uma política detalhada ainda é obrigatória. Não há implementação de percentual de frequência, evasão, repasse, retroativa, reabertura ou duração experimental por suposição.

## Consulta das marcações persistidas

`GET /api/lessons/{id}/attendance/` consulta os registros originais de presença, com retorno `{lesson,status,marks:[{enrollment,student_name,present,created_at}],definition}`. A definição exibida é: “Marcações gravadas na conclusão; não recalculadas pela elegibilidade atual.” A leitura mantém o vínculo autorizado da aula e não expõe financeiro ou dados adicionais do autor. Aula agendada sem marcações retorna lista vazia. Consultar histórico não permite reabrir, corrigir ou recalcular chamada e não habilita gravação pendente DN-014.

A consulta readonly e seus seis testes integram a suíte final PostgreSQL de 87 testes; o schema GET/POST separado foi validado sem avisos ou erros.

| Requisitos | Novas verificações em academic/tests.py | Resultado |
|---|---|---|
| RF-020; RN-010/RN-022; RNF-004 | scheduled_lesson_has_empty_readonly_attendance_history; own_attendance_history_is_visible_without_financial_or_actor_data | Diário lê marcas gravadas; payload mínimo, sem exigir política nova para leitura |
| CA-012; RNF-001 | substitute_can_read_only_assigned_lesson_history; third_party_cannot_read_attendance_history; revoked_user_cannot_read_old_attendance_history | Substituto limitado à aula atribuída, terceiros e conta revogada impedidos |
| RF-020; RNF-005 | attendance_history_preserves_recorded_marks_after_financial_change | Cancelamento ou dívida posterior não altera presença registrada; evaluator financeiro não é chamado |

Essa consulta não implementa percentual de frequência, metas, evasão, correção ou reabertura. DN-014/DN-018 permanecem pendentes.

## Evidência representativa de navegador informada pelo coordenador

Em 07/10/2026, o coordenador percorreu no navegador o fluxo **login → painel → alunos → novo aluno → detalhe → matrícula de R$ 120,00 → recarga da página**. O aluno e a matrícula criados permaneceram após a recarga, conferindo o caminho frontend/API/persistência. A interface foi examinada em desktop e em viewport móvel de 390 × 844, com apresentação legível. Essa observação cobre o marco representativo; não equivale a homologação WCAG, teste em todos os navegadores ou aceite institucional por perfil.

As verificações finais do frontend aprovaram **18 testes**, `npm run typecheck` e `npm run build`. O [registro de verificação](verification.md) documenta também taxa sintética de R$ 20,00 persistida, CSV de 01–07/10 com quatro obrigações de R$ 320,00, diário bloqueado pelas decisões pendentes e restrições reais dos perfis Instrutor e Comunicação. **Recebimento e conversão não foram concluídos no navegador:** a revisão automática bloqueou os cliques finais, sem tentativa de contorno; suas evidências são de testes isolados de backend. O registro detalha o alcance visual e as limitações, sem presumir homologação institucional.

A conferência estática identificou exatamente 63 RN, 32 RF, 15 RNF, 6 UC, 16 CA e 22 DN, sem lacunas na matriz principal. Nenhum dos 22 DN foi homologado.
