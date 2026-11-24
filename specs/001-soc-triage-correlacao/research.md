# Research: SOC Agent — Triagem, Correlação, Geração de Consultas e Proposta de Contenção

**Feature**: `001-soc-triage-correlacao`  
**Date**: 2026-11-23  
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Objetivo

Consolidar decisões técnicas da ETAPA 4 para viabilizar implementação alinhada à
constituição (R1–R7) e à especificação, resolvendo pontos em aberto com escolhas
recomendadas (aceitas pelo usuário para esta etapa).

## Decisões

### D-001 — Linguagem e runtime principal
- **Decision:** Python 3.11+ como linguagem principal do núcleo do agente, adapters e
  ferramentas de validação local.
- **Rationale:** ecossistema maduro para automação de segurança, manipulação de dados/
  JSON Schema, integração com ferramentas locais e testes; facilita implementação de
  arquitetura hexagonal e adapters substituíveis no piloto.
- **Alternatives considered:** Go (bom para binários/concorrência, porém menor
  conveniência para prototipação rápida de análise/LLM adapters no piloto); TypeScript/
  Node.js (bom para integrações, porém menor aderência ao ecossistema analítico local).

### D-002 — Estilo arquitetural e separação de capacidades
- **Decision:** arquitetura hexagonal (ports & adapters). Núcleo de domínio e casos de
  uso dependem apenas de contratos/capacidades abstratas; integrações concretas vivem em
  adapters de infraestrutura.
- **Rationale:** atende diretamente à exigência de trocar implementações (ex.: fontes de
  busca/alertas/intel/LLM) sem refatorar o agente; reforça R3 (read-only por padrão) e
  testabilidade por contratos.
- **Alternatives considered:** integração direta acoplada a ferramentas específicas
  (rejeitada: viola objetivo de migração por troca de adapters); microserviços desde o
  início (complexidade desnecessária para piloto).

### D-003 — Interfaces de capacidade obrigatórias
- **Decision:** definir e versionar contratos abstratos para `SearchBackend`,
  `AlertSource`, `EnrichmentProvider`, `ThreatIntelStore`, `ActionProposalQueue`,
  `AuditSink`, `PolicyEngine`, além de `LlmProvider` (adapter de LLM). Todas as integrações
  implementam interfaces em `contracts/`.
- **Rationale:** exigência explícita da ETAPA 4; permite substituição de backends locais
  declarados no piloto por capacidades equivalentes futuras.
- **Alternatives considered:** interfaces parciais apenas para SIEM/LLM (rejeitada:
  incompleta frente ao requisito).

### D-004 — Contratos de dados (entrada/saída)
- **Decision:** JSON Schema (draft 2020-12) como formato canônico dos contratos de
  entrada/saída em `contracts/schemas/`, cobrindo artefatos de domínio e envelopes de
  capacidade (alertas, evidências, triagem, correlação, proposta de consulta, proposta de
  contenção, aprovação, auditoria, decisão de política, requisições/respostas de LLM).
- **Rationale:** validação automatizável, linguagem-agnóstica e adequada para revisão
  humana; suporta rastreabilidade (R6) e consistência de campos obrigatórios (confiança,
  fontes/timestamps, hipóteses, rollback).
- **Alternatives considered:** apenas tipagem em código (insuficiente para contrato
  compartilhado/versionado); OpenAPI exclusivo (não cobre todos os artefatos internos).

### D-005 — PolicyEngine e ponto obrigatório de avaliação
- **Decision:** `PolicyEngine` implementado com OPA/Rego em `contracts/policy/` (artefatos
  de política) e interface de avaliação síncrona. O núcleo DEVE invocar o PolicyEngine
  **antes de qualquer proposta de ação** ser emitida/finalizada (contenção e propostas que
  impliquem execução/revisão para produção), recebendo decisão explícita (permitir
  proposta, exigir ajustes, bloquear/escalar).
- **Rationale:** cumprimento direto de R2/R4/R5/R7 e do requisito da ETAPA 4; separa
  decisão de política auditável da lógica de orquestração.
- **Alternatives considered:** validações ad hoc em código (rejeitada: menor
  auditabilidade/substituibilidade); avaliação após emissão da proposta (rejeitada:
  viola requisito de chamada antes da proposta).

### D-006 — LLM atrás de adapter
- **Decision:** todo acesso a modelo passa por interface `LlmProvider` com contratos de
  entrada/saída e metadados de versão; o núcleo de domínio não conhece provedor, modelo
  concreto, endpoint ou SDK específico.
- **Rationale:** requisito explícito da ETAPA 4 e da constituição; facilita piloto local e
  migração futura.
- **Alternatives considered:** chamadas diretas a SDK/provedor no núcleo (rejeitada).

### D-007 — Armazenamento, fila e auditoria no piloto
- **Decision:** abstrair persistência por capacidades `AuditSink` (append-only lógico) e
  `ActionProposalQueue` (fila/registro de propostas e estados). Adapters de piloto podem
  usar armazenamento local simples (ex.: arquivos JSONL/SQLite) desde que preservem
  imutabilidade do ponto de vista do agente (apêndice, sem edição in-place de eventos).
- **Rationale:** atende R6 sem acoplar a produto; viável para piloto 100% local.
- **Alternatives considered:** banco específico hardcoded (rejeitado no núcleo).

### D-008 — Testes e validação (incluindo guardrails de primeira classe)
- **Decision:** estratégia de testes em `pytest` com camadas: unit (domínio/regras),
  contract (conformidade de schemas/interfaces/adapters), integration (fluxos com adapters
  locais/fakes) e evaluation/guardrails (R1/R2/R4/R5/R7). Casos de ação destrutiva DEVEM
  provar falha/bloqueio sem aprovação registrada.
- **Rationale:** alinhado à constituição e à ETAPA 5 futura; reduz risco de regressão em
  segurança.
- **Alternatives considered:** apenas testes unitários (insuficiente para contratos e
  guardrails).

### D-009 — Observabilidade e metadados de rastreabilidade
- **Decision:** padronizar campos de rastreabilidade em schemas (entrada, fontes com
  timestamps, raciocínio resumido, confiança, versões de modelo/prompt/política, desfecho,
  IDs de correlação) e emitir eventos para `AuditSink` em cada decisão relevante.
- **Rationale:** cumprimento de R6 e suporte a revisão humana/auditoria.
- **Alternatives considered:** logs não estruturados livres (insuficiente).

### D-010 — Escopo operacional do piloto (decisões assumidas)
- **Decision:** fontes de leitura incluem todas as categorias declaradas (alertas/
  telemetria, enriquecimento, inteligência de ameaças, busca analítica); triagem híbrida
  (automática e sob demanda), correlação/consultas sob demanda; aprovação apenas por
  registro explícito vinculado; propostas de contenção em todas as categorias de domínio
  aplicáveis, sempre sem execução automática.
- **Rationale:** consolida clarificações aceitas na ETAPA 3.
- **Alternatives considered:** escopos reduzidos (adiáveis, mas não selecionados).

## Resolução de NEEDS CLARIFICATION

| Item | Resolução | Observação |
|---|---|---|
| Linguagem/stack do núcleo | Python 3.11+ | Recomendação aceita para planejamento |
| Dependências principais | Bibliotecas de validação JSON Schema, execução/integração OPA, testes `pytest`, CLI local | Adapters concretos definidos por implementação |
| Armazenamento piloto | Abstrato via `AuditSink`/`ActionProposalQueue`; adapters locais append-only | Sem acoplamento a produto no núcleo |
| Metas de desempenho | Piloto local: processamento confiável e rastreável priorizado sobre throughput alto; metas quantitativas refináveis na implementação | Sem impacto em contratos R1–R7 |

## Riscos e Mitigações (nível de plano)

- **Risco:** ambiguidade em alvos de contenção. **Mitigação:** PolicyEngine + regra de
  bloqueio/escalonamento; schema exige alvo e confiança; testes de contrato/guardrail.
- **Risco:** prompt injection em dados externos. **Mitigação:** pipeline trata entradas
  como dados, marca IoC potencial, registra e sinaliza; avaliação de guardrail dedicada.
- **Risco:** consulta custosa/ampla. **Mitigação:** schema exige janela/escopo/custo ou
  justificativa; revisão humana antes de produção; política pode bloquear.
- **Risco:** ausência de aprovação confundida com autorização. **Mitigação:** estados
  explícitos e exigência de registro vinculado; testes negativos obrigatórios.
