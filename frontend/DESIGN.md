# Direção MOVI+

## Checkpoint — consultas e histórico — 08/10/2026

Histórico das condições comerciais acrescentado à ficha da matrícula com os componentes existentes: seção, lista de definição, datas locais e links para autoria/auditoria. As seções da coluna usam intervalo de 24px e mantêm a paleta e tipografia vigentes. Histórico vazio e erro de consulta possuem mensagens distintas e nova tentativa.

Matrículas do aluno, cobranças da matrícula e encontros da turma usam a paginação compartilhada. Listagens mantêm busca/filtros/página no endereço e oferecem “Limpar filtros”. Relatórios possuem caminhos separados para cobranças e recebimentos no período consultado; abas financeiras preservam as datas. Testes de componentes e build aprovados; inspeção visual destas alterações em navegador ainda pendente conforme `docs/progress.md`.

Direção vigente aprovada pelo usuário em 08/10/2026: sistema de gestão de **alunos, matrículas e leads**, com branco, preto e vermelho da marca em `favicon.ico`. Domínio: cadastro do aluno, lead, matrícula, condição comercial, cobrança, recebimento e chamada. Assinatura: Lead → Aluno → Matrícula → Participação, mantendo a distinção entre cadastro e elegibilidade. A paleta anterior marfim/verde/azul/âmbar foi substituída.

## Checkpoint — revisão de marca e interação

Intent: secretaria e demais perfis consultam alunos e leads e administram matrículas; apresentação objetiva de gestão. Hierarchy: título da rotina, ação principal e informações do vínculo preservam a ordem existente. Palette: branco `#ffffff` nas superfícies, preto `#111111` no texto e na área institucional do acesso, vermelho `#8a2527` extraído do favicon nas ações, links, navegação ativa e impedimentos. Cinzas neutros organizam metadados, controles e estados informativos/confirmados; fundo vermelho suave acompanha avisos. Depth: bordas pretas de baixa opacidade, sem sombras decorativas. Surfaces: branco e cinza neutro inset. Typography: Manrope local e escala existente. Spacing: base 4px, controles 44px, linhas 56px e áreas 24–40px preservados. Evitam-se cores adicionais, linguagem de portal estudantil e contorno de containers ao clicar.

Interação: pointerdown identifica uso de mouse/toque e suprime outlines de clique. Tab e teclas de navegação restauram o indicador vermelho de foco em controles; containers com tabindex=-1 não recebem contorno. Bordas estruturais dos campos permanecem. Favicon original publicado sem alterações em public/favicon.ico.

QA da revisão: navegador confirmou fundo branco e marca `#8a2527`; mouse em campo e abertura de diálogo produzem outline=none; Tab produz foco solid de 2px no botão seguinte. Em 390×844, a rolagem horizontal fica restrita à tabela: clientWidth/scrollWidth da página iguais a 375px, tabela 669px dentro de área 333px. O container da tabela estabelece o contexto para labels acessíveis posicionados; navegação móvel fechada fica invisível e fora da ordem de foco. Menu abre e fecha pela seleção da rotina. Evidências em docs/screenshots/tema-leads-desktop.jpg e tema-leads-mobile.jpg.

## Checkpoint — estrutura, autenticação, painel, alunos, matrícula

Intent: secretaria conduz cadastros e matrículas com clareza. Hierarquia: agenda do dia é foco do painel; nome e vínculo focam o aluno; ação principal única em cada formulário. Palette: branco, preto e vermelho da marca. Depth: bordas sutis, sem elevação decorativa. Surfaces: branco e controles neutros levemente inset. Typography: Manrope local, corpo 14px, escala 14/16/20/28/36, peso e cor separados em quatro níveis. Spacing: base 4px, controles 44px, linhas 56px; seção 32px e área principal 40px.

Componentes compartilhados: Button 44px, radius 8px; Field labels 13px/600; Modal nativo com gestão de foco; Notice com resultado textual e IDs DN; tabela responsiva com overflow restrito à área de dados. Nenhum gráfico ou preenchimento artificial. Layout compacto em mobile com navegação colapsável.

## Checkpoint — fichas, oferta e conversão

Intent: secretaria confere identidade e oferta antes de confirmar vínculos. Hierarchy: nome da ficha e ação de próximo passo; informações estáveis em lista de definição e aulas em agenda. Palette: branco para documentos, preto para informações, vermelho para ação e impedimentos. Depth: somente bordas suaves. Surfaces: branco e controles inset neutros. Typography: mesma escala Manrope, título 28–32px, metadados 10–12px. Spacing: ficha 24px, informação 16px, controle 44px, base 4px. Conversão confirma identidade e informa separação entre aluno, matrícula e participação.

## Checkpoint — financeiro, diário, acesso e relatórios

Intent: registrar apenas recebimentos conferidos, observar elegibilidade e tomar decisões de acesso rastreáveis. Hierarchy: devido/recebido separados no documento financeiro; bloqueio institucional precede marcações do diário; função e vínculo focam o diálogo administrativo; período precede indicadores no relatório. Palette: preto/cinza para confirmação e informação, vermelho da marca para pendências e impedimentos, com ícones e texto identificando cada situação. Depth: bordas suaves e divisões consistentes. Surfaces: nenhuma sombra ou gradiente novo. Typography: valores tabulares em 24–36px, condições 12px e definições 10–11px. Spacing: mesma base 4px, controles 44px, seções 24px, colunas 24px. Relatório separa população comercial, contagem cadastral atual e datas financeiras; não inventa taxas, metas ou repasses.

## Verificação do marco representativo

Coordenador confirmou em navegador real: login administrativo → painel PostgreSQL → criar aluno → detalhe → matrícula → reload com persistência; desktop e viewport mobile 390×844 sem sobreposição. Ajustes decorrentes: identificação demo movida para o Shell e sugestão do valor padrão após selecionar turma. Manrope embutida com subset latin; nenhuma dependência remota de fonte.

Diário concluído consulta marcações originais em GET attendance; nenhuma frequência histórica é recalculada com a elegibilidade atual. Percentuais e alertas continuam condicionados. Navegação por pathname retorna ao início do conteúdo e move foco para o main; sidebar mantém rolagem independente. Sessão revalidada em403 de recursos, sem encerrar uma sessão aprovada por uma recusa operacional; troca de função/usuário e logout descartam cache privado.

QA por perfil: listagens do instrutor usam “SEU DIÁRIO” e descrevem consulta ao escopo autorizado, mantendo hierarquia, paleta, superfícies, Manrope e espaçamento existentes. Erros404 apresentam mensagem neutra em português e preservam a resposta estruturada para tratamento interno.

Histórico: ações e cadastros afetados têm apresentação centralizada em português, abrangendo os 24 códigos de ação e 10 tipos atualmente emitidos pelo backend. Filtros usam rótulos legíveis e preservam os valores técnicos no transporte; pesquisa orienta a consulta pelo motivo registrado. A ficha conserva os dados originais do evento.
