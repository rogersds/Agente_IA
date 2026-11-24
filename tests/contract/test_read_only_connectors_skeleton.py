from soc_agent.adapters.alert_source.read_only_skeleton import ReadOnlyAlertSourceSkeleton, ReadOnlyConnectorConfig
from soc_agent.adapters.enrichment.read_only_skeleton import ReadOnlyEnrichmentSkeleton
from soc_agent.adapters.search_backend.read_only_skeleton import ReadOnlySearchBackendSkeleton
from soc_agent.adapters.threat_intel.read_only_skeleton import ReadOnlyThreatIntelSkeleton


def test_alert_source_skeleton_contract_and_fail_safe():
    cfg = ReadOnlyConnectorConfig(timeout_seconds=3.0, max_retries=1, enabled=False)
    s = ReadOnlyAlertSourceSkeleton(cfg)
    r1 = s.fetch_alerts({"query": "x"})
    r2 = s.get_alert({"alert_id": "SYNTH-A"})
    for r, op in ((r1, "fetch_alerts"), (r2, "get_alert")):
        assert r["status"] == "unavailable"
        assert r["read_only"] is True
        assert r["connected"] is False
        assert r["request_ref"]["operation"] == op
        assert r["timeout_seconds"] == 3.0
        assert r["max_retries"] == 1
        assert "timestamp" in r


def test_search_backend_skeleton_no_execution_and_fail_safe():
    s = ReadOnlySearchBackendSkeleton(ReadOnlyConnectorConfig(timeout_seconds=2.5, max_retries=2))
    r = s.search({"time_window": {"start": "s", "end": "e"}, "data_scope": {"index": "i"}, "cost_estimate": {"summary": "x"}})
    assert r["status"] == "unavailable"
    assert r["read_only"] is True
    assert r["execution_performed"] is False
    assert r["request_ref"]["has_time_window"] is True
    assert r["request_ref"]["has_data_scope"] is True
    assert r["request_ref"]["has_cost_estimate"] is True
    assert "Consulta real não executada" in r["note"]


def test_enrichment_and_threat_intel_skeletons_fail_safe():
    e = ReadOnlyEnrichmentSkeleton(ReadOnlyConnectorConfig())
    t = ReadOnlyThreatIntelSkeleton(ReadOnlyConnectorConfig())
    re = e.enrich({"indicators": ["SYNTH-IOC"]})
    rt = t.lookup({"indicator": "SYNTH-IOC"})
    assert re["status"] == "unavailable" and re["read_only"] is True and re["connected"] is False
    assert rt["status"] == "unavailable" and rt["read_only"] is True and rt["connected"] is False
    assert re["timeout_seconds"] == 5.0 and re["max_retries"] == 2
    assert rt["timeout_seconds"] == 5.0 and rt["max_retries"] == 2
