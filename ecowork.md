MOVI+ — Proposta de Implementação do Módulo EcoWork

> Atualização de 04/11/2026: este texto é a proposta inicial. As decisões posteriores e o andamento estão em [Plano de implementação](docs/plano-implementacao-ecowork.md). O escopo vigente inclui hora, meia diária, diária e planos mensal/semestral/anual; não há pagamento parcial de uma cobrança. Semestral/anual admitem parcelamento no cartão ou pela secretaria, em até 6/12 parcelas mensais, com vigência iniciada no pagamento da primeira parcela. Moradores com residência validada em condomínio associado têm 50% de desconto nos três planos, preservado até o fim do plano contratado. Comprovantes são apenas conferidos, sem upload. A seção “Parcial” abaixo é histórica e foi substituída por essas decisões.

1. Objetivo
Implementar um módulo de gestão do EcoWork dentro do MOVI V2, com foco no controle de mensalidades, pagamentos e situação financeira dos frequentadores.

Atualmente, o principal problema é a falta de um controle centralizado que permita identificar rapidamente se uma pessoa que utiliza o EcoWork está com seus pagamentos em dia.

O módulo deve permitir que a secretaria consulte o cadastro de qualquer frequentador e verifique se sua mensalidade está paga, pendente ou vencida, além de visualizar seu histórico financeiro.

O registro de horários de entrada e saída poderá ser incluído como funcionalidade complementar, caso seja necessário.
2. Funcionalidades principais
2.1. Cadastro de frequentadores
Cada pessoa que utiliza o EcoWork deverá possuir um cadastro com as seguintes informações:
- Nome completo.
- Telefone.
- E-mail (opcional).
- Data de início da utilização.
- Situação cadastral (ativo ou inativo).
- Observações administrativas.
O cadastro deverá reunir o histórico de mensalidades e pagamentos do frequentador.

O histórico financeiro deverá ser preservado mesmo que a pessoa deixe de utilizar o espaço.
2.2. Controle de mensalidades
O sistema deverá permitir o registro e acompanhamento das mensalidades de cada frequentador.

Cada mensalidade deverá conter:
- Frequentador vinculado.
- Mês e ano de referência (competência).
- Valor da mensalidade.
- Data de vencimento.
- Valor recebido.
- Saldo pendente.
- Situação do pagamento.
As situações financeiras deverão ser identificadas automaticamente:
Situação	Descrição
Pago	Mensalidade integralmente quitada.
Pendente	Mensalidade ainda não paga, dentro do prazo.
Vencido	Mensalidade não quitada após o vencimento.
Parcial	Pagamento realizado, mas ainda existe saldo.
Isento	Frequentador com isenção autorizada.
Sem lançamento	Não existe mensalidade cadastrada para o período.

O sistema deverá impedir lançamentos duplicados acidentais para o mesmo frequentador e competência.

Importante: a ausência de pagamento registrado não significa necessariamente que a pessoa não pagou. Nesses casos, a secretaria deverá conferir o recebimento antes de confirmar a inadimplência.
2.3. Registro de pagamentos
A secretaria deverá conseguir registrar os pagamentos recebidos dos frequentadores.

Cada pagamento deverá conter:
- Frequentador.
- Mensalidade correspondente.
- Valor recebido.
- Data do pagamento.
- Forma de pagamento (Pix, dinheiro, cartão, transferência ou outro).
- Funcionário responsável pelo registro.
- Observações ou referência do pagamento.
Após registrar o recebimento, o sistema deverá atualizar automaticamente o saldo e a situação financeira da mensalidade.

Também deverá ser possível consultar o histórico completo de pagamentos, com identificação de quem realizou cada lançamento.

Correções financeiras deverão ser auditadas, evitando a exclusão de informações sem justificativa.
3. Tela principal — Gestão EcoWork
O módulo deverá possuir uma tela centralizada para acompanhamento financeiro.

A principal funcionalidade será a pesquisa rápida por nome, permitindo localizar um frequentador e verificar imediatamente sua situação.

Exemplo de visualização:
Frequentador	Mensalidade	Vencimento	Valor	Situação
João Silva	Novembro/2026	10/11	R$ 100,00	Pago
Maria Souza	Novembro/2026	10/11	R$ 100,00	Pendente
Pedro Santos	Outubro/2026	10/10	R$ 100,00	Vencido

Dados e valores meramente ilustrativos.

A tela também deverá permitir filtrar os registros por mês, situação financeira e nome.

Na parte superior, poderão ser exibidos indicadores simples, como quantidade de frequentadores ativos, mensalidades pagas, pendentes e vencidas.

Ao selecionar uma pessoa, a secretaria deverá conseguir visualizar seu cadastro e histórico de pagamentos, além de registrar novos recebimentos.
4. Controle de entrada e saída (opcional)
Caso seja necessário acompanhar a frequência dos usuários do EcoWork, o sistema poderá oferecer um controle simples de entrada e saída.

As informações registradas serão:
- Frequentador.
- Data e horário da entrada.
- Data e horário da saída, quando informado.
- Responsável pelo registro.
Essa funcionalidade permitirá consultar o histórico de utilização e verificar a situação financeira de quem está frequentando o espaço.

Não será necessário implementar controle de estações, reservas, catracas, QR Code ou bloqueios automáticos de acesso.

O controle de frequência será independente do controle financeiro.
5. Fluxo de funcionamento
O funcionamento do módulo deverá seguir um processo simples:
1. A secretaria cadastra o frequentador ou consulta um cadastro existente.
2. Registra a mensalidade correspondente ao período.
3. Quando recebe ou confirma o pagamento, registra o recebimento no sistema.
4. O MOVI+ atualiza automaticamente a situação financeira.
5. Ao consultar o nome de um frequentador, a secretaria consegue verificar se a mensalidade está quitada ou se existem pendências.
6. Caso seja implementado o controle de frequência, a secretaria poderá registrar os horários de entrada e saída.
O objetivo é reduzir o trabalho manual e oferecer informações financeiras confiáveis e acessíveis.
6. Integração com o MOVI V2
O módulo deverá seguir a arquitetura e os padrões já utilizados pelo MOVI+, aproveitando a infraestrutura existente.

Backend: Django e Django REST Framework.

Frontend: React com TypeScript.

Banco de dados: PostgreSQL.

Autenticação e permissões: aproveitar o sistema de usuários e controle de acesso existente.

Auditoria: registrar as operações financeiras relevantes, incluindo criação, alteração e cancelamento de lançamentos.

A implementação poderá utilizar um aplicativo Django independente, denominado ecowork, integrado ao backend principal.

No frontend, será adicionada uma seção EcoWork ao menu lateral do MOVI+.

O módulo deverá possuir entidades próprias para frequentadores, mensalidades e pagamentos, evitando misturar os registros financeiros do EcoWork com as matrículas acadêmicas do sistema.
7. Requisitos essenciais
Para considerar a implementação funcional, o sistema deverá permitir:
- Cadastrar, editar e consultar frequentadores.
- Registrar mensalidades por mês e ano.
- Registrar pagamentos vinculados às mensalidades.
- Consultar pagamentos anteriores.
- Identificar mensalidades pagas, pendentes e vencidas.
- Pesquisar rapidamente a situação financeira de um frequentador.
- Visualizar saldos em aberto.
- Preservar o histórico de alterações financeiras.
- Restringir operações financeiras a usuários autorizados.
- Impedir que mensalidades sem pagamento confirmado sejam identificadas incorretamente como quitadas.
8. Funcionalidades fora do escopo
Nesta implementação, não será necessário desenvolver reservas de estações, mapas de ocupação, agendamento de espaços, portal do frequentador, integração bancária, pagamentos online ou automações de mensagens.

Essas funcionalidades acrescentariam complexidade sem resolver diretamente a necessidade atual da secretaria.
9. Informações que precisam ser confirmadas
Antes de implementar as regras definitivas de cobrança, será necessário confirmar com o MCJB:
1. Qual é o valor atual da mensalidade e se existem diferentes categorias de cobrança.
2. Como são definidos os vencimentos.
3. Quais formas de pagamento são utilizadas e como os recebimentos são confirmados.
4. Se pagamentos parciais são permitidos e como são tratadas correções e devoluções.
5. Se o registro de entrada e saída realmente será necessário.
Essas informações permitirão adequar o módulo ao funcionamento real do EcoWork.
10. Prioridade da implementação
Primeira etapa — Essencial

Desenvolver o cadastro de frequentadores, lançamento de mensalidades, registro de pagamentos, consulta da situação financeira e histórico de operações.

Segunda etapa — Opcional

Acrescentar o registro de entrada e saída e relatórios financeiros simples, caso a equipe identifique necessidade.
11. Resultado esperado
Ao finalizar a implementação, o MCJB deverá possuir um controle financeiro centralizado do EcoWork.

A secretaria poderá pesquisar o nome de qualquer frequentador e identificar rapidamente:
- Se a mensalidade do período está quitada.
- Qual foi o último pagamento registrado.
- Quando o pagamento foi realizado.
- Se existem mensalidades vencidas.
- Qual é o saldo financeiro pendente.
O objetivo principal é garantir que o MCJB tenha visibilidade sobre os pagamentos dos frequentadores do EcoWork, reduzindo a falta de controle financeiro e facilitando as atividades administrativas da secretaria.
