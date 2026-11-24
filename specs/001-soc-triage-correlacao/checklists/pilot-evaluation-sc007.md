# Avaliação humana do piloto — SC-007 (T054)

> **Objetivo (SC-007):** ao menos 90% dos casos amostrados avaliados como rastreáveis e compreensíveis por analista/revisor humano.  
> **Regra:** esta avaliação é **humana**. A IA apenas **prepara** o plano, as evidências e preenche campos **objetivos**; **não** simula aprovação, decisão ou assinatura.  
> **Conformidade:** R1–R7; sem segredos/credenciais reais (R3); dados/fixtures **sintéticos**; evidências em diretório ignorado pelo git (`runtime/sc007/`).

## Plano de amostragem (preparado pela IA — Passo 1)

- **Período/janela avaliada:** 2026-11-23 (execução sintética local, preparação SC-007; evidências em `runtime/sc007/`).
- **Amostra (mín. 20 casos, ou 100% se houver menos):** 20 casos sintéticos cobrindo: triagem automática/ingestão simulada e triagem sob demanda, correlação de incidentes, proposta de consulta, proposta de contenção, casos indeterminado/bloqueado e ≥1 caso com instrução embutida tratada como IoC (R1). Nenhuma conexão a sistemas reais; nenhuma credencial real.
- **Responsável pela seleção (humano):** 
- **Critérios de inclusão (objetivos):** representação de fluxos principais (US1–US4), diversidade de status/decisões (incl. `indeterminado`, `blocked`/pendente conforme aplicável), presença de rastreabilidade (`trace`/request_id, refs/correlation_refs quando disponíveis) e evidência de comportamento read-only/proposta-sem-execução.

## Casos amostrados (IDs/refs e campos objetivos preenchidos pela IA; decisão humana em branco)

| Caso/ID | Tipo | Evidências (arquivo, refs, trace/correlation_refs) | Rastreável? (s/n) | Compreensível? (s/n) | Sem segredos? (s/n) | Observações objetivas |
|---|---|---|---|---|---|---|
| T01_auto_ingest_high | triage | `runtime\sc007\outputs\triage\T01_auto_ingest_high.json`; audit=`runtime\sc007\audit\triage_T01_auto_ingest_high.jsonl`; refs: triage_id=triage-72734f82-4e8f-4f41-8c24-f9f74d7cd5de, request_id=req-53843e97-c8b9-4939-8fad-d1bb97da5246, classificacao=indeterminado, confianca=low |  |  |  | execução CLI exit 0 |
| T02_auto_ingest_medium | triage | `runtime\sc007\outputs\triage\T02_auto_ingest_medium.json`; audit=`runtime\sc007\audit\triage_T02_auto_ingest_medium.jsonl`; refs: triage_id=triage-58cd8e4e-f0a4-4a29-aff4-086a6f917f57, request_id=req-6cd88b93-3aad-4625-91ae-bd5161ad533d, classificacao=indeterminado, confianca=low |  |  |  | execução CLI exit 0 |
| T03_auto_ingest_low | triage | `runtime\sc007\outputs\triage\T03_auto_ingest_low.json`; audit=`runtime\sc007\audit\triage_T03_auto_ingest_low.jsonl`; refs: triage_id=triage-99cc1512-97a2-4b7c-bddc-fb20538d07a1, request_id=req-6668b6b7-2308-466e-a8c0-cf49c5a6fdf3, classificacao=indeterminado, confianca=low |  |  |  | execução CLI exit 0 |
| T04_on_demand_suspicious | triage | `runtime\sc007\outputs\triage\T04_on_demand_suspicious.json`; audit=`runtime\sc007\audit\triage_T04_on_demand_suspicious.jsonl`; refs: triage_id=triage-5f34cf1b-1d82-46b9-b49e-3432ae0d4d98, request_id=req-ae36c7d6-d363-413b-afee-0595fba322c7, classificacao=indeterminado, confianca=low |  |  |  | execução CLI exit 0 |
| T05_on_demand_insufficient | triage | `runtime\sc007\outputs\triage\T05_on_demand_insufficient.json`; audit=`runtime\sc007\audit\triage_T05_on_demand_insufficient.jsonl`; refs: triage_id=triage-70f3721f-cce1-4b2c-90db-cfc1e9222f67, request_id=req-f503c799-0729-4006-b6d7-197d8aa1d94c, classificacao=indeterminado, confianca=low |  |  |  | execução CLI exit 0 |
| T06_on_demand_r1_ioc | triage | `runtime\sc007\outputs\triage\T06_on_demand_r1_ioc.json`; audit=`runtime\sc007\audit\triage_T06_on_demand_r1_ioc.jsonl`; refs: triage_id=triage-15c0a4e0-6d1b-43cf-9c88-1c5604d93153, request_id=req-383e3015-3d39-4b09-9a81-57b231fdc6a4, classificacao=indeterminado_potencial_ioc, confianca=low |  |  |  | execução CLI exit 0 |
| C01_strong_evidence_same_asset | correlation | `runtime\sc007\outputs\correlation\C01_strong_evidence_same_asset.json`; audit=`runtime\sc007\audit\corr_C01_strong_evidence_same_asset.jsonl`; refs: correlation_id=corr-4fe78fcc-b1e2-4dc2-a9b9-21a77cf6613c, request_id=req-6cc3bbab-62b0-4a5e-bf34-861ab991207e, classificacao=correlacao_possivel, confianca=medium |  |  |  | execução CLI exit 0 |
| C02_indeterminate_no_link | correlation | `runtime\sc007\outputs\correlation\C02_indeterminate_no_link.json`; audit=`runtime\sc007\audit\corr_C02_indeterminate_no_link.jsonl`; refs: correlation_id=corr-4c2922dc-ff6e-4745-bd14-5256b1ac0bcb, request_id=req-94d343fe-f535-429b-8e91-ad3570f2e477, classificacao=indeterminado, confianca=low |  |  |  | execução CLI exit 0 |
| C03_contradiction_same_asset | correlation | `runtime\sc007\outputs\correlation\C03_contradiction_same_asset.json`; audit=`runtime\sc007\audit\corr_C03_contradiction_same_asset.jsonl`; refs: correlation_id=corr-42c83b2e-74ba-41b6-87bd-a00c614f93ee, request_id=req-c8db1490-8565-442f-9533-34f4388495b7, classificacao=correlacao_possivel, confianca=medium |  |  |  | execução CLI exit 0 |
| C04_insufficient_telemetry_gap | correlation | `runtime\sc007\outputs\correlation\C04_insufficient_telemetry_gap.json`; audit=`runtime\sc007\audit\corr_C04_insufficient_telemetry_gap.jsonl`; refs: correlation_id=corr-d4b184f1-23bb-4e63-993d-45a77b83502a, request_id=req-4939bb86-5285-4ad0-bf73-34e12baceb4c, classificacao=indeterminado, confianca=low |  |  |  | execução CLI exit 0 |
| Q01_valid_complete | query_proposal | `runtime\sc007\outputs\query\Q01_valid_complete.json`; audit=`runtime\sc007\audit\query_Q01_valid_complete.jsonl`; queue=`runtime\sc007\queues\query_Q01_valid_complete.jsonl`; refs: query_proposal_id=qp-fefc9f6d-2095-43d4-8875-abce2f537125, request_id=req-12df518e-3fdd-446c-9910-69a1cdfe735d, policy=n/d/action_proposal.rego, classificacao=proposta_consulta, confianca=medium |  |  |  | execução CLI exit 0; execution_status=pending_review |
| Q02_incomplete_blocked_r7 | query_proposal | `runtime\sc007\outputs\query\Q02_incomplete_blocked_r7.json`; audit=`runtime\sc007\audit\query_Q02_incomplete_blocked_r7.jsonl`; queue=`runtime\sc007\queues\query_Q02_incomplete_blocked_r7.jsonl`; refs: query_proposal_id=qp-ef1aa9df-41d0-4df5-9d0b-7127ec9ea030, request_id=req-3ea2d7cb-b77b-419e-a898-96e50f93caf1, policy=n/d/action_proposal.rego, classificacao=proposta_consulta, confianca=medium |  |  |  | execução CLI exit 0; execution_status=blocked |
| Q03_valid_network_scope | query_proposal | `runtime\sc007\outputs\query\Q03_valid_network_scope.json`; audit=`runtime\sc007\audit\query_Q03_valid_network_scope.jsonl`; queue=`runtime\sc007\queues\query_Q03_valid_network_scope.jsonl`; refs: query_proposal_id=qp-608c1e3c-c5bb-4edd-9546-1460a087d199, request_id=req-44f3e4d8-f8c8-4a03-859a-05ec388bc4d1, policy=n/d/action_proposal.rego, classificacao=proposta_consulta, confianca=medium |  |  |  | execução CLI exit 0; execution_status=pending_review |
| Q04_partial_cost_missing_indeterminate | query_proposal | `runtime\sc007\outputs\query\Q04_partial_cost_missing_indeterminate.json`; audit=`runtime\sc007\audit\query_Q04_partial_cost_missing_indeterminate.jsonl`; queue=`runtime\sc007\queues\query_Q04_partial_cost_missing_indeterminate.jsonl`; refs: query_proposal_id=qp-ce148923-ac0d-4b41-88f8-e7ae0377e852, request_id=req-50cfc1bb-356f-478c-992c-3bb5eda17bf2, policy=n/d/action_proposal.rego, classificacao=proposta_consulta, confianca=medium |  |  |  | execução CLI exit 0; execution_status=blocked |
| Q05_valid_endpoint_scope | query_proposal | `runtime\sc007\outputs\query\Q05_valid_endpoint_scope.json`; audit=`runtime\sc007\audit\query_Q05_valid_endpoint_scope.jsonl`; queue=`runtime\sc007\queues\query_Q05_valid_endpoint_scope.jsonl`; refs: query_proposal_id=qp-7b37f4af-04ae-49a5-a479-6f8f2fe975cc, request_id=req-33227d08-290f-42a4-babd-b0044df78dea, policy=n/d/action_proposal.rego, classificacao=proposta_consulta, confianca=medium |  |  |  | execução CLI exit 0; execution_status=pending_review |
| CT01_valid_host_with_rollback | containment_proposal | `runtime\sc007\outputs\containment\CT01_valid_host_with_rollback.json`; audit=`runtime\sc007\audit\contain_CT01_valid_host_with_rollback.jsonl`; queue=`runtime\sc007\queues\contain_CT01_valid_host_with_rollback.jsonl`; refs: proposal_id=cp-14a37b5a-bf26-4c72-9d02-f93997b64767, request_id=req-31dee96a-66f3-4149-b196-849bf9cf3377, policy=n/d/action_proposal.rego, classificacao=proposta_contencao, confianca=0.7 |  |  |  | execução CLI exit 0; approval_status=pending |
| CT02_missing_rollback_blocked | containment_proposal | `runtime\sc007\outputs\containment\CT02_missing_rollback_blocked.json`; audit=`runtime\sc007\audit\contain_CT02_missing_rollback_blocked.jsonl`; queue=`runtime\sc007\queues\contain_CT02_missing_rollback_blocked.jsonl`; refs: proposal_id=cp-a8e1fd26-af20-4af7-b5fb-c7b3cbabfa9b, request_id=req-fc0dc74d-528b-402e-aaf1-870274f97565, policy=n/d/action_proposal.rego, classificacao=proposta_contencao, confianca=0.4 |  |  |  | execução CLI exit 0; approval_status=blocked |
| CT03_ambiguous_target_blocked | containment_proposal | `runtime\sc007\outputs\containment\CT03_ambiguous_target_blocked.json`; audit=`runtime\sc007\audit\CT03_ambiguous_target_blocked.jsonl` (existe, evento `containment_proposal_blocked_ambiguous_target`); queue=n/a por desenho (bloqueio sem proposta; sem enfileiramento) |  |  |  | execução CLI exit 10 (bloqueio controlado, sem traceback); stderr controlado com audit_id; sem proposta criada/enfileirada e sem execução. Nota objetiva: fila ausente por desenho (opção a), não por falha de persistência; se critério esperar queue, registrar inconsistência na avaliação humana sem reinterpretar. |
| CT04_insufficient_data_blocked | containment_proposal | `runtime\sc007\outputs\containment\CT04_insufficient_data_blocked.json`; audit=`runtime\sc007\audit\contain_CT04_insufficient_data_blocked.jsonl`; queue=`runtime\sc007\queues\contain_CT04_insufficient_data_blocked.jsonl`; refs: proposal_id=cp-951697c6-be8a-40d7-9a29-d7400fb6e147, request_id=req-0dc8ee98-5e25-4754-a305-8304afb29837, policy=n/d/action_proposal.rego, classificacao=proposta_contencao, confianca=0.2 |  |  |  | execução CLI exit 0; approval_status=blocked |
| CT05_valid_credential_token_with_rollback | containment_proposal | `runtime\sc007\outputs\containment\CT05_valid_credential_token_with_rollback.json`; audit=`runtime\sc007\audit\contain_CT05_valid_credential_token_with_rollback.jsonl`; queue=`runtime\sc007\queues\contain_CT05_valid_credential_token_with_rollback.jsonl`; refs: proposal_id=cp-88017a3d-f8b8-4f97-8eca-6fcda9cb2ab6, request_id=req-5861c514-112f-4942-a53c-dbee07a85bf6, policy=n/d/action_proposal.rego, classificacao=proposta_contencao, confianca=0.6 |  |  |  | execução CLI exit 0; approval_status=pending |

## Critérios de avaliação por caso (humano)

Marque **s** (sim) somente se:
- **Rastreável:** entrada, fontes consultadas (incl. indisponíveis quando aplicável), raciocínio/hipóteses, confiança e versões/refs estão identificáveis (R6) nas evidências referenciadas.
- **Compreensível:** o revisor entende a conclusão/proposta, incertezas/lacunas e próximos passos sem suposições indevidas.
- **Sem segredos:** nenhuma credencial/token/segredo real aparece na saída ou evidência (R3).

Caso **aprovado** = Rastreável = s **e** Compreensível = s **e** Sem segredos = s.

## Consolidação (preenchimento humano)

- **Total de casos avaliados:** 
- **Casos aprovados:** 
- **Percentual aprovado:**  % (meta: ≥ 90%)
- **Decisão SC-007:** ☐ Atende ☐ Não atende ☐ Parcial (justificar)

## Observações, divergências e ações (humano)

- 
- 

## Assinatura/registro do revisor humano

- **Nome/identificação:** 
- **Papel:** 
- **Data:** 
- **Assinatura/registro:** 

---
*Checklist preparado para avaliação humana (T054/SC-007). Campos de decisão, consolidação e assinatura devem ser preenchidos exclusivamente por humano.*
