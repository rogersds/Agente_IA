# Checklist de prontidão — primeiro conector read-only real (PREPARAÇÃO)

> **Status:** preparação documental. **Não conectar a sistemas reais sem confirmação explícita de ambiente autorizado.**  
> **Conformidade:** R1 (dado externo é dado), R2/R7 (consultas como propostas/artefatos; execução externa com aprovação humana), R3 (somente nomes de variáveis, nunca valores/segredos), read-only por padrão e fail-safe.

## 1) Inventário de fontes (a confirmar por ambiente autorizado)

| Fonte | Sistema/fornecedor (a confirmar) | Finalidade (read-only) | Proprietário/aprovador | Ambiente autorizado confirmado? (humano) |
|---|---|---|---|---|
| SIEM |  | busca/consulta de eventos e alertas |  | ☐ |
| EDR |  | telemetria de endpoint/host |  | ☐ |
| TI (Threat Intelligence) |  | enriquecimento/lookup de indicadores |  | ☐ |
| CMDB / inventário de ativos |  | contexto de ativos/identidades |  | ☐ |
| Outras (se aplicável) |  |  |  | ☐ |

## 2) Escopo, índices/datasets e janelas (por fonte)

| Fonte | Índices/datasets/escopos permitidos (read-only) | Janela máxima permitida | Limites de volume/resultado | Restrições de dados sensíveis |
|---|---|---|---|---|
| SIEM |  |  |  |  |
| EDR |  |  |  |  |
| TI |  |  |  |  |
| CMDB |  |  |  |  |

- Definir escopo mínimo necessário (least privilege) e janelas explícitas em toda proposta de consulta (R7).
- Proibir consultas sem janela/escopo/custo definidos quando exigido por política/contratos.

## 3) Limites de custo e proteção operacional

| Item | Limite/política | Responsável |
|---|---|---|
| Custo estimado máximo por consulta/proposta |  |  |
| Taxa de requisições (rate limit) |  |  |
| Timeout por requisição (read-only) |  |  |
| Retries limitados (máx. tentativas/backoff) |  |  |
| Comportamento em falha/timeout/indisponibilidade | Fail-safe: sem execução, registrar indisponibilidade, escalar/incerteza conforme R4 |  |
| Horários/janelas operacionais autorizadas |  |  |

## 4) Método de autenticação aprovado e gestão de segredos (apenas nomes de variáveis)

> **Proibido:** valores, tokens, chaves, senhas, certificados privados ou segredos em arquivos, código, logs, issues, commits ou evidências. Configurar valores somente em cofre/ambiente autorizado.

| Fonte | Método de autenticação aprovado (a confirmar) | Nomes de variáveis de ambiente (apenas nomes) | Cofre/gestão aprovada (processo) | Rotação/revogação definida? |
|---|---|---|---|---|
| SIEM |  | `SIEM_BASE_URL` (exemplo de nome), `SIEM_AUTH_TOKEN` / `SIEM_CLIENT_ID` / `SIEM_CLIENT_SECRET` (definir nomes aprovados) |  | ☐ |
| EDR |  | `EDR_BASE_URL`, `EDR_AUTH_TOKEN` / `EDR_CLIENT_ID` / `EDR_CLIENT_SECRET` (definir nomes aprovados) |  | ☐ |
| TI |  | `TI_BASE_URL`, `TI_API_KEY` (definir nomes aprovados) |  | ☐ |
| CMDB |  | `CMDB_BASE_URL`, `CMDB_AUTH_TOKEN` (definir nomes aprovados) |  | ☐ |

- Registrar em configuração apenas referências aos **nomes**; injetar valores em runtime seguro.
- Validar que saídas/logs/trilhas de auditoria não reproduzem credenciais (R3).

## 5) Aprovação, execução externa e rastreabilidade

- [ ] Ambiente/sistemas de destino confirmados como autorizados (humano).
- [ ] Conexões limitadas a operações **read-only**.
- [ ] Consultas reais tratadas como execução externa à proposta: exigem proposta versionável e aprovação humana explícita registrada antes de qualquer execução fora do agente (R2/R7).
- [ ] Trilhas de auditoria append-only habilitadas e sem segredos (R6/R3).
- [ ] Plano de rollback/contingência operacional documentado quando aplicável.

## 6) Critérios de pronto para habilitar um conector real

- [ ] Skeleton do conector passa testes de contrato/guardrail.
- [ ] Testes com sentinelas sintéticas provam ausência de vazamento de segredos (R3).
- [ ] Timeout, retries limitados e fail-safe validados.
- [ ] Aprovação humana e evidências de ambiente autorizado registradas.
- [ ] Quickstart/runbook atualizado com nomes de variáveis (sem valores) e procedimento seguro.

**Responsável pela aprovação final (humano):** ____________________  **Data:** __________  **Registro:** __________
