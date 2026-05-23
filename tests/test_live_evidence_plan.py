from datetime import datetime

from sis.live_evidence_plan import build_live_evidence_plan


def test_build_live_evidence_plan_on_weekend_picks_shared_next_window() -> None:
    now = datetime.fromisoformat("2026-05-23T01:45:00+00:00")  # Sat 10:45 JST

    plan = build_live_evidence_plan(["QQQ", "SPY", "XAU"], now=now)

    assert plan.symbols == ["QQQ", "SPY", "XAU"]
    assert plan.target_start_jst.isoformat() == "2026-05-26T22:45:00+09:00"
    assert plan.target_spec_jst == "2026-05-26T22:45"


def test_build_live_evidence_plan_during_index_session_uses_index_start() -> None:
    now = datetime.fromisoformat("2026-05-22T14:05:00+00:00")  # Fri 23:05 JST

    plan = build_live_evidence_plan(["QQQ", "SPY", "XAU"], now=now)

    assert plan.target_start_jst.isoformat() == "2026-05-22T22:45:00+09:00"
