# EcoWork — andamento da implementação

## Segunda entrega — contratos, parcelas e interface — 04/11/2026

Implementados contratos e vendas avulsas em `ecowork.Order`, cobranças em `ecowork.Charge` e recebimentos em `ecowork.Payment`, separados do financeiro acadêmico. `Order` concentra a condição comercial de uma operação; `months > 0` identifica plano, enquanto avulsos não possuem cobertura mensal.

Decisões confirmadas pelo solicitante nesta entrega:

- Parcelas da secretaria mantêm o dia mensal do primeiro vencimento, ajustando dias 29/30/31 ao último dia de meses curtos e retornando ao dia original nos meses seguintes.
- Aprovação da compra parcelada no cartão confirma o pagamento do cliente e inicia vigência. Não equivale a recebimento dos repasses da operadora.

Comportamentos entregues:

- Preços e desconto calculados no servidor, com preço esperado enviado pela tela para detectar mudança de elegibilidade antes da contratação.
- Registro preserva preço, desconto e origem da residência/associação. Alteração posterior de condomínio não reescreve contratos.
- À vista: uma cobrança. Secretaria: até 6 parcelas no semestral e 12 no anual, com divisão exata dos centavos. Cartão: uma cobrança do total da compra contra o cliente, guardando a quantidade de parcelas contratada.
- Pagamento integral obrigatório, proibição de datas futuras e de pagamentos posteriores registrados antes da primeira parcela. Avulso somente aparece como pago após quitação.
- Primeira quitação inicia vigência; término exclusivo calculado por 1/6/12 meses civis a partir dessa data, ajustando meses curtos. Pagamentos seguintes não mudam o início nem o fim.
- Registro no cartão exige meio cartão e referência da compra aprovada. Não há integração bancária.
- Reenvios idempotentes de contratação e pagamento. Locks por pessoa/contratação e por chave de recebimento evitam duplicações concorrentes; auditoria participa da mesma transação.
- Novas rotas: `GET/POST /api/ecowork/orders/`, `GET /api/ecowork/orders/{id}/`, `GET /api/ecowork/charges/` e `POST /api/ecowork/charges/{id}/receive/`.
- Tela `/ecowork` com busca, paginação, contratação, situação da cobertura, parcelas, saldo e confirmação de recebimento. Formulários reutilizam Field/Button/Modal/Notice, autenticação e CSRF existentes.
- Cadastros em `/pessoas`, `/condominios`, `/associacoes` e `/residencias`, incluindo encerramento justificado da associação e revogação da residência pelas respectivas fichas.

Verificação realizada:

- PostgreSQL 16 local, banco temporário `test_movi_ecowork_tests`: **127 testes aprovados, nenhum skip**, incluindo dois novos testes de concorrência financeira com operadores distintos; banco temporário destruído pela suíte.
- Frontend: **34 testes aprovados em 9 arquivos**, incluindo três testes novos de consulta/recebimento/contratação; TypeScript e build aprovados.
- OpenAPI validado sem erros/avisos; migrations sem divergências e diff sem erros de whitespace.
- Chrome headless: login em prévia isolada → plano semestral com residência validada → desconto de 50% → total R$ 349,50 em 6 cobranças → confirmação da primeira parcela → recarga mostrando plano vigente e saldo R$ 291,25.
- Inspeção desktop 1440×1000 e celular 390×844. Corrigido overflow da tabela; largura final da página 390/390px e nenhum erro de JavaScript. Evidências locais ignoradas pelo Git: `.local/ecowork-create-desktop.png`, `.local/ecowork-desktop.png`, `.local/ecowork-mobile.png`.
- Prévia utiliza apenas dados sintéticos em `.local/ecowork-preview.sqlite3`; as migrations também foram exercitadas no PostgreSQL temporário. Nenhuma migration aplicada ao banco operacional, nenhum deploy e nenhum pagamento real.

Limites e próxima etapa:

- Migração definitiva de `Student` para `Person` continua pendente; ambos os nomes ainda apontam à mesma tabela, e a visão acadêmica antiga ainda precisa distinguir frequentadores exclusivos.
- Não há cancelamento/estorno financeiro, devolução, renegociação, bloqueio por atraso, importação histórica, relatórios consolidados ou frequência. Recebimentos são imutáveis pela API atual; correções devem ganhar fluxo próprio antes do uso operacional com casos que exijam retificação.
- Renovação é uma nova contratação com nova elegibilidade; não há ação dedicada de renovação, vínculo com contrato anterior ou política automática de sobreposição. A possibilidade de contratar períodos sobrepostos continua pendente de regra institucional.
- Vencimento inicial é informado pela secretaria. Não foram acrescentados juros/taxas ou parcelamento da mensalidade. Não há simulação automática de excedentes de horas.
- Histórico de catálogo versionado e manutenção de tarifas pela interface permanecem pendentes; cada contratação já preserva seus próprios valores.
- Filtros financeiros avançados, consolidação por pessoa e refinamento do cadastro central são os próximos incrementos. Não declarar todo o plano concluído por esta entrega.

## Histórico — primeira entrega

## Recursos disponíveis no código

- `GET/POST /api/people/` e `GET/PUT/PATCH /api/people/{id}/`: mesmos registros, validações e auditoria da API de alunos. Não exige matrícula. Contas de funcionários continuam em `/api/users/`.
- `GET/POST /api/condominiums/` e `GET/PUT/PATCH /api/condominiums/{id}/`: nome e situação administrativa.
- `GET/POST /api/condominium-associations/`: períodos associativos sem sobreposição; filtrar por `condominium`. A data `ends_on` é exclusiva.
- `POST /api/condominium-associations/{id}/end/`: `ends_on` e `reason`, sem apagar o registro anterior. Período já encerrado não pode ser reescrito por essa ação.
- `GET/POST /api/residence-verifications/`: `person`, `condominium`, `declared: true` e `proof_checked: true`. Data e operador vêm do servidor. Sem campo de arquivo. Filtros por pessoa/condomínio.
- `POST /api/residence-verifications/{id}/revoke/`: `reason` obrigatório. Preserva declaração/conferência originais e registra autor/data de encerramento.
- `GET /api/ecowork/products/`: catálogo inicial dos seis produtos, duração, preço e máximo de parcelas.
- `POST /api/ecowork/quote/`: `person` e `product` (`hour`, `half_day`, `day`, `monthly`, `semiannual`, `annual`). Retorna preço base, desconto, total e origem da elegibilidade. É somente consulta, sem contratação ou garantia de preço futuro.

Todas as rotas exigem conta interna aprovada de Secretaria ou Coordenação. Operações persistentes revalidam a autorização sob transação e gravam auditoria. Não há exclusão de condomínios, associações ou verificações pela API. Registros de associação/residência não permitem edição genérica; possuem ações explícitas para preservar histórico.

## Instalação e limites

Migração adicionada: `core.0003_ecowork_residence_foundation`. Deve ser aplicada no ambiente de desenvolvimento antes de usar os endpoints; não foi aplicada ao banco operacional durante esta entrega.

`Person = Student` é uma ponte de compatibilidade, não uma conclusão da migração para cadastro central. Não existe segunda tabela de pessoas. O menu e a listagem antiga de alunos ainda não distinguem frequentadores exclusivos do EcoWork; a interface será adaptada em etapa posterior.

O catálogo inicial é código explícito com valores homologados. Versionamento de tarifas, contratos, parcelas, cobranças, pagamentos, preservação comercial por contrato, telas e frequência não foram implementados nesta etapa. A simulação de desconto reavalia a associação atual e não deve ser utilizada para recalcular contratos antigos.

Testes não aplicam política institucional, não publicam o sistema e não alteram dados operacionais.

## Verificação executada em 04/11/2026

- `TEST_SQLITE=1 manage.py test core billing academic ecowork --noinput`: 117 testes executados, 110 aprovados e 7 ignorados por dependerem de concorrência PostgreSQL; nenhuma falha. Banco de testes criado e destruído pela suíte.
- Os 11 novos testes abrangem identidade compartilhada, catálogo, elegibilidade/desconto, evidências obrigatórias, autoria, revogação, períodos associativos, preservação de histórico, rollback de auditoria e permissões.
- `manage.py check`: sem problemas.
- `manage.py makemigrations --check --dry-run`: nenhuma alteração pendente.
- `manage.py spectacular --file .local/ecowork-openapi.yaml --validate --fail-on-warn`: aprovado, sem avisos; artefato local, schema também disponível pela API.
- `git diff --check`: sem erros de whitespace.

Limites de verificação: concorrência real e migração em PostgreSQL ainda não exercitadas nesta entrega. Não houve teste de navegador, alteração de frontend nem migração do banco operacional. A suíte executada valida regressão acadêmica e os novos serviços em SQLite, sem substituir os testes posteriores de PostgreSQL e de ponta a ponta.
