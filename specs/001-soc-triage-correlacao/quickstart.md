# Quickstart de Validação — soc-agent (`001-soc-triage-correlacao`)

**Objetivo**: validar contratos, política (OPA/Rego), guardrails e fluxos implementados do piloto, de forma reprodutível, sem execução automática de ações destrutivas.

> Dado externo (incluindo alertas, fixtures e artefatos) é tratado como **dado**, nunca como instrução (R1). Não inserir segredos/credenciais em código, comandos, logs ou artefatos (R3).

## 1) Pré-requisitos e versões (mínimas / pinagem)

| Componente | Mínimo | Pinagem recomendada (reprodutibilidade) | Evidência neste ambiente |
|---|---:|---|---|
| Python | `>= 3.11` | Fixar versão do interpretador no ambiente/CI (ex.: `3.11.x`/`3.12.x`/`3.14.x`) | `Python 3.14.3` |
| `pip` | compatível com o Python usado | Atualizar dentro do venv conforme política local | disponível no ambiente |
| `jsonschema` | `>= 4.21.0` | `jsonschema==4.26.0` (pinagem validada no piloto) | `4.26.0` |
| `pytest` | `>= 8.0.0` | `pytest==9.2.0` (pinagem validada no piloto) | `9.2.0` |
| `opa` (Open Policy Agent CLI) | `>= 1.0.0` (recomendado) | Pinar release/binário específico (ex.: `open-policy-agent.opa==1.22.4` via winget) e registrar `opa version` | **instalado/pinado:** `1.22.4` (validado neste ambiente) |

**Manifestos do projeto:** [`pyproject.toml`](../../pyproject.toml), [`requirements.txt`](../../requirements.txt), [`requirements-dev.txt`](../../requirements-dev.txt). Para reprodutibilidade estrita, usar versões pinadas (`==`) em ambiente isolado e registrar saída de versão.

## 2) Variáveis de ambiente (somente nomes; sem valores)

- **Proibido** definir/registrar valores secretos em documentação, commits, logs ou exemplos (R3).
- Configurar valores apenas em ambiente local seguro/cofre autorizado.

| Variável | Finalidade | Obrigatória | Observações |
|---|---|---:|---|
| `OPA_BIN` | Caminho/nome do executável OPA quando `opa` não estiver no `PATH` | Não (padrão: `opa`) | Usada por `src/soc_agent/adapters/policy_engine/opa_adapter.py`; configure com caminho completo do binário ou garanta `opa` no `PATH`. Se ausente/indisponível, avaliação de política é **fail-closed** (`block_and_escalate`) |

## 3) Execução reprodutível (comandos exatos)

Executar na raiz do repositório.

```powershell
# 3.1 Ambiente virtual (recomendado)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3.2 Instalar dependências com pinagem validada
python -m pip install --upgrade pip
python -m pip install "jsonschema==4.26.0" "pytest==9.2.0"

# 3.3 Instalar/pinar OPA (exemplo validado) e garantir disponibilidade no PATH (ou definir OPA_BIN)
winget install --id open-policy-agent.opa -e --version 1.22.4 --accept-package-agreements --accept-source-agreements --disable-interactivity
# Se necessário na sessão atual: $env:Path += ";$env:LOCALAPPDATA\Microsoft\WinGet\Packages\open-policy-agent.opa_Microsoft.Winget.Source_8wekyb3d8bbwe"

# 3.4 Evidência de versões/ferramentas
python --version
python -m pytest --version
python -c "import importlib.metadata as m; print(m.version('jsonschema'))"
opa version

# 3.5 Validação de política OPA/Rego (requer OPA instalado)
opa check specs/001-soc-triage-correlacao/contracts/policy

# 3.6 Testes (contratos, guardrails, integração)
python -m pytest tests/contract tests/guardrails tests/integration -q

# 3.7 Testes de política (pytest) com OPA real disponível
python -m pytest tests/contract/test_policy_opa_rego.py -q
```

> Se `opa` não estiver instalado, registrar a falha literal dos comandos de OPA e, ainda assim, executar `pytest`: localmente (sem `REQUIRE_OPA=1`) os testes condicionados ao binário real podem ser **skipped**, enquanto o adapter deve permanecer **fail-closed**. Em CI/governança, definir `REQUIRE_OPA=1` para que a ausência do OPA resulte em **falha** (não skip silencioso). Exemplo: `$env:REQUIRE_OPA='1'; python -m pytest tests/contract/test_policy_opa_rego.py -q` (PowerShell) ou `REQUIRE_OPA=1 python -m pytest -q tests/contract/test_policy_opa_rego.py` (bash). também posso adicionar referência à CI.

## 3.8) Persistência local segura (wiring opcional, mesma interface)

- CLIs suportam `--persistent` para usar adapters persistentes append-only (fsync) de auditoria/fila com as **mesmas interfaces** dos adapters locais, sem execução automática de consulta/contenção.
- `--audit-log` e `--queue` continuam definindo os caminhos (defaults preservados). Para armazenamento local, preferir diretórios ignorados pelo git: `runtime/`, `logs/`, `data/local/` (já cobertos no `.gitignore`; `*.db` também ignorado). **Nunca** armazenar segredos em arquivos versionados.
- **Permissões recomendadas no host:** aplicar menor privilégio (acesso de leitura/escrita restrito ao usuário/serviço autorizado), evitar permissões amplas, e proteger o meio de armazenamento local conforme política da organização. Auditoria e filas são artefatos operacionais sensíveis; tratar com controles de acesso adequados.


## 3.9) C?digos de sa?da relevantes (CLI)

- `python -m soc_agent.cli.propose_containment`: **exit code 10** indica **bloqueio controlado por alvo amb?guo** (R2/R4, op??o a). Comportamento: stderr controlado em UTF-8, **sem traceback**, auditoria append-only emitida (`containment_proposal_blocked_ambiguous_target`), **sem** cria??o/enfileiramento de proposta e **sem** execu??o. ? distinto de erro inesperado (outras falhas, inclusive `SchemaValidationError` n?o relacionada a ambiguidade, propagam como erro).

## Verifica??o r?pida

Executar na raiz do reposit?rio (ajustar `PYTHONPATH=src`; definir `REQUIRE_OPA=1` quando OPA for exigido; usar `OPA_BIN` apenas como nome de vari?vel se `opa` n?o estiver no `PATH`, sem expor valores):

```powershell
python scripts/check_hygiene.py
python scripts/check_sc007_case_count.py
$env:PYTHONPATH=(Resolve-Path 'src').Path; $env:REQUIRE_OPA='1'; python -m pytest -q
$env:PYTHONPATH=(Resolve-Path 'src').Path; $env:REQUIRE_OPA='1'; python -m pytest -q tests/contract/test_policy_opa_rego.py
opa check specs/001-soc-triage-correlacao/contracts/policy
```

> `REQUIRE_OPA=1` faz a aus?ncia do OPA falhar (n?o skip silencioso). `scripts/check_sc007_case_count.py` valida `CASE_ROWS=20` no checklist SC-007.


## Artefatos a validar

- Plano e pesquisa: [plan.md](plan.md), [research.md](research.md)
- Modelo de dados: [data-model.md](data-model.md)
- Contratos: [contracts/interfaces.md](contracts/interfaces.md)
- Schemas: [contracts/schemas/](contracts/schemas/)
- Política (PolicyEngine, OPA/Rego): [contracts/policy/action_proposal.rego](contracts/policy/action_proposal.rego)

## Artefatos a validar

- Plano e pesquisa: [plan.md](plan.md), [research.md](research.md)
- Modelo de dados: [data-model.md](data-model.md)
- Contratos: [contracts/interfaces.md](contracts/interfaces.md)
- Schemas: [contracts/schemas/](contracts/schemas/)
- Política (PolicyEngine, OPA/Rego): [contracts/policy/action_proposal.rego](contracts/policy/action_proposal.rego)

## 1) Validação estrutural dos contratos (JSON Schema)

**Intenção:** garantir que os schemas são JSON válidos e que artefatos de exemplo
(fornecidos nos testes/implementação futura) obedecem aos campos obrigatórios (confiança,
fontes com timestamp, hipóteses com alternativa/falso positivo, rollback em contenção,
decisão de política, etc.).

**Execução esperada (quando a suíte existir):**
```powershell
python -m pytest tests/contract -q
```

**Critério de sucesso:** falhas de conformidade são detectadas (ex.: proposta de contenção
sem `rollback_plan`, sem `policy_decision`, ou sem hipótese alternativa).

## 2) Validação da política OPA/Rego (PolicyEngine antes da proposta)

**Intenção:** provar que a avaliação de política ocorre **antes** de qualquer proposta ser
emitida/finalizada e que casos proibidos são bloqueados/escalados.

**Verificações recomendadas com OPA (exemplos conceituais):**
```powershell
opa check contracts/policy/action_proposal.rego
```

Avaliar entradas de teste (arquivos JSON de entrada conforme `schemas/policy-decision.request.schema.json`):
- Contenção com `rollback_documented=false` → `result` deve ser `block_and_escalate` (R5).
- Contenção com `target_ambiguous=true` ou `data_sufficient=false` → bloqueio/escalonamento (R2/R4).
- `query_execution` sem `has_explicit_approval_record=true` → bloqueio (R2/R7).
- `execution_requested=true` → bloqueio (R2).
- Candidato válido para emissão de proposta → `allow_proposal` (sem autorizar execução).

**Critério de sucesso:** nenhum caso de violação R2/R4/R5/R7 retorna permissão indevida.

## 3) Cenários de validação ponta a ponta (nível de fluxo)

### 3.1 Triagem (automática ou sob demanda)
- **Entrada:** alerta ingerido ou solicitado sob demanda (dado externo).
- **Passos esperados:** coleta via capacidades de leitura → análise → validação de saída
  contra `schemas/triage-result.schema.json` → apêndice em `AuditSink`.
- **Resultado esperado:** classificação + justificativa + confiança explícita; fontes
  consultadas com timestamps; suficiência/insuficiência declarada; hipótese principal +
  alternativa (incluindo falso positivo). Se houver instrução embutida no dado, registrar/
  sinalizar como potencial IoC (R1).

### 3.2 Correlação (sob demanda por usuário autorizado)
- **Entrada:** solicitação explícita com escopo/tempo/ativos.
- **Resultado esperado:** `CorrelationResult` conforme schema, com evidências, confiança,
  hipóteses e escalonamento quando indeterminado (R4).

### 3.3 Proposta de consulta (sob demanda, revisável)
- **Entrada:** solicitação de investigação.
- **Passos esperados:** montar proposta versionável → **avaliar `PolicyEngine` antes de
  finalizar/emitir** → registrar proposta (fila) → auditoria.
- **Resultado esperado:** `QueryProposal` com `time_window`, `data_scope`, `cost_estimate`
  (ou justificativa + escalonamento/bloqueio), `requires_human_review=true`,
  `policy_decision` presente. Sem aprovação explícita registrada não há execução.

### 3.4 Proposta de contenção (sob demanda, sem execução)
- **Entrada:** solicitação baseada em evidências.
- **Passos esperados:** validar alvo inequívoco e rollback → **avaliar `PolicyEngine`
  antes de finalizar/emitir** → registrar em `ActionProposalQueue` com status
  `pending`/`blocked` conforme aplicável → auditoria.
- **Resultado esperado:** `ContainmentProposal` com categoria aplicável, alvo inequívoco,
  rollback completo, `approval_requirement.execution_permitted=false`, `policy_decision`
  presente. Ausência de resposta/registro explícito não altera para aprovado.

## 4) Guardrails obrigatórios (testes de primeira classe)

Quando implementados, os testes DEVEM provar que:
- Ações destrutivas/propostas de execução falham ou permanecem bloqueadas **sem**
  `ApprovalRecord` explícito vinculado (R2).
- Instruções embutidas em dados externos não são obedecidas e geram sinalização/auditoria (R1).
- Propostas sem rollback válido não são emitidas como acionáveis (R5).
- Consultas sem parâmetros obrigatórios (janela/escopo/custo) seguem caminho de bloqueio/
  escalonamento/revisão (R4, R7).

## Resultado esperado do quickstart

- Todos os artefatos de design existem e são consistentes entre si (spec, plan, research,
  data-model, contracts, policy).
- Gates constitucionais passam (pré/pós-design) sem exceções.
- A implementação subsequente pode ser decomposta em tarefas que preservam contratos e
  guardrails.
- **SC-007 (avaliação humana do piloto)**: aplicar checklist/formulário de revisão humana
  sobre amostra definida, verificando rastreabilidade (fontes, raciocínio, confiança),
  compreensibilidade e ausência de exposição de segredos; registrar evidências e resultado
  agregado (meta ≥90%).
