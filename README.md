# MOVI+

Aplicação de gestão de alunos, matrículas e leads em React/TypeScript, Django REST Framework e PostgreSQL. Interface em português, tema branco/preto/vermelho conforme a marca, valores em reais e datas civis em `America/Sao_Paulo`.

**Estado:** núcleo cadastral e financeiro avulso integrado; operação definitiva e homologação dependem das decisões institucionais listadas em [docs/decisions.md](docs/decisions.md). As políticas pendentes aparecem na aplicação e retornam HTTP 409 quando impedem uma ação. Uma aprovação configurada por ID não inventa o conteúdo de uma política.

## Executar localmente

Requer Python 3.11+, Node 22.12+ e PostgreSQL 16 (ou Docker para o banco). Os comandos abaixo usam PowerShell na raiz do projeto.

```powershell
Copy-Item .env.example .env
# Edite .env e defina SECRET_KEY. Não use valores de desenvolvimento em produção.
docker compose up -d db
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.lock.txt
.\.venv\Scripts\python.exe backend\manage.py migrate
.\.venv\Scripts\python.exe backend\manage.py createsuperuser
.\.venv\Scripts\python.exe backend\manage.py runserver 127.0.0.1:8000
```

Em outro terminal:

```powershell
Set-Location frontend
npm ci
npm run dev
```

Abra [MOVI+ local](http://127.0.0.1:5173). O Vite encaminha `/api/` ao Django. A sessão usa cookie HttpOnly; mutações usam token CSRF, incluindo entrada e solicitação de acesso. A conta inicial criada com `createsuperuser` recebe Coordenação para inicializar a operação. Contas solicitadas pela interface ficam pendentes até aprovação.

Se já possui PostgreSQL, crie banco e usuário e ajuste `DATABASE_URL`; Docker é opcional. `compose.yaml` contém somente o banco e um volume persistente. Comandos de recriação/apagamento de volume não fazem parte da inicialização.

## Ambiente preparado nesta sessão

Foi preparado PostgreSQL portátil oficial em `.local/postgresql-win/pgsql`, com cluster **exclusivo de demonstração** em `.local/pgdata`, escutando apenas `127.0.0.1:55432`. `.env` local aponta a esse banco e habilita `DEMO_MODE=true`; esses arquivos são ignorados pelo Git. Os binários não são parte do código distribuído. A alternativa reproduzível normal é Docker ou instalação PostgreSQL própria.

Com o banco ativo e as dependências instaladas, este comando inicia a interface e a API em segundo plano, sem depender de manter os terminais abertos:

```powershell
powershell -NoProfile -File .\scripts\start-local.ps1
```

O comando verifica a resposta da página e da API pelo proxy, reutiliza as portas já ativas e grava logs em `.local/backend.*.log` e `.local/frontend.*.log`. Os serviços ficam restritos a `127.0.0.1`. Execute novamente após reiniciar o computador; não há inicialização automática com o Windows. Se o PostgreSQL estiver parado, inicie-o antes conforme abaixo.

Se o cluster local desta sessão estiver parado:

```powershell
& '.\.local\postgresql-win\pgsql\bin\pg_ctl.exe' -D '.local\pgdata' -l '.local\postgres.log' -o '-p 55432 -h 127.0.0.1' start
```

Para parar somente esse cluster:

```powershell
& '.\.local\postgresql-win\pgsql\bin\pg_ctl.exe' -D '.local\pgdata' stop -m fast
```

## Dados demonstrativos

Em um banco vazio e exclusivo de desenvolvimento, configure `DEBUG=true` e `DEMO_MODE=true` em `.env` e execute:

```powershell
.\.venv\Scripts\python.exe backend\manage.py seed_demo --password 'Movi-demo-2026!'
```

Contas: `secretaria@example.test`, `instrutor@example.test`, `comunicacao@example.test`. Use a senha passada no comando. A conta `solicitante@example.test` demonstra uma solicitação pendente, sem senha utilizável. Nenhum CPF ou dado pessoal real é incluído. Cada registro sintético é identificado e a interface informa o ambiente de demonstração. O comando é idempotente e recusa banco previamente preenchido sem marcador de demonstração. Não habilita propostas nem políticas por conta própria. Cadastros feitos manualmente no ambiente demo persistem nesse banco.

## Verificações

```powershell
.\.venv\Scripts\python.exe backend\manage.py check
.\.venv\Scripts\python.exe backend\manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe backend\manage.py test core billing academic --noinput
.\.venv\Scripts\python.exe backend\manage.py spectacular --file docs\openapi.yaml --validate --fail-on-warn
Set-Location frontend
npm run test
npm run typecheck
npm run build
```

Os testes usam banco separado `test_<nome_do_banco>`; o usuário PostgreSQL precisa da permissão CREATEDB para executá-los. Não use banco de produção para testes. Testes de concorrência exigem PostgreSQL real e são explicitamente pulados no fallback opcional `TEST_SQLITE=1`. Não rode duas suítes simultâneas contra o mesmo banco de teste. A senha MD5 de alguns testes é um otimizador exclusivamente de testes; a aplicação usa os validadores e hashers padrão Django.

Resultados efetivamente executados e limitações estão em [docs/verification.md](docs/verification.md).

## Contratos e rastreabilidade

- [Contrato de integração](docs/CONTRACT.md): recursos, campos, erros, paginação, perfis e responsabilidades.
- [OpenAPI gerado](docs/openapi.yaml), [Swagger local](http://127.0.0.1:8000/api/docs/) e [schema local](http://127.0.0.1:8000/api/schema/).
- [Matriz de requisitos](docs/requirements.md): RN, RF, RNF, UC e CA, com estados e evidências.
- [Decisões pendentes](docs/decisions.md): DN-001 a DN-022 e impactos.
- [Especificação funcional original](MOVI_Regras_de_Negocio_e_Requisitos.md).

## Limites operacionais explícitos

As regras Base foram implementadas como referência do levantamento, sem afirmar aceite institucional. `BUSINESS_APPROVALS` permanece vazio por padrão. RN-013 (CPF único), RN-016 (conversão com vínculo) e RN-019 (arquivamento) possuem mecanismos técnicos testados, mas as operações propostas dependem de aprovação. A unicidade condicional do CPF serializa escritores da API; inserções manuais no ORM não equivalem à API e não possuem constraint CPF incondicional.

Matrícula não comprova pagamento nem participação. Taxa isolada não libera; mensalidade vencida bloqueia em data local; pagamento preserva cancelamento. Mensalidade paga sem política de cobertura retorna elegibilidade indeterminada. Geração automática, vigência definitiva, bolsas, pagamentos parciais/excedentes, estornos, suspensão/trancamento, repasse final, alertas de evasão e comunicação automática permanecem bloqueados conforme suas decisões. Experimental exige política detalhada e não é liberado por um ID de aprovação isolado. Chamada possui motor transacional testado; gravação operacional exige DN-014 e política detalhada, além de elegibilidade definida. As condições comerciais iniciais são preservadas, mas edição com efeito futuro/retroativo depende de política.

Relatórios são extratos descritivos com definições explícitas: recebimentos por data de recebimento e cobranças por vencimento no período. A base e o valor final de repasse ficam indeterminados até DN-016/DN-017; contagens de conversão e matrícula são distintas. Exportações CSV cobrem todos os resultados filtrados e respeitam permissão; campos sensíveis não são incluídos. Dados médicos, retenção institucional e permissões para dados de responsáveis aguardam DN-020.

O diário concluído consulta as marcações originais, preservando presenças mesmo após mudança financeira. A capacidade técnica de gravação é descrita em [docs/decisions.md](docs/decisions.md): `ATTENDANCE_POLICY` deve conter JSON com a política detalhada expressamente aprovada para DN-014; permanece ausente no ambiente demonstrativo. Nenhum ID isolado habilita a chamada.

## Implantação e manutenção

Este projeto inclui ambiente local, sem publicação externa. Antes de operar em produção, a instituição deve homologar regras/perfis e fornecer configuração de hospedagem, domínio/HTTPS, rotinas de backup/restauração e retenção. Defina `DEBUG=false`, segredo aleatório, banco externo, hosts e origens CSRF exatas; cookies seguros são ativados fora de DEBUG. O Django deve ficar atrás do servidor de aplicação/reverse proxy escolhido, com frontend compilado e API no mesmo domínio. Nenhum objetivo de carga, recuperação ou disponibilidade foi presumido (DN-022).

Backup PostgreSQL pode ser feito com `pg_dump` e restaurado em banco separado com `pg_restore`; exercício de recuperação e metas RPO/RTO ainda precisam ser definidos e executados. Não há gateway bancário, portal de aluno, envio de mensagens ou fechamento automático de repasse.
