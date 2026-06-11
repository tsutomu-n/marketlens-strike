from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

from sis.paper.observation_session import (
    PaperObservationThresholds,
    create_paper_observation_session,
)


def _write_source(path: Path, payload: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _schema() -> dict:
    return json.loads(Path("schemas/paper_observation_session_manifest.v1.schema.json").read_text())


def test_create_paper_observation_session_writes_schema_valid_manifest(tmp_path) -> None:
    data_dir = tmp_path / "data"
    backtest = _write_source(data_dir / "research/strategy_lifecycle/backtest.json", {"ok": True})
    promotion = _write_source(data_dir / "research/ndx/operator_promotion.json", {"ok": True})
    intent_preview = _write_source(data_dir / "bot/paper_intent_preview.json", [{"ok": True}])

    result = create_paper_observation_session(
        data_dir=data_dir,
        source_backtest_acceptance_path=backtest,
        source_operator_promotion_path=promotion,
        source_intent_preview_path=intent_preview,
        session_id="session-001",
        thresholds=PaperObservationThresholds(
            min_fills_for_pass=2,
            min_trading_days_for_pass=1,
            max_blocked_rate=0.25,
            max_consecutive_blocked=2,
            max_open_position_age_hours=12.0,
        ),
        smoke=True,
    )

    payload = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    Draft202012Validator(_schema()).validate(payload)
    assert result.session_id == "session-001"
    assert result.session_dir == data_dir / "paper/observations/session-001"
    assert result.observation_ledger_path == result.session_dir / "paper_observation_ledger.jsonl"
    assert payload["schema_version"] == "paper_observation_session_manifest.v1"
    assert payload["observation_ledger_path"] == result.observation_ledger_path.as_posix()
    assert payload["paper_orders_path"] == (data_dir / "paper/orders.parquet").as_posix()
    assert payload["source_backtest_acceptance_sha256"].startswith("sha256:")
    assert payload["source_operator_promotion_sha256"].startswith("sha256:")
    assert payload["source_intent_preview_sha256"].startswith("sha256:")
    assert payload["thresholds"]["min_fills_for_pass"] == 2
    assert payload["thresholds"]["min_trading_days_for_pass"] == 1
    assert payload["thresholds"]["max_blocked_rate"] == 0.25
    assert payload["smoke"] is True
    assert payload["permits_live_order"] is False
    assert payload["wallet_used"] is False
    assert payload["venue_write_used"] is False
    assert payload["exchange_write_used"] is False


def test_create_paper_observation_session_fails_closed_for_missing_source(tmp_path) -> None:
    data_dir = tmp_path / "data"
    backtest = _write_source(data_dir / "research/strategy_lifecycle/backtest.json", {"ok": True})
    intent_preview = _write_source(data_dir / "bot/paper_intent_preview.json", [{"ok": True}])

    with pytest.raises(FileNotFoundError, match="source artifact missing"):
        create_paper_observation_session(
            data_dir=data_dir,
            source_backtest_acceptance_path=backtest,
            source_operator_promotion_path=data_dir / "research/ndx/missing.json",
            source_intent_preview_path=intent_preview,
            session_id="session-001",
        )


def test_paper_observation_session_manifest_schema_is_valid() -> None:
    Draft202012Validator.check_schema(_schema())
