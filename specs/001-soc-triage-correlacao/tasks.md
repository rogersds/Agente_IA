# Tasks: SOC Agent — Triagem, Correlação, Geração de Consultas e Proposta de Contenção

**Input**: Design documents from `/specs/001-soc-triage-correlacao/`
**Prerequisites**: [plan.md](plan.md) (required), [spec.md](spec.md) (required), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: Incluídos como tarefas de primeira classe (obrigatório neste projeto): guardrails R1/R2/R4/R5/R7, conformidade de contratos/schemas/política e avaliações de fluxo. Tarefas que envolvem ações destrutivas/propostas de contenção DEVEM incluir testes que provem falha/bloqueio sem aprovação registrada.

**Organization**: Tarefas agrupadas por fase e por user story para implementação e validação independentes.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Paralelizável (arquivos diferentes, sem dependência de tarefa incompleta)
- **[Story]**: User story da fase (`[US1]`–`[US4]`)
- Cada tarefa inclui caminho(s) de arquivo explícito(s)

## Path Conventions

- Código: `src/soc_agent/`
- Testes: `tests/unit/`, `tests/contract/`, `tests/integration/`, `tests/guardrails/`
- Contratos normativos: `specs/001-soc-triage-correlacao/contracts/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Inicialização do projeto, estrutura e ferramentas de validação

- [X] T001 Criar estrutura de diretórios conforme [plan.md](plan.md) (`src/soc_agent/{domain,application,ports,adapters,contracts_runtime,cli}/`, `src/soc_agent/adapters/{alert_source,search_backend,enrichment,threat_intel,proposal_queue,audit_sink,policy_engine,llm_provider}/`, `tests/{unit,contract,integration,guardrails}/`, `tests/fixtures/`) e adicionar `__init__.py` onde aplicável
- [X] T002 Inicializar projeto Python 3.11+ com manifesto e dependências de validação/teste (ex.: `pyproject.toml`, `requirements-dev.txt` ou equivalente) incluindo `pytest` e validador JSON Schema; configurar execução padrão em `tests/` (ex.: `pytest.ini`/`pyproject.toml`)
- [X] T003 [P] Configurar lint/format (ex.: `ruff.toml`, `.editorconfig`, `pyproject.toml`) e documentação mínima de execução local em `README.md` (sem segredos, referências a variáveis de ambiente)
- [X] T004 [P] Criar utilitário de carregamento de artefatos de contrato em `src/soc_agent/contracts_runtime/loader.py` para resolver schemas e política em `specs/001-soc-triage-correlacao/contracts/` (sem copiar/alterar contratos normativos)
- [X] T005 [P] Criar fixtures base de teste em `tests/conftest.py` e `tests/fixtures/` (fábricas de entrada válida/inválida, relógio/timestamps controláveis, IDs) para reutilização em `tests/contract/`, `tests/integration/` e `tests/guardrails/`

---

## Phase 2: Foundational (Blocking Prerequisites) — Guardrails e contratos como primeira classe

**Purpose**: Núcleo ports & adapters, validação de contratos, PolicyEngine/LlmProvider/Audit, e harness de guardrails R1–R7. **CRÍTICO:** nenhuma user story inicia antes desta fase.

**⚠️ CRITICAL**: Toda proposta de ação deve passar por `PolicyEngine` antes de emissão/finalização; dados externos são dados (R1); auditoria append-only (R6); sem execução destrutiva (R2).

### Testes de contrato e guardrails fundacionais (primeira classe)

- [X] T006 [P] Implementar testes de conformidade dos JSON Schemas em `tests/contract/test_json_schemas.py` validando artefatos de exemplo contra `specs/001-soc-triage-correlacao/contracts/schemas/*.schema.json` (campos obrigatórios e `$defs` em `common.schema.json`)
- [X] T007 [P] Implementar testes de contrato do PolicyEngine em `tests/contract/test_policy_engine_contract.py` para `policy-decision.request/response` (`specs/001-soc-triage-correlacao/contracts/schemas/policy-decision.request.schema.json`, `policy-decision.response.schema.json`) cobrindo `PolicyDecision.result` (`allow_proposal|require_revision|block_and_escalate`), `PolicyDecision.reasons[]` e `PolicyDecision.policy_version` conforme [data-model.md](data-model.md) `PolicyDecision.result`, `PolicyDecision.reasons`, `PolicyDecision.policy_version`
- [X] T008 [P] Implementar testes de política OPA/Rego em `tests/guardrails/test_policy_action_proposal_rego.py` usando `specs/001-soc-triage-correlacao/contracts/policy/action_proposal.rego` (casos: rollback ausente R5, alvo ambíguo/insuficiência R2/R4, `query_execution` sem aprovação explícita R2/R7, `execution_requested=true` R2, candidato válido => `allow_proposal` sem autorizar execução)
- [X] T009 [P] Implementar testes de guardrail R1 em `tests/guardrails/test_r1_external_data_not_instruction.py` garantindo que conteúdo com instruções embutidas é tratado como dado/IoC potencial e nunca executado/obedecido (fixtures em `tests/fixtures/alerts/r1_injection.json`)
- [X] T010 [P] Implementar testes de guardrail R2 (aprovação/ausência de aprovação) em `tests/guardrails/test_r2_no_destructive_execution.py` provando que ações destrutivas/propostas de execução permanecem bloqueadas/não aprovadas sem `ApprovalRecord` explícito vinculado, citando [data-model.md](data-model.md) `ApprovalRecord.proposal_id`, `ApprovalRecord.approver`, `ApprovalRecord.decision`, `ApprovalRecord.scope`, `ApprovalRecord.decided_at` e ausência de registro ≠ aprovação
- [X] T011 [P] Implementar testes de guardrail R5/R7 em `tests/guardrails/test_r5_r7_rollback_and_query_artifacts.py` cobrindo contenção sem rollback acionável e consulta sem janela/escopo/custo/justificativa conforme [data-model.md](data-model.md) `ContainmentProposal.rollback_plan`, `QueryProposal.time_window`, `QueryProposal.data_scope`, `QueryProposal.cost_estimate`, `QueryProposal.requires_human_review`

### Implementação fundacional (núcleo e portas)

- [X] T012 [P] Definir interfaces/ports em `src/soc_agent/ports/` (`alert_source.py`, `search_backend.py`, `enrichment_provider.py`, `threat_intel_store.py`, `action_proposal_queue.py`, `audit_sink.py`, `policy_engine.py`, `llm_provider.py`) alinhadas a [contracts/interfaces.md](contracts/interfaces.md) e schemas de request/response em `specs/001-soc-triage-correlacao/contracts/schemas/`
- [X] T013 [P] Implementar modelos/validadores comuns de domínio em `src/soc_agent/domain/common.py` e `src/soc_agent/domain/validators.py` para `Evidence/ConsultedSource`, `classification`, `confidence`, `data_sufficiency`, `hypotheses` (principal + alternativa, suporte a falso positivo) e `trace`, citando [data-model.md](data-model.md) `Evidence/ConsultedSource.capability`, `Evidence/ConsultedSource.status`, `Evidence/ConsultedSource.consulted_at`, `TriageResult.consulted_sources`, `TriageResult.data_sufficiency`, `TriageResult.hypotheses`, `TriageResult.trace`
- [X] T014 [P] Implementar modelos e transições de `PolicyDecision` e envelopes de proposta em `src/soc_agent/domain/policy.py` citando [data-model.md](data-model.md) `PolicyDecision.input_ref`, `PolicyDecision.result`, `PolicyDecision.evaluated_at` e regra “avaliação antes de emissão/finalização”
- [X] T015 [P] Implementar modelo/estado de `ApprovalRecord` e verificação de aprovação explícita vinculada em `src/soc_agent/domain/approval.py`, citando [data-model.md](data-model.md) `ApprovalRecord.approval_id`, `ApprovalRecord.proposal_id`, `ApprovalRecord.proposal_type`, `ApprovalRecord.approver`, `ApprovalRecord.decision`, `ApprovalRecord.scope`, `ApprovalRecord.decided_at`
- [X] T016 [P] Implementar modelo `AuditEvent` append-only e construtor de eventos em `src/soc_agent/domain/audit.py`, citando [data-model.md](data-model.md) `AuditEvent.audit_id`, `AuditEvent.event_type`, `AuditEvent.occurred_at`, `AuditEvent.input_summary`, `AuditEvent.reasoning_summary`, `AuditEvent.outcome` (sem edição/sobrescrita pelo agente)
- [X] T017 Implementar runtime de validação de schemas e artefatos em `src/soc_agent/contracts_runtime/validator.py` (validação contra `specs/001-soc-triage-correlacao/contracts/schemas/` e helpers para `tests/contract`) dependente de T004, T012, T013
- [X] T018 Implementar adapter `PolicyEngine` (OPA/Rego) em `src/soc_agent/adapters/policy_engine/opa_adapter.py` com chamada síncrona e mapeamento para [policy-decision schemas](specs/001-soc-triage-correlacao/contracts/schemas/policy-decision.request.schema.json) e [action_proposal.rego](specs/001-soc-triage-correlacao/contracts/policy/action_proposal.rego); garantir ponto único de avaliação antes de emissão/finalização de propostas em `src/soc_agent/application/policy_gate.py` (T014, T017)
- [X] T019 Implementar adapter `LlmProvider` (provedor encapsulado, núcleo agnóstico) em `src/soc_agent/adapters/llm_provider/adapter.py` e contrato de chamada em `src/soc_agent/application/llm_gateway.py` conforme `llm.request/response` schemas (`specs/001-soc-triage-correlacao/contracts/schemas/llm.request.schema.json`, `llm.response.schema.json`), sem segredos no código (R3)
- [X] T020 [P] Implementar adapters locais append-only de piloto para `AuditSink` e `ActionProposalQueue` em `src/soc_agent/adapters/audit_sink/local_append_only.py` e `src/soc_agent/adapters/proposal_queue/local_queue.py` (armazenamento local abstrato, sem edição de eventos), citando [data-model.md](data-model.md) `AuditEvent` (imutável pelo agente) e transições de propostas vinculadas a `PolicyDecision`/`ApprovalRecord`
- [X] T021 Implementar pipeline de tratamento de entrada externa (R1) em `src/soc_agent/application/input_guard.py` para marcar instruções embutidas como potencial IoC, separar dado de instrução e produzir sinalização/auditoria; integrar com `src/soc_agent/domain/audit.py` e `src/soc_agent/contracts_runtime/validator.py`
- [X] T022 Implementar orquestração base de casos de uso e registro de auditoria em `src/soc_agent/application/orchestrator.py` (injeção de ports/adapters, coleta de fontes com timestamp/tentativa, chamada ao gate de política antes de propostas, emissão de `AuditEvent` em decisões relevantes) dependente de T012–T021

**Checkpoint**: Fundação pronta — contratos validados, PolicyEngine/LLM isolados, auditoria append-only, guardrails R1/R2/R5/R7 testáveis; user stories podem iniciar.

---

## Phase 3: User Story 1 - Triagem de alerta com classificação explicável (Priority: P1) 🎯 MVP

**Goal**: Produzir triagem (automática e sob demanda) com classificação, justificativa, confiança explícita, fontes com timestamp, suficiência/insuficiência e hipóteses (principal + alternativa, incluindo falso positivo), tratando dado externo como dado (R1).

**Independent Test**: Fornecer alerta isolado (com contexto suficiente e com insuficiência/indisponibilidade) e validar saída conforme `schemas/triage-result.schema.json` e cenários de aceitação da US1 em [spec.md](spec.md); confirmar sinalização de instrução embutida sem obediência.

### Tests for User Story 1 (obrigatórios)

- [X] T023 [P] [US1] Criar testes de contrato para `AlertSource` e `TriageResult` em `tests/contract/test_us1_triage_contracts.py` usando `specs/001-soc-triage-correlacao/contracts/schemas/alert-source.request.schema.json`, `alert-source.response.schema.json`, `triage-result.schema.json`
- [X] T024 [P] [US1] Criar testes de guardrail/avaliação R1+R4 da triagem em `tests/guardrails/test_us1_triage_guardrails.py` (alerta com instrução embutida; dados insuficientes => `indeterminado`, escalonamento, sem invenção) citando [data-model.md](data-model.md) `TriageResult.classification`, `TriageResult.confidence`, `TriageResult.data_sufficiency`, `TriageResult.hypotheses`, `TriageResult.consulted_sources`
- [X] T025 [P] [US1] Criar testes de integração de triagem em `tests/integration/test_us1_triage_flow.py` (automática no ingest e sob demanda) com adapters/fakes e verificação de `AuditEvent` append-only em `src/soc_agent/adapters/audit_sink/local_append_only.py`

### Implementation for User Story 1

- [X] T026 [P] [US1] Implementar modelos de `Alert` e `TriageResult` em `src/soc_agent/domain/alert.py` e `src/soc_agent/domain/triage.py`, citando [data-model.md](data-model.md) `Alert.alert_id`, `Alert.source`, `Alert.received_at`, `Alert.content`, `TriageResult.triage_id`, `TriageResult.alert_id`, `TriageResult.classification`, `TriageResult.confidence`, `TriageResult.consulted_sources`, `TriageResult.data_sufficiency`, `TriageResult.hypotheses`, `TriageResult.trace`
- [X] T027 [P] [US1] Implementar adapters de leitura read-only para triagem (piloto, substituíveis) em `src/soc_agent/adapters/alert_source/`, `src/soc_agent/adapters/search_backend/`, `src/soc_agent/adapters/enrichment/`, `src/soc_agent/adapters/threat_intel/` respeitando contratos de [specs/001-soc-triage-correlacao/contracts/interfaces.md](contracts/interfaces.md) e schemas correspondentes
- [X] T028 [US1] Implementar caso de uso de triagem em `src/soc_agent/application/triage_service.py` (coleta de evidências, chamada `LlmProvider` via gateway, validação de saída, marcação IoC R1, classificação `indeterminado` sob insuficiência R4, geração de `AuditEvent`) dependente de T021, T022, T026, T027
- [X] T029 [US1] Implementar pontos de entrada de triagem automática e sob demanda em `src/soc_agent/cli/triage.py` e `src/soc_agent/application/triage_ingest.py` (FR-001: ingest/chegada e solicitação autorizada), sem execução de ações destrutivas
- [X] T030 [US1] Adicionar validação/serialização de saída de triagem e logging/auditoria operacional em `src/soc_agent/application/triage_service.py` e `src/soc_agent/contracts_runtime/validator.py` garantindo conformidade com `schemas/triage-result.schema.json`

**Checkpoint**: US1 funcional e validável de forma independente (MVP), com guardrails R1/R4 e rastreabilidade R6.

---

## Phase 4: User Story 2 - Correlação de sinais em incidente (Priority: P2)

**Goal**: Correlacionar múltiplos alertas/evidências sob demanda em visão de incidente com classificação, confiança, fontes com timestamp, tratamento de insuficiência e hipóteses (incluindo falso positivo).

**Independent Test**: Solicitar correlação para conjunto relacionado e conjunto sem relação clara; validar `schemas/correlation-result.schema.json`, declaração de lacunas/indeterminação e registro em auditoria.

### Tests for User Story 2 (obrigatórios)

- [X] T031 [P] [US2] Criar testes de contrato para correlação em `tests/contract/test_us2_correlation_contracts.py` usando `specs/001-soc-triage-correlacao/contracts/schemas/correlation-result.schema.json` e `common.schema.json`
- [X] T032 [P] [US2] Criar testes de integração/avaliação de correlação em `tests/integration/test_us2_correlation_flow.py` cobrindo relação provável, sinais insuficientes/contraditórios e hipótese de falso positivo (R4), com escopo solicitado sob demanda. Cobertura negativa complementar em `tests/guardrails/test_r4_correlation_negative.py` (R4/R6) e campos adicionais compatíveis (`timeline`, `grouping`, `telemetry_gaps`) para atender critérios B.1 sem violar schemas; vínculo alerta↔incidente representado por `related_alerts` no resultado e `correlation_refs`/`trace` em auditoria (equivalência documentada nos testes).

### Implementation for User Story 2

- [X] T033 [P] [US2] Implementar modelo `CorrelationResult` em `src/soc_agent/domain/correlation.py`, citando [data-model.md](data-model.md) `CorrelationResult.correlation_id`, `CorrelationResult.scope`, `CorrelationResult.related_alerts`, `CorrelationResult.classification`, `CorrelationResult.confidence`, `CorrelationResult.consulted_sources`, `CorrelationResult.data_sufficiency`, `CorrelationResult.hypotheses`, `CorrelationResult.trace`
- [X] T034 [US2] Implementar caso de uso de correlação sob demanda em `src/soc_agent/application/correlation_service.py` (agregação de alertas/evidências via ports de leitura, análise, validação de saída, auditoria) dependente de T022, T027, T033
- [X] T035 [US2] Implementar ponto de entrada CLI/API local de correlação em `src/soc_agent/cli/correlate.py` aceitando escopo/período/ativos e retornando resultado rastreável sem ações destrutivas

**Checkpoint**: US1 e US2 funcionam independentemente, com rastreabilidade e hipóteses alternativas.

---

## Phase 5: User Story 3 - Geração de consulta analítica como proposta revisável (Priority: P3)

**Goal**: Gerar propostas de consulta versionáveis (sob demanda) com janela/escopo/custo (ou justificativa e escalonamento), revisão humana obrigatória, `policy_decision` pré-emissão e sem execução automática (R7, R2).

**Independent Test**: Solicitar consulta com contexto suficiente e com parâmetros ausentes; validar `schemas/query-proposal.schema.json`, bloqueio/revisão/escalonamento quando incompleta, e presença de decisão de política antes de emissão/finalização.

### Tests for User Story 3 (obrigatórios)

- [X] T036 [P] [US3] Criar testes de contrato para `SearchBackend` e `QueryProposal` em `tests/contract/test_us3_query_proposal_contracts.py` usando `specs/001-soc-triage-correlacao/contracts/schemas/search-backend.request.schema.json`, `search-backend.response.schema.json`, `query-proposal.schema.json` (B.2: janela/escopo/custo explícitos, parâmetros nomeados sintéticos, sem execução direta R7; equivalência documentada com `tests/guardrails/test_r7_query_proposal_only.py`).
- [X] T037 [P] [US3] Criar testes de guardrail R7/R2 para propostas de consulta em `tests/guardrails/test_us3_query_proposal_guardrails.py` (parâmetros ausentes => indeterminado/revisão/bloqueio conforme política; `requires_human_review=true`; sem execução automática; `query_execution` sem aprovação explícita bloqueado) citando [data-model.md](data-model.md) `QueryProposal.time_window`, `QueryProposal.data_scope`, `QueryProposal.cost_estimate`, `QueryProposal.requires_human_review`, `QueryProposal.execution_status`, `QueryProposal.policy_decision`
- [X] T038 [P] [US3] Criar testes de integração de geração de proposta de consulta em `tests/integration/test_us3_query_proposal_flow.py` validando chamada ao `PolicyEngine` antes de `ActionProposalQueue.enqueue` e registro em auditoria

### Implementation for User Story 3

- [X] T039 [P] [US3] Implementar modelo `QueryProposal` e validações em `src/soc_agent/domain/query_proposal.py`, citando [data-model.md](data-model.md) `QueryProposal.query_proposal_id`, `QueryProposal.objective`, `QueryProposal.query_artifact`, `QueryProposal.time_window`, `QueryProposal.data_scope`, `QueryProposal.cost_estimate`, `QueryProposal.execution_status`, `QueryProposal.requires_human_review`, `QueryProposal.policy_decision`, `QueryProposal.hypotheses`, `QueryProposal.data_sufficiency`, `QueryProposal.trace`
- [X] T040 [US3] Implementar caso de uso de geração de proposta de consulta em `src/soc_agent/application/query_proposal_service.py` (subsidiado por `SearchBackend`/fontes de leitura, montagem versionável, avaliação `PolicyEngine` via `policy_gate` antes de emitir/finalizar, enfileiramento em `ActionProposalQueue`, auditoria) dependente de T018, T020, T022, T039
- [X] T041 [US3] Implementar ponto de entrada sob demanda para geração de propostas de consulta em `src/soc_agent/cli/propose_query.py` (entrada de objetivo/contexto, saída de artefato proposto para revisão, sem execução em produção)

**Checkpoint**: US3 entrega propostas de consulta revisáveis e bloqueáveis por política, sem execução automática.

---

## Phase 6: User Story 4 - Proposta de contenção com aprovação humana e rollback (Priority: P4)

**Goal**: Gerar apenas propostas de contenção (todas categorias de domínio aplicáveis) com alvo inequívoco, evidência, rollback completo e `policy_decision` pré-emissão; exigir aprovação humana identificada registrada para qualquer execução externa futura (não realizada pelo agente).

**Independent Test**: Validar cenário com evidências/alvo claros (proposta pendente com rollback e gate de política), cenário ambíguo/insuficiente (bloqueio/escalonamento sem proposta acionável), e estado sem registro explícito de aprovação (permanece não aprovado). **Cada tarefa que envolva ação destrutiva chega com teste que prova falha/bloqueio sem aprovação registrada.**

### Tests for User Story 4 (obrigatórios, primeira classe para ação destrutiva)

- [X] T042 [P] [US4] Criar testes de contrato para `ContainmentProposal` e `ApprovalRecord` em `tests/contract/test_us4_containment_contracts.py` usando `specs/001-soc-triage-correlacao/contracts/schemas/containment-proposal.schema.json`, `approval-record.schema.json`, `action-proposal-queue.request.schema.json`, `action-proposal-queue.response.schema.json` (B.2: alvo/rollback/validação/sem execução, aprovação explícita vinculada; equivalência documentada com guardrails R2/R5 existentes).
- [X] T043 [P] [US4] Criar testes de guardrail R2/R4/R5 para contenção em `tests/guardrails/test_us4_containment_guardrails.py` provando bloqueio sem `rollback_plan` válido, sem alvo inequívoco, com dados insuficientes, e **falha/bloqueio de execução/progressão sem `ApprovalRecord` explícito vinculado**; citar [data-model.md](data-model.md) `ContainmentProposal.action_category`, `ContainmentProposal.target`, `ContainmentProposal.rollback_plan`, `ContainmentProposal.approval_requirement`, `ContainmentProposal.approval_status`, `ContainmentProposal.policy_decision`, `ApprovalRecord.proposal_id`, `ApprovalRecord.approver`, `ApprovalRecord.decision`, `ApprovalRecord.decided_at`
- [X] T044 [P] [US4] Criar testes de integração do fluxo de proposta de contenção em `tests/integration/test_us4_containment_proposal_flow.py` (avaliação `PolicyEngine` antes de emissão/finalização, enfileiramento sem execução, transições com registro explícito aprovado/rejeitado e manutenção de pendente sem registro)

### Implementation for User Story 4

- [X] T045 [P] [US4] Implementar modelo `ContainmentProposal` e validações em `src/soc_agent/domain/containment.py`, citando [data-model.md](data-model.md) `ContainmentProposal.proposal_id`, `ContainmentProposal.incident_or_alert_ref`, `ContainmentProposal.action_category`, `ContainmentProposal.target`, `ContainmentProposal.classification`, `ContainmentProposal.confidence`, `ContainmentProposal.rollback_plan`, `ContainmentProposal.approval_requirement`, `ContainmentProposal.approval_status`, `ContainmentProposal.hypotheses`, `ContainmentProposal.data_sufficiency`, `ContainmentProposal.policy_decision`, `ContainmentProposal.trace`
- [X] T046 [US4] Implementar caso de uso de proposta de contenção em `src/soc_agent/application/containment_proposal_service.py` (avaliação de evidências/alvo, construção de rollback, avaliação `PolicyEngine` antes de emissão/finalização, bloqueio/escalonamento quando inválido, enfileiramento em `ActionProposalQueue`, auditoria) dependente de T015, T018, T020, T022, T045
- [X] T047 [US4] Implementar registro/atualização de decisões de aprovação explícita em `src/soc_agent/application/approval_service.py` e integração com `src/soc_agent/adapters/proposal_queue/local_queue.py` aceitando apenas `ApprovalRecord` válido e vinculado (aprovação/rejeição) e mantendo pendente sem registro; sem qualquer caminho de execução destrutiva
- [X] T048 [US4] Implementar ponto de entrada para gerar propostas de contenção e consultar estado em `src/soc_agent/cli/propose_containment.py` (somente proposta/estado/auditoria, saída clara de pendente/aprovada/rejeitada/bloqueada)

**Checkpoint**: US4 produz apenas propostas controladas; bloqueios e exigência de aprovação explícita comprovados por testes; sem execução automática.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Consolidação transversal após user stories (guardrails já implementados e testados nas fases anteriores)

- [X] T049 [P] Atualizar documentação operacional e de contratos em `README.md` e `specs/001-soc-triage-correlacao/quickstart.md` com comandos de validação reprodutíveis (`pytest tests/contract tests/guardrails tests/integration`, `opa check`), versões mínimas/pinagem de ferramentas quando aplicável e notas de variáveis de ambiente (sem segredos) (Fase A; OPA 1.22.4 pinado/validado)
- [X] T050 [P] Revisar consistência de rastreabilidade (campos de auditoria, versões modelo/prompt/política) em `src/soc_agent/domain/audit.py`, `src/soc_agent/application/orchestrator.py` e schemas relacionados, citando [data-model.md](data-model.md) `AuditEvent.model_version`, `AuditEvent.prompt_version`, `AuditEvent.policy_version`, `AuditEvent.correlation_refs` (propagação de `trace`/versões/correlation_refs reforçada em serviços e build de auditoria)
- [X] T051 Executar validação descrita em [quickstart.md](quickstart.md) (contratos, política, fluxos) e registrar ajustes finais de conformidade em `specs/001-soc-triage-correlacao/tasks.md` (marcação de conclusão) e código correspondente nos caminhos afetados (evidências literais coletadas em Fases A–C/B; `opa check` verde, suítes pytest verdes)
- [X] T052 [P] Refatorações de segurança/manutenibilidade sem alterar comportamento (ex.: centralizar validações em `src/soc_agent/contracts_runtime/validator.py`, endurecer tratamento de erros em adapters read-only) mantendo gates R1–R7 (refino seguro: flush em persistência local de auditoria/fila, mensagens de validação mais diagnósticas; suíte completa verde)
- [X] T053 [P] Implementar guardrail/teste de conformidade R3/FR-011 em `tests/guardrails/test_r3_no_secrets_in_outputs.py` validando que resultados, propostas, logs operacionais de teste e artefatos gerados não expõem credenciais/tokens/chaves/segredos (usar fixtures/sentinelas sintéticas), cobrindo serializações em `src/soc_agent/contracts_runtime/validator.py`, `src/soc_agent/application/orchestrator.py` e adapters de saída/auditoria
- [X] T054 [P] Criar instrumento de avaliação humana do piloto para SC-007 em `specs/001-soc-triage-correlacao/checklists/pilot-evaluation-sc007.md` (amostragem, critérios de rastreabilidade/compreensibilidade, verificação de ausência de segredos e registro de resultado ≥90%), referenciando saídas auditáveis e [quickstart.md](quickstart.md)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: sem dependências — início imediato
- **Phase 2 (Foundational)**: depende da Phase 1 — **BLOQUEIA** todas as user stories
- **Phase 3 (US1, P1)**: depende da Phase 2 — entrega MVP de triagem
- **Phase 4 (US2, P2)**: depende da Phase 2; pode reutilizar evidências/saídas de triagem mas deve permanecer testável independentemente
- **Phase 5 (US3, P3)**: depende da Phase 2 (e de capacidades de busca/leitura fundacionais); independente de US4
- **Phase 6 (US4, P4)**: depende da Phase 2 (PolicyEngine, fila, aprovação/auditoria); independente de US3
- **Phase 7 (Polish)**: depende das user stories desejadas concluídas

### User Story Dependencies

- **US1 (P1)**: após Foundational; sem dependência de outras stories
- **US2 (P2)**: após Foundational; pode correlacionar alertas/triagens existentes, mas cenários de teste usam fixtures independentes
- **US3 (P3)**: após Foundational; proposta de consulta independente, sujeita a gate de política e fila
- **US4 (P4)**: após Foundational; proposta de contenção independente, com exigência adicional de rollback/aprovação explícita

### Within Each User Story

- Testes de contrato/guardrails/integração da story antes ou em paralelo controlado, devendo falhar antes da implementação correspondente quando aplicável
- Modelos/validações → serviços/casos de uso → pontos de entrada/integração
- `PolicyEngine` avaliado antes de qualquer emissão/finalização de proposta (US3/US4)
- Registrar `AuditEvent` em decisões relevantes

### Parallel Opportunities

- Phase 1: T003, T004, T005 em paralelo após T001–T002
- Phase 2: T006–T011 e T012–T016, T020 em paralelo conforme arquivos; T017–T019, T021–T022 em sequência de dependências
- Após Phase 2: US1–US4 podem avançar em paralelo por equipe; dentro de cada story, tarefas marcadas `[P]` são paralelizáveis
- US3 e US4 compartilham infraestrutura de política/fila/auditoria (Foundational) mas têm modelos/serviços distintos

---

## Parallel Example: User Story 1

```bash
# Testes/contratos em paralelo (arquivos diferentes):
Task: "T023 [US1] tests/contract/test_us1_triage_contracts.py"
Task: "T024 [US1] tests/guardrails/test_us1_triage_guardrails.py"
Task: "T025 [US1] tests/integration/test_us1_triage_flow.py"

# Modelos e adapters read-only em paralelo:
Task: "T026 [US1] src/soc_agent/domain/alert.py, src/soc_agent/domain/triage.py"
Task: "T027 [US1] src/soc_agent/adapters/alert_source/ ... src/soc_agent/adapters/threat_intel/"
```

## Parallel Example: User Story 4 (ação destrutiva = proposta controlada)

```bash
# Guardrails e contratos de contenção/aprovação em paralelo:
Task: "T042 [US4] tests/contract/test_us4_containment_contracts.py"
Task: "T043 [US4] tests/guardrails/test_us4_containment_guardrails.py (inclui prova de bloqueio sem ApprovalRecord explícito)"
Task: "T044 [US4] tests/integration/test_us4_containment_proposal_flow.py"

# Domínio e serviços após fundação:
Task: "T045 [US4] src/soc_agent/domain/containment.py"
Task: "T046 [US4] src/soc_agent/application/containment_proposal_service.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Concluir **Phase 1: Setup**
2. Concluir **Phase 2: Foundational** (contratos, PolicyEngine, LLM adapter, auditoria, guardrails R1/R2/R5/R7 base) — crítico
3. Concluir **Phase 3: US1**
4. **Parar e validar**: executar testes US1 e cenários de [quickstart.md](quickstart.md) (triagem)
5. Demonstrar triagem explicável e rastreável (MVP)

### Incremental Delivery

1. Setup + Foundational → base segura e auditável
2. US1 → triagem (MVP) → validar independentemente
3. US2 → correlação → validar independentemente
4. US3 → propostas de consulta revisáveis (R7/política) → validar independentemente
5. US4 → propostas de contenção com rollback/aprovação (R2/R5/política) → validar independentemente
6. Cada incremento preserva R1–R7 e contratos

### Parallel Team Strategy

1. Equipe conclui Phase 1 e Phase 2 em conjunto
2. Após fundação: desenvolvedores podem assumir US1–US4 em paralelo (interfaces/arquivos distintos), sincronizando apenas em contratos compartilhados
3. Integrar por checkpoints e suíte de guardrails/contratos

---

## Notes

- `[P]` = arquivos diferentes e sem dependência bloqueante
- `[USn]` mapeia rastreabilidade à user story em [spec.md](spec.md)
- Guardrails R1/R2 e suíte de avaliação são **tarefas de primeira classe** (Phases 2–6), não apenas polish
- Toda ação destrutiva é apenas **proposta**; tarefas de contenção incluem testes que provam falha/bloqueio sem aprovação registrada explícita
- `PolicyEngine` (OPA/Rego) deve ser avaliado **antes** de emissão/finalização de qualquer proposta de ação
- Citações `data-model.md` + `Entidade.campo` nas tarefas indicam definições canônicas de campos/constraints (não duplicar regras contraditórias)

