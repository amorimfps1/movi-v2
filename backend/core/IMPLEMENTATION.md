# Núcleo administrativo

Implementação de `core`, conforme `docs/CONTRACT.md` e documento integral de requisitos. Não representa homologação institucional.

## Arquivos

- `models.py` e `migrations/`: usuário, aluno, interessado, modalidade, instrutor, turma, auditoria e mutex técnico de identidades.
- `permissions.py`: `IsInternal`, `IsAdministrative`, `is_administrative(user)`; toda requisição interna relê a autorização atual do banco.
- `audit.py`: helper contratual `record(actor, action, target, reason='', metadata=None)`.
- `serializers.py`, `views.py`, `urls.py`: API administrativa, sessão com proteção CSRF explícita, busca, filtros, ordenação e paginação limitada a 100 registros.
- `services.py`: decisões de acesso e conversão transacionais.
- `tests/test_core.py`: testes de autorização, CPF, conversão, CSRF, histórico, rollback e concorrência PostgreSQL.

## Regras implementadas

RN-001–012: solicitação pendente; aprovação administrativa com funções válidas; rejeição motivada; última função removida devolve conta a pendente; atribuição distinta de função aprova; alteração própria impedida; auditoria atômica; instrutor exige vínculo único e ativo. E-mail de usuário único sem distinguir caixa. CPF opcional com dígitos verificadores e normalização.

RN-014 e RN-017: conversão procura CPF e e-mail, reaproveita correspondência inequívoca, é idempotente e não cria matrícula. Identidade com vários candidatos exige escolha explícita dentre as correspondências e motivo auditado; nenhum aluno é escolhido arbitrariamente. A conversão permanece bloqueada enquanto não houver aprovação RN-016, porque o vínculo preservado foi classificado como Proposta.

RN-020–024: vínculos protegidos entre turma, modalidade e instrutor; especialidades reais M2M; horários válidos; instrutor consulta somente turmas próprias e não consegue alterar atribuição. Aulas substitutas são tratadas em `academic` e não expandem acesso a uma turma inteira.

RF-029 e RF-032: listas paginadas, filtros declarados, pesquisa, ordenação e auditoria somente leitura para Secretaria/Coordenação. DELETE físico não é exposto; FKs preservam histórico.

## Aprovações e pendências

- `BUSINESS_APPROVALS` permanece vazio por padrão. RN-013 ativa a prevenção de CPF duplicado nos escritores da API sob mutex global no banco. Sem aprovação, não se afirma que esta proposta é uma regra vigente.
- RN-016 libera o fluxo de conversão. Conflitos são exibidos como 409 com `detail` e `decisions` (RN-015/DN-003), sem presumir prioridade entre CPF e e-mail. A resolução exige `student_id` e `reason`.
- RN-019 libera arquivamento. Reabrir aluno arquivado permanece condicionado a DN-021, pois efeito sobre matrículas e histórico não foi definido.
- Comunicação não possui CRUD de interessados: acesso proposto permanece ausente. Indicadores comerciais Base são responsabilidade do módulo de relatórios.
- Dados médicos e responsáveis não possuem campos ou endpoints enquanto DN-020 está pendente. A API não automatiza comunicação.
- Capacidade, choque de agenda e compatibilidade de especialidade aguardam DN-012; não se inventam exceções ou políticas.
- Aprovar substitui funções; adicionar função é ação distinta. Segunda aprovação de solicitação já decidida retorna 409 DN-002. Reabertura de interessado não convertido e reversão de conversão permanecem bloqueadas até decisão institucional.

## Concorrência e preservação

Escritores relêem autorização dentro de transação após lock do(s) User(s), ordenados por PK. Mudanças cadastrais adquirem lock do registro antes de validar e salvar, para preservar PATCH concorrente em campos distintos. Atribuição/alteração de turma bloqueia ClassGroup. Atualização de instrutor bloqueia suas ClassGroups antes do cadastro profissional; `Instructor.user` é somente leitura no CRUD e só é atribuído sob lock de User nas ações de acesso.

Mutações de alunos adquirem `OperationLock('student-identities')`, depois ClassGroups de suas matrículas em ordem PK e depois Student. Conversão usa o mesmo mutex antes de verificar correspondências, bloqueia Lead e Student e grava vínculo/status/auditoria na mesma transação. Criação de matrícula também deve adquirir esse mutex antes de ClassGroup e revalidar arquivamento, para impedir corrida com arquivamento do aluno.

O mutex impede duplicação CPF em escritores API após aprovação da RN-013, inclusive ausência de linha inicial. A rotina não alega existir unicidade condicional no banco para escritas manuais SQL/ORM: tais escritas devem utilizar o mesmo serviço/mutex, ou uma migração de constraint deve ser aprovada após saneamento da base. PostgreSQL é necessário para validar a garantia de locks; SQLite é apenas fallback explícito de teste funcional.

Falhas no histórico fazem rollback da ação crítica. Conversão repetida não duplica evento nem aluno. Alteração posterior de dados pessoais não apaga eventos. Remoção/rejeição de autorização invalida próximas requisições protegidas de sessões existentes, sem depender de expiração do cookie.

## Verificação

Executar `.venv/Scripts/python.exe backend/manage.py test core --noinput` com ambiente de desenvolvimento configurado. Os testes concorrentes usam conexões independentes e são explicitamente pulados quando o backend não é PostgreSQL. A execução real e seu resultado devem constar no relatório final da integração; não tratar skip SQLite como validação concorrente.

Em 7 de outubro de 2026, a execução coordenada da suíte completa em PostgreSQL 16.15 terminou com **81 testes aprovados em 48,259 segundos, exit code 0, nenhum skip e banco de teste removido corretamente**: core 29, billing 22 e academic 30. Os sete cenários concorrentes da integração foram executados em conexões PostgreSQL independentes; quatro pertencem a core (CPF simultâneo, conversão simultânea, aprovação simultânea e PATCH concorrente). O fechamento explícito `connections.close_all()` nos workers foi validado pelo teardown bem-sucedido.

Também foram executados `manage.py check` (nenhum problema) e `makemigrations core --check --dry-run` (nenhuma alteração pendente). O schema de core recebeu anotações explícitas para autenticação e ações administrativas; o coordenador validou o schema integrado. A revisão independente de billing/config encontrou e encaminhou três defeitos concretos, corrigidos e incluídos na verificação final: filtro de cobranças sem pagamentos usando SUM nulo, motivo nulo/objeto aceito no cancelamento e contagem de turmas de instrutor inativo.
