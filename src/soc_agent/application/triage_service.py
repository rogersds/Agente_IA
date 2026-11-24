from __future__ import annotations

from typing import Any
from uuid import uuid4

from soc_agent.application.input_guard import analyze_external_payload
from soc_agent.application.llm_gateway import generate_structured
from soc_agent.application.orchestrator import RuntimeContext, emit_audit, unavailable_source
from soc_agent.contracts_runtime.validator import SchemaValidator
from soc_agent.domain.common import classification, consulted_source, data_sufficiency, hypotheses, hypothesis, make_trace, utc_now_iso
from soc_agent.domain.triage import build_indeterminate_triage, validate_triage_result
from soc_agent.ports.alert_source import AlertSource
from soc_agent.ports.enrichment_provider import EnrichmentProvider
from soc_agent.ports.llm_provider import LlmProvider
from soc_agent.ports.search_backend import SearchBackend
from soc_agent.ports.threat_intel_store import ThreatIntelStore


class TriageService:
    def __init__(
        self,
        alert_source: AlertSource | None = None,
        search_backend: SearchBackend | None = None,
        enrichment: EnrichmentProvider | None = None,
        threat_intel: ThreatIntelStore | None = None,
        llm_provider: LlmProvider | None = None,
        validator: SchemaValidator | None = None,
    ):
        self.alert_source = alert_source
        self.search_backend = search_backend
        self.enrichment = enrichment
        self.threat_intel = threat_intel
        self.llm_provider = llm_provider
        self.validator = validator or SchemaValidator()

    def triage_alert(self, alert: dict[str, Any], ctx: RuntimeContext, request_id: str | None = None) -> dict[str, Any]:
        req_id = request_id or f"req-{uuid4()}"
        alert_id = str(alert.get("alert_id") or "unknown-alert")
        consulted: list[dict[str, Any]] = []
        src = alert.get("source")
        src_id = src.get("source_id") if isinstance(src, dict) else (str(src) if src is not None else None)
        consulted.append(consulted_source("alert_source", {"alert_id": alert_id}, "ok", utc_now_iso(), source_id=src_id))
        guard = analyze_external_payload(alert.get("content"))
        ioc_signals = guard.get("ioc_signals", [])

        # read-only enrichment/ti/search best-effort
        consulted.extend(self._collect_optional_sources(alert))
        known = ["alert_received"]
        missing: list[str] = []
        if not (alert.get("attributes") or alert.get("occurred_at")):
            missing.append("contexto_completo_do_alerta")

        trace = make_trace(request_id=req_id, prompt_version=ctx.prompt_version, agent_version=ctx.agent_version)
        llm_meta = {"model_version": None, "prompt_version": None}
        if self.llm_provider:
            llm_resp = generate_structured(self.llm_provider, {"request_id": req_id, "purpose": "triage", "input": {"alert": alert}})
            llm_meta["model_version"] = llm_resp.get("model_version")
            llm_meta["prompt_version"] = llm_resp.get("prompt_version")
            trace = make_trace(
                request_id=req_id,
                model_version=llm_meta["model_version"],
                prompt_version=llm_meta["prompt_version"] or ctx.prompt_version,
                agent_version=ctx.agent_version,
            )

        if guard.get("has_embedded_instructions"):
            reason = "Conteúdo externo contém instrução embutida; tratado como dado/potencial IoC (R1). Análise limitada a evidências seguras."
            result = build_indeterminate_triage(
                triage_id=f"triage-{uuid4()}",
                alert_id=alert_id,
                consulted_sources=consulted,
                known=known + ["possivel_tentativa_de_injecao_detectada"],
                missing=missing or ["confirmacao_de_impacto"],
                reason=reason,
                trace=trace,
                ioc_signals=ioc_signals,
            )
            result["classification"] = classification(
                "indeterminado_potencial_ioc",
                "Texto dirigido ao agente identificado em dado externo; não obedecido, sinalizado para revisão humana (R1).",
            )
            result["hypotheses"] = hypotheses(
                primary=hypothesis("Tentativa de injeção de instrução em dado externo", "Padrões de comando/instrução embutidos no conteúdo.", False),
                alternatives=[hypothesis("Falso positivo (texto benigno)", "O texto pode ser legítimo ou informativo sem intenção maliciosa.", True)],
            )
            validate_triage_result(result)
            self.validator.validate("triage-result.schema.json", result)
            emit_audit(ctx, "triage_r1_ioc", {"alert_id": alert_id}, "Instrução embutida detectada em dado externo; tratada como IoC potencial.", {"triage_id": result["triage_id"], "status": "indeterminado"}, consulted_sources=consulted, confidence=result.get("confidence"), model_version=llm_meta["model_version"], prompt_version=llm_meta["prompt_version"] or ctx.prompt_version, correlation_refs=[alert_id], trace=trace)
            return result

        insufficient = len(missing) > 0
        if insufficient:
            reason = "Dados insuficientes para classificação conclusiva; resultado marcado como indeterminado e escalado (R4)."
            result = build_indeterminate_triage(
                triage_id=f"triage-{uuid4()}",
                alert_id=alert_id,
                consulted_sources=consulted,
                known=known,
                missing=missing,
                reason=reason,
                trace=trace,
            )
            self.validator.validate("triage-result.schema.json", result)
            emit_audit(ctx, "triage_indeterminate", {"alert_id": alert_id}, reason, {"triage_id": result["triage_id"]}, consulted_sources=consulted, confidence=result.get("confidence"), model_version=llm_meta["model_version"], prompt_version=llm_meta["prompt_version"] or ctx.prompt_version, correlation_refs=[alert_id], trace=trace)
            return result

        # basic deterministic classification for pilot
        sev = str(alert.get("reported_severity") or "unknown").lower()
        label = "suspeito" if sev in {"high", "critical", "medium"} else "informativo_ou_baixa_prioridade"
        result = {
            "triage_id": f"triage-{uuid4()}",
            "alert_id": alert_id,
            "classification": classification(label, f"Classificação inicial baseada em atributos disponíveis do alerta (severidade reportada: {sev})."),
            "confidence": "medium" if sev != "unknown" else "low",
            "consulted_sources": consulted,
            "data_sufficiency": data_sufficiency(True, known=known + ["atributos_basicos_disponiveis"], missing=[], escalation_required=False),
            "hypotheses": hypotheses(
                primary=hypothesis("Atividade potencialmente maliciosa ou relevante", "Sinais do alerta indicam necessidade de análise conforme severidade/contexto.", False),
                alternatives=[hypothesis("Falso positivo", "O alerta pode refletir comportamento benigno ou regra excessivamente sensível.", True)],
            ),
            "recommended_next_steps": ["Correlacionar com eventos relacionados", "Revisar evidências adicionais se necessário"],
            "escalation": None,
            "trace": trace,
        }
        validate_triage_result(result)
        self.validator.validate("triage-result.schema.json", result)
        emit_audit(ctx, "triage_completed", {"alert_id": alert_id}, "Triagem concluída com base nas evidências consultadas.", {"triage_id": result["triage_id"], "label": label}, consulted_sources=consulted, confidence=result.get("confidence"), model_version=llm_meta["model_version"], prompt_version=llm_meta["prompt_version"] or ctx.prompt_version, correlation_refs=[alert_id], trace=trace)
        return result

    def _collect_optional_sources(self, alert: dict[str, Any]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        # best-effort read-only consultations; failures become unavailable evidence entries
        for cap, client, ref in [
            ("search_backend", self.search_backend, {"alert_id": alert.get("alert_id")}),
            ("enrichment", self.enrichment, {"alert_id": alert.get("alert_id")}),
            ("threat_intel", self.threat_intel, {"alert_id": alert.get("alert_id")}),
        ]:
            if client is None:
                out.append(unavailable_source(cap, ref, "capability_not_configured"))
                continue
            try:
                if cap == "search_backend":
                    client.search({"query": ref, "time_window": None, "scope": None})
                elif cap == "enrichment":
                    client.enrich({"subject": ref})
                else:
                    client.lookup({"indicator": ref})
                out.append(consulted_source(cap, ref, "ok", utc_now_iso()))
            except Exception as e:
                out.append(unavailable_source(cap, ref, f"error:{e}"))
        return out
