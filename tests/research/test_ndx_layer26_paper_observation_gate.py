from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from jsonschema import Draft202012Validator
import polars as pl

from sis.research.ndx.artifacts import sha256_file
from support.cli import invoke_cli
from research.test_ndx_layer25_strategy_lab_export import (
    _approved_layer24_artifacts,
    _validate_json_artifact,
)


def test_layer26_approves_paper_observation_review_with_local_quote(tmp_path) -> None:
    data_dir, artifact_dir, reports_dir = _layer25_export(tmp_path)
    quotes_path = _write_xyz_quote(data_dir)

    result = invoke_cli(
        [
            "research-ndx-paper-observation-gate",
            "--data-dir",
            str(data_dir),
            "--artifact-dir",
            str(artifact_dir),
            "--reports-dir",
            str(reports_dir),
            "--quotes-path",
            str(quotes_path),
        ]
    )

    assert result.exit_code == 0, result.stdout
    decision_path = artifact_dir / "paper_observation_gate_decision.json"
    payload = json.loads(decision_path.read_text(encoding="utf-8"))
    assert payload["decision"] == "APPROVE_PAPER_OBSERVATION_REVIEW"
    assert payload["paper_observation_dry_run_ready"] is True
    assert payload["permits_operator_promotion_review"] is True
    assert payload["permits_paper_candidate"] is False
    assert payload["permits_paper_intent_preview"] is False
    assert payload["permits_live_order"] is False
    assert payload["quotes_hash"] == sha256_file(quotes_path)
    _validate_json_artifact(
        schema_path=Path("schemas/ndx_paper_observation_gate_decision.v1.schema.json"),
        artifact_path=decision_path,
    )


def test_layer26_revises_when_xyz_quote_is_missing(tmp_path) -> None:
    data_dir, artifact_dir, reports_dir = _layer25_export(tmp_path)
    quotes_path = _write_xyz_quote(data_dir, symbol="SP500")

    result = invoke_cli(
        [
            "research-ndx-paper-observation-gate",
            "--data-dir",
            str(data_dir),
            "--artifact-dir",
            str(artifact_dir),
            "--reports-dir",
            str(reports_dir),
            "--quotes-path",
            str(quotes_path),
        ]
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(
        (artifact_dir / "paper_observation_gate_decision.json").read_text(encoding="utf-8")
    )
    assert payload["decision"] == "REVISE_2_5"
    assert payload["paper_observation_dry_run_ready"] is False
    assert "PAPER_QUOTE_MISSING" in payload["block_reasons"]


def test_layer26_schema_is_valid() -> None:
    Draft202012Validator.check_schema(
        json.loads(
            Path("schemas/ndx_paper_observation_gate_decision.v1.schema.json").read_text(
                encoding="utf-8"
            )
        )
    )


def _layer25_export(tmp_path: Path) -> tuple[Path, Path, Path]:
    data_dir, artifact_dir, reports_dir = _approved_layer24_artifacts(tmp_path)
    result = invoke_cli(
        [
            "research-ndx-strategy-lab-export",
            "--data-dir",
            str(data_dir),
            "--artifact-dir",
            str(artifact_dir),
            "--reports-dir",
            str(reports_dir),
        ]
    )
    assert result.exit_code == 0, result.stdout
    return data_dir, artifact_dir, reports_dir


def _write_xyz_quote(data_dir: Path, *, symbol: str = "XYZ100") -> Path:
    quotes_path = data_dir / "normalized/quotes.parquet"
    quotes_path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    pl.DataFrame(
        [
            {
                "ts_client": now,
                "venue": "trade_xyz",
                "canonical_symbol": symbol,
                "venue_symbol": symbol,
                "best_bid": 99.9,
                "best_ask": 100.1,
                "bid_price": 99.9,
                "ask_price": 100.1,
                "mark_price": 100.0,
                "mid_price": 100.0,
                "oracle_price": 100.0,
                "index_price": 100.0,
                "spread_bps": 2.0,
                "depth_10bps_usd": 5000.0,
                "funding_rate": 0.0,
                "source_confidence": 0.95,
                "venue_quality_score": 0.95,
                "trade_allowed": True,
                "fee_mode": "standard",
                "oracle_ts_ms": int(now.timestamp() * 1000),
                "market_status": "open",
                "is_tradable": True,
            }
        ]
    ).write_parquet(quotes_path)
    return quotes_path
