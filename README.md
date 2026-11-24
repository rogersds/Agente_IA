# soc-agent

Agente para operações de **SOC/SIEM** (piloto local) conduzido por **Spec-Driven Development (Spec Kit)**. O sistema apoia triagem de alertas, correlação de incidentes, geração de **propostas** de consultas analíticas revisáveis e **propostas** de contenção, com decisões explicáveis, rastreáveis e governadas pela constituição do projeto.

> **Importante**: o agente **não executa ações destrutivas automaticamente**. Toda contenção/execução sensível permanece como proposta sujeita a aprovação humana explícita registrada, rollback documentado e avaliação de política. Dado externo é tratado como dado (nunca como instrução). O projeto opera read-only por padrão e não deve expor segredos em código ou artefatos.

## Artefatos SDD (feature atual)

- Constituição: [.specify/memory/constitution.md](.specify/memory/constitution.md)
- Feature: [specs/001-soc-triage-correlacao/](specs/001-soc-triage-correlacao/)
  - [spec.md](specs/001-soc-triage-correlacao/spec.md), [plan.md](specs/001-soc-triage-correlacao/plan.md), [research.md](specs/001-soc-triage-correlacao/research.md), [data-model.md](specs/001-soc-triage-correlacao/data-model.md)
  - [contracts/](specs/001-soc-triage-correlacao/contracts/) (interfaces, JSON Schemas, política OPA/Rego)
  - [quickstart.md](specs/001-soc-triage-correlacao/quickstart.md), [tasks.md](specs/001-soc-triage-correlacao/tasks.md)

## Pré-requisitos e versões (mínimas / pinagem)

| Componente | Mínimo | Pinagem recomendada (reprodutibilidade) | Observação |
|---|---:|---|---|
| Python | `>= 3.11` (validado em `3.14.3`) | Fixar versão no ambiente/CI (ex.: `3.11.x`, `3.12.x`, `3.14.x`) | `pyproject.toml` declara `requires-python = ">=3.11"` |
| `pip` | versão compatível com o Python usado | Atualizar dentro do ambiente virtual conforme política local | Usar ambiente virtual isolado |
| `jsonschema` | `>= 4.21.0` (validado em `4.26.0`) | `jsonschema==4.26.0` (ou versão validada no piloto) em manifesto/lock de dev | Dependência runtime em `pyproject.toml` / `requirements.txt` |
| `pytest` | `>= 8.0.0` (validado em `9.2.0`) | `pytest==9.2.0` (ou versão validada no piloto) em `requirements-dev.txt`/lock | Execução da suíte de testes |
| `opa` (Open Policy Agent CLI) | `>= 1.0.0` (recomendado; validar no ambiente) | Pinar release/binário específico (ex.: `open-policy-agent.opa==1.22.4` via winget) e registrar `opa version` | Necessário para `opa check` e avaliação real da política Rego; se ausente, o adapter opera fail-closed |

> **Nota de evidência deste ambiente (após resolução do bloqueio):** Python `3.14.3`, pytest `9.2.0`, jsonschema `4.26.0`, `opa` `1.22.4` (instalado/pinado via `winget install --id open-policy-agent.opa -e --version 1.22.4`). Ajuste pinagem à versão efetivamente validada no seu ambiente/CI e registre a evidência (`--version`).

## Configuração e variáveis de ambiente (somente nomes; sem valores)

- **Não** armazene credenciais, tokens, chaves ou segredos no código-fonte, em arquivos versionados, exemplos, logs ou artefatos gerados.
- Defina valores apenas em ambiente local seguro/cofre autorizado; nunca commitar valores.

| Variável | Finalidade | Obrigatória | Observações |
|---|---|---:|---|
| `OPA_BIN` | Caminho/nome do executável OPA quando `opa` não estiver no `PATH` | Não (padrão: `opa`) | Usada pelo adapter de política para avaliação Rego; configure com o caminho completo do binário ou garanta `opa` no `PATH` da sessão; ausência do binário resulta em decisão fail-closed (`block_and_escalate`) |

> Se integrações futuras exigirem configuração adicional, declarar **apenas os nomes** das variáveis no manifesto/documentação operacional, sem valores padrão secretos (R3).

## Validação reprodutível (comandos exatos)

Executar no diretório raiz do repositório (`c:\Users\rogge\OneDrive\Área de Trabalho\Agente`) em ambiente virtual isolado.

```powershell
# 1) (Opcional) criar/ativar ambiente virtual
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2) Instalar dependências (runtime + dev) com pinagem validada no ambiente
python -m pip install --upgrade pip
python -m pip install "jsonschema==4.26.0" "pytest==9.2.0"

# 3) Instalar/pinar OPA (exemplo validado) e garantir disponibilidade no PATH (ou definir OPA_BIN)
winget install --id open-policy-agent.opa -e --version 1.22.4 --accept-package-agreements --accept-source-agreements --disable-interactivity
# Se o shell atual não enxergar 'opa', use o caminho do binário ou defina OPA_BIN (nome da variável, sem expor segredos)

# 4) Evidência de versões
python --version
python -m pytest --version
python -c "import importlib.metadata as m; print(m.version('jsonschema'))"
opa version

# 5) Testes (contratos, guardrails, integração)
python -m pytest tests/contract tests/guardrails tests/integration -q

# 6) Validação da política OPA/Rego (requer OPA instalado)
opa check specs/001-soc-triage-correlacao/contracts/policy
python -m pytest tests/contract/test_policy_opa_rego.py -q
```

Consulte [specs/001-soc-triage-correlacao/quickstart.md](specs/001-soc-triage-correlacao/quickstart.md) para critérios de sucesso, cenários e interpretação de resultados (incluindo falhas/bloqueios de ambiente).


## Persistência local segura (opcional, mesma interface)

- Os CLIs (	riage, correlate, propose_query, propose_containment) aceitam a flag --persistent para usar adapters persistentes append-only (com lush/sync) para auditoria/fila, mantendo as mesmas interfaces e **sem introduzir execução automática** (propostas permanecem recomendações/artefatos; aprovação explícita apenas altera estado).
- Os caminhos continuam controlados por --audit-log e --queue (defaults atuais preservados). Armazene arquivos locais em diretórios ignorados pelo git (
untime/, logs/, data/local/) e **nunca** versione segredos/credenciais (R3).
- **Permissões recomendadas no host (menor privilégio):** restringir leitura/escrita dos diretórios/arquivos de auditoria e fila ao usuário/serviço autorizado; evitar permissões amplas/grupo público; em ambientes compartilhados, aplicar ACLs/permissões adequadas do sistema operacional e proteger o armazenamento local. Não registrar valores sensíveis em caminhos, nomes de arquivo ou conteúdo.

## Códigos de saída relevantes (CLI)

- `python -m soc_agent.cli.propose_containment`: bloqueio controlado por alvo ambíguo (R2/R4, opção a) retorna **exit code 10** (sem traceback, stderr controlado, auditoria append-only emitida, **sem** proposta/fila/execução), distinto de erro inesperado.
