# Plano de implementação — Cadastros compartilhados e EcoWork

Data: 04/11/2026. Status: fundação, contratação, parcelamento, recebimentos e interface inicial implementados. Migrations exercitadas em ambientes isolados; banco operacional preservado.

### Progresso da segunda entrega

Contratos/vendas avulsas, cobranças e quitação integral estão implementados, com preço/desconto preservados, idempotência, concorrência e auditoria. A tela EcoWork integra contratação, consulta de parcelas, saldo, vigência e confirmação de recebimento. Cadastros compartilhados, condomínios e residência possuem telas iniciais. Foram confirmados vencimentos mensais ajustados para meses curtos e aprovação da compra no cartão como início da vigência. Verificação: 127 testes PostgreSQL sem skips, 34 testes frontend, build e fluxo de navegador desktop/celular aprovados.

O plano não está integralmente concluído: migração definitiva de identidade, retificação/cancelamento financeiro, relatórios, catálogo versionado e renovação dedicada permanecem pendentes. Detalhes e limitações em [ecowork-implementacao.md](ecowork-implementacao.md). A seção de primeira entrega abaixo é histórica.

### Progresso da primeira entrega

- Implementados `/api/people/` sobre a mesma tabela e serviços de alunos, cadastro de condomínios, períodos de associação, validação/revogação de residência, catálogo inicial e consulta de preço/desconto.
- Estratégia transitória adotada: `Person` é um alias Python de `Student`, sem novo modelo/tabela. As duas rotas compartilham validações, locks, IDs e auditoria `core.student`. A migração lógica definitiva e a separação visual de alunos/frequentadores ainda não foram executadas.
- Migração `core.0003_ecowork_residence_foundation` adiciona apenas condomínios, períodos associativos e verificações de residência; não altera matrículas nem dados pessoais existentes.
- Períodos de associação usam início inclusivo e término exclusivo. Uma pessoa possui no máximo uma residência vigente; mudança exige encerramento justificado e novo registro, preservando o anterior.
- Catálogo inicial contém os preços confirmados e limites de parcelas. Ainda não é catálogo versionado de contratos. Consulta de preço é uma simulação sem gerar cobrança; contratação futura deverá revalidar elegibilidade em transação e preservar valores históricos.
- Permissões seguem o padrão administrativo atual (Secretaria/Coordenação); Instrutor/Comunicação não acessam os novos recursos. Não foram alteradas as políticas acadêmicas existentes.
- Próxima entrega: contratos e vendas, cobranças/parcelamento e quitação, seguida de interface e testes integrados. A regra de início na primeira parcela e preservação do desconto contratado está documentada, mas não há contratos implementados nesta fundação.

Verificações e limites desta entrega: [ecowork-implementacao.md](ecowork-implementacao.md).

Este plano considera `ecowork.md` e as decisões posteriores do solicitante na conversa. As decisões abaixo substituem o pagamento parcial e o foco exclusivo em mensalidades do documento inicial. A proposta antiga de reservas e estações não faz parte desta entrega.

## 1. Resultado esperado

A secretaria deverá localizar uma pessoa em um cadastro central, conferir sua residência validada, contratar um plano ou registrar um uso avulso do EcoWork, registrar o pagamento integral e consultar pendências e histórico.

Uma pessoa poderá ter matrículas acadêmicas e utilizar o EcoWork sem duplicar seus dados pessoais. Contas de acesso dos funcionários continuarão separadas dos cadastros de pessoas.

## 2. Regras confirmadas

| Produto | Preço normal | Preço com desconto de associado |
|---|---:|---:|
| Hora avulsa | R$ 5,00 | Sem desconto previsto |
| Meia diária — 4 horas | R$ 15,00 | Sem desconto previsto |
| Diária — 8 horas | R$ 25,00 | Sem desconto previsto |
| Plano mensal | R$ 169,00 | R$ 84,50 |
| Plano semestral | R$ 699,00 | R$ 349,50 |
| Plano anual | R$ 969,00 | R$ 484,50 |

- Não haverá pagamento parcial de cobranças.
- Planos semestral e anual podem ser pagos à vista ou parcelados. Parcelamento contratado não é pagamento parcial de uma cobrança.
- Parcelamento disponível tanto no cartão quanto por cobranças administradas pela secretaria: semestral em até 6 parcelas mensais e anual em até 12 parcelas mensais.
- A vigência do plano começa no pagamento; nos contratos parcelados, o pagamento da primeira parcela inicia a vigência.
- Avulsos são pagos antes do uso.
- Os planos permitem uso em todos os dias de funcionamento, sem limite de horas dentro desse funcionamento.
- Moradores de condomínios associados têm direito a 50% de desconto nos três planos.
- A secretaria registra a declaração de residência da pessoa e a conferência de comprovante, com data e funcionário responsável.
- Não haverá upload nem armazenamento do comprovante.
- Se o condomínio deixar de ser associado, o desconto de um plano já contratado permanece até seu término. A renovação reavalia a elegibilidade.
- O histórico financeiro é preservado.
- Controle de entrada e saída é opcional e fica fora da primeira entrega proposta.

Os preços semestral e anual são os valores de referência dos respectivos planos. Estão confirmados os dois mecanismos de parcelamento, com limites de 6 e 12 parcelas mensais, respectivamente. Ainda devem ser definidos os vencimentos e eventuais encargos; não adicionar juros ou taxas presumidas.

Nas parcelas controladas pelo MOVI+, cada parcela terá cobrança própria, número, vencimento e quitação integral. O contrato mostrará total contratado, total recebido e saldo restante; a soma das parcelas deverá corresponder ao total contratado, com ajuste determinístico de centavos. No parcelamento no cartão, distinguir pagamento do cliente e recebimento da operadora, sem criar dívidas mensais fictícias do frequentador. Registrar o mecanismo no contrato. Definir como a secretaria confirma a primeira parcela do cartão, sem presumir integração bancária nem equiparar autorização da venda ao recebimento da operadora.

## 3. Diagnóstico do código atual

- `backend/core/models.py`: `Student` já reúne nome, CPF, contatos, endereço e arquivamento. `User` representa contas de acesso; `AuditEvent` registra auditoria.
- `backend/billing/models.py`: `Enrollment.student` referencia o cadastro; `Charge` exige uma matrícula. Não serve diretamente para vender EcoWork sem criar uma matrícula artificial.
- `Enrollment.associated` registra uma condição acadêmica, sem condomínio ou validação de residência. Não será usado como comprovação do benefício EcoWork.
- `core.Lead.student`, serviços de conversão, serializers, permissões e testes dependem de `Student` e das rotas `/api/students/`.
- A presença acadêmica referencia matrículas; deve continuar funcionando após a evolução do cadastro.
- O financeiro acadêmico já possui a restrição de uma quitação por cobrança, mas o EcoWork terá regras e entidades próprias.
- Existem alterações locais anteriores no repositório. A implementação deve preservá-las e integrar mudanças de navegação sem sobrescrever trabalho existente.

## 4. Arquitetura proposta

### Cadastro central

Evoluir `core.Student` para `core.Person` com migração controlada, preservando IDs e dados. A interface passa a apresentar **Cadastros > Pessoas**. “Alunos” poderá continuar como uma visão acadêmica filtrada; uma pessoa apenas do EcoWork não deve aparecer como aluno por ter cadastro.

Estratégia recomendada:

1. Inventariar dependências de `Student`, `student_id`, rotas, relatórios, seeds, fixtures e auditoria.
2. Renomear o modelo lógico para `Person`, mantendo inicialmente a tabela física `core_student`, por migração explícita de estado/banco revisada. Isso reduz alterações físicas e preserva referências.
3. Manter temporariamente o campo acadêmico `Enrollment.student` e os contratos antigos de API como compatibilidade, ambos apontando para a mesma pessoa. Não manter dois cadastros graváveis independentes.
4. Disponibilizar `/api/people/` e atualizar a interface para o cadastro central. Garantir validações e permissões equivalentes em todas as rotas de escrita.
5. Revisar permissões e content types Django, rótulos, identidade de auditoria e consultas antigas. Eventos históricos de `Student` devem continuar consultáveis no histórico da pessoa.
6. Migrar consumidores internos para a nomenclatura nova progressivamente. Renomear tabela física e campos legados somente se houver benefício e após retirar dependências.

Não unir registros automaticamente por nome. Manter regras existentes de identidade e tratar conflitos de CPF/e-mail com revisão explícita. Não transformar automaticamente instrutores, funcionários ou leads não convertidos em pessoas nesta etapa; preparar a estrutura para vínculos futuros.

O arquivamento global da pessoa e a inativação de seu vínculo EcoWork serão ações distintas. Encerrar EcoWork não pode desativar uma matrícula acadêmica.

### Condomínios e residência

| Entidade proposta | Responsabilidade |
|---|---|
| `Condominium` | Nome e situação cadastral do condomínio |
| `CondominiumAssociation` | Períodos de associação, início/fim e autoria das alterações |
| `ResidenceVerification` | Pessoa, condomínio, declaração registrada, comprovante conferido, data, operador e encerramento/revogação |

Uma verificação válida exige declaração e conferência. A aplicação deve permitir escolher o condomínio e consultar a validação; não oferecer um simples campo livre “tem desconto”. Mudanças de residência encerram o vínculo anterior e preservam seu histórico. Sua repercussão sobre planos existentes precisa seguir a decisão pendente da seção 10.

Cadastros migrados começam sem residência validada. Não inferir condomínio a partir do endereço textual nem benefício a partir de matrículas antigas.

### Domínio EcoWork

Criar app Django `ecowork`, reaproveitando sessão, CSRF, auditoria, paginação e convenções de API.

| Entidade proposta | Responsabilidade |
|---|---|
| `EcoWorkMember` | Vínculo único da pessoa com EcoWork, início, situação e observações operacionais |
| `EcoWorkProduct` | Os seis produtos, duração/unidade, preço e vigência das versões |
| `EcoWorkContract` | Plano contratado, período, preço original, desconto, preço final e origem da elegibilidade |
| `EcoWorkSale` | Venda avulsa, produto, quantidade e data/período de referência |
| `EcoWorkCharge` | Obrigação financeira ligada a contrato ou venda, vencimento e valor histórico; identificação de parcela quando houver cobrança parcelada interna |
| `EcoWorkPayment` | Quitação integral, data, forma, referência e operador; correções preservam o original |

Contrato guarda uma fotografia comercial: produto/versão, preços, percentual aplicado, condomínio, validação de residência e data de decisão. Alterar tarifa ou associação não recalcula cobranças ou contratos anteriores.

Cobranças de avulsos não podem usar a restrição “uma por pessoa/mês”, pois a mesma pessoa pode comprar várias diárias. A identidade da cobrança deve estar ligada à venda ou ao período contratual correspondente.

## 5. Fluxos e consistência financeira

### Contratação de plano

Localizar pessoa → ativar vínculo EcoWork → selecionar plano e condição à vista/parcelada → consultar elegibilidade no backend → apresentar preço original, desconto, total e condições de pagamento → confirmar contratação → criar cobrança(s) conforme mecanismo definido → confirmar pagamento → iniciar vigência conforme gatilho acordado.

Não iniciar a vigência na simples criação do contrato. Preservar separadamente data efetiva do pagamento e data de registro no sistema. No parcelamento, o pagamento da primeira parcela inicia a vigência; pagamentos posteriores não reiniciam o prazo contratado. Atrasos posteriores não implicam bloqueio automático de acesso sem regra aprovada.

O backend calcula valores; não confia em um desconto enviado pelo navegador. Sem condomínio associado e residência validada, o sistema informa por que o benefício não está disponível. Permitir concluir pelo preço normal não equivale a validar residência.

### Uso avulso

Localizar pessoa → selecionar hora, meia diária ou diária → informar quantidade/data aplicável → apresentar total → registrar venda e cobrança → confirmar recebimento integral antes do uso.

Não haverá conversão automática de horas em pacotes nem cobrança automática de excedentes enquanto essas regras não forem definidas. A venda avulsa não exige controle de presença.

### Estados

- **Pago:** quitação integral confirmada e válida.
- **Pendente:** cobrança aberta com vencimento ainda não ultrapassado.
- **Vencido:** cobrança aberta após o vencimento, usando a data local de São Paulo.
- **Cancelado:** lançamento cancelado por ação autorizada e auditada, conforme política definida.
- **Sem lançamento:** informação da consulta quando não há cobrança para um período esperado; não é prova de quitação nem de inadimplência.

Não haverá estado “Parcial”. Isenção não se confunde com desconto de associado e não será implementada sem regra específica.

A interface separa validade do plano e situação financeira. Uma cobrança vencida indica pendência no sistema; não confirma, por si só, que não houve recebimento fora dele. A secretaria deve conferir antes de registrar uma conclusão ou cobrança ao frequentador.

### Proteções obrigatórias

- Dinheiro em decimal; valor recebido deve coincidir com o valor integral devido.
- Transações e bloqueio da cobrança ao registrar pagamento; duas solicitações simultâneas não quitam duas vezes.
- Chaves de idempotência para contratação, venda e recebimento; a mesma tentativa reenviada não duplica registros.
- Pagamento cancelado/retificado preserva autor, motivo e histórico; nenhuma exclusão silenciosa.
- Referências financeiras protegidas contra exclusão física.
- Uma cobrança tem exatamente uma origem válida: contrato ou venda.
- Renovação gera novo registro e reavalia residência/associação, sem alterar o contrato anterior.
- Auditoria e operação financeira devem ser confirmadas na mesma transação.

## 6. Interface e API

### Telas propostas

1. **Cadastros > Pessoas:** pesquisa, contatos e acesso aos vínculos acadêmico/EcoWork; residência com data e responsável pela conferência.
2. **Cadastros > Condomínios:** cadastro e períodos de associação.
3. **EcoWork > Gestão:** pesquisa por nome, produto/plano, vigência, cobrança, vencimento, total e situação; alerta separado para dívidas anteriores.
4. **Detalhe do frequentador:** cadastro compartilhado, vínculo EcoWork, contratos, vendas, cobranças, pagamentos e auditoria permitida.
5. **Contratar plano / Registrar avulso / Registrar pagamento:** ações a partir da gestão ou detalhe, com confirmação do total.

Filtros devem distinguir período de contratação, vigência, vencimento e data de recebimento. Semestral/anual à vista não devem parecer sem pagamento nos meses cobertos por uma cobrança já quitada. Nos contratos parcelados, exibir parcelas pagas, a vencer e vencidas, além do saldo total. Não exigir uma mensalidade fictícia para cada mês de cobertura.

Reutilizar componentes e padrões visuais existentes. Validar desktop/celular, navegação por teclado, carregamento, lista vazia, erro e proteção contra duplo envio.

### Recursos de API propostos

- `/api/people/`, `/api/condominiums/`, `/api/residence-verifications/`.
- `/api/ecowork/members/`, `/api/ecowork/products/`, `/api/ecowork/contracts/`.
- `/api/ecowork/sales/`, `/api/ecowork/charges/`, `/api/ecowork/payments/`.
- Consulta de elegibilidade/preço e ações explícitas de renovação e correção conforme contratos definidos.
- Atualizar OpenAPI e cliente central `frontend/src/api.ts`.

Secretaria e Coordenação são os perfis iniciais propostos para operação. A matriz final deve identificar quem mantém associações, valida residência, altera tarifas e corrige financeiro. Não ampliar acesso de Instrutor ou Comunicação aos dados EcoWork. Autorizar cada operação no backend, além de ajustar menus.

## 7. Sequência de implementação

### Etapa 1 — Contratos de negócio e preparação

- Consolidar este plano e as respostas pendentes em especificação única, atualizando `ecowork.md` na implementação para remover regras superadas.
- Definir datas de cobertura, vencimentos, forma de faturamento, renovação e correções.
- Inventariar dependências e conferir baseline de testes antes da migração.
- Registrar matriz de permissões e contratos de API.

Entrega: regras suficientes para implementar financeiro sem presumir políticas.

### Etapa 2 — Cadastro central e migração

- Evoluir `Student` para `Person`, com compatibilidade das integrações existentes.
- Adaptar formulários, navegação, conversão de interessados e consultas acadêmicas.
- Conferir IDs, totais, vínculos e auditoria antes/depois em cópia de desenvolvimento.

Entrega: uma pessoa compartilhada entre módulos; matrículas, cobranças e presença acadêmica preservadas.

### Etapa 3 — Associação e residência

- Implementar condomínios, histórico associativo e validação da residência.
- Registrar declaração/conferência sem armazenar arquivo.
- Implementar cálculo de elegibilidade e auditoria.

Entrega: origem verificável do desconto.

### Etapa 4 — Backend EcoWork

- Criar modelos, migrações, serviços, permissões e endpoints.
- Cadastrar os seis produtos com preços confirmados, em rotina idempotente e com vigência explícita.
- Implementar contratos, vendas avulsas, cobranças, quitação integral e histórico.
- Preservar desconto contratado e reavaliar na renovação.

Entrega: fluxo financeiro íntegro disponível pela API.

### Etapa 5 — Operação na interface

- Implementar gestão, detalhe do frequentador e ações financeiras.
- Destacar pendências antigas mesmo com plano atual pago.
- Separar cobertura, cobrança e recebimento nas consultas.

Entrega: secretaria executa o fluxo completo no MOVI+.

### Etapa 6 — Validação e disponibilização

- Executar testes de migração, regras, permissões, concorrência e regressão acadêmica.
- Executar checks do Django, validação OpenAPI, checagem TypeScript e build conforme scripts do projeto.
- Homologar exemplos com a secretaria em desenvolvimento.
- Preparar backup, sequência de migrações e procedimento de recuperação. Após novas movimentações, não reverter banco apagando dados: priorizar correção progressiva ou recuperação controlada.
- Documentar operação e somente então preparar a publicação, sem executar implantação de produção como parte deste planejamento.

## 8. Critérios de aceite

- [ ] Aluno existente pode utilizar EcoWork sem novo cadastro pessoal; novo frequentador não precisa de matrícula acadêmica.
- [ ] Migração preserva IDs, vínculos, saldos, presenças, leads convertidos e auditoria existente.
- [ ] Inativar vínculo EcoWork não inativa matrículas.
- [ ] Os seis preços estão corretos; planos com benefício custam R$ 84,50, R$ 349,50 e R$ 484,50.
- [ ] Avulsos não recebem o desconto de planos.
- [ ] Residência sem declaração ou comprovante conferido não concede benefício.
- [ ] Condomínio não associado não habilita novo contrato com desconto.
- [ ] Conferência registra data e operador, sem upload.
- [ ] Encerrar associação não modifica preço do plano já contratado; renovação reavalia benefício.
- [ ] Alterar preço de catálogo não modifica histórico.
- [ ] Pagamento parcial ou superior ao devido é rejeitado; quitação integral atualiza o estado.
- [ ] Contratação semestral/anual permite à vista ou parcelamento conforme condições definidas.
- [ ] Ambos os mecanismos, cartão e cobrança pela secretaria, permitem até 6 parcelas mensais no semestral e 12 no anual; quantidades acima desses limites são rejeitadas no backend.
- [ ] Quando houver parcelas administradas pelo MOVI+, sua soma corresponde exatamente ao total do contrato, inclusive com desconto e divisão de centavos.
- [ ] Quitação de uma parcela não marca todo o contrato como quitado.
- [ ] Vigência começa no pagamento da primeira parcela no parcelamento; contratação isolada não inicia cobertura e parcelas posteriores não reiniciam o prazo.
- [ ] Venda avulsa exige pagamento confirmado antes de ser apresentada como pronta para uso.
- [ ] Reenvios e pagamentos simultâneos não duplicam obrigações/recebimentos.
- [ ] Várias vendas avulsas legítimas no mesmo mês são permitidas.
- [ ] Plano quitado com cobertura de seis/doze meses é exibido corretamente durante toda a vigência.
- [ ] Dívidas anteriores aparecem mesmo com a cobrança atual paga.
- [ ] Correção preserva registro anterior, motivo, autor e data.
- [ ] Operações não autorizadas são negadas pela API.
- [ ] Fluxo acadêmico e login continuam funcionando.

## 9. Fora desta entrega

Reservas, estações, mapa de ocupação, catracas, QR Code, portal externo, integração bancária, mensagens automáticas, pagamentos parciais, descontos de avulsos, cálculo automático de excedentes, gratuidade não definida e unificação do financeiro acadêmico com EcoWork.

Frequência, relatórios ampliados e vínculo de outros domínios ao cadastro central ficam para evolução posterior. A consulta operacional de valores e histórico faz parte desta entrega.

## 10. Decisões ainda necessárias

Estas pendências não impedem preparar cadastros e estrutura, mas precisam ser resolvidas antes de concluir os fluxos dependentes:

1. **Detalhes do parcelamento:** confirmados cartão e cobranças pela secretaria, semestral até 6 parcelas mensais e anual até 12. Definir eventuais encargos, meios aceitos nas cobranças da secretaria e como se confirma a primeira parcela no cartão. Parcelamento da mensalidade não foi autorizado nesta definição.
2. **Vigência e vencimento:** confirmado início no pagamento da primeira parcela. Definir cálculo do término, dias 29/30/31, vencimento da primeira cobrança e das seguintes, além do efeito de estorno do pagamento que iniciou a vigência.
3. **Avulsos:** confirmado pagamento antes do uso. Hora aceita frações? Como tratar excedentes das 4h/8h? Até definição, somente venda manual do produto escolhido, sem cálculo automático de tempo.
4. **Renovação:** exclusivamente manual inicialmente? Permitir contratar próxima vigência antecipadamente ou planos sobrepostos?
5. **Correções e cancelamentos:** quem autoriza, como corrigir recebimento registrado indevidamente e como tratar devolução real de dinheiro?
6. **Residência:** mudança de endereço durante plano preserva benefício? Qual prazo de validade da conferência? A manutenção já confirmada refere-se à perda de associação do condomínio.
7. **Permissões:** confirmar poderes de Secretaria e Coordenação, especialmente associação, tarifas e correções financeiras.
8. **Dados iniciais:** lista de condomínios associados e respectivos períodos; existência de frequentadores/obrigações anteriores a importar. Não criar pagamentos fictícios para inicializar histórico.

## 11. Riscos principais e tratamento

- **Migração ampla do cadastro:** compatibilidade transitória, revisão das migrations e testes com dados existentes.
- **Condição acadêmica confundida com residência:** não inferir elegibilidade de `Enrollment.associated`.
- **Histórico comercial reescrito:** valores e origem do desconto preservados por contrato/cobrança.
- **Interface confundir plano válido com pagamento confirmado:** exibir informações separadas.
- **Escopo crescer para regras não definidas:** implementar somente decisões confirmadas e manter pendências explícitas.
