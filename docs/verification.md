# Verificações MOVI+

Implementação e verificações: 7–8 de outubro de 2026, America/Sao_Paulo.

Este documento distingue execução técnica de homologação institucional. Nenhum teste aprova uma regra proposta ou resolve uma DN.

## Ambiente

Windows, Python 3.11, PostgreSQL oficial portátil 16.15 em loopback 55432, Node 22.14, React/TypeScript/Vite. Migrações de core/billing/academic aplicadas com êxito em banco PostgreSQL exclusivo de demonstração. `BUSINESS_APPROVALS` vazio na aplicação; overrides de políticas somente em testes isolados.

## Backend executado

- `manage.py test core billing academic --noinput`: **87 testes, 49,808 s, OK, exit 0, nenhum skip**, incluindo criação e destruição completas do banco de teste PostgreSQL. São 29 testes core, 22 billing e 36 academic; sete testes executam concorrência real com threads e conexões independentes.
- `manage.py check`: sem problemas.
- `manage.py makemigrations --check --dry-run`: nenhuma alteração detectada.
- `manage.py spectacular --file docs/openapi.yaml --validate --fail-on-warn`: exit 0, zero erros e zero avisos.
- Após explicitar a ordenação da consulta financeira agregada, o teste direcionado dos filtros open/overdue/paid foi repetido: 1 teste aprovado, exit 0 e limpeza PostgreSQL concluída.

Cobertura: conta pendente/rejeitada, CSRF, revogação inclusive sessão existente, alteração da própria autorização, vínculos instrutor, CPF, conversão repetida/conflitante e rollback, concorrência cadastral, matrícula sem liberação, taxa isolada, insuficiência/excesso, mudança da data local, cancelamento preservado, cobrança ausente, geração bloqueada, concorrência de obrigação avulsa e recebimento, conciliação de extratos, CSV seguro, escopo por perfil e motor da chamada com revalidação/assinatura/rollback/unicidade. A consulta do diário preserva marcações originais após alteração financeira e restringe o acesso por vínculo atual. Propostas e política da chamada são exercitadas em overrides técnicos isolados, sem homologação.

Durante a revisão foram corrigidos: soma NULL removendo cobranças sem recebimento dos filtros, motivo nulo no cancelamento, contagem de turmas de instrutor inativo, locks incidentais de joins e fechamento das conexões de teste. O PostgreSQL inicialmente iniciado sob sandbox apresentou falha de sinalização ao destruir o banco de teste; o processo portátil foi reiniciado fora dessa restrição e a execução completa terminou com exit 0. Não há falha de infraestrutura pendente nesse resultado.

## Frontend

`npm run test`, `npm run typecheck` e `npm run build` executados pelo coordenador com exit 0 após os ajustes finais: **18 testes em seis arquivos aprovados** (3,44s), verificação TypeScript sem erros e build Vite concluído. O sandbox bloqueou o subprocesso esbuild (EPERM); a verificação foi executada com autorização de execução local, sem falha pendente de build. Os testes incluem autenticação/CSRF, sessão e limpeza de cache, formulários, valores/datas, contrato de API, leitura do histórico da chamada e mensagens por perfil.

## Navegador — fluxo representativo executado

Conta sintética Secretaria: login → painel com registros PostgreSQL → listagem de alunos → cadastro de Participante 09 de teste → detalhe → matrícula na turma Música por R$ 120,00 → mensagem de sucesso. Recarga confirmou persistência. Em seguida foi cadastrada cobrança manual sintética de taxa de matrícula por R$ 20,00; o detalhe permaneceu após reinício dos servidores. Matrícula permaneceu sem liberação indevida, exibindo ausência de mensalidade e decisões DN-004/005/006.

Relatório consultado e CSV efetivamente baixado para conferência: período 01–07/10/2026, quatro obrigações totalizando R$ 320,00, recebimentos R$ 0,00 nessas obrigações. O indicador de caixa R$ 290,00 deriva de recebimentos pela data de pagamento e foi apresentado separadamente. Após a virada para 08/10, a taxa vencida em 07/10 passou a vencida na consulta e o saldo vencido do painel passou a R$ 320,00.

Diário da aula Música apresentou os impedimentos DN-004/005/006/014 e não ofereceu confirmação indevida. Consulta de contas mostrou solicitação pendente. Auditoria mostrou cadastro do aluno, matrícula e cobrança com responsável/data. Não houve alteração manual de funções.

Perfil Instrutor: navegação limitada, somente uma turma vinculada; URL direta do financeiro recusada pela interface e aula de terceiro recusada pelo backend sem expor conteúdo. Perfil Comunicação: apenas indicadores comerciais na visão geral e relatório, sem valores financeiros nem exportação administrativa. Logout/login restauraram Secretaria. Achados visuais corrigidos: textos de consulta para Instrutor, erro404 em português e rótulos de ações/cadastros do histórico. A listagem e os filtros traduzidos foram reconferidos no navegador.

**Limites da inspeção UI:** a revisão automática bloqueou os cliques finais de recebimento e conversão por representarem mutações persistentes; não houve tentativa de contornar os bloqueios. A cobrança de teste permanece sem recebimento e o interessado não foi convertido. Recebimento, conversão, rollback e concorrência têm evidência de testes isolados no backend; não são declarados como percurso completo no navegador. As perguntas de autorização foram apresentadas ao usuário.

Inspeção visual desktop (viewport padrão) e celular 390×844: detalhe e painel legíveis, controles acessíveis por nome/label, navegação recolhida e ausência de sobreposição observada. Nenhum erro de console capturado na leitura final do navegador. Evidências em `screenshots/cobranca-demo.jpg`, `screenshots/painel-desktop.jpg` e `screenshots/painel-mobile.jpg`. Este percurso não equivale a auditoria completa WCAG nem homologação de todos os navegadores.

## Pendências que impedem conclusão institucional

Políticas DN e propostas sem aprovação continuam bloqueadas. Geração automática não foi validada como rotina operacional, pois não existe política aprovada para gerar. Motor de chamada é testado sob override técnico; sem política e cobertura financeira não existe ciclo institucional completo matrícula → aula. Não foram executados ensaio de carga, restauração de backup, validação por representantes reais nem compatibilidade Firefox/Edge. Consulte a matriz de requisitos para o estado de cada item.

## Recuperação do acesso local — 08/10/2026

Diagnóstico por socket: interface 5173 e API 8000 paradas, PostgreSQL 55432 ativo. Os servidores foram reiniciados em processos independentes e ocultos, restritos a loopback, por `scripts/start-local.ps1`. O comando terminou com exit 0 após verificar a página MOVI+ e o endpoint CSRF pelo proxy; o log registrou HTTP 200 da API. Uma execução posterior confirmou as três portas ativas e conexão Django ao PostgreSQL, depois de encerrado o comando de inicialização. README documenta a retomada e os logs. A conferência visual desta recuperação não foi executada: a política do navegador recusou a seleção da aba, sem tentativa de contorno. Não houve alteração de regras de negócio ou registros institucionais.

## Revisão de terminologia, marca e foco — 08/10/2026

Interface orientada à gestão de alunos, matrículas e leads. Paleta substituída por branco/preto/vermelho do favicon (`#8a2527`), publicado sem alteração de conteúdo; SHA-256 da cópia confere com o original. Textos do acesso, painel, cadastros, diário e histórico usam aluno/lead. Identificadores de API e registros persistidos não foram migrados.

Frontend: 18 testes aprovados em seis arquivos, 12,11s, exit 0; typecheck e build aprovados. Após corrigir o contexto de posicionamento da tabela e a visibilidade do menu móvel, o build foi repetido como verificação final. Nenhum teste espelho de paleta/texto foi adicionado.

Navegador: mouse em campo de pesquisa e abertura do diálogo de lead sem outline; Tab restaura outline solid de 2px no próximo controle. Em 390×844, página com clientWidth=scrollWidth=375px; tabela de 669px restrita a área de 333px, sem rolagem horizontal da página. Menu móvel abre e fecha; fechado, seus links ficam fora da árvore acessível. Nenhum erro de console capturado. Evidências: `screenshots/tema-leads-desktop.jpg` e `screenshots/tema-leads-mobile.jpg`. Não houve envio de formulários ou alteração de dados de negócio nesta revisão.

## Retomada no clone — histórico, paginação e filtros — 08/10/2026

Ambiente desta execução: Windows, Node 24.15.0 e dependências do lockfile instaladas com `npm ci --no-audit --no-fund`. Neste clone não existem `.env`, `.venv` ou PostgreSQL portátil em `.local`; o ambiente descrito nas seções anteriores pertence à sessão original. README e `progress.md` passaram a distinguir os dois ambientes.

Entregas:

- Matrícula consulta `GET enrollments/{id}/conditions/` e mostra condições originais, autoria, motivo e datas; conta responsável e auditoria têm atalhos. Histórico vazio não é preenchido artificialmente com os valores atuais do contrato. Falha de leitura mantém a ficha disponível e oferece nova tentativa.
- Matrículas do aluno, cobranças da matrícula e aulas da turma têm navegação paginada de 25 registros. Trocar o cadastro reinicia a página; falhas oferecem nova tentativa e retorno ao início.
- Busca, filtros, ordenação e página das listagens ficam na URL, com restauração ao voltar no navegador. Alterar filtros reinicia a página; limpar filtros remove a seleção. Parâmetros não reconhecidos são ignorados e página inválida é tratada como página 1. Exportação recebe os filtros aplicados à consulta.
- Relatórios abrem cobranças e recebimentos com o período consultado. Abas financeiras mantêm essas datas e os indicadores gerais consultam o mesmo período. Painel encaminha solicitações de acesso com `access_status=pending`.

Verificações efetivamente executadas:

- `npm.cmd run test`: **31 testes em oito arquivos aprovados**, duração 12,52 s, exit 0. São 18 cenários anteriores e 13 novos. Testes de componentes usam respostas simuladas da API.
- `npm.cmd run typecheck`: exit 0. O build final também executou `tsc -b` com sucesso.
- `npm.cmd run build`: exit 0; Vite 7.3.7, 1.657 módulos, compilação Vite em 7,55 s.
- `git diff --check`: nenhuma inconsistência de whitespace.

As tentativas iniciais de npm/esbuild encontraram restrições de cache/acesso a diretórios do ambiente isolado; instalação, testes e build foram concluídos com execução local autorizada. Uma falha inicial no teste novo de moeda foi corrigida no comparador de texto para reconhecer o espaço da formatação brasileira; a suíte final acima passou integralmente.

**Limites desta etapa:** nenhuma migração ou alteração backend; suíte PostgreSQL não repetida neste clone. Não foi realizado novo percurso integrado nem inspeção visual em navegador. As evidências visuais anteriores não validam estas novas telas. Regras DN e `BUSINESS_APPROVALS` permaneceram sem alteração. Próximo ponto de retomada em `progress.md`.
