# Contratos de Capacidade — soc-agent

**Feature**: `001-soc-triage-correlacao`  
**Versão do contrato**: 1.0.0-draft  
**Data**: 2026-11-23

## Princípios

- O núcleo de domínio depende exclusivamente destas capacidades abstratas. Integrações
  concretas (piloto local ou futuras) são implementadas como **adapters** em infraestrutura,
  sem refatorar o núcleo.
- Toda integração implementa uma interface abstrata declarada neste diretório.
- Entradas/saídas são validadas por JSON Schemas em `schemas/`.
- O `PolicyEngine` é avaliado **antes de qualquer proposta de ação** ser emitida ou
  finalizada.
- O acesso a LLM ocorre somente via `LlmProvider`; o restante do código não conhece
  provedor, SDK ou endpoint.
- Operações de leitura são padrão (R3). Escrita/execução não pertencem a estas interfaces
  de proposta; execução externa exige aprovação humana registrada (R2).

## Interfaces obrigatórias

### 1. `AlertSource` (leitura)
Fornece acesso a alertas/sinais para triagem.
- **Operações conceituais**
  - `fetch_alerts(request) -> AlertBatchResponse`: busca/recebe alertas por critérios
    (janela, filtros, paginação) para triagem automática ou sob demanda.
  - `get_alert(request) -> AlertResponse`: recupera um alerta específico.
- **Entrada/saída**: `schemas/alert-source.request.schema.json`,
  `schemas/alert-source.response.schema.json` (o envelope/estrutura de alertas retornados
  é definido neste contrato de resposta).
- **Erros/limites**: indisponibilidade parcial deve ser reportada com status e timestamp
  de tentativa (R4/R6).

### 2. `SearchBackend` (leitura analítica)
Executa consultas analíticas de suporte à investigação/correlação e subsidia propostas de
consulta versionáveis.
- **Operações conceituais**
  - `search(request) -> SearchResponse`: consulta analítica em escopo declarado.
- **Requisitos**: requisição deve declarar janela temporal e escopo de dados quando
  aplicável; resposta deve indicar custo/impacto observado ou estimado quando disponível.
  Consultas propostas para produção são artefatos revisados (R7), não execução automática.
- **Entrada/saída**: `schemas/search-backend.request.schema.json`,
  `schemas/search-backend.response.schema.json`.

### 3. `EnrichmentProvider` (leitura)
Enriquece entidades/indicadores com contexto adicional autorizado.
- **Operações conceituais**
  - `enrich(request) -> EnrichmentResponse`: retorna contexto para ativos, usuários,
    indicadores, etc.
- **Entrada/saída**: `schemas/enrichment.request.schema.json`,
  `schemas/enrichment.response.schema.json`.

### 4. `ThreatIntelStore` (leitura)
Consulta inteligência de ameaças disponível no escopo autorizado.
- **Operações conceituais**
  - `lookup(request) -> ThreatIntelResponse`: busca por indicadores/contextos de ameaça.
- **Entrada/saída**: `schemas/threat-intel.request.schema.json`,
  `schemas/threat-intel.response.schema.json`.

### 5. `ActionProposalQueue`
Registra e gerencia propostas (consulta/contenção) e seus estados, sem executar ações.
- **Operações conceituais**
  - `enqueue(proposal) -> QueueAck`: registra proposta após avaliação de política.
  - `update_status(request) -> QueueAck`: atualiza estado com base em eventos válidos
    (ex.: registro explícito de aprovação/rejeição vinculado).
  - `get(proposal_id) -> ProposalRecord`.
- **Entrada/saída**: `schemas/action-proposal-queue.request.schema.json`,
  `schemas/action-proposal-queue.response.schema.json`, `schemas/containment-proposal.schema.json`,
  `schemas/query-proposal.schema.json`, `schemas/approval-record.schema.json`.
- **Regra**: ausência de registro explícito de aprovação => estado não aprovado/pendente.

### 6. `AuditSink` (append-only do ponto de vista do agente)
Persiste eventos de auditoria imutáveis para o agente.
- **Operações conceituais**
  - `append(event) -> AuditAck`: anexa evento de auditoria.
  - `query(request) -> AuditQueryResponse` (opcional/leitura): consulta para suporte
    operacional, sujeita a escopo.
- **Entrada/saída**: `schemas/audit-event.schema.json`, `schemas/audit.request.schema.json`,
  `schemas/audit.response.schema.json`.
- **Regra**: sem edição/sobrescrita pelo agente (R6).

### 7. `PolicyEngine` (OPA/Rego)
Avalia políticas antes da emissão/finalização de propostas.
- **Operações conceituais**
  - `evaluate(request) -> PolicyDecision`: avalia proposta candidata e contexto.
- **Momento obrigatório**: chamado **antes de qualquer proposta de ação** ser emitida/
  finalizada (contenção e propostas de consulta/executão em escopo de produção conforme
  aplicável).
- **Implementação**: políticas em Rego (`policy/*.rego`) executadas por mecanismo
  compatível com OPA; versão da política registrada na decisão e auditoria.
- **Entrada/saída**: `schemas/policy-decision.request.schema.json`,
  `schemas/policy-decision.response.schema.json`.

## Interface adicional requerida

### 8. `LlmProvider` (adapter de LLM)
Abstrai acesso a modelos de linguagem; o núcleo não conhece provedor.
- **Operações conceituais**
  - `generate(request) -> LlmResponse`: geração/análise estruturada com metadados de
    versão de modelo e prompt.
- **Entrada/saída**: `schemas/llm.request.schema.json`, `schemas/llm.response.schema.json`.
- **Regras**: dados externos permanecem dados (R1); saídas devem ser validadas contra
  schemas de artefatos antes de aceitação; sem credenciais no código/contexto (R3).

## Mapeamento para artefatos de domínio

| Artefato | Schemas principais |
|---|---|
| Triage | `schemas/triage-result.schema.json`, `schemas/common.schema.json` |
| Correlação | `schemas/correlation-result.schema.json`, `schemas/common.schema.json` |
| Proposta de consulta | `schemas/query-proposal.schema.json`, `schemas/common.schema.json` |
| Proposta de contenção | `schemas/containment-proposal.schema.json`, `schemas/common.schema.json` |
| Aprovação | `schemas/approval-record.schema.json` |
| Auditoria | `schemas/audit-event.schema.json` |
| Política | `schemas/policy-decision.request.schema.json`, `schemas/policy-decision.response.schema.json` |

## Versionamento e compatibilidade

- Alterações incompatíveis nos contratos exigem incremento de versão e atualização de
  adapters/tests de contrato.
- Campos obrigatórios de conformidade (confiança, fontes+timestamp, hipóteses, rollback
  quando aplicável, decisão de política) não podem ser removidos.
