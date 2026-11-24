# Implementation Plan: SOC Agent — Triagem, Correlação, Geração de Consultas e Proposta de Contenção

**Branch**: `001-soc-triage-correlacao` | **Date**: 2026-11-23 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `specs/001-soc-triage-correlacao/spec.md`

## Summary

Entregar o design técnico (ETAPA 4) para um agente SOC local de triagem de alertas,
correlação de incidentes, geração de propostas de consulta e propostas de contenção,
operando sob regras invioláveis R1–R7. A abordagem adota arquitetura hexagonal
(ports & adapters): o núcleo de domínio orquestra casos de uso usando apenas capacidades
abstratas definidas em `contracts/`, com `PolicyEngine` em OPA/Rego avaliado **antes de
qualquer proposta de ação** e acesso a modelo de linguagem isolado por `LlmProvider`
adapter (provedor desconhecido pelo núcleo). O piloto local utiliza adapters read-only
substituíveis para as categorias declaradas; migração futura ocorre por troca de adapters.

## Technical Context

**Language/Version**: Python 3.11+ (núcleo, adapters e suíte de validação)  
**Primary Dependencies**: `jsonschema` (ou equivalente) para validação de contratos JSON
Schema draft 2020-12; integração com OPA/Rego para `PolicyEngine` (CLI/runtime compatível
no piloto); `pytest` para testes unitários, de contrato, integração e guardrails;
serialização/CLI padrão da linguagem para ferramentas locais  
**Storage**: Abstrato no núcleo via `AuditSink` (append-only lógico) e
`ActionProposalQueue`; adapters de piloto podem usar armazenamento local simples
(arquivos JSONL/SQLite) preservando imutabilidade do ponto de vista do agente (R6). Sem
acoplamento a produto no domínio  
**Testing**: `pytest` em camadas: `tests/unit`, `tests/contract`, `tests/integration`,
`tests/guardrails`/avaliação (R1, R2, R4, R5, R7) com casos negativos obrigatórios  
**Target Platform**: Piloto 100% local, compatível com estações/servidores Linux e
Windows (execução local; integrações de leitura declaradas via adapters autorizados)  
**Project Type**: Aplicação/serviço local modular (núcleo + adapters + contratos) com
interfaces CLI/orquestração conforme tarefas futuras  
**Performance Goals**: Priorizar correção, rastreabilidade e segurança sobre throughput;
processar eventos/solicitações do piloto de forma confiável com respostas auditáveis
(metas quantitativas refináveis em implementação)  
**Constraints**: Conformidade estrita R1–R7; read-only por padrão (R3); nenhuma execução
destrutiva automática (R2); rollback obrigatório em propostas de contenção (R5); queries
como artefatos revisados com janela/escopo/custo (R7); sem credenciais no código/contexto  
**Scale/Scope**: Piloto SOC local com fontes de leitura nas quatro categorias declaradas
(alertas/telemetria, enriquecimento, inteligência de ameaças, busca analítica); fluxos de
triagem (automática e sob demanda), correlação e propostas sob demanda; categorias de
contenção cobertas como propostas controladas

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Phase 0 (passou)

| Princípio/Requisito | Gate | Status | Evidência no plano |
|---|---|---|---|
| R1 Dado externo nunca é instrução | Entradas externas tratadas como dados; sinalização/registro de IoC | PASS | [research.md](research.md) D-006/D-009; [data-model.md](data-model.md) TriageResult/ioc_signals e AuditEvent; [quickstart.md](quickstart.md) |
| R2 Nenhuma ação destrutiva executada | Apenas propostas; aprovação explícita registrada; sem resposta ≠ aprovação; alvo ambíguo bloqueia | PASS | [contracts/interfaces.md](contracts/interfaces.md), [contracts/schemas/containment-proposal.schema.json](contracts/schemas/containment-proposal.schema.json), [contracts/schemas/approval-record.schema.json](contracts/schemas/approval-record.schema.json), [contracts/policy/action_proposal.rego](contracts/policy/action_proposal.rego) |
| R3 Read-only por padrão / sem segredos | Capacidades de leitura; sem credenciais em artefatos | PASS | [research.md](research.md) D-002/D-007; Technical Context; contratos sem campos de segredo |
| R4 Incerteza escala | `indeterminado`, suficiência conhecida/faltante, hipóteses alternativas | PASS | [data-model.md](data-model.md), schemas de resultados/propostas, política de bloqueio/escalonamento |
| R5 Reversibilidade | Rollback documentado antes de aprovação/emissão válida | PASS | [contracts/schemas/containment-proposal.schema.json](contracts/schemas/containment-proposal.schema.json), [contracts/policy/action_proposal.rego](contracts/policy/action_proposal.rego) |
| R6 Rastreabilidade | Auditoria append-only com campos/metadados obrigatórios | PASS | [contracts/schemas/audit-event.schema.json](contracts/schemas/audit-event.schema.json), `AuditSink`, [data-model.md](data-model.md) |
| R7 Queries como artefatos | Proposta versionável com janela/escopo/custo e revisão humana | PASS | [contracts/schemas/query-proposal.schema.json](contracts/schemas/query-proposal.schema.json), [contracts/policy/action_proposal.rego](contracts/policy/action_proposal.rego) |
| ETAPA 4 capacidades/adapters | Integrações via interfaces abstratas em `contracts/` | PASS | [contracts/interfaces.md](contracts/interfaces.md) |
| ETAPA 4 interfaces obrigatórias | `SearchBackend`, `AlertSource`, `EnrichmentProvider`, `ThreatIntelStore`, `ActionProposalQueue`, `AuditSink`, `PolicyEngine` (+ `LlmProvider`) | PASS | [contracts/interfaces.md](contracts/interfaces.md), `contracts/schemas/*` |
| PolicyEngine OPA/Rego antes de proposta | Avaliação obrigatória pré-emissão/finalização | PASS | [contracts/policy/action_proposal.rego](contracts/policy/action_proposal.rego), schemas de propostas (`policy_decision`), [research.md](research.md) D-005 |
| LLM atrás de adapter | Núcleo sem conhecimento de provedor | PASS | `LlmProvider` em interfaces/schemas, [research.md](research.md) D-006 |

### Post-Phase 1 (reavaliação)

- **Resultado:** PASS (sem violações). Artefatos gerados (`research.md`, `data-model.md`,
  `contracts/`, `quickstart.md`) preservam gates R1–R7 e requisitos mandatórios da ETAPA 4.
- **Justificativas:** nenhuma exceção necessária; complexidade adicional não introduzida
  além da separação ports & adapters exigida para conformidade e substituibilidade.

## Project Structure

### Documentation (this feature)

```text
specs/001-soc-triage-correlacao/
├── plan.md              # This file (/speckit-plan output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── interfaces.md
│   ├── policy/
│   │   └── action_proposal.rego
│   └── schemas/
│       ├── common.schema.json
│       ├── triage-result.schema.json
│       ├── correlation-result.schema.json
│       ├── query-proposal.schema.json
│       ├── containment-proposal.schema.json
│       ├── approval-record.schema.json
│       ├── audit-event.schema.json
│       ├── policy-decision.request.schema.json
│       ├── policy-decision.response.schema.json
│       ├── alert-source.request.schema.json
│       ├── alert-source.response.schema.json
│       ├── search-backend.request.schema.json
│       ├── search-backend.response.schema.json
│       ├── enrichment.request.schema.json
│       ├── enrichment.response.schema.json
│       ├── threat-intel.request.schema.json
│       ├── threat-intel.response.schema.json
│       ├── action-proposal-queue.request.schema.json
│       ├── action-proposal-queue.response.schema.json
│       ├── audit.request.schema.json
│       ├── audit.response.schema.json
│       ├── llm.request.schema.json
│       └── llm.response.schema.json
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit-tasks - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/
└── soc_agent/
    ├── domain/                 # Entidades, regras e validações de negócio (sem dependência de provedores)
    ├── application/            # Casos de uso: triagem, correlação, propostas, orquestração
    ├── ports/                  # Interfaces de capacidade (contratos de programação alinhados a contracts/)
    ├── adapters/
    │   ├── alert_source/       # Adapters read-only (piloto/local declarado)
    │   ├── search_backend/
    │   ├── enrichment/
    │   ├── threat_intel/
    │   ├── proposal_queue/
    │   ├── audit_sink/
    │   ├── policy_engine/      # Adapter de avaliação OPA/Rego (chamado antes de propostas)
    │   └── llm_provider/       # Adapter de LLM (provedor encapsulado)
    ├── contracts_runtime/      # Carregamento/validação de schemas e mapeamentos (opcional)
    └── cli/                    # Entradas de execução local (sob demanda/automação controlada)

tests/
├── unit/                       # Regras de domínio e casos de uso
├── contract/                   # Conformidade de schemas e interfaces/adapters
├── integration/                # Fluxos com adapters locais/fakes
└── guardrails/                 # Avaliações R1, R2, R4, R5, R7 (inclui falha sem aprovação)
```

**Structure Decision**: Projeto único modular com arquitetura hexagonal em `src/soc_agent/`.
Os contratos normativos vivem em `specs/001-soc-triage-correlacao/contracts/` (design) e
devem ser tratados como fonte versionada para geração/alinhamento de interfaces e
validações na implementação. Adapters concretos do piloto são substituíveis sem alteração
do núcleo.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| *(nenhuma)* | — | Estrutura ports & adapters é necessária para cumprir substituibilidade por capacidade e isolamento do LLM; não há violação constitucional a justificar. |
