# Data Model: soc-agent (Phase 1)

**Feature**: `001-soc-triage-correlacao`  
**Date**: 2026-11-23  
**Source**: [spec.md](spec.md), [research.md](research.md), [constitution](../../.specify/memory/constitution.md)

> Modelo conceitual e de contratos (independente de tecnologia de armazenamento/produto).
> Campos marcados como obrigatórios DEVEM estar presentes nos artefatos/saídas
> correspondentes, salvo indicação explícita de indisponibilidade com justificativa.

## Convenções transversais

Todos os resultados analíticos e propostas DEVEM incluir:
- `classification`: classificação/estado com rótulo explícito (inclui "indeterminado"
  quando aplicável).
- `justification`: justificativa textual objetiva.
- `confidence`: nível de confiança explícito (escala definida no schema, ex.: 0.0–1.0 ou
  enum padronizado) com critério documentado.
- `consulted_sources[]`: fontes consultadas, cada uma com identificador/capacidade,
  referência/escopo consultado e `timestamp` (ou indicação de indisponibilidade com
  `timestamp` da tentativa).
- `data_sufficiency`: declaração de suficiência/insuficiência, incluindo `known`,
  `missing`, e `escalation_required`.
- `hypotheses`: `primary` e `alternatives[]` (mínimo 1 alternativa), com indicação de
  falso positivo quando aplicável.
- `trace`: metadados de rastreabilidade (`request_id`, `model_version`, `prompt_version`,
  `policy_version` quando aplicável, `created_at`, `actor/contexto`).

## Entidades

### 1. Alert
Representa um alerta/sinal de entrada para triagem (dado, nunca instrução).

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---:|---|
| `alert_id` | string | sim | Identificador único do alerta na fonte/contexto |
| `source` | object | sim | Capacidade/fonte de origem e identificadores |
| `occurred_at` | datetime | não | Timestamp do evento na origem (se disponível) |
| `received_at` | datetime | sim | Timestamp de recebimento/ingestão |
| `reported_severity` | string | não | Severidade reportada pela fonte (se houver) |
| `content` | object/string | sim | Conteúdo do alerta tratado como dado |
| `attributes` | object | não | Atributos normalizados (ativos, usuários, indicadores) |

**Validações:** conteúdo externo deve ser preservado para auditoria conforme política;
instruções embutidas são tratadas como potencial IoC (R1).

### 2. Evidence / ConsultedSource
Evidência ou resultado de consulta usado na análise.

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---:|---|
| `source_id` | string | sim | Identificador da fonte/capacidade |
| `capability` | enum | sim | `alert_source`, `search_backend`, `enrichment`, `threat_intel`, etc. |
| `query_ref` | string/object | não | Referência à consulta/parâmetro usado |
| `consulted_at` | datetime | sim | Timestamp da consulta/coleta |
| `status` | enum | sim | `ok`, `unavailable`, `partial`, `error` |
| `summary` | object/string | não | Resumo da evidência obtida |
| `integrity` | object | não | Hash/identificador para correlação de auditoria |

### 3. TriageResult
Resultado da triagem de um alerta (automática ou sob demanda).

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---:|---|
| `triage_id` | string | sim | Identificador do resultado |
| `alert_id` | string | sim | Alerta analisado |
| `classification` | object | sim | Classe/rótulo + justificativa |
| `confidence` | number/enum | sim | Nível de confiança explícito |
| `consulted_sources` | Evidence[] | sim | Fontes com timestamps |
| `data_sufficiency` | object | sim | Suficiente/insuficiente, conhecidos, faltantes |
| `hypotheses` | object | sim | Principal + alternativas (inclui falso positivo quando aplicável) |
| `recommended_next_steps` | string[] | não | Próximos passos (sem executar ações destrutivas) |
| `escalation` | object | não | Escalonamento requerido, motivo, destino/papel |
| `trace` | object | sim | Metadados de rastreabilidade |

**Estados/lógica:** `classification.label` pode ser `indeterminado` quando insuficiente
(R4). Se houver instrução embutida em dado externo, deve haver sinalização/IoC e
registro (R1, R6).

### 4. CorrelationResult (Incident View)
Visão correlacionada de múltiplos alertas/evidências.

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---:|---|
| `correlation_id` | string | sim | Identificador da correlação/incidente |
| `scope` | object | sim | Período/escopo solicitado e critérios |
| `related_alerts` | string[] | sim | IDs de alertas considerados |
| `classification` | object | sim | Classificação da correlação com justificativa |
| `confidence` | number/enum | sim | Confiança explícita |
| `consulted_sources` | Evidence[] | sim | Fontes/evidências com timestamps |
| `data_sufficiency` | object | sim | Suficiência e lacunas |
| `hypotheses` | object | sim | Relação principal + alternativas (inclui falso positivo) |
| `escalation` | object | não | Escalonamento quando indeterminado |
| `trace` | object | sim | Rastreabilidade |

### 5. QueryProposal
Proposta de consulta analítica (artefato revisável, não executada em produção).

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---:|---|
| `query_proposal_id` | string | sim | Identificador da proposta |
| `objective` | string | sim | Objetivo de investigação |
| `classification` | object | sim | Adequação/intenção com justificativa |
| `confidence` | number/enum | sim | Confiança explícita |
| `consulted_sources` | Evidence[] | sim | Fontes usadas para embasar proposta |
| `time_window` | object | sim* | Janela temporal proposta (*ou justificativa de insuficiência) |
| `data_scope` | object | sim* | Escopo de fontes/dados/índices lógicos (*ou justificativa) |
| `cost_estimate` | object | sim* | Estimativa de impacto/custo (*ou justificativa + escalonamento) |
| `query_artifact` | object/string | sim | Consulta proposta (conteúdo versionável) |
| `execution_status` | enum | sim | `proposed`, `pending_review`, `approved`, `rejected`, `blocked` |
| `requires_human_review` | boolean | sim | Deve ser `true` para execução em produção |
| `hypotheses` | object | sim | Hipótese principal + alternativas (inclui falso positivo) |
| `data_sufficiency` | object | sim | Parâmetros faltantes/suficiência |
| `policy_decision` | object | sim | Decisão do PolicyEngine antes da emissão/finalização |
| `trace` | object | sim | Rastreabilidade |

**Regras:** sem janela/escopo/custo válidos, a proposta deve ser parcial/bloqueada e
escalada conforme aplicável (R4, R7). Aprovação depende de registro explícito vinculado.

### 6. ContainmentProposal
Proposta de contenção (nunca execução automática).

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---:|---|
| `proposal_id` | string | sim | Identificador da proposta |
| `incident_or_alert_ref` | string | sim | Referência ao contexto analisado |
| `action_category` | enum | sim | `network`, `host`, `identity_account`, `process`, `credential_token` |
| `target` | object | sim | Alvo proposto (deve ser inequívoco) |
| `classification` | object | sim | Classificação da ação com justificativa |
| `confidence` | number/enum | sim | Confiança explícita |
| `consulted_sources` | Evidence[] | sim | Fontes com timestamps |
| `rollback_plan` | object | sim | Plano de rollback (pré-condições, passos, responsáveis, validação, limitações) |
| `approval_requirement` | object | sim | Exige aprovador humano identificado e autorizado |
| `approval_status` | enum | sim | `pending`, `approved`, `rejected`, `blocked` |
| `hypotheses` | object | sim | Principal + alternativas (inclui falso positivo) |
| `data_sufficiency` | object | sim | Suficiência/indeterminação |
| `policy_decision` | object | sim | Decisão do PolicyEngine antes da proposta |
| `trace` | object | sim | Rastreabilidade |

**Regras:** alvo ambíguo ou dados insuficientes => `blocked`/escalado, sem proposta
acionável (R2, R4). Sem rollback válido a proposta é inválida (R5).

### 7. ApprovalRecord
Registro explícito de decisão humana vinculado a uma proposta.

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---:|---|
| `approval_id` | string | sim | Identificador do registro |
| `proposal_id` | string | sim | Proposta vinculada |
| `proposal_type` | enum | sim | `containment`, `query_execution` |
| `approver` | object | sim | Identidade do aprovador humano identificado |
| `decision` | enum | sim | `approved`, `rejected` |
| `scope` | object | sim | Escopo/objeto aprovado ou rejeitado |
| `decided_at` | datetime | sim | Timestamp da decisão |
| `notes` | string | não | Observações |

**Regra:** ausência de registro explícito = não aprovado (R2).

### 8. AuditEvent (append-only)
Registro imutável de decisão/evento relevante.

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---:|---|
| `audit_id` | string | sim | Identificador do evento de auditoria |
| `event_type` | string | sim | Tipo (triagem, correlação, proposta, política, aprovação, IoC, etc.) |
| `occurred_at` | datetime | sim | Timestamp do evento |
| `input_summary` | object/string | sim | Entrada/resumo rastreável |
| `consulted_sources` | Evidence[] | não | Fontes consultadas (quando aplicável) |
| `reasoning_summary` | string | sim | Raciocínio resumido |
| `confidence` | number/enum/string | não | Confiança (quando aplicável) |
| `model_version` | string | não | Versão do modelo (quando aplicável) |
| `prompt_version` | string | não | Versão do prompt/instruções (quando aplicável) |
| `policy_version` | string | não | Versão da política (quando aplicável) |
| `outcome` | object | sim | Desfecho/estado resultante |
| `correlation_refs` | string[] | não | IDs relacionados (alerta, incidente, proposta) |

**Regra:** eventos não são editados pelo agente; correções por novos eventos de apêndice.

### 9. PolicyDecision
Resultado da avaliação do PolicyEngine (OPA/Rego) antes da emissão/finalização de proposta.

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---:|---|
| `decision_id` | string | sim | Identificador da decisão |
| `policy_id` | string | sim | Identificador/nome da política |
| `policy_version` | string | sim | Versão/revisão da política |
| `evaluated_at` | datetime | sim | Timestamp da avaliação |
| `input_ref` | object | sim | Referência ao artefato avaliado |
| `result` | enum | sim | `allow_proposal`, `require_revision`, `block_and_escalate` |
| `reasons` | string[] | sim | Motivos objetivos |
| `required_actions` | string[] | não | Ajustes/escalações exigidas |

## Relacionamentos principais

- `Alert` 1..* → `TriageResult` (uma triagem por execução; histórico permitido)
- `TriageResult`/`Alert`/evidências → `CorrelationResult` (agregação por escopo)
- `CorrelationResult`/`TriageResult` → `QueryProposal` e/ou `ContainmentProposal`
- `QueryProposal`/`ContainmentProposal` 0..* → `ApprovalRecord` (vinculado)
- Todas as decisões relevantes → `AuditEvent` (append-only)
- Toda proposta candidata → `PolicyDecision` antes da emissão/finalização

## Transições de estado (alto nível)

### Propostas (consulta/contenção)
- `draft_candidate` (interno) → **PolicyEngine** → `proposed` | `blocked` | `pending_review`
- `proposed/pending_review` → (registro explícito aprovado) → `approved`
- `proposed/pending_review` → (registro explícito rejeitado) → `rejected`
- `blocked` permanece bloqueado até novo contexto/artefato (novo ciclo, nova avaliação)

> Estados concretos podem ser refinados na implementação, mas DEVEM preservar: avaliação de
> política antes da proposta, ausência de aprovação explícita = não aprovado, e bloqueio/
> escalonamento em ambiguidade/insuficiência.
