# Contratos e chamada — implementação de 03/11/2026

## Diagnóstico e fonte

Fonte: `promptimpmodalidades.md` e respostas do usuário nesta conversa. A planilha XLSX não foi encontrada no repositório. Somente os valores transcritos no prompt foram usados, sem alegar conferência da aba original.

Já existiam matrículas, condições comerciais, cobranças, pagamentos, aulas, presença, auditoria, permissões, locks e snapshots assinados da chamada. Foram estendidos com vigência, parcelamento, categoria/associação, geração, renovação, correção de chamada e comunicação, preservando registros legados.

## Regras confirmadas

- Valores são **totais contratuais**, substituindo a interpretação de mensalidade de outubro para contratos novos. Trimestral: 3 meses, 1/2/3 parcelas. Anual: 12 meses, 3/6/10/12 parcelas.
- Tabela de cartão 2026, categorias 1–6. Categoria e tipo de taxa são configurados explicitamente na modalidade; não há associação automática por nome. Karatê, boleto, anos seguintes e configurações ausentes são recusados sem criar obrigações. `default_price` legado não é usado nos novos contratos.
- Taxa separada: convencional 25/35 reais; Ginástica Rítmica 35/70 reais, associado/não associado respectivamente.
- Matrícula e parcelas do período são criadas atomicamente. Snapshot guarda datas/valores originais; geração usa chave única por obrigação e locks. Regularização gera ausentes sem duplicar; divergências exigem revisão, sem mudança silenciosa.
- Ativação exige **primeira parcela e taxa pagas**, confirmado pelo usuário. Futuras ainda não vencidas não bloqueiam; vencidas, ausentes/divergentes, cancelamento e expiração impedem liberação. Pagar atrasado não muda a vigência nem paga outras obrigações.
- Renovação explícita cria matrícula vinculada, com início após o fim anterior e **sem nova taxa**, confirmado pelo usuário. Não altera dívidas/histórico anteriores nem renova automaticamente. Novo ano exige nova tabela.
- Nova chamada somente hoje; zero presentes e lista vazia permitidos. Bloqueados continuam identificados. Instrutor mantém restrição de turma/aula no backend.
- Correção somente de marcações existentes em chamada concluída, com motivo e autorização revalidada. Auditoria guarda antes/depois, autor e horário. Não cria chamada retroativa nem acrescenta participantes históricos.
- **WhatsApp com revisão/envio manual**, escolhido pelo usuário. Guarda destinatário, telefone, texto, autor e data. Abrir link não marca envio; confirmação explícita registra quem declarou envio e quando, sem alegar entrega/leitura. Nenhuma mensagem foi enviada nos testes.

## Provisório e convenções técnicas

Vencimentos sujeitos a validação: primeira cobrança dia 15 para matrícula até dia 15, ou último dia do mês após dia 15. Demais parcelas mensais no dia original, ajustando meses curtos sem perder referência. Regularização conserva vencimentos, inclusive já passados.

Vigência: início inclusivo e fim no dia anterior ao aniversário de 3/12 meses, ajustando aniversário inexistente ao último dia válido. Conferir essa convenção no instrumento contratual. Parcelas calculadas em centavos inteiros/Decimal, resto distribuído nas primeiras parcelas, soma exata e diferença máxima de um centavo; sem float. Pagamento considerado pela data `paid_on` até a data consultada.

## Arquivos e migrations

- Novo `backend/billing/contracts.py`: tabela, datas, cronograma, geração e autorização.
- Billing `models.py`, `serializers.py`, `views.py`, `services.py`: contrato, renovação, regularização, recebimento idempotente e mensagens.
- Core `models.py`, `serializers.py`: categoria e taxa. Academic `services.py`, `serializers.py`, `views.py`: chamada vazia e correção.
- Frontend `schema.tsx`, `forms.tsx`, `EnrollmentDetail.tsx`, `Academic.tsx`, `Finance.tsx`, novo `CollectionMessages.tsx`, `format.ts`: formulários e ações. `vite.config.ts`: alvo de API isolado via `MOVI_API_TARGET`.
- Novo `backend/billing/test_contracts.py`; testes financeiros, acadêmicos e de formulário ajustados às regras substituídas.

Migrations: `core/0002_modality_enrollment_fee_kind_modality_price_category`, `billing/0003_enrollment_associated_enrollment_contract_version_and_more`, `billing/0004_collectionmessage`. Aplicadas somente ao banco demo nesta etapa. Matrículas anteriores continuam versão 0 sem conversão artificial; API exige contrato parametrizado para novas matrículas. Nenhum DELETE público adicionado.

## API

- Modalidade: `price_category` (1–7/nulo), `enrollment_fee_kind` (`standard`/`rhythmic`/vazio pendente).
- `POST enrollments/`: aluno, turma, início, plano, `associated`, `payment_method`, `installments`; servidor calcula total e devolve `contract_version`, `end_date`, `fee_amount`, `schedule`.
- `POST enrollments/{id}/repair_charges/`: gera ausentes do snapshot. `POST enrollments/{id}/renew/`: novos parâmetros, mantém aluno/turma; repetição retorna renovação existente.
- `POST charges/{id}/receive/`: baixa integral; repetição idêntica em contrato novo retorna pagamento original, divergência recusada.
- `GET/POST charges/{id}/messages/`: histórico/preparo com `recipient`, `phone` internacional só dígitos. `POST charges/{id}/confirm_message/` recebe `message` para confirmar envio manual.
- `POST lessons/{id}/correct_attendance/`: `marks` e `reason`, mesmos locks/permissões do diário.

## Pendências

Conferir XLSX, mapear modalidades e validar vencimentos provisórios. Karatê/parcelamento atípico, boleto e tabelas seguintes ficam indisponíveis. Mensal legado permanece no histórico. Bolsa, desconto, parcial/estorno, suspensão, transferência e repasse não foram definidos pelo prompt.

Resultados executados em `verification.md`. Este documento substitui os bloqueios históricos de decisões/requisitos/contrato apenas nos pontos expressamente cobertos acima.
