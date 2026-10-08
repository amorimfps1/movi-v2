# MOVI+ Regras de negócio e engenharia de requisitos

**Versão:** 1.0  
**Data:** 7 de outubro de 2026  
**Finalidade:** especificar o produto para reconstrução em React, Django e PostgreSQL.

## 1 Objetivo e status da especificação

O MOVI+ é um sistema de gestão de atividades educacionais e comunitárias. Deve acompanhar interessados, alunos, matrículas, modalidades, turmas, instrutores, aulas, frequência e movimentações financeiras, oferecendo informações para secretaria, coordenação e comunicação.

Este documento define comportamentos de negócio e critérios de aceitação para a nova aplicação. A tecnologia escolhida é uma restrição do projeto; as regras são descritas sem depender da implementação anterior.

Os itens usam três classificações:

| Classificação | Significado |
|---|---|
| Base | Comportamento identificado no levantamento anterior e candidato à preservação. Ainda requer aceite do responsável pelo negócio. |
| Proposta | Comportamento recomendado para a nova aplicação, sujeito a aprovação de negócio. |
| A definir | Decisão institucional pendente. O documento não estabelece uma resposta por suposição. |

O levantamento anterior é a fonte desta reformulação. Este documento não representa uma nova inspeção do repositório nem uma homologação institucional. Itens propostos não devem ser tratados como regras já aprovadas.

## 2 Objetivos do produto

- Centralizar o cadastro e o acompanhamento dos participantes.
- Acompanhar o interessado desde o primeiro contato até sua conversão em aluno.
- Organizar a oferta de modalidades, turmas, horários e aulas.
- Relacionar matrículas, cobranças, pagamentos e autorização para participar das aulas.
- Permitir que instrutores registrem a frequência dos participantes sob sua responsabilidade.
- Produzir indicadores com conceitos consistentes e períodos identificados.
- Preservar o histórico acadêmico e financeiro necessário à operação.
- Restringir cada usuário às informações e ações autorizadas para sua função.

## 3 Escopo

### 3.1 Núcleo da primeira versão

Identidade e acesso; gestão de usuários; alunos; interessados e conversão; modalidades; instrutores; turmas e aulas; matrículas; cobranças e pagamentos; elegibilidade para aula; chamada; consultas e relatórios; indicadores; histórico de ações críticas.

A geração de cobranças integra o núcleo financeiro proposto. Seu comportamento depende da definição da política de cobrança, registrada na seção 13.

### 3.2 Funcionalidades condicionadas a decisões de negócio

- Repasse final aos instrutores e fechamento de repasses.
- Suspensão, trancamento, renovação, descontos e bolsas.
- Validação de capacidade e conflitos de agenda.
- Políticas de comunicação e tratamento de dados pessoais.

### 3.3 Evoluções fora do compromisso inicial

Portal de aluno ou responsável; vínculo familiar; pagamento por gateway; emissão de documentos fiscais; atendimento com protocolos; automação de mensagens; integração oficial com WhatsApp; assinatura eletrônica; múltiplas unidades ou organizações independentes.

Esses itens só entram na versão inicial mediante alteração expressa do escopo. Um link para contato por WhatsApp pode integrar o núcleo sem assumir envio automático de mensagens.

## 4 Atores e permissões

| Ator | Responsabilidade |
|---|---|
| Solicitante de acesso | Solicitar uma conta e acompanhar a situação de aprovação. |
| Secretaria | Executar cadastros e rotinas administrativas, acadêmicas e financeiras autorizadas. |
| Coordenação | Acompanhar a operação acadêmica, gerir atribuições e consultar indicadores autorizados. |
| Instrutor | Consultar suas turmas e aulas autorizadas e registrar chamadas. |
| Comunicação | Acompanhar interessados, contatos e indicadores de aquisição e conversão. |
| Aluno ou responsável | Participante do negócio; não pressupõe conta de acesso nesta versão. |

### 4.1 Matriz inicial para validação

**B** = acesso previsto na base; **P** = acesso proposto; **D** = detalhamento pendente; **—** = acesso não previsto inicialmente.

| Operação | Secretaria | Coordenação | Instrutor | Comunicação |
|---|---|---|---|---|
| Aprovar e revogar acesso | B | B | — | — |
| Gerir alunos e matrículas | B | B | — | — |
| Gerir modalidades, turmas e aulas | B | B | — | — |
| Gerir interessados | B | B | — | P |
| Converter interessado em aluno | B | B | — | D |
| Registrar cobranças e pagamentos | B | B | — | — |
| Consultar financeiro institucional | B | B | — | — |
| Consultar base de repasse própria | D | D | B | — |
| Consultar diário autorizado | B | B | B | — |
| Registrar chamada autorizada | B | B | B | — |
| Consultar indicadores de comunicação | B | B | — | B |
| Consultar dados médicos ou de responsáveis | D | D | D | — |

Secretaria e coordenação tinham poderes administrativos equivalentes no levantamento. Qualquer diferenciação na nova aplicação precisa ser aprovada. Não se pressupõe que uma função possa acessar todos os dados apenas por possuir um painel próprio.

## 5 Vocabulário do domínio

| Termo | Definição |
|---|---|
| Interessado ou lead | Pessoa acompanhada antes ou durante sua decisão de participar de uma atividade. |
| Aluno | Pessoa cadastrada para participação nas atividades. Ter cadastro não implica possuir matrícula ativa. |
| Modalidade | Atividade oferecida, com classificação e condições comerciais próprias. |
| Turma | Oferta concreta de uma modalidade, com agenda, local, instrutor e capacidade. |
| Aula | Ocorrência de uma turma em determinada data. |
| Matrícula | Vínculo do aluno com uma oferta e suas condições acadêmicas e comerciais. |
| Plano | Conjunto de condições de contratação. Duração e periodicidade de cobrança precisam ser definidas separadamente. |
| Competência | Período ao qual uma cobrança ou receita se refere. |
| Vencimento | Data limite para quitação de uma cobrança. |
| Cobrança | Obrigação de pagamento com valor, finalidade, competência e vencimento. |
| Pagamento | Registro de recebimento associado a uma obrigação ou categoria de receita. Não pressupõe integração bancária. |
| Quitação | Atendimento integral do valor exigido para liquidar uma cobrança. |
| Inadimplência | Existência de obrigação vencida que não atende ao critério de quitação. |
| Elegibilidade | Condição que autoriza a matrícula a participar de uma aula. |
| Chamada | Registro de frequência das matrículas elegíveis para uma aula. |
| Base de repasse | Receita considerada antes da aplicação de uma regra de remuneração do instrutor. |
| Repasse | Valor final devido ao instrutor após a aplicação da política aprovada. |

## 6 Regras de negócio

### 6.1 Identidade e acesso

| ID | Regra | Status |
|---|---|---|
| RN-001 | Uma solicitação de conta deve iniciar pendente de aprovação. | Base |
| RN-002 | Conta pendente ou rejeitada não pode acessar funcionalidades internas. | Base |
| RN-003 | A aprovação deve atribuir ao menos uma função autorizada e registrar o responsável e a data da decisão. | Base |
| RN-004 | A rejeição de uma solicitação deve exigir motivo e impedir o acesso interno. | Base |
| RN-005 | A remoção da última função deve suspender a autorização e devolver a conta à situação pendente. | Base |
| RN-006 | A atribuição administrativa de uma função deve colocar a conta na situação aprovada. | Base |
| RN-007 | Um administrador não pode alterar a própria autorização por meio das rotinas comuns de gestão de acesso. | Base |
| RN-008 | Alterações de função, aprovação e rejeição devem preservar ator, alvo, data, ação e motivo quando aplicável. | Base |
| RN-009 | Uma conta de instrutor deve possuir vínculo profissional inequívoco; vínculos ambíguos impedem a concessão desse acesso. | Base |
| RN-010 | O usuário somente pode executar ações e consultar dados permitidos por sua função e pelo vínculo com o registro. | Base |

A política de aprovação com substituição de funções ou acumulação de funções deve ser formalizada. Na base, aprovar substitui as funções anteriores; adicionar uma função é uma operação distinta.

### 6.2 Alunos e interessados

| ID | Regra | Status |
|---|---|---|
| RN-011 | O cadastro de aluno e o cadastro de interessado devem possuir nome. | Base |
| RN-012 | O CPF, quando informado, deve ser válido. Sua obrigatoriedade não está estabelecida. | Base |
| RN-013 | Não deve ser permitido cadastrar dois alunos com o mesmo CPF informado, considerando apenas seus dígitos. | Proposta |
| RN-014 | Na conversão, o sistema deve procurar um aluno existente por CPF ou e-mail antes de criar outro cadastro. | Base |
| RN-015 | Quando CPF e e-mail apontarem para alunos diferentes ou houver múltiplas correspondências, a conversão deve exigir resolução da identidade. | Proposta |
| RN-016 | A conversão deve concluir com aluno identificado, interessado marcado como convertido e vínculo preservado entre os dois registros. | Base quanto à conversão; vínculo é Proposta |
| RN-017 | Converter um interessado não cria automaticamente uma matrícula nem comprova pagamento ou participação. | Base |
| RN-018 | O contato comercial deve respeitar a política institucional aplicável ao canal, à finalidade e às preferências registradas. | Proposta; política A definir |
| RN-019 | Cadastros com histórico acadêmico ou financeiro devem ser encerrados ou arquivados sem apagar os registros relacionados. | Proposta |

O e-mail compartilhado por familiares não deve ser presumido como identificação única. A política de correspondência precisa definir prioridade, confirmação e resolução de conflitos.

### 6.3 Modalidades, instrutores, turmas e aulas

| ID | Regra | Status |
|---|---|---|
| RN-020 | Uma turma deve identificar sua modalidade; uma aula deve identificar sua turma e sua data. | Base |
| RN-021 | A especialidade atribuída ao instrutor deve corresponder a uma modalidade cadastrada. | Base |
| RN-022 | O instrutor pode consultar turmas sob sua responsabilidade e aulas para as quais recebeu atribuição específica. | Base |
| RN-023 | O instrutor não pode transferir uma aula para outro instrutor nem alterar sua turma por conta própria. | Base |
| RN-024 | Uma turma pode permitir ou impedir a participação de matrículas experimentais. | Base |
| RN-025 | Deve existir uma única aula por turma e data. Permitir duas sessões no mesmo dia exige revisão dessa regra. | Base |
| RN-026 | A matrícula acima da capacidade deve ser impedida ou exigir uma exceção autorizada, conforme política aprovada. | Proposta; exceções A definir |
| RN-027 | Agendas incompatíveis de sala ou instrutor devem impedir a confirmação da turma ou exigir exceção autorizada. | Proposta; política A definir |
| RN-028 | A compatibilidade entre especialidade do instrutor e modalidade da turma deve seguir a política institucional. | A definir |

### 6.4 Matrículas e planos

| ID | Regra | Status |
|---|---|---|
| RN-029 | Uma nova matrícula deve iniciar pendente de liberação. | Base |
| RN-030 | O cadastro da matrícula deve identificar aluno, oferta, início e condições comerciais aplicáveis. | Base |
| RN-031 | Na base, os planos mensal, trimestral e anual correspondem a durações de um, três e doze meses. A relação com cobrança deve ser confirmada. | Base; semântica A definir |
| RN-032 | O valor padrão da modalidade pode sugerir o valor da matrícula. Valores zero, bolsas e descontos devem seguir política própria. | Base quanto à sugestão; exceções A definir |
| RN-033 | Situações de liberação e bloqueio financeiro devem resultar das regras de cobrança e pagamento, sem edição manual comum. | Base |
| RN-034 | Cancelamento, suspensão, trancamento e demais situações administrativas não devem ser revertidos automaticamente por um pagamento. | Base |
| RN-035 | Alterações de condições comerciais devem preservar sua data de efeito e o histórico das condições anteriores. | Proposta |
| RN-036 | Os efeitos de suspensão e trancamento sobre vigência, cobrança e participação devem ser aprovados antes da implementação. Não se assume prorrogação fixa de trinta dias. | A definir |

### 6.5 Cobranças, pagamentos e inadimplência

| ID | Regra | Status |
|---|---|---|
| RN-037 | Uma cobrança de mensalidade deve identificar matrícula, aluno correspondente, competência, vencimento e valor devido. | Base; unicidade por competência é Proposta |
| RN-038 | Uma mensalidade somente pode ser considerada quitada integralmente quando possui data de pagamento, valor devido positivo e valor recebido suficiente. | Base |
| RN-039 | O pagamento apenas da taxa de matrícula não libera o aluno para participar das aulas. | Base |
| RN-040 | Na base, uma mensalidade integralmente paga e a ausência de mensalidades vencidas permitem a liberação financeira, respeitando a situação administrativa. | Base |
| RN-041 | Uma mensalidade não quitada fica vencida no dia seguinte ao vencimento, considerando a data de Brasília/São Paulo. Não há carência na base. | Base |
| RN-042 | Uma mensalidade vencida deve bloquear financeiramente a matrícula elegível à automação financeira. | Base |
| RN-043 | Após a quitação de todas as obrigações vencidas, a liberação deve ser reavaliada sem restaurar situações administrativas encerradas ou suspensas. | Base |
| RN-044 | A situação apresentada e a elegibilidade para aula devem considerar a data vigente, mesmo sem uma edição manual dos registros. | Base |
| RN-045 | As cobranças previstas no contrato devem ser geradas de forma confiável; repetir a geração não pode duplicar uma mesma obrigação. | Proposta |
| RN-046 | A inexistência de uma cobrança esperada não deve, por si só, comprovar adimplência. O tratamento dessa ausência precisa ser aprovado. | Proposta; efeito A definir |
| RN-047 | Uma baixa integral deve registrar o valor efetivamente recebido e a data, e satisfazer o critério de quitação. | Base quanto à quitação; confirmação do recebido é Proposta |
| RN-048 | Correções, cancelamentos e estornos de recebimentos devem preservar o histórico e provocar nova avaliação financeira da matrícula. | Proposta; políticas A definir |

A regra de liberação da base não define a cobertura temporal de uma mensalidade paga. Para a nova aplicação, a instituição precisa decidir se o pagamento deve cobrir a competência da aula, um pacote contratado ou outra condição. Um pagamento antigo não deve ser tratado automaticamente como cobertura eterna.

Pagamento parcial, valor devido zero, bolsa integral, pagamento excedente, crédito, multa, juros, rateio e alteração de vencimento são decisões pendentes. A ausência de decisão não autoriza implementar uma política financeira arbitrária.

### 6.6 Frequência e chamada

| ID | Regra | Status |
|---|---|---|
| RN-049 | Uma matrícula comum somente deve aparecer na chamada quando sua situação acadêmica e financeira permitir participação. | Base |
| RN-050 | Uma matrícula experimental pode aparecer na chamada quando a turma permitir essa participação. | Base |
| RN-051 | A chamada deve conter exatamente uma marcação para cada matrícula elegível. | Base |
| RN-052 | A mesma matrícula não pode possuir duas marcações ativas para a mesma turma e data. | Base |
| RN-053 | A autorização do instrutor e a elegibilidade dos participantes devem ser verificadas novamente ao confirmar a chamada. | Base |
| RN-054 | Se a lista elegível mudar durante o preenchimento, o sistema deve impedir confirmação silenciosa e solicitar atualização da lista. | Base |
| RN-055 | A conclusão da chamada e a indicação de aula realizada devem ocorrer juntas; uma falha não pode deixar apenas parte do resultado registrada. | Base |
| RN-056 | Correções de chamada devem identificar responsável, momento e justificativa conforme a política de reabertura. | Proposta; política A definir |

Chamadas retroativas, aulas canceladas, aulas sem participantes elegíveis e distinção entre falta justificada e não justificada precisam de decisões específicas. A data usada para avaliar a elegibilidade de uma chamada retroativa não está definida.

### 6.7 Financeiro e indicadores

| ID | Regra | Status |
|---|---|---|
| RN-057 | Receita recebida deve considerar os recebimentos reconhecidos no período, com separação entre mensalidades, taxas e outras categorias. | Base; regime temporal A definir |
| RN-058 | A base de repasse do instrutor deve considerar mensalidades quitadas elegíveis; taxas e extras ficam fora dessa base. | Base |
| RN-059 | Base de repasse e valor final de repasse são conceitos distintos. O valor final depende de política aprovada. | Base |
| RN-060 | Previsão, valor contratado, valor a receber e valor recebido devem ser apresentados como indicadores distintos. | Proposta |
| RN-061 | Um mesmo indicador deve ter a mesma definição em todos os relatórios, incluindo período, população e critérios de inclusão. | Proposta |
| RN-062 | Conversão em aluno deve ser medida pelo vínculo entre interessado e aluno; conversão em matrícula deve ser um indicador distinto. | Proposta |
| RN-063 | Metas de alunos, frequência e alertas de evasão devem ser parâmetros aprovados, com critérios e vigência identificados. | Proposta; valores A definir |

Não ficam estabelecidos neste documento meta de quinhentos alunos, frequência mínima de 75% ou 80%, nem alerta a partir de duas ou três faltas. Esses valores dependem de validação institucional.

## 7 Requisitos funcionais e critérios de aceite

**Essencial** = necessário ao núcleo operacional; **Complementar** = pode ser entregue após o núcleo; **Condicionado** = depende de decisão de negócio. A prioridade não elimina a necessidade de validar regras classificadas como Proposta.

### RF-001 Solicitar acesso

**Ator:** solicitante. **Prioridade:** Essencial. **Regras:** RN-001 e RN-002.

O sistema deve permitir solicitar uma conta e informar sua situação de aprovação.

**Aceite:** ao concluir um cadastro válido, a conta fica pendente; a tentativa de acesso interno é impedida; falhas de cadastro são apresentadas sem indicar aprovação inexistente.

### RF-002 Autenticar e encerrar sessão

**Ator:** usuário. **Prioridade:** Essencial. **Regras:** RN-002 e RN-010.

O sistema deve autenticar usuários e permitir encerrar a sessão.

**Aceite:** credenciais válidas de usuário aprovado liberam somente os recursos autorizados; conta pendente, rejeitada ou sem função não obtém acesso interno; após sair, ações protegidas exigem nova autenticação.

### RF-003 Aprovar ou rejeitar acesso

**Ator:** administrador autorizado. **Prioridade:** Essencial. **Regras:** RN-003, RN-004, RN-007 e RN-008.

O sistema deve listar solicitações e permitir decidir sobre elas.

**Aceite:** aprovar exige função válida; rejeitar exige motivo; a decisão registra o responsável e a data; uma falha mantém a solicitação e a autorização em condição consistente.

### RF-004 Gerenciar funções e vínculos profissionais

**Ator:** administrador autorizado. **Prioridade:** Essencial. **Regras:** RN-005 a RN-010.

O sistema deve permitir atribuir e remover funções e relacionar a conta do instrutor ao cadastro profissional.

**Aceite:** remover a última função impede o acesso; a alteração da própria autorização é recusada; atribuição de instrutor com vínculo ambíguo é recusada; alterações ficam registradas no histórico.

### RF-005 Gerenciar alunos

**Ator:** secretaria ou coordenação. **Prioridade:** Essencial. **Regras:** RN-011 a RN-013 e RN-019.

O sistema deve permitir cadastrar, consultar, editar e arquivar alunos, incluindo contatos e dados complementares autorizados.

**Aceite:** nome é obrigatório; CPF informado inválido é recusado; conforme aprovação da RN-013, CPFs equivalentes não geram dois alunos, inclusive com cadastros simultâneos; arquivamento preserva histórico.

### RF-006 Gerenciar interessados

**Ator:** equipe com permissão comercial. **Prioridade:** Essencial. **Regras:** RN-011 e RN-018.

O sistema deve registrar interessados, modalidades de interesse, canal de origem, situação e acompanhamento.

**Aceite:** nome é obrigatório; é possível filtrar por situação, origem e interesse; o cadastro não é contado como aluno ou matrícula antes da conversão correspondente.

### RF-007 Converter interessado em aluno

**Ator:** equipe autorizada. **Prioridade:** Essencial. **Regras:** RN-014 a RN-017.

O sistema deve identificar um aluno existente ou criar um novo, concluir a conversão e preservar o vínculo de origem.

**Aceite:** correspondência inequívoca reutiliza o aluno; conflito de identidade exige resolução; repetir a conversão não cria outro aluno; uma falha não deixa conversão concluída sem aluno identificado.

### RF-008 Gerenciar modalidades

**Ator:** secretaria ou coordenação. **Prioridade:** Essencial. **Regras:** RN-020, RN-021 e RN-032.

O sistema deve manter nome, área, situação e valor padrão de cada modalidade.

**Aceite:** a modalidade fica disponível para os vínculos permitidos; inativar preserva seu histórico; o valor padrão pode sugerir condições para uma nova matrícula sem alterar contratos anteriores.

### RF-009 Gerenciar instrutores

**Ator:** administrador autorizado. **Prioridade:** Essencial. **Regras:** RN-009 e RN-021 a RN-023.

O sistema deve manter cadastro profissional, contatos, situação e especialidades.

**Aceite:** especialidade deve referir-se a modalidade válida; a conta profissional possui vínculo inequívoco; o instrutor não consulta cadastros profissionais de terceiros sem autorização adicional.

### RF-010 Gerenciar turmas e agenda

**Ator:** secretaria ou coordenação. **Prioridade:** Essencial. **Regras:** RN-020, RN-024 e RN-026 a RN-028.

O sistema deve manter modalidade, instrutor, dias, horários, sala, faixa etária, capacidade, situação e permissão para experimental.

**Aceite:** vínculos e horários são válidos; conflitos e capacidade seguem a política aprovada; eventual exceção identifica responsável e justificativa. Enquanto a política não for aprovada, não se presume autorização de exceção.

### RF-011 Gerenciar aulas e substituições

**Ator:** secretaria ou coordenação; instrutor nas ações autorizadas. **Prioridade:** Essencial. **Regras:** RN-022, RN-023 e RN-025.

O sistema deve consultar e registrar aulas, cancelamentos, reposições e atribuições de substitutos.

**Aceite:** não existe duplicação de aula na mesma turma e data conforme a regra base; uma atribuição específica libera apenas a aula correspondente; o instrutor não altera sua própria atribuição.

### RF-012 Cadastrar matrícula

**Ator:** secretaria ou coordenação. **Prioridade:** Essencial. **Regras:** RN-029 a RN-032.

O sistema deve vincular aluno e oferta, registrar início, plano e condições comerciais.

**Aceite:** aluno e oferta são identificados; a matrícula inicia pendente de liberação; o valor sugerido pode ser ajustado conforme permissão e política; o cadastro isolado não comprova pagamento.

### RF-013 Consultar e calcular vigência

**Ator:** equipe administrativa. **Prioridade:** Condicionado. **Regras:** RN-031 e RN-036.

O sistema deve apresentar a vigência conforme duração contratada e ajustes autorizados.

**Aceite:** plano e data inicial determinam o término segundo convenção aprovada; casos de fim de mês e ano bissexto possuem resultado definido; suspensão não acrescenta prazo arbitrário.

### RF-014 Alterar situação administrativa da matrícula

**Ator:** equipe autorizada. **Prioridade:** Essencial para cancelamento; demais transições Condicionadas. **Regras:** RN-033 a RN-036.

O sistema deve permitir transições administrativas válidas e registrar motivo e data de efeito.

**Aceite:** uma transição não permitida é recusada; pagamento não reativa matrícula cancelada ou suspensa; alteração retroativa e reativação seguem política expressa.

### RF-015 Gerar cobranças por competência

**Ator:** rotina automática ou operador autorizado. **Prioridade:** Essencial após validação da política. **Regras:** RN-037, RN-045 e RN-046.

O sistema deve gerar obrigações previstas no contrato para o período devido.

**Aceite:** repetir a execução não duplica a obrigação; cada cobrança identifica contrato e competência; períodos cancelados ou suspensos seguem a política definida; falhas e cobranças esperadas ausentes ficam visíveis para resolução.

### RF-016 Registrar cobranças avulsas

**Ator:** equipe financeira autorizada. **Prioridade:** Essencial. **Regras:** RN-037 e RN-039.

O sistema deve permitir lançar mensalidade, taxa de matrícula e outras categorias autorizadas.

**Aceite:** mensalidade identifica matrícula e aluno correspondente; taxa de matrícula não é confundida com mensalidade para liberação; categoria, valor e vencimento seguem sua política.

### RF-017 Registrar recebimento e baixa

**Ator:** equipe financeira autorizada. **Prioridade:** Essencial. **Regras:** RN-038 e RN-047.

O sistema deve registrar valor recebido, data, forma de pagamento e obrigação correspondente.

**Aceite:** mensalidade sem data ou com recebimento insuficiente não é declarada integralmente quitada; o valor registrado corresponde ao recebido confirmado; pagamentos parciais e excedentes seguem a política aprovada.

### RF-018 Corrigir ou estornar recebimento

**Ator:** equipe financeira com permissão específica. **Prioridade:** Condicionado. **Regras:** RN-048.

O sistema deve permitir corrigir um registro financeiro e, quando autorizado, registrar estorno.

**Aceite:** são preservados valor original, alteração, responsável e motivo; o valor líquido dos relatórios reflete a operação; a elegibilidade é recalculada; estorno não apaga silenciosamente o recebimento original.

### RF-019 Avaliar situação financeira e liberação

**Ator:** sistema; consulta pelas equipes autorizadas. **Prioridade:** Essencial. **Regras:** RN-033, RN-034 e RN-038 a RN-046.

O sistema deve apresentar situação financeira e resultado de elegibilidade com seu motivo.

**Aceite:** taxa isolada não libera; obrigação vencida bloqueia segundo a regra base; quitação reavalia o acesso; situação administrativa é preservada; ausência de cobrança esperada recebe tratamento aprovado e visível.

### RF-020 Consultar diário do instrutor

**Ator:** instrutor autorizado. **Prioridade:** Essencial. **Regras:** RN-010, RN-022, RN-049 e RN-050.

O sistema deve listar turmas, aulas e participantes necessários ao trabalho do instrutor.

**Aceite:** o instrutor vê apenas seu escopo; uma substituição libera a aula atribuída; dados pessoais adicionais só são mostrados quando autorizados para aquela finalidade.

### RF-021 Registrar chamada

**Ator:** instrutor ou equipe autorizada. **Prioridade:** Essencial. **Regras:** RN-049 a RN-055.

O sistema deve apresentar a lista elegível e receber uma marcação de frequência por matrícula.

**Aceite:** lista incompleta ou duplicada é recusada; a autorização e a lista são reavaliadas ao confirmar; mudanças relevantes exigem atualização; a chamada concluída registra a aula como realizada; falha não deixa conclusão parcial.

### RF-022 Corrigir chamada

**Ator:** usuário com permissão de correção. **Prioridade:** Condicionado. **Regras:** RN-056.

O sistema deve permitir corrigir uma chamada já concluída conforme prazo e autorização definidos.

**Aceite:** alteração identifica registro anterior, novo valor, responsável e justificativa; nenhuma duplicidade é criada; a correção repercute nos indicadores correspondentes.

### RF-023 Consultar indicadores gerais

**Ator:** secretaria ou coordenação. **Prioridade:** Complementar. **Regras:** RN-060 a RN-063.

O sistema deve consolidar alunos, matrículas, receita, inadimplência, ocupação e conversões autorizadas.

**Aceite:** cada indicador identifica definição e período; filtros equivalentes produzem valores compatíveis com os relatórios de origem; metas não aprovadas não aparecem como parâmetro institucional obrigatório.

### RF-024 Consultar financeiro

**Ator:** equipe com permissão financeira. **Prioridade:** Essencial para extratos e inadimplência; gráficos Complementares. **Regras:** RN-057, RN-060 e RN-061.

O sistema deve apresentar obrigações, recebimentos, vencidos, categorias e períodos.

**Aceite:** recebido e previsto são separados; totais permitem consultar registros que os compõem; categorias e períodos equivalentes produzem totais consistentes; estornos e correções seguem a definição aprovada.

### RF-025 Consultar base de repasse

**Ator:** financeiro; instrutor para a própria base quando autorizado. **Prioridade:** Complementar. **Regras:** RN-058 e RN-059.

O sistema deve apresentar mensalidades elegíveis à base de repasse, com período e atribuição identificados.

**Aceite:** taxas e extras ficam fora; o instrutor não vê a base de terceiros; a tela não apresenta a base como remuneração final; titular, substituto e período seguem critérios aprovados.

### RF-026 Calcular e fechar repasse

**Ator:** equipe autorizada. **Prioridade:** Condicionado. **Regras:** RN-059.

O sistema deve calcular o valor final segundo a política institucional e registrar a aprovação do fechamento.

**Aceite:** percentual ou fórmula, competência, descontos e substituições são conhecidos; é possível explicar o cálculo; um fechamento aprovado só é alterado por procedimento autorizado. Não implementar o cálculo final antes dessas definições.

### RF-027 Consultar frequência e alertas acadêmicos

**Ator:** coordenação; instrutor no escopo autorizado. **Prioridade:** Complementar. **Regras:** RN-061 e RN-063.

O sistema deve apresentar frequência por participante e turma e alertas conforme critérios aprovados.

**Aceite:** numerador, denominador, período e tratamento de aulas canceladas são identificados; percentual com denominador zero não é exibido como resultado válido; alerta de evasão usa o parâmetro aprovado.

### RF-028 Consultar indicadores comerciais

**Ator:** comunicação e gestão autorizada. **Prioridade:** Complementar. **Regras:** RN-061 e RN-062.

O sistema deve apresentar interessados por origem, interesse e situação e conversões separadas em aluno e matrícula.

**Aceite:** converter cadastro não implica matricular; o período e a população de cada taxa são identificados; o usuário pode verificar os registros que compõem o indicador dentro de suas permissões.

### RF-029 Pesquisar filtrar e exportar

**Ator:** usuário autorizado. **Prioridade:** Essencial para consultas; exportação Complementar. **Regras:** RN-010 e RN-061.

O sistema deve permitir pesquisa, filtros, ordenação e exportação das listagens autorizadas.

**Aceite:** a exportação declara se cobre a página ou todos os resultados filtrados; filtros e permissões são respeitados; nenhum campo restrito é incluído por meio da exportação.

### RF-030 Iniciar contato por WhatsApp

**Ator:** equipe autorizada. **Prioridade:** Complementar. **Regras:** RN-018.

O sistema deve permitir abrir o canal de contato com número e mensagem previamente conferidos.

**Aceite:** telefone inválido recebe orientação; a ação respeita a política aprovada; abrir o contato não é registrado automaticamente como mensagem enviada ou entregue.

### RF-031 Notificar pendências operacionais

**Ator:** usuário responsável. **Prioridade:** Complementar. **Regras:** RN-001, RN-045 e RN-046.

O sistema deve apresentar pendências de aprovação e de geração de cobranças; outras notificações dependem de definição.

**Aceite:** a notificação identifica a pendência e sua situação atual; concluir a pendência atualiza o aviso; usuários sem permissão não recebem detalhes restritos.

### RF-032 Consultar histórico de ações críticas

**Ator:** usuário com permissão específica. **Prioridade:** Essencial para acesso e financeiro; extensão Complementar. **Regras:** RN-008, RN-019, RN-035, RN-048 e RN-056.

O sistema deve permitir consultar alterações de autorização, situação administrativa, condições comerciais, recebimentos e chamadas.

**Aceite:** cada evento identifica responsável, momento, alvo e ação; motivo é preservado quando obrigatório; a consulta respeita as permissões; editar o registro operacional não apaga o evento histórico.

## 8 Casos de uso principais

### UC-001 Aprovar acesso

**Ator:** administrador. **Pré-condição:** solicitação existente e administrador autorizado.

1. Consultar a solicitação.
2. Identificar a função a atribuir.
3. Conferir o vínculo profissional quando se tratar de instrutor.
4. Confirmar a decisão.
5. Atualizar autorização e situação e registrar o histórico.

**Alternativas:** função inválida; vínculo ambíguo; tentativa de alterar a própria autorização; solicitação já decidida por outro responsável.

**Pós-condição:** a decisão e a autorização estão consistentes. Nenhuma decisão é confirmada parcialmente.

### UC-002 Converter interessado

**Ator:** equipe comercial autorizada. **Pré-condição:** interessado cadastrado.

1. Selecionar o interessado.
2. Identificar correspondências de CPF e e-mail.
3. Confirmar o aluno existente ou preencher o cadastro de novo aluno.
4. Resolver qualquer conflito de identidade.
5. Confirmar a conversão.
6. Preservar o vínculo entre interessado e aluno.

**Alternativas:** correspondências contraditórias; dados inválidos; conversão já concluída; falha ao registrar o resultado.

**Pós-condição:** interessado convertido com aluno identificado. A matrícula permanece um caso de uso separado.

### UC-003 Matricular e liberar participação

**Ator:** secretaria ou coordenação. **Pré-condição:** aluno e oferta existentes.

1. Selecionar aluno e oferta.
2. Definir plano, início e condições comerciais.
3. Validar capacidade e condições de participação conforme política aprovada.
4. Criar matrícula pendente de liberação.
5. Gerar as cobranças previstas.
6. Registrar o recebimento confirmado.
7. Avaliar situação administrativa e financeira.
8. Apresentar a decisão de elegibilidade e seu motivo.

**Alternativas:** turma lotada; ausência de política aplicável; bolsa ou valor zero; obrigação vencida; pagamento insuficiente; geração incompleta.

**Pós-condição:** matrícula registrada, obrigações identificadas e participação liberada ou impedida segundo regra aprovada.

### UC-004 Gerar cobranças do período

**Ator:** rotina ou operador autorizado. **Pré-condição:** política de cobrança e contratos aplicáveis definidos.

1. Identificar o período de geração.
2. Selecionar contratos que possuem obrigação no período.
3. Aplicar condições com vigência naquele período.
4. Identificar obrigações já geradas.
5. Criar somente as obrigações ausentes.
6. Apresentar resultado, falhas e pendências.

**Alternativas:** contrato suspenso; mudança comercial; cancelamento; dados incompletos; execução repetida ou simultânea.

**Pós-condição:** cada obrigação prevista foi gerada uma única vez ou ficou identificada como pendência.

### UC-005 Regularizar inadimplência

**Ator:** equipe financeira. **Pré-condição:** matrícula com obrigação vencida.

1. Consultar os débitos da matrícula.
2. Confirmar os valores recebidos e as datas.
3. Registrar a baixa conforme a política.
4. Reavaliar obrigações vencidas e cobertura contratual.
5. Reavaliar participação respeitando a situação administrativa.

**Alternativas:** pagamento parcial; estorno; valor divergente; outra obrigação ainda vencida; matrícula cancelada ou suspensa.

**Pós-condição:** financeiro atualizado e elegibilidade coerente. Quitar dívida não implica reativação administrativa automática.

### UC-006 Registrar chamada

**Ator:** instrutor ou equipe autorizada. **Pré-condição:** turma, data e atribuição válidas.

1. Selecionar a aula.
2. Consultar matrículas elegíveis.
3. Marcar a frequência de cada participante.
4. Confirmar o preenchimento.
5. Revalidar autorização, lista e unicidade.
6. Registrar a chamada e concluir a aula em conjunto.

**Alternativas:** lista alterada; participante repetido; marcação ausente; atribuição revogada; chamada já registrada; situação de aula incompatível.

**Pós-condição:** chamada completa e aula realizada, ou nenhuma conclusão parcial.

## 9 Estados e transições

### 9.1 Conta de acesso

| Origem | Evento | Destino | Condição |
|---|---|---|---|
| Sem conta | Solicitação válida | Pendente | Conta criada |
| Pendente | Aprovação | Aprovada | Função válida atribuída |
| Pendente | Rejeição | Rejeitada | Motivo obrigatório |
| Aprovada | Remoção da última função | Pendente | Sem autorização restante |
| Pendente ou rejeitada | Atribuição administrativa de função | Aprovada | Operação autorizada |

Reabertura de solicitação rejeitada e desativação definitiva de conta exigem política própria.

### 9.2 Interessado

Situações identificadas: **novo**, **em atendimento**, **aguardando retorno**, **convertido** e **não convertido**.

Converter exige vínculo com aluno. Reabrir acompanhamento de um não convertido e desfazer conversão são decisões pendentes. Não se impõe uma sequência rígida entre os estados sem aprovação institucional.

### 9.3 Matrícula

Situações centrais identificadas: **pendente de liberação**, **ativa**, **bloqueada por inadimplência**, **experimental**, **suspensa**, **trancada** e **cancelada**. A lista final e os nomes devem ser aprovados.

| Origem | Evento | Resultado esperado | Status |
|---|---|---|---|
| Nova matrícula | Cadastro | Pendente de liberação | Base |
| Pendente | Quitação elegível e ausência de vencidos | Ativa, se não houver impedimento administrativo | Base; cobertura temporal pendente |
| Ativa | Obrigação torna-se vencida | Bloqueada por inadimplência | Base |
| Bloqueada | Regularização financeira | Ativa, se demais condições permitirem | Base |
| Ativa ou pendente | Suspensão, trancamento ou cancelamento autorizado | Situação administrativa solicitada | Política detalhada pendente |
| Suspensa, trancada ou cancelada | Pagamento | Preserva a situação administrativa | Base |

**Proposta de conceito:** apresentar situação administrativa, situação financeira e elegibilidade como informações distintas. Uma matrícula cancelada pode possuir dívida; uma matrícula suspensa pode estar financeiramente regular. O negócio deve conseguir consultar ambas sem perder significado.

### 9.4 Aula e cobrança

Aulas: **agendada**, **realizada**, **cancelada** e **reposição** são os conceitos identificados. Definir se reposição é situação ou tipo de aula, e quando uma chamada pode alterar a situação.

Cobranças: estados propostos de **em aberto**, **quitada** e **cancelada**. **Vencida** é uma condição derivada da data e da quitação. Pagamento parcial e estorno requerem política própria; este documento não fixa uma máquina de estados definitiva para eles.

## 10 Modelo conceitual de informações

O modelo abaixo descreve os conceitos e os vínculos necessários ao produto, sem prescrever tabelas, APIs ou bibliotecas.

| Entidade | Informações principais | Relações e observações |
|---|---|---|
| Usuário | Identidade, situação de acesso, funções | Pode representar um instrutor; não equivale automaticamente a aluno. |
| Decisão de acesso | Alvo, responsável, ação, motivo, data | Histórico das decisões administrativas. |
| Interessado | Nome, contato, origem, interesses, situação | Pode resultar em aluno; vínculo de conversão proposto. |
| Aluno | Identificação, contatos, dados complementares autorizados | Pode possuir várias matrículas; duplicidade de matrícula na mesma oferta A definir. |
| Modalidade | Nome, área, situação, valor padrão | Classifica turmas e especialidades. |
| Instrutor | Cadastro profissional, contatos, situação, especialidades | Relaciona-se a usuário, turmas e aulas atribuídas. |
| Turma | Modalidade, responsável, agenda, sala, capacidade, situação | Oferece aulas e recebe matrículas. |
| Aula | Turma, data, responsável atribuído, situação | Possui registros de frequência. |
| Matrícula | Aluno, oferta, início, vigência, plano, condições | Origina obrigações e participação acadêmica. |
| Condição comercial | Valor, desconto ou bolsa, início de efeito | Histórico proposto; regras comerciais pendentes. |
| Cobrança | Finalidade, competência, vencimento, valor, situação | Para mensalidade, deve corresponder à matrícula e ao aluno. |
| Recebimento | Valor, data, forma, responsável | Associado à cobrança; rateios e múltiplos recebimentos A definir. |
| Frequência | Aula, matrícula, marcação | Uma marcação ativa por participação. |
| Repasse | Período, base, regra, valor, aprovação | Condicionado à política de remuneração. |
| Preferência ou registro de comunicação | Finalidade, canal, decisão, data | Proposta; conteúdo e política de tratamento A definir. |
| Evento de histórico | Responsável, momento, ação, alvo, motivo | Preserva alterações críticas autorizadas. |

Vínculos adicionais com família, responsável, unidade ou organização dependem de expansão de escopo. A preservação do responsável de um menor não implica portal familiar na primeira versão.

## 11 Requisitos não funcionais

Todos os requisitos abaixo descrevem o resultado esperado para a nova aplicação. Os valores mensuráveis apresentados como proposta devem ser aprovados e usados na homologação.

| ID | Requisito | Critério de verificação |
|---|---|---|
| RNF-001 | Controle de acesso | Tentativas de consultar ou alterar registros fora da função ou do vínculo são recusadas, inclusive por acesso direto aos serviços da aplicação. |
| RNF-002 | Consistência das operações | Falhas em conversão, aprovação e chamada não deixam resultados parciais apresentados como concluídos. |
| RNF-003 | Controle de concorrência | Ações simultâneas não geram aluno com CPF duplicado, obrigação duplicada ou chamada duplicada conforme as regras aprovadas. |
| RNF-004 | Privacidade | Cada perfil recebe apenas os dados autorizados para sua finalidade, inclusive nas exportações. |
| RNF-005 | Preservação de histórico | Arquivamento e correções mantêm registros acadêmicos e financeiros necessários segundo a política de retenção aprovada. |
| RNF-006 | Tratamento de dados pessoais | Finalidades, categorias de dados, permissões e procedimentos de atendimento aos titulares devem ser definidos pela instituição antes da operação. |
| RNF-007 | Clareza operacional | Mensagens informam o resultado da ação e, em caso de impedimento, o motivo e o caminho de resolução. |
| RNF-008 | Usabilidade | Proposta de homologação: secretaria e instrutor conseguem concluir os fluxos principais com dados representativos, sem auxílio do desenvolvedor. |
| RNF-009 | Acessibilidade | Proposta: fluxos essenciais atendem WCAG 2.2 nível AA, com navegação por teclado, foco perceptível e identificação de erros. |
| RNF-010 | Compatibilidade | Proposta: fluxos principais funcionam nas versões estáveis homologadas de Chrome, Edge e Firefox e nos dispositivos móveis definidos pelo projeto. |
| RNF-011 | Desempenho | Proposta: 95% das consultas principais respondem em até dois segundos, em ambiente, volume e carga simultânea previamente definidos; exportações são avaliadas separadamente. |
| RNF-012 | Recuperação de falhas | Proposta: perda máxima tolerada de dados e prazo de recuperação são definidos pela instituição e verificados em exercício de restauração. Não há valor aprovado neste documento. |
| RNF-013 | Consistência temporal | Datas de vencimento e inadimplência usam America/Sao_Paulo; competência, data da aula e data de recebimento possuem significados distintos. |
| RNF-014 | Correção financeira | Cálculos preservam centavos e usam política aprovada de arredondamento; totais equivalentes conciliam entre relatórios. |
| RNF-015 | Homologação por perfil | Cada fluxo essencial possui cenário positivo e de impedimento validado pelo perfil responsável. |

Esses requisitos não constituem parecer jurídico nem confirmação de conformidade. As políticas institucionais de dados, retenção e comunicação precisam de responsáveis e aprovação próprios.

## 12 Cenários de aceitação do negócio

### CA-001 Conta pendente

**Dado** um usuário que solicitou acesso e ainda não foi aprovado, **quando** tentar acessar uma funcionalidade interna, **então** o acesso deve ser impedido e sua situação informada.

### CA-002 Revogação de acesso

**Dado** um usuário com apenas uma função, **quando** um administrador autorizado remover essa função, **então** sua autorização deve ser retirada e novas ações protegidas devem ser recusadas.

### CA-003 CPF repetido

**Dado** um aluno com CPF informado, **quando** outro cadastro informar o mesmo CPF com formatação diferente, **então**, após aprovação da RN-013, o novo cadastro deve ser recusado como duplicado.

### CA-004 Conversão com conflito de identidade

**Dado** um interessado cujo CPF corresponde a um aluno e e-mail corresponde a outro, **quando** sua conversão for solicitada, **então** o sistema deve exigir resolução da identidade antes de concluir.

### CA-005 Conversão sem matrícula

**Dado** um interessado convertido em aluno, **quando** os indicadores forem consultados, **então** a conversão em aluno pode ser contada, mas não uma matrícula que não foi criada.

### CA-006 Taxa sem mensalidade

**Dado** uma matrícula pendente com apenas a taxa de matrícula paga, **quando** sua participação for avaliada, **então** ela deve continuar sem liberação financeira para a aula.

### CA-007 Vencimento e mudança de data

**Dado** uma mensalidade em aberto com vencimento hoje, **quando** a data local passar para o dia seguinte, **então** ela deve ser considerada vencida e a participação deve seguir a regra de bloqueio, mesmo sem edição manual.

### CA-008 Quitação insuficiente

**Dado** uma mensalidade de R$ 100,00 com recebimento de R$ 60,00, **quando** for solicitada baixa integral, **então** a obrigação não deve ser apresentada como integralmente quitada. Seu tratamento posterior depende da política de pagamentos parciais.

### CA-009 Regularização de matrícula cancelada

**Dado** uma matrícula cancelada com dívida, **quando** a dívida for quitada, **então** o financeiro deve ser atualizado e o cancelamento preservado.

### CA-010 Geração repetida de cobrança

**Dado** uma obrigação já gerada para a competência e o contrato aplicáveis, **quando** a geração for repetida ou executada simultaneamente, **então** nenhuma obrigação duplicada deve ser criada.

### CA-011 Competência esperada ausente

**Dado** um contrato que prevê cobrança no período e cuja cobrança não foi gerada, **quando** sua elegibilidade for avaliada, **então** a ausência deve ser identificada e receber o tratamento aprovado, sem ser considerada automaticamente prova de adimplência.

### CA-012 Instrutor substituto

**Dado** um instrutor atribuído a uma aula específica de turma que não é sua, **quando** consultar o diário, **então** deve acessar os recursos necessários àquela aula, sem obter autorização irrestrita para outras turmas.

### CA-013 Experimental

**Dado** uma matrícula experimental, **quando** a turma permitir experimental, **então** a matrícula pode integrar a chamada segundo a regra aplicável; se a turma não permitir, sua participação deve ser impedida.

### CA-014 Mudança durante a chamada

**Dado** uma chamada aberta, **quando** a lista elegível mudar antes da confirmação, **então** o sistema deve solicitar atualização e impedir conclusão silenciosa com a lista antiga.

### CA-015 Falha ao concluir chamada

**Dado** uma chamada preenchida, **quando** ocorrer falha ao confirmar o conjunto de registros, **então** a aula não deve aparecer como realizada com frequência parcialmente gravada.

### CA-016 Separação da base de repasse

**Dado** mensalidade de R$ 100,00, taxa de R$ 20,00 e extra de R$ 10,00 reconhecidos conforme a política, **quando** a receita e a base de repasse forem consultadas para o mesmo escopo, **então** a receita pode totalizar R$ 130,00 e a base elegível de mensalidades R$ 100,00. Esse valor não representa o repasse final.

## 13 Decisões de negócio pendentes

| ID | Decisão necessária | Resultado que precisa ser aprovado |
|---|---|---|
| DN-001 | Secretaria e coordenação | Matriz final de permissões e quem pode conceder cada função. |
| DN-002 | Aprovação e múltiplas funções | Substituição ou acumulação de funções; reabertura de rejeição; desativação definitiva. |
| DN-003 | Identificação de alunos | CPF obrigatório ou opcional, exceções, correspondência por e-mail e tratamento de cadastros sem documento. |
| DN-004 | Plano e cobrança | Duração, periodicidade, valor por período, cobertura temporal e vencimento. Plano trimestral não implica por si só três cobranças mensais. |
| DN-005 | Geração de obrigações | Momento de geração, horizonte, proporcionalidade, primeiro vencimento, mudança de contrato e períodos sem obrigação. |
| DN-006 | Cobrança esperada ausente | Impedir participação, exigir resolução administrativa ou aplicar outra política expressa; definir responsável e prazo. |
| DN-007 | Bolsas e descontos | Quem concede, limites, vigência, valor zero e efeito sobre participação e repasse. |
| DN-008 | Pagamento parcial e excedente | Quitação, saldo, crédito, múltiplos recebimentos, rateio e efeito sobre elegibilidade. |
| DN-009 | Inadimplência | Confirmar ausência de carência; regras de multa, juros, renegociação, anistia e exceções de acesso. |
| DN-010 | Suspensão e trancamento | Quem autoriza; prazo; cobrança durante o período; ajuste de vigência; retorno; eventual retroatividade. |
| DN-011 | Cancelamento e renovação | Data de efeito, dívida remanescente, devolução, renovação e prevenção de matrícula duplicada na mesma oferta. |
| DN-012 | Capacidade e agenda | Bloqueio, lista de espera, exceções, conflito de sala ou instrutor e compatibilidade de especialidade. |
| DN-013 | Aula experimental | Duração, quantidade permitida, necessidade de cobrança e restrições por aluno ou modalidade. |
| DN-014 | Chamada | Marcação permitida, falta justificada, chamada retroativa, data de elegibilidade, prazo de correção e aula sem participantes. |
| DN-015 | Aulas e reposições | Uma ou várias sessões por turma e dia; reposição como tipo ou situação; efeitos de cancelamento. |
| DN-016 | Repasse | Percentual ou fórmula, titular e substituto, período, bolsas, estornos, descontos, aprovação e reabertura. |
| DN-017 | Indicadores financeiros | Regime de caixa ou competência, valores bruto e líquido, categorias, estornos e política de arredondamento. |
| DN-018 | Frequência e evasão | Fórmula, período, aulas incluídas, metas e limiar de alertas; definir consecutivas ou acumuladas. |
| DN-019 | Conversão e ocupação | Denominadores, coortes ou períodos, matrículas consideradas e experimental no cálculo de vagas. |
| DN-020 | Dados e comunicação | Finalidades, canais, preferências, menores, dados médicos, retenção, acesso e atendimento aos titulares. |
| DN-021 | Arquivamento e transferência | Efeito de arquivar aluno; mudar turma ou modalidade; preservar cobranças e frequência anteriores. |
| DN-022 | Escopo e capacidade operacional | Unidades atendidas, volume inicial, usuários simultâneos, disponibilidade e objetivos de recuperação. |

As decisões DN-004 a DN-011 são necessárias para fechar o comportamento financeiro. Elas devem ser respondidas antes da implementação definitiva da geração de cobranças e da liberação para aulas.

## 14 Rastreabilidade

| Domínio | Regras | Requisitos | Cenários | Decisões principais |
|---|---|---|---|---|
| Acesso | RN-001 a RN-010 | RF-001 a RF-004 e RF-032 | CA-001 e CA-002 | DN-001 e DN-002 |
| Alunos e interessados | RN-011 a RN-019 | RF-005 a RF-007 e RF-030 | CA-003 a CA-005 | DN-003, DN-019 a DN-021 |
| Oferta e agenda | RN-020 a RN-028 | RF-008 a RF-011 | CA-012 e CA-013 | DN-012, DN-013 e DN-015 |
| Matrículas | RN-029 a RN-036 | RF-012 a RF-014 | CA-006 e CA-009 | DN-004, DN-007, DN-010 e DN-011 |
| Financeiro e liberação | RN-037 a RN-048 | RF-015 a RF-019 e RF-024 | CA-006 a CA-011 | DN-004 a DN-011 e DN-017 |
| Frequência | RN-049 a RN-056 | RF-020 a RF-022 e RF-027 | CA-012 a CA-015 | DN-013 a DN-015 e DN-018 |
| Repasse e indicadores | RN-057 a RN-063 | RF-023 a RF-028 | CA-005 e CA-016 | DN-016 a DN-019 |
| Consultas e pendências | RN-010, RN-018, RN-045, RN-046 e RN-061 | RF-029 a RF-032 | Cenários dos domínios relacionados | DN-001, DN-006 e DN-020 |

Critérios detalhados devem ser associados a histórias de entrega sem perder seus vínculos com regras e decisões. Uma mudança de regra exige revisar os requisitos e os cenários afetados.

## 15 Ordem de definição e entrega

### Etapa 1 Validar o negócio

Aprovar o escopo inicial, a matriz de acesso, o significado dos planos, a política de cobrança, a elegibilidade para aula e as transições administrativas. Registrar responsável, decisão e data para os itens pendentes.

### Etapa 2 Entregar o núcleo cadastral

Contas, autorização, alunos, interessados, conversão, modalidades, instrutores, turmas e aulas. Aceitar os fluxos com representantes da secretaria, coordenação e comunicação.

### Etapa 3 Entregar o ciclo de matrícula e participação

Matrícula, obrigações por competência, recebimentos, inadimplência, elegibilidade, diário e chamada. Homologar o ciclo completo com cenários de quitação, atraso, ausência de cobrança, cancelamento e mudança durante a chamada.

### Etapa 4 Entregar consultas e acompanhamento

Relatórios financeiros e acadêmicos, pesquisa, exportação, indicadores, notificações e histórico de ações. Validar definições e conciliar totais com registros de origem.

### Etapa 5 Entregar funcionalidades condicionadas

Repasse final, políticas avançadas de bolsas e suspensão, automações de comunicação e demais evoluções aprovadas. Não definir percentuais, prazos ou direitos operacionais por conveniência da implementação.

## 16 Critério de conclusão da primeira versão

A primeira versão pode ser aceita quando:

- As regras do núcleo possuem aprovação identificada e as decisões financeiras essenciais foram respondidas.
- Cada perfil consegue concluir suas rotinas permitidas e é impedido de acessar operações e dados não autorizados.
- O ciclo matrícula, cobrança, recebimento, elegibilidade e chamada produz resultados coerentes, incluindo falhas e ações simultâneas.
- A geração repetida de cobranças e a confirmação repetida de chamadas não criam duplicidades.
- Arquivamentos, correções e encerramentos preservam o histórico aprovado pelo negócio.
- Relatórios financeiros e acadêmicos aplicam conceitos documentados e permitem conferir os registros de origem.
- Os cenários de aceitação do núcleo foram homologados por representantes das áreas responsáveis.
- Requisitos não funcionais e funcionalidades adiadas possuem aceite ou restrição de escopo documentados.

O objetivo da reconstrução é entregar uma operação coerente e verificável, com regras institucionais explícitas e separação clara entre cadastro, contrato, obrigação financeira, recebimento e participação acadêmica.
