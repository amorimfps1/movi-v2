# Progresso e ponto de retomada — MOVI+

Este é o ponto de entrada para continuar o desenvolvimento. Requisitos e decisões estão em `requirements.md` e `decisions.md`; evidências de execução estão em `verification.md`.

## Etapa atual — 08/10/2026

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

## Dependências de negócio

As 22 decisões DN continuam pendentes. Para completar matrícula → cobrança → liberação → chamada, definir primeiro DN-004/005/006 (plano, cobertura e geração) e DN-014 (chamada). A instrução de continuar o desenvolvimento não define o conteúdo dessas políticas.

## Como retomar

1. Ler este arquivo e consultar `git status` dentro de `movi-v2/`.
2. Conferir a última seção de `verification.md` para distinguir verificações atuais de evidências anteriores.
3. Continuar pelo próximo passo registrado ao fim da etapa; não ativar políticas pendentes por suposição.

## Próximo passo concreto

1. Preparar backend e PostgreSQL de desenvolvimento neste clone conforme o README: ambiente Python, `.env`, banco local, migrações e dados sintéticos em banco exclusivo de demonstração. O frontend já possui dependências e build; os serviços não foram iniciados nesta etapa.
2. Validar no navegador o histórico comercial, a navegação além de 25 vínculos, o retorno pelo histórico do navegador e relatório → cobranças/recebimentos com o mesmo período; conferir desktop e celular. Executar as verificações backend no ambiente preparado. Os testes desta etapa usam API simulada e não substituem esse percurso integrado.
3. Registrar as definições institucionais de DN-004/005/006 e DN-014 para implementar geração, cobertura e chamada operacionais. Demais decisões permanecem em `decisions.md`.

**Ponto de parada:** código frontend e documentação atualizados; 31 testes e build aprovados; pendente preparação do backend/banco e validação integrada das novas consultas. Não há falha pendente nos testes frontend executados.
