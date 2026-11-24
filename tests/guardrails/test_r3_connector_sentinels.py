import json

from soc_agent.adapters.alert_source.read_only_skeleton import ReadOnlyAlertSourceSkeleton
from soc_agent.adapters.enrichment.read_only_skeleton import ReadOnlyEnrichmentSkeleton
from soc_agent.adapters.search_backend.read_only_skeleton import ReadOnlySearchBackendSkeleton
from soc_agent.adapters.threat_intel.read_only_skeleton import ReadOnlyThreatIntelSkeleton


SENTINELS = [
    "SYNTH_SECRET_VALUE_DO_NOT_LEAK",
    "SYNTH_TOKEN_12345",
    "SYNTH_PASSWORD_ABC",
]


def _assert_no_sentinels(obj):
    blob = json.dumps(obj, ensure_ascii=False)
    for s in SENTINELS:
        assert s not in blob


def test_connector_skeletons_do_not_leak_sentinel_values():
    req = {
        "token": SENTINELS[1],
        "password": SENTINELS[2],
        "api_key": SENTINELS[0],
        "nested": {"secret": SENTINELS[0]},
        "indicator": "SYNTH-IOC-ONLY",
        "alert_id": "SYNTH-A-1",
    }
    outputs = [
        ReadOnlyAlertSourceSkeleton().fetch_alerts(req),
        ReadOnlyAlertSourceSkeleton().get_alert(req),
        ReadOnlySearchBackendSkeleton().search(req),
        ReadOnlyEnrichmentSkeleton().enrich(req),
        ReadOnlyThreatIntelSkeleton().lookup(req),
    ]
    for out in outputs:
        _assert_no_sentinels(out)
        assert out.get("connected") is False
        assert out.get("read_only") is True
