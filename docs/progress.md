# Progresso e ponto de retomada — MOVI+

## Cancelamento programado — 12/11/2026

O cancelamento acadêmico aceita data de efeito futura, preservando elegibilidade, ocupação e situação regular até essa data. A Coordenação pode selecionar parcelas posteriores não pagas relativas a serviços não prestados; ficam bloqueadas para recebimento desde o agendamento e são canceladas na data escolhida. Suspensões não podem ultrapassar essa data. Testes direcionados e TypeScript passaram; validação integrada e concorrência em PostgreSQL permanecem pendentes. As notas históricas abaixo sobre cancelamento futuro descrevem o estado anterior a esta implementação.

O catálogo EcoWork aceita desconto de morador de 100% em planos. A contratação começa no próprio dia, sem cobrança ou pagamento fictício, e aparece no resumo do cliente. A migration `ecowork.0004` foi aplicada ao banco de desenvolvimento. A autorização individual de bolsas e descontos EcoWork continua pendente. A suíte anterior ao desconto integral passou com 198 testes em PostgreSQL; os testes específicos da nova regra passaram em SQLite.

Atualização: solicitações de benefício agora distinguem Acadêmico e EcoWork. No EcoWork, a Coordenação configura o limite de aprovação no catálogo e aprova os benefícios; percentuais acima do limite e bolsas integrais exigem referência institucional. Na contratação, o desconto individual é aplicado após o de morador e os dois valores ficam preservados no histórico. Bolsas integrais iniciam na data da contratação, sem cobrança ou pagamento fictício. As migrations `billing.0022` e `ecowork.0005` foram aplicadas ao banco de desenvolvimento. Cinco testes do catálogo e benefícios passaram em PostgreSQL, 36 testes de contrato/catálogo passaram em SQLite, e TypeScript e 41 testes de frontend passaram. Alterações posteriores em benefícios já aplicados ainda não estão implementadas. A nota anterior sobre autorização individual pendente descreve o estado anterior a esta atualização.

## Acordos de repasse — 12/11/2026

Solicitante confirmou que o banco atual é de desenvolvimento e que as migrations anteriores foram aplicadas. Criado cadastro de acordos por instrutor, modalidade, vigência, percentual e critério de apropriação, restrito à Coordenação, auditado e sem alteração de acordos existentes. Períodos sobrepostos para o mesmo instrutor/modalidade são recusados. `billing.0015` aplicada ao banco de desenvolvimento; teste direcionado em SQLite e TypeScript passaram.

O cálculo, a atribuição em substituições, o fechamento mensal e a reabertura auditada ainda não foram implementados. O cadastro por si só não produz valores de repasse.

O serviço de rateio distribui recebimentos entre meses de prestação por dias ou por meses de contrato, preservando a soma exata em centavos e o dia original em meses curtos. Três testes unitários passaram. O serviço ainda não está conectado ao cálculo ou fechamento de repasses.

Coordenação pode invalidar um acordo cadastrado incorretamente, com motivo e auditoria, permitindo cadastrar outro para a mesma vigência. O acordo invalidado permanece no histórico. A migration `billing.0017` foi aplicada ao banco de desenvolvimento; teste direcionado e TypeScript passaram. Ao implementar fechamentos, a invalidação deverá respeitar fechamentos já aprovados e exigir reabertura quando necessário.

`billing.0018` adiciona restrições de consistência de motivo e responsável para invalidações de pagamento e acordo; aplicada ao banco de desenvolvimento. Os testes direcionados dos dois fluxos passaram em SQLite.

Bolsas e descontos acadêmicos: Secretaria ou Coordenação solicita; Coordenação decide com justificativa. Benefícios acima do limite configurável e bolsas integrais exigem referência de autorização institucional. Contratos preservam as condições, redistribuem o valor líquido em centavos e registram isenção da taxa separadamente; bolsa integral não cria pagamento fictício. As migrations `billing.0019` e `0020` foram aplicadas ao banco de desenvolvimento. Testes direcionados de desconto parcial, bolsa integral e limite aprovado passaram em SQLite; falta homologação de interface, concorrência PostgreSQL, alterações de benefícios existentes e benefícios EcoWork.

Catálogo EcoWork: Coordenação pode configurar produtos, duração, preço, parcelamento e desconto de morador em versões com prévia, publicação auditada e vigência. Novas contratações guardam a versão; antigas preservam os valores. Após a primeira publicação, datas sem catálogo são recusadas. É possível encerrar vigência sem efeito retroativo e copiar a configuração para nova versão. A migration `ecowork.0003` foi aplicada ao banco de desenvolvimento; testes direcionados e TypeScript passaram. A versão atual limita desconto de morador a 99%; bolsa integral e isenções EcoWork ainda exigem implementação.

Recebimentos acadêmicos incorretos podem ser invalidados pela Coordenação com justificativa e auditoria. O lançamento permanece no histórico, o saldo é recalculado e os relatórios excluem esse lançamento inválido. A ação não representa devolução de dinheiro. Migration `billing.0016` aplicada ao banco de desenvolvimento; 22 testes direcionados e TypeScript passaram.

Devoluções acadêmicas são ajustes separados, registrados pela Coordenação com data, valor, meio, justificativa e chave idempotente; não reabrem a cobrança. O caixa líquido considera a devolução em sua própria data e há exportação CSV específica. Valores devolvidos não podem exceder o pagamento e impedem a invalidação posterior do lançamento. Migration `billing.0021` aplicada no banco de desenvolvimento; teste direcionado, TypeScript e OpenAPI passaram. Concorrência PostgreSQL e interface ainda requerem validação.

## Continuação — tabelas financeiras e recebimentos acadêmicos

Catálogos acadêmicos podem ser editados pela Coordenação, conferidos e publicados com justificativa; publicação valida estrutura, vigência e revisão da prévia. Novas matrículas consultam a tabela publicada aplicável e guardam sua referência; condições e cobranças antigas são preservadas. Enquanto não houver tabela publicada, a tabela original de 2026 permanece como compatibilidade transitória; após a primeira publicação, datas sem tabela são recusadas. Bolsas e regras EcoWork ainda não são parametrizadas por essa tela.

Continuação: a tabela também permite escolher primeiro vencimento (dia 15/fim do mês, início ou dia fixo) e referência das parcelas seguintes. Dias inexistentes são ajustados sem perder o dia fixo original. Bolsas e regras EcoWork continuam pendentes. A ocupação de turma é verificada nos intervalos sobrepostos antes de criar matrícula.

Continuação: planos personalizados podem ser definidos em rascunho com nome, duração e parcelamentos e selecionados na matrícula conforme a tabela vigente. A migration `billing.0013` amplia os identificadores de plano e não foi aplicada ao banco operacional. Testes direcionados cobrem contratação por plano personalizado; descontos, bolsas e catálogo EcoWork continuam pendentes.

Lista de espera: cadastro e retirada justificada disponíveis para Secretaria/Coordenação na ficha da turma. A matrícula respeita a ordem da fila e vincula a primeira pessoa à matrícula na mesma transação. A migration `billing.0009` ainda não foi aplicada ao banco operacional. Os testes de fila, lotação e ausência de cobrança indevida passaram em SQLite; falta validar concorrência PostgreSQL e os conflitos de agenda/exceções.

Conflitos de horários de turma por sala e instrutor e especialidade são verificados nas alterações de oferta; a remoção de especialidade usada por turma ativa é recusada. Escritas de turmas e especialidades compartilham bloqueio transacional. Cinco testes direcionados em SQLite e geração/validação do OpenAPI passaram; falta validar concorrência PostgreSQL e o fluxo integrado em navegador.

Exceções de lotação exigem Coordenação, justificativa e limite físico da turma cadastrado; a matrícula é recusada se ultrapassar esse limite. A migration `core.0007` ainda não foi aplicada ao banco operacional. Testes direcionados de autorização e limite passaram em SQLite; falta validação em PostgreSQL e navegador.

Relatórios mostram ocupação atual por turma (matrículas regulares, capacidade, experimentais e espera separados) e frequência das matrículas regulares vigentes em 30/90 dias, com alerta de três faltas consecutivas e exclusão de aulas canceladas. Testes direcionados passaram em SQLite. Faltam parametrização de limiares/janelas, evasão, conversões por coorte, validação com volume e conferência visual.

Continuação: Coordenação pode configurar as duas janelas de frequência e o limite de faltas, com justificativa e auditoria. A conversão por coorte conta leads pela data de cadastro e distingue vínculo com pessoa de matrícula com lead de origem explicitamente informado; vínculos antigos não são inferidos. As migrations `billing.0010` e `billing.0011` não foram aplicadas ao banco operacional. Validação de volume e conferência visual continuam pendentes.

Evasão: cancelamentos novos registram data de efeito; a migration `billing.0012` recupera datas explícitas da auditoria quando disponíveis. O relatório separa cancelamentos antecipados, conclusões normais e registros antigos com vigência ou cancelamento desconhecidos. A migration não foi aplicada ao banco operacional. O indicador e a recuperação de datas requerem validação com dados reais em cópia e testes em PostgreSQL; cancelamento futuro ainda não está implementado.

Cancelamento acadêmico com efeito no dia atual permite à Coordenação selecionar parcelas futuras sem recebimentos, confirmar que se referem a serviços não prestados e registrar justificativa. Parcelas canceladas permanecem no histórico, não aceitam recebimento e são excluídas dos saldos ativos. A migration `billing.0014` não foi aplicada ao banco operacional. Cancelamento com data futura, estorno e revisão dos casos parcialmente pagos ainda estão pendentes; teste direcionado e TypeScript passaram.

Validação adicional: testes em SQLite confirmaram que Secretaria não cancela parcelas, parcelas pagas são recusadas sem cancelar a matrícula, cobranças canceladas aparecem no filtro próprio e não compõem o saldo ativo do período. OpenAPI validado e TypeScript aprovado. Repasses, transferência e demais DN ainda exigem implementação.

Comunicação pode consultar leads em modo de leitura com nome, contato autorizado, origem e situação, sem CPF, anotações ou vínculo ao cadastro acadêmico; pesquisa por CPF e alterações são recusadas pelo backend. Gestão de leads continua com Secretaria/Coordenação. Testes direcionados de acesso passaram em SQLite.

Preferências de contato são registradas por pessoa ou lead, canal e finalidade em histórico auditável. Na visão de Comunicação, cada canal comercial só é exibido após autorização explícita e deixa de aparecer quando a última preferência revoga essa autorização; a pesquisa desse perfil usa nome, evitando pesquisa indireta de contato omitido. A migration `core.0006` não foi aplicada ao banco operacional. Retenção e revisão jurídica permanecem pendentes.

Aula experimental foi implementada como participação separada: uma por pessoa/modalidade, aula agendada, turma autorizada, controle de vaga e autorização de responsável para menor com data de nascimento conhecida. Após concluir a aula, o responsável pela chamada registra presença ou falta e pode corrigir a marcação com justificativa auditada. Arquivar pessoa ou cancelar aula encerra a experimental agendada. A migration `academic.0002` ainda não foi aplicada ao banco operacional. Testes direcionados passaram em SQLite; faltam concorrência PostgreSQL e validação em navegador.

Reposições são aulas novas ligadas à ocorrência original, com data, horário, instrutor, justificativa e verificação de conflitos de sala/instrutor. Alteração das referências de uma reposição exige cancelar e registrar outra. A migration `academic.0003` ainda não foi aplicada ao banco operacional. Testes direcionados e 36 testes acadêmicos anteriores passaram em SQLite (um teste PostgreSQL ignorado); falta validação em PostgreSQL e navegador.

Recebimentos acadêmicos aceitam pagamentos parciais e múltiplos, mediante chave de operação, recusando excedente. Estorno e correção de recebimento continuam pendentes, assim como pagamentos parciais EcoWork. As migrations `billing.0005`, `0006` e `0007` não foram aplicadas ao banco operacional.

Suspensões acadêmicas podem ser autorizadas pela Coordenação por até 30 dias, sem retroatividade, dentro da vigência, com justificativa e histórico. A participação fica bloqueada nas datas inclusivas; cobranças e vigência não são alteradas. A migration `billing.0008` ainda não foi aplicada ao banco operacional. Dois testes direcionados passaram em SQLite; a interface nova precisa ser exercitada em navegador e a concorrência em PostgreSQL.

Verificações: 38 testes existentes e novos de financeiro, contratos e rascunhos passaram em SQLite; após adicionar proteção contra prévia desatualizada, mais 7 testes direcionados passaram. TypeScript aprovado. A tela nova e a concorrência em PostgreSQL ainda precisam de validação.

## Configuração financeira — início

Criado `FinancialCatalogVersion` e migration `billing.0005_financialcatalogversion` como estrutura inicial para versões com vigência, configuração, autoria e metadados de publicação. Ainda não há serviço/API/interface de edição e publicação, validação de conteúdo ou seleção de versão na contratação; os preços existentes continuam fixos no código. Essa estrutura ainda não implementa a parametrização financeira das DN-004–011. A migration não foi aplicada ao banco operacional. Em SQLite, os 11 testes existentes de contratos acadêmicos passaram; não verificam o novo catálogo.

Continuação: API `/api/financial-catalogs/` permite à Coordenação criar e editar rascunhos versionados com auditoria e revalidação de permissão na transação. A publicação retorna erro até existirem validação de conteúdo e prévia de impacto; nenhum contrato consulta esses rascunhos. Dois testes de autorização e ciclo do rascunho passaram em SQLite. Falta a interface, validação, publicação e integração com contratos.

Foi acrescentada prévia inicial que verifica estrutura de planos, preços e taxas, incluindo combinações duplicadas. A prévia ainda não calcula impacto sobre contratações nem cobre todos os parâmetros exigidos; a publicação permanece bloqueada. Três testes do catálogo passaram em SQLite. A gestão de contas foi restrita à Coordenação na API e na navegação. O arquivamento de pessoa aprovado foi habilitado sem eliminar histórico; a elegibilidade de pessoa arquivada continua indeterminada.

## Identidade DN-003 — 11/11/2026

Aprovação do solicitante registrada em `decisions.md`. CPF informado agora é único, com validação na API e constraint condicional na migration `core.0005_person_cpf_unique`. A migration interrompe sua aplicação se houver duplicatas, para tratamento prévio sem fusão automática. Conversão de lead está habilitada sem override e exige resolução justificada quando CPF e e-mail indicam pessoas distintas, inclusive quando o único resultado por e-mail tem CPF diferente. E-mail de pessoa continua compartilhável. Ainda é necessário aplicar a migration ao ambiente escolhido e conferir a interface de resolução de identidade.

Verificação: `TEST_SQLITE=1 manage.py test core.tests.test_core --noinput`: 32 testes, 4 ignorados por exigirem PostgreSQL; `makemigrations --check --dry-run`: sem divergências. Concorrência e migração em banco operacional não foram verificadas nesta etapa.

A interface de conversão consulta o cadastro central `people/`, exclui pessoas arquivadas da seleção e abre a ficha de pessoa após a conversão. O endpoint anterior `students/` também usa o cadastro central; a mudança explicita o fluxo por pessoa. TypeScript aprovado e 7 testes existentes de detalhes passaram; o fluxo novo não foi inspecionado em navegador.

Este é o ponto de entrada para continuar o desenvolvimento. Requisitos e decisões estão em `requirements.md` e `decisions.md`; evidências de execução estão em `verification.md`.

## Cadastro central e consultas EcoWork — 05/11/2026

Retomada da segunda entrega EcoWork (`ee49ddd`). `Person` agora é o modelo real, mantendo tabela física `core_student`, IDs, relações e identidade histórica da auditoria. O alias e os imports antigos foram removidos; endpoints acadêmicos permanecem compatíveis. Migration `core.0004_person_identity` preserva content types e concessões de permissões. Aplicada apenas em testes e cópia sintética de prévia, não no banco operacional.

Lista de alunos e contador do painel consideram pessoas com matrícula acadêmica; Pessoas reúne todos os cadastros e permite filtrar vínculos acadêmicos/EcoWork. Ficha da pessoa mostra totais EcoWork de todo o histórico e atalhos para os dois módulos. EcoWork filtra cobertura, situação de parcela e intervalo de vencimento, preservando consulta e pessoa na URL. Filtros financeiros combinados devem corresponder à mesma parcela; a ficha exibe o contrato inteiro.

Próximo passo: definir e implementar correção/cancelamento financeiro e renovação dedicada (incluindo sobreposição de planos), depois catálogo versionado e relatórios. Frequência permanece opcional. O plano completo ainda não está concluído. Detalhes e verificações atuais em `ecowork-implementacao.md`; os pontos de parada abaixo são históricos.

## Contratos e chamada — 03/11/2026

Implementação do `promptimpmodalidades.md`: diagnóstico, regras, arquivos, migrations e pendências em [contracts-2026.md](contracts-2026.md). Cartão 2026, categorias 1–6, contratos trimestral/anual, primeira parcela + taxa para ativação, renovação sem nova taxa, WhatsApp manual e correção auditável de chamada. Legados preservados. Próximo passo institucional: conferir planilha, configurar modalidades e validar vencimentos provisórios. Evidências em `verification.md`. Registros abaixo descrevem etapas anteriores.

## Retomada — 03/11/2026

Na `main`, após o merge `72b0fd9`, foi preparado um PostgreSQL de demonstração isolado em contêiner Docker `movi-codex-demo`, porta local 55432, com configuração em `.env.demo`; o `.env` existente foi preservado. Migrações e dados sintéticos foram aplicados ao banco demo. O contêiner criado não tem volume nomeado: seus dados persistem enquanto o contêiner existir, mas são perdidos se ele for removido.

Verificações nesta retomada: 87 testes backend em PostgreSQL aprovados sem skips, inclusive concorrência; 31 testes frontend, typecheck e build aprovados. Detalhes e limitações em `verification.md`.

O preparador portátil aceita `--env-file` para preservar uma configuração existente, mas o `initdb.exe` disponível falhou com código 3221225781; usou-se Docker. O inicializador de serviços reutilizou processos já ativos nas portas 5173/8000, cuja API estava conectada à porta 5432, não ao banco demo 55432. Nenhuma operação de negócio foi realizada nesses serviços. As novas consultas ainda precisam de validação integrada em navegador contra o banco demo, incluindo mais de 25 vínculos, navegação de histórico, filtros e período dos relatórios, em desktop e celular. Não presumir que `start-local.ps1` troca a configuração de serviços já ativos.

As decisões DN-004/005/006 e DN-014 continuam necessárias para implementar o fluxo operacional completo. As definições parciais financeiras estão em `decisions.md`.

## Registro anterior — ambiente e integração — 08/10/2026

Retomada a partir do commit `18f7cfd`, na branch `trabalho`, inicialmente sem alterações locais. Objetivo: preparar Python/PostgreSQL neste clone, executar verificações backend e validar em navegador as consultas entregues. Resultados e próximos passos serão atualizados ao concluir a etapa. Definições de planos, vencimento e primeiro mês foram solicitadas ao usuário; trabalho técnico independente continua enquanto essas regras permanecem pendentes.

## Etapa anterior — consultas — 08/10/2026

**Concluída nesta etapa:** consulta de histórico e de registros vinculados, conforme RF-012, RF-024, RF-029, RF-031 e RF-032. O projeto completo continua com as dependências institucionais abaixo.

- Histórico comercial da matrícula: plano, valor original, data de efeito, responsável, motivo e momento do registro; atalhos para conta responsável e auditoria. Ausência de histórico e falha de consulta têm estados próprios.
- Paginação das matrículas do aluno, cobranças da matrícula e aulas da turma: consulta além dos primeiros 25 resultados, retorno à primeira página ao mudar de cadastro, nova tentativa após falha e recuperação de página indisponível.
- Listagens preservam busca, filtros, ordenação e página na URL. Voltar pelo navegador restaura a consulta; alterar filtros reinicia a página e “Limpar filtros” remove a seleção. Parâmetros desconhecidos não são encaminhados à API.
- Relatório abre cobranças por vencimento e recebimentos por data de pagamento no período consultado. As abas financeiras preservam as datas; os indicadores gerais identificam seu período. O atalho de acesso do painel abre somente solicitações pendentes.
- **Verificação final: 31 testes em oito arquivos, exit 0; TypeScript e build Vite aprovados.** Foram acrescentados 13 cenários em `frontend/src/details.test.tsx` e `frontend/src/lists.test.tsx`. Detalhes e limites em `verification.md`.
- Entrega reunida na branch `trabalho` de `amorimfps1/movi-v2`, no commit `feat: completa consultas de histórico, paginação e filtros`. Consulte `git log -1` para o identificador. O envio ao GitHub não publica o aplicativo em hospedagem.

## Estado encontrado nesta retomada

- Código inicial em `e8dcb4a`, sem alterações locais no início. Projeto dentro de `movi-v2/`, com repositório Git próprio.
- Última entrega documentada: revisão de terminologia, marca, foco por teclado e menu móvel em 08/10/2026.
- Evidências anteriores: 87 testes backend e 18 frontend aprovados, descritos em `verification.md`; esses números não representam execução nesta retomada.
- No início, este clone não continha `.env`, `.venv`, `.local` nem dependências do frontend. As dependências frontend foram instaladas nesta etapa. O PostgreSQL portátil descrito no README pertencia ao ambiente da sessão anterior.

## Dependências registradas antes do prompt de 03/11/2026

As 22 decisões DN continuam pendentes. Para completar matrícula → cobrança → liberação → chamada, definir primeiro DN-004/005/006 (plano, cobertura e geração) e DN-014 (chamada). A instrução de continuar o desenvolvimento não define o conteúdo dessas políticas.

## Instruções de retomada anteriores

1. Ler este arquivo e consultar `git status` dentro de `movi-v2/`.
2. Conferir a última seção de `verification.md` para distinguir verificações atuais de evidências anteriores.
3. Continuar pelo próximo passo registrado ao fim da etapa; não ativar políticas pendentes por suposição.

## Próximo passo registrado em 08/10/2026

1. Preparar backend e PostgreSQL de desenvolvimento neste clone conforme o README: ambiente Python, `.env`, banco local, migrações e dados sintéticos em banco exclusivo de demonstração. O frontend já possui dependências e build; os serviços não foram iniciados nesta etapa.
2. Validar no navegador o histórico comercial, a navegação além de 25 vínculos, o retorno pelo histórico do navegador e relatório → cobranças/recebimentos com o mesmo período; conferir desktop e celular. Executar as verificações backend no ambiente preparado. Os testes desta etapa usam API simulada e não substituem esse percurso integrado.
3. Registrar as definições institucionais de DN-004/005/006 e DN-014 para implementar geração, cobertura e chamada operacionais. Demais decisões permanecem em `decisions.md`.

**Ponto de parada:** código frontend e documentação atualizados; 31 testes e build aprovados; pendente preparação do backend/banco e validação integrada das novas consultas. Não há falha pendente nos testes frontend executados.
