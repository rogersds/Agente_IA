# Fluxo de aprovação humana e execução externa (DESENHO)

**Status:** especificação de desenho (Passo 5). **Nenhum caminho no código do agente executa ação ou consulta automaticamente.** Execução, quando existir no futuro, é componente **separado** do agente.

## Princípios normativos (R1–R7)

- **R2:** nenhuma ação destrutiva é executada automaticamente; execução exige aprovação humana **explícita e identificada**, vinculada inequivocamente à proposta. Ausência de registro explícito **não** implica aprovação.
- **R5:** proposta acionável exige rollback documentado antes da aprovação/acionamento.
- **R7:** consultas são artefatos versionados/revisáveis (janela, escopo, custo); sem aprovação explícita registrada não há execução.
- **R3/R6:** sem segredos em registros; toda decisão é auditável (append-only) com rastreabilidade.

## Modelo atual no agente (somente proposta/estado, sem execução)

- Contrato: `contracts/schemas/approval-record.schema.json` (registro de decisão vinculada).
- Domínio/validação: `src/soc_agent/domain/approval.py` (decisões `approved|rejected`, vínculo `proposal_id`+`proposal_type`, aprovador identificado `id`/`display_name`, escopo e `decided_at`).
- Serviço: `src/soc_agent/application/approval_service.py` registra decisão explícita, valida contrato/domínio, atualiza **apenas** estado/metadados na fila de propostas e emite evento de auditoria; **não executa** ações nem consultas.

## Fluxo de aprovação (especificação)

1. **Geração da proposta (agente, read-only):** triagem/correlação gera evidências; `propose_query` ou `propose_containment` emite artefato versionável com `policy_decision`, rastreabilidade e, no caso de contenção, `approval_requirement.execution_permitted=false` e rollback. Fila registra estado inicial (`pending`/`blocked` conforme regras).
2. **Revisão humana:** revisor analisa proposta, evidências, impacto, rollback (R5) e parâmetros (R7). Dados externos permanecem dados (R1).
3. **Registro de decisão explícita (vínculo inequívoco):**
   - **Identidade do aprovador:** identificador único e nome/apresentação (`approver.id`, `approver.display_name`), conforme política organizacional.
   - **Vínculo à proposta:** `proposal_id` e `proposal_type` (`containment` ou `query_execution`) devem corresponder exatamente à proposta revisada; registro sem vínculo válido não é aceito como aprovação.
   - **Decisão:** `approved` | `rejected` | `revoked` | `expired` (estados de ciclo de vida). *Nota de implementação atual:* o contrato/validação existente suporta `approved|rejected`; extensão para `revoked/expired` requer evolução controlada de schema/validação e testes de contrato (sem quebrar compatibilidade sem aviso).
   - **Horário e justificativa:** `decided_at` (timestamp) obrigatório; justificativa/motivo registrado (recomendado/obrigatório por política) para auditoria.
   - **Escopo:** escopo da aprovação (alvo, janela, limites) explicitamente registrado e coerente com a proposta.
4. **Auditoria:** cada registro/alteração de decisão gera evento append-only com IDs, decisão, ator, timestamps e referências correlatas, sem segredos (R3/R6).
5. **Efeito no agente:** atualização de estado da proposta/fila (ex.: aprovado/rejeitado/bloqueado/revogado/expirado) para fins de rastreio. **Nenhuma execução é disparada pelo agente.**

## Execução futura (componente separado, fora do agente)

Qualquer execução real de consulta ou contenção, se necessária no futuro, deve ocorrer em **serviço/componente externo** ao `soc_agent`, com:

- **Autorização:** somente mediante `approval-record` explícito, válido, vigente (não revogado/expirado), vinculado à proposta específica.
- **Controles de acesso:** identidade autenticada, menor privilégio, segregação de funções quando aplicável.
- **Janela/escopo restritos:** execução limitada estritamente ao aprovado (janela temporal, escopo, alvo, parâmetros), conforme proposta versionada (R7).
- **Rollback validado:** pré-condições e plano de rollback verificados antes de execução (R5).
- **Trilha de auditoria:** registros append-only de solicitação, aprovação, início/fim, resultado e ações de rollback, sem segredos.
- **Fail-safe:** falhas de validação, expiração, revogação ou ambiguidade impedem execução e geram escalonamento.

## Critérios de conformidade

- O agente permanece exclusivamente proponente/read-only: **nenhum** módulo/CLI do `soc_agent` realiza conexão de execução real, disparo de contenção ou execução de consulta aprovada.
- Testes de guardrail devem falhar se caminhos de execução automática forem introduzidos.
- Evoluções de contrato/ciclo de vida (`revoked/expired`) devem ser versionadas e validadas por testes antes de uso operacional.
