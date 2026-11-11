# MOVI+ V2 — Decisões de Negócio DN-001 a DN-022

**Data de consolidação:** 11/11/2026  
**Escopo:** acesso, identidade, contratos, financeiro, operação acadêmica, indicadores, dados e operação.  
**Natureza deste documento:** consolidação de regras já confirmadas no projeto e de propostas para aprovação institucional. Este texto **não** representa homologação automática nem confirma que todas as funções já estão implementadas.

## Orientações gerais

1. **Regra já confirmada**: decisão registrada anteriormente pelo solicitante e documentada no projeto, a ser preservada.
2. **Proposta para aprovação**: recomendação de negócio e implementação que depende de validação institucional.
3. **Implementado** e **homologado** são estados diferentes de **aprovado**. Cada decisão deve ter registro separado de aprovação, entrega técnica e testes de aceite.
4. Alterações em regras comerciais não podem modificar silenciosamente contratos e transações históricas.
5. Todas as operações sensíveis devem registrar usuário, data/hora, valores antes/depois e motivo quando aplicável.

> **Diretriz adicional solicitada:** toda a parametrização de **planos, valores, taxas, parcelamentos, vencimentos, cobranças, descontos, bolsas e inadimplência** deve ser realizada **pelo próprio site**, na área administrativa do MOVI+ V2, sem alteração manual do código, do banco de dados nem novo deploy para ajustes usuais de negócio.

---

## DN-001 e DN-002 — Funções, permissões e contas

**Proposta para aprovação:** diferenciar Secretaria e Coordenação, embora atualmente ambas possuam permissões administrativas equivalentes em partes do backend.

- **Secretaria:** cadastros, atendimento, interessados, alunos, matrículas, turmas, cobranças, registro de recebimentos e consulta de relatórios autorizados.
- **Coordenação:** operações da Secretaria, gerenciamento de contas e funções, aprovação de exceções, configuração comercial e supervisão acadêmica/financeira.
- **Instrutor:** acesso somente a turmas e aulas próprias ou explicitamente atribuídas, inclusive chamada autorizada, sem exposição desnecessária de informações financeiras.
- **Comunicação:** contatos e indicadores comerciais autorizados, sem acesso irrestrito aos dados acadêmicos e financeiros.
- **Aprovar/rejeitar contas:** somente Coordenação. Rejeição exige motivo.
- **Reabrir solicitação rejeitada:** somente Coordenação, com justificativa e auditoria.
- **Conceder ou remover funções:** somente Coordenação; nenhum usuário pode modificar suas próprias permissões pela rotina comum.
- **Desativar conta:** somente Coordenação; revogação imediata do acesso, mantendo histórico.
- **Múltiplas funções:** permitidas, quando justificadas pelo trabalho exercido.
- **Aprovação inicial:** substitui o conjunto de funções pelas funções expressamente aprovadas; adicionar funções posteriormente deve ser ação separada, sem remover as existentes.

**Critérios de aceite:** usuários sem função válida ou com conta pendente/rejeitada/desativada não acessam rotas internas; permissões são verificadas no backend, não apenas pela interface; todas as mudanças críticas são auditadas.

## DN-003 — Identidade, CPF, e-mail e conversão de interessados

**Proposta para aprovação:**

- CPF continua **opcional**, mas, quando informado, deve ser validado, normalizado e **único por pessoa**.
- E-mail pode ser compartilhado entre pessoas, especialmente familiares; não deve ser chave exclusiva de identidade de alunos.
- A unicidade de e-mail para **contas de login** é uma regra separada da identidade de pessoas cadastradas.
- Na conversão de interessado, buscar correspondência por CPF e, como indício auxiliar, por e-mail.
- Se CPF e e-mail apontarem para pessoas diferentes, ou surgirem múltiplas correspondências, **bloquear a conversão automática** e solicitar resolução manual justificada.
- Conversão não cria automaticamente matrícula, pagamento ou direito à participação.
- Não fundir automaticamente pessoas com histórico financeiro ou acadêmico.

**Critérios de aceite:** tentativa de CPF duplicado é recusada; e-mails familiares compartilhados são aceitos em cadastros de pessoas; conversão ambígua exige resolução explícita e mantém os vínculos e a auditoria.

## DN-004, DN-005, DN-006 e DN-007 — Planos, cobranças, taxas, descontos e bolsas

### Diretriz obrigatória: todas as configurações pelo site

O MOVI+ V2 deverá possuir um módulo **Administração > Configurações Financeiras**, no qual a Coordenação poderá, sem intervenção técnica:

| Grupo | O que deve ser configurável na interface |
|---|---|
| Planos | Criar, editar, ativar/desativar, definir nome, vigência, duração, elegibilidade e planos personalizados |
| Tabelas de preços | Valor total por modalidade, categoria, ano/período de vigência, associação e meio de pagamento |
| Parcelamento | Quantidade permitida de parcelas, periodicidade, regras de distribuição dos centavos e condições de contratação |
| Vencimentos | Primeiro vencimento, dia de referência, tratamento dos dias 29/30/31, vencimentos específicos por plano |
| Cobranças | Geração automática/manual autorizada, horizonte de geração, taxa adicional, correção de obrigação ausente e ajustes controlados |
| Taxas | Criar, alterar, ativar/desativar e isentar taxas de matrícula ou outras taxas |
| Descontos e bolsas | Valor fixo ou percentual, bolsa parcial/integral, vigência, escopo, limite de autorização e isenção de taxa |
| Inadimplência | Bloqueios, carência, juros, multas, exceções e eventual renegociação, com padrões conservadores |
| Autorizações | Quem pode visualizar, propor, aprovar e alterar cada parâmetro ou exceção |

**Requisitos técnicos da parametrização:** persistir regras em tabelas próprias no PostgreSQL, versionar políticas e tabelas, manter datas de vigência, guardar snapshots das condições nos contratos, validar conflitos, auditar alterações e oferecer prévia/simulação do impacto antes de publicar uma nova tabela. **Não usar preços ou regras comerciais fixos em funções Python como fonte permanente de configuração.**

**Política de efeitos:** alterações no catálogo devem atingir **novas contratações por padrão**. Mudanças em contratos já existentes exigem ação específica autorizada, data de efeito e registro das condições anteriores; cobranças pagas nunca devem ser reescritas silenciosamente.

### Regras de contratos de 2026 já confirmadas

- Contratos novos seguem as regras de **2026**, substituindo a interpretação antiga de valor mensal para novos contratos.
- **Trimestral:** 3 meses, com opção de 1, 2 ou 3 parcelas.
- **Anual:** 12 meses, com opção de 3, 6, 10 ou 12 parcelas.
- Os valores da tabela de 2026 representam **totais contratuais**.
- Ativação depende de **primeira parcela e taxa de matrícula quitadas**, quando a taxa for aplicável.
- Parcelas futuras ainda não vencidas não bloqueiam por si só. Parcelas vencidas, cobrança obrigatória ausente/divergente, cancelamento e expiração impedem liberação.
- Pagamento atrasado não prorroga vigência nem quita outras parcelas.
- Renovação explícita não cobra nova taxa de matrícula.
- Tabelas incompletas, meios de pagamento ainda sem preços aprovados e modalidades sem enquadramento validado não devem ser disponibilizados como se tivessem preço definido.

### Vencimento e cronograma — convenção atual, sujeita à aprovação

- Matrícula iniciada até o dia 15: primeiro vencimento no dia 15 do mês inicial.
- Matrícula iniciada após o dia 15: primeiro vencimento no último dia do mês inicial.
- Vencimentos seguintes seguem a referência mensal definida no contrato; meses sem o dia 29, 30 ou 31 usam o último dia válido **sem alterar a referência original**.
- Na contratação, criar todas as obrigações previstas e a taxa aplicável atomicamente, com chaves de idempotência para impedir duplicações.
- Cobranças esperadas ausentes impedem liberação e são encaminhadas à regularização pela Secretaria ou Coordenação, sem presumir adimplência. Divergências exigem revisão e não são corrigidas silenciosamente.
- Vigência encerra no fim contratual definido, independentemente de pagamentos feitos depois do prazo; alterações exigem operação própria.

**Importante:** a convenção de vencimentos acima já é utilizada tecnicamente como provisória no projeto, mas deve ser validada na instituição e ser configurável no site.

### Descontos e bolsas — proposta para aprovação

- Secretaria pode **solicitar** descontos e registrar propostas, mas a aprovação fica com a Coordenação.
- Coordenação pode aprovar descontos de até **20%**, com justificativa; percentuais maiores e bolsas integrais exigem autorização institucional específica, formalizada pela Coordenação.
- Os próprios limites de aprovação precisam ser **configuráveis no site**, conforme a política aprovada.
- Descontos podem ter valor fixo ou percentual, início/fim, modalidade, plano, pessoa/contrato e justificativa.
- Bolsa de **100%** pode liberar participação caso todas as demais condições sejam atendidas, registrando **isenção/dispensa da obrigação**, não um pagamento fictício de R$ 0,00.
- Isentar a mensalidade/contrato não isenta a taxa automaticamente: a taxa deve ter regra de isenção própria.
- Alterações de desconto não podem recalcular retroativamente valores já quitados sem procedimento formal de ajuste.

**Critérios de aceite:** a Coordenação modifica plano, preço, desconto, taxa e vencimento pela interface; novo contrato utiliza a versão vigente; contrato antigo mantém snapshot; tentativa de alterar obrigação quitada exige procedimento próprio; alterações com impacto financeiro aparecem na auditoria.

## DN-008, DN-009, DN-010 e DN-011 — Pagamentos, inadimplência e ciclo do contrato

### Pagamentos — proposta

- Aceitar **pagamentos parciais** e múltiplos recebimentos associados à mesma cobrança.
- Saldo restante = valor devido atualizado menos recebimentos líquidos válidos.
- Uma cobrança somente fica integralmente quitada quando seu saldo for zero (respeitadas isenções autorizadas).
- Pagamento parcial não libera participação quando ainda houver obrigação vencida não quitada.
- **Excedente:** recusar inicialmente, sem gerar créditos automáticos; módulo de crédito poderá ser definido no futuro.
- Cada recebimento deve ter data, valor, meio, referência, responsável e histórico imutável de correções/estornos.

**Diferença para o estado atual:** a baixa integral exata já existe; pagamentos parciais e tratamento de excedente exigem desenvolvimento específico.

### Inadimplência — proposta

- Padrão inicial: **sem carência, sem multa e sem juros automáticos**.
- Cobrança em aberto torna-se vencida no dia seguinte ao vencimento na data local da instituição.
- Pendências vencidas impedem a liberação, salvo política de exceção expressamente configurada e autorizada.
- Pagar pendências não reativa matrícula cancelada ou suspensa automaticamente.
- Carência, juros, multas e regras de renegociação devem permanecer configuráveis pelo site, ainda que inicialmente desativados.

### Suspensão e trancamento — proposta

- Somente Coordenação autoriza; justificar, registrar data de início/fim e responsável.
- Prazo inicial sugerido: **até 30 dias por solicitação**, prorrogável mediante nova aprovação.
- Aluno não participa das aulas durante o período autorizado.
- Ajustes de vigência e cobranças futuras somente mediante condição contratual/aditivo registrado; não presumir prorrogação automática de 30 dias para todos os casos.
- Proibir efeitos retroativos automáticos e preservar integralmente cobrança, pagamento e frequência anteriores.

### Cancelamento e renovação

- Cancelamento vale a partir da **data de efeito autorizada** e registrada; mantém histórico e valores exigíveis de períodos já prestados.
- Eventuais devoluções referentes a serviços não utilizados dependem das condições contratuais e da legislação aplicável, com análise e registro próprios; **não calcular reembolso automaticamente sem política aprovada**.
- Renovação é **explícita**, vinculada à matrícula anterior e começa após o término do contrato atual, sem sobreposição na mesma oferta por padrão.
- Renovação **não repete a taxa de matrícula** e não apaga pendências do contrato anterior — regra já confirmada para 2026.

## DN-012, DN-013, DN-014 e DN-015 — Turmas, experimentais, chamada e reposição

### Capacidade e agenda — proposta

- Capacidade atingida bloqueia novas matrículas regulares.
- Permitir **lista de espera** por ordem de solicitação.
- Exceção de lotação só com Coordenação e dentro de limites físicos/de segurança.
- Conflitos de sala, instrutor e horários impedem confirmação até resolução autorizada.
- Turma deve ser compatível com as especialidades do instrutor.

### Aula experimental — proposta

- **Uma aula experimental gratuita por pessoa e modalidade**, sujeita à disponibilidade e autorização administrativa.
- Duração igual à aula regular da turma.
- Não exigir cobrança, desde que a modalidade permita experimentais.
- Menores exigem autorização do responsável quando aplicável.
- Registrar a participação separadamente; conversão para matrícula regular não presume pagamento.

### Chamada — regras de 2026 já confirmadas

- Marcação: **presença/falta**.
- Elegibilidade conferida na data da aula.
- Nova chamada somente **na data atual**, sem criação retroativa.
- Permitir conclusão com **todos ausentes** ou **sem participantes elegíveis**.
- Correção apenas das marcações existentes de chamada concluída, com motivo, autorização e trilha de auditoria; não criar participantes históricos por correção.
- Instrutor atua somente em aula própria ou especificamente atribuída; revalidar autorização e lista antes de salvar.

### Reposição e cancelamento — proposta

- Reposição deve ser nova ocorrência vinculada à aula original, com data, horário, instrutor e justificativa.
- Aula cancelada não é considerada falta nem entra no cálculo regular de frequência.
- Evitar sobrescrever aulas concluídas ou recalcular presenças passadas.
- Respeitar conflito de agenda e capacidade na reposição.

## DN-016, DN-017, DN-018 e DN-019 — Repasses e indicadores

### Repasse — proposta

- **Não adotar um percentual único global.** Criar regra parametrizável por contrato, instrutor, modalidade e período.
- Fórmula-base quando pactuado repasse percentual: **repasse = base elegível × percentual contratado**.
- Base elegível considera a receita contratual efetivamente recebida e atribuível ao período; taxas de matrícula e receitas extras ficam fora por padrão.
- Descontos, bolsas e estornos reduzem a base conforme a política pactuada; bolsa integral gera base zero, salvo remuneração fixa/garantia contratual.
- Contratos pagos antecipadamente exigem critério de apropriação por período, sem atribuir receita de meses futuros a um mês único de prestação.
- Substituição de instrutor exige atribuição rastreável das aulas e cálculo segundo o acordo de cada profissional.
- Fechamento mensal, aprovação pela Coordenação e reabertura somente auditada.

### Indicadores financeiros — proposta

Apresentar **regime de caixa e regime de competência**, claramente identificados, sem misturar seus totais.

- **Caixa:** entradas/devoluções conforme a data do movimento financeiro.
- **Competência:** valores atribuídos ao período de prestação do serviço, mesmo que recebidos em outra data.
- Separar valor contratado, previsto, recebido, a receber, vencido, descontos, estornos, taxas e mensalidades.
- Mostrar valores brutos e líquidos, período e critérios utilizados.
- Cálculos monetários com `Decimal`/centavos, arredondamento consistente e conciliação.

### Frequência e evasão — proposta

- **Frequência (%) = presenças ÷ (presenças + faltas) × 100** nas aulas efetivamente realizadas e aplicáveis à matrícula.
- Excluir aulas canceladas; indicadores experimentais devem ser separados.
- Visualizar janelas de **30 e 90 dias** e alertar após **três faltas consecutivas**.
- **Evasão:** proporção de matrículas encerradas antecipadamente em relação às matrículas ativas no início do período; contratos concluídos normalmente são classificados separadamente.
- Períodos, metas e limiares devem ser parametrizáveis e explicitados nos relatórios.

### Conversão e ocupação — proposta

- **Conversão de leads em alunos (%) = leads da coorte convertidos em pessoa/aluno ÷ leads da coorte × 100**.
- **Conversão em matrícula** é indicador separado, contabilizando os leads que produziram contratação.
- **Ocupação (%) = matrículas regulares ativas da turma ÷ capacidade cadastrada × 100**.
- Experimentais são mostrados em indicador próprio de uso temporário de vagas, não ocupação contratual regular.
- Lista de espera não compõe ocupação efetiva.
- Definir coortes e períodos de forma visível para evitar denominadores inconsistentes.

## DN-020, DN-021 e DN-022 — Dados, comunicação, histórico e operação

### Acesso a dados e comunicação — proposta

| Perfil | Acesso recomendado |
|---|---|
| Secretaria | Cadastro, contato, responsáveis e dados necessários ao atendimento e à matrícula |
| Coordenação | Dados administrativos e acadêmicos e acesso sensível estritamente justificado e autorizado |
| Instrutor | Identificação e informações essenciais para conduzir com segurança suas turmas e aulas |
| Comunicação | Dados de contato comercial autorizados e métricas comerciais; sem dados médicos |
| Responsável | Somente dados de menores sob sua responsabilidade, caso seja criado portal específico |

- Informações médicas exigem finalidade concreta, acesso separado, necessidade comprovada, proteção reforçada e registro de acesso quando apropriado.
- **WhatsApp manual com revisão e confirmação explícita de envio** já foi escolhido. Abrir link não significa envio/entrega/leitura.
- E-mail pode atender comunicações administrativas e notificações autorizadas.
- Registrar preferências de contato e finalidades. Não habilitar disparos automáticos sem regras e bases adequadas.
- Definir retenção por categoria e obrigação legal: como proposta, revisar contatos comerciais inativos após **12 meses**, enquanto dados contratuais/financeiros seguem prazos específicos a serem validados juridicamente.
- Antes do uso de dados pessoais reais, submeter política de privacidade, acesso, retenção e atendimento a titulares à validação institucional/jurídica.

### Arquivamento e transferência — proposta

- Arquivar pessoa ou turma **não apaga** histórico de cobranças, pagamentos, frequência, contrato e auditoria.
- Transferência entre turmas/modalidades registra origem, destino e data de efeito.
- Preferir novo vínculo ou evento histórico ao recálculo retroativo dos vínculos antigos.
- Não alterar silenciosamente frequência ou valores anteriores à transferência.

### Capacidade operacional — metas iniciais de projeto (não verificadas)

| Indicador | Meta proposta |
|---|---|
| Unidades atendidas | 1 inicialmente, com expansão futura |
| Pessoas cadastradas | 5.000 inicialmente |
| Usuários simultâneos | 50 |
| Disponibilidade | 99,5% ao mês |
| Consultas principais | p95 de até 2 segundos sob carga homologada |
| Backup | Backup completo diário **e** mecanismo adicional que assegure o RPO |
| RPO | Até 4 horas de dados perdidos |
| RTO | Até 8 horas para restaurar o serviço |
| Exercício de recuperação | Mensal |

**Nota:** backup diário isolado **não** garante RPO de 4 horas. Será preciso usar backups incrementais, arquivamento de logs/WAL ou estratégia equivalente e testar a restauração.

---

## Plano de implementação

1. **Registrar e homologar decisões:** atualizar a matriz DN com regra, exceção, responsável, data, exemplos e testes de aceite. Marcar separadamente confirmado, proposto, aprovado, implementado e homologado.
2. **Acesso e identidade (DN-001–003):** diferenciar permissões, controlar contas/funções, aplicar unicidade de CPF e resolver conversões ambíguas sem perda de histórico.
3. **Configuração financeira via site (DN-004–011):** criar entidades versionadas para planos/tabelas/preços/taxas/parcelamentos/vencimentos/descontos/bolsas/inadimplência; construir telas administrativas; migrar regras de 2026 do código para parâmetros; preservar snapshots dos contratos existentes; implementar pagamento parcial, ajustes, suspensão/cancelamento e renovação.
4. **Operação acadêmica (DN-012–015):** capacidade, lista de espera, experimentais, chamada e correções auditadas, cancelamentos e reposições.
5. **Repasses e indicadores (DN-016–019):** parametrizar contratos de repasse, atribuição a instrutores, estornos e relatórios com fórmulas/denominadores rastreáveis.
6. **Proteção de dados e infraestrutura (DN-020–022):** controlar acesso a dados sensíveis, retenção e canais; preservar histórico em arquivamentos/transferências; testar carga, backups e recuperação.
7. **Validação integrada:** testar regra e permissão por perfil, migrações não destrutivas, concorrência, idempotência, contratos legados, valores em centavos e cenários de bloqueio. Homologar por fluxo antes de declarar a funcionalidade concluída.

### Ordem de prioridade sugerida

1. Parametrização financeira no site, com tabelas versionadas e preservação dos contratos de 2026.
2. Elegibilidade financeira, pagamento parcial, descontos/bolsas e cobrança ausente.
3. Suspensão, cancelamento, ajustes financeiros e renovação.
4. Controle de acesso e dados sensíveis, caso ainda não estejam adequados ao perfil de operação.
5. Agenda, experimentais, lista de espera e reposições.
6. Indicadores, repasses e metas operacionais.

## Critérios globais de aceite

- A Coordenação consegue **alterar pelo site** as regras usuais de planos, cobranças e descontos, sem editar código, SQL ou arquivos de configuração e sem deploy.
- Parâmetros são persistidos, versionados, autorizados e auditados; o sistema informa quando cada versão passa a valer.
- Contratos e cobranças existentes preservam seus valores originais, salvo alteração formal autorizada e registrada.
- Geração de obrigações é idempotente e pagamentos têm saldo correto, inclusive nas condições excepcionais aprovadas.
- Elegibilidade é calculada de modo consistente conforme vigência, pagamento, situação administrativa e regra vigente do próprio contrato.
- Nenhuma operação crítica pode ser executada por perfil não autorizado, inclusive por chamadas diretas à API.
- Histórico acadêmico/financeiro não desaparece com arquivamento, correção, transferência ou renovação.
- Testes técnicos e homologação do negócio são documentados separadamente.

## Referências do projeto

- [Matriz de decisões (`docs/decisions.md`)](https://github.com/amorimfps1/movi-v2/blob/main/docs/decisions.md)
- [Contratos 2026 (`docs/contracts-2026.md`)](https://github.com/amorimfps1/movi-v2/blob/main/docs/contracts-2026.md)
- [Regras e requisitos de negócio](https://github.com/amorimfps1/movi-v2/blob/main/MOVI_Regras_de_Negocio_e_Requisitos.md)
- [Progresso (`docs/progress.md`)](https://github.com/amorimfps1/movi-v2/blob/main/docs/progress.md)

**Situação final:** este documento reúne as respostas e as propostas para aprovação. A implementação atual do repositório **ainda não oferece toda a parametrização financeira pela interface**: em particular, o arquivo `backend/billing/contracts.py` contém preços e condições de 2026 definidos no código, que deverão migrar para configuração persistida e administrável pelo site.
