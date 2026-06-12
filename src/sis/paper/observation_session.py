from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sis.research.ndx.artifacts import sha256_file, utc_now_iso, write_json

SCHEMA_VERSION = "paper_observation_session_manifest.v1"


@dataclass(frozen=True)
class PaperObservationThresholds:
    min_fills_for_pass: int = 20
    min_trading_days_for_pass: int = 10
    max_blocked_rate: float = 0.5
    max_consecutive_blocked: int = 3
    max_open_position_age_hours: float = 0.0


@dataclass(frozen=True)
class PaperObservationSession:
    session_id: str
    session_dir: Path
    manifest_path: Path
    observation_ledger_path: Path
    payload: dict[str, Any]


def create_paper_observation_session(
    *,
    data_dir: Path,
    source_backtest_acceptance_path: Path,
    source_operator_promotion_path: Path,
    source_intent_preview_path: Path,
    source_paper_candidate_pack_path: Path | None = None,
    source_promotion_decision_path: Path | None = None,
    session_id: str | None = None,
    thresholds: PaperObservationThresholds | None = None,
    smoke: bool = False,
) -> PaperObservationSession:
    selected_session_id = _validate_session_id(session_id or _default_session_id())
    selected_thresholds = thresholds or PaperObservationThresholds()
    for path in (
        source_backtest_acceptance_path,
        source_operator_promotion_path,
        source_intent_preview_path,
        *(
            path
            for path in (source_paper_candidate_pack_path, source_promotion_decision_path)
            if path is not None
        ),
    ):
        if not path.exists():
            raise FileNotFoundError(f"paper observation session source artifact missing: {path}")

    session_dir = data_dir / "paper/observations" / selected_session_id
    manifest_path = session_dir / "paper_observation_session_manifest.json"
    observation_ledger_path = session_dir / "paper_observation_ledger.jsonl"
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "session_id": selected_session_id,
        "created_at": utc_now_iso(),
        "data_dir": data_dir.as_posix(),
        "session_dir": session_dir.as_posix(),
        "observation_ledger_path": observation_ledger_path.as_posix(),
        "paper_orders_path": (data_dir / "paper/orders.parquet").as_posix(),
        "paper_fills_path": (data_dir / "paper/fills.parquet").as_posix(),
        "paper_positions_path": (data_dir / "paper/positions.parquet").as_posix(),
        "source_backtest_acceptance_path": source_backtest_acceptance_path.as_posix(),
        "source_backtest_acceptance_sha256": sha256_file(source_backtest_acceptance_path),
        "source_operator_promotion_path": source_operator_promotion_path.as_posix(),
        "source_operator_promotion_sha256": sha256_file(source_operator_promotion_path),
        "source_intent_preview_path": source_intent_preview_path.as_posix(),
        "source_intent_preview_sha256": sha256_file(source_intent_preview_path),
        "thresholds": {
            "min_fills_for_pass": selected_thresholds.min_fills_for_pass,
            "min_trading_days_for_pass": selected_thresholds.min_trading_days_for_pass,
            "max_blocked_rate": selected_thresholds.max_blocked_rate,
            "max_consecutive_blocked": selected_thresholds.max_consecutive_blocked,
            "max_open_position_age_hours": selected_thresholds.max_open_position_age_hours,
        },
        "smoke": smoke,
        "external_api_used": False,
        "credentials_used": False,
        "permits_live_order": False,
        "wallet_used": False,
        "venue_write_used": False,
        "exchange_write_used": False,
    }
    if source_paper_candidate_pack_path is not None:
        payload["source_paper_candidate_pack_path"] = source_paper_candidate_pack_path.as_posix()
        payload["source_paper_candidate_pack_sha256"] = sha256_file(
            source_paper_candidate_pack_path
        )
    if source_promotion_decision_path is not None:
        payload["source_promotion_decision_path"] = source_promotion_decision_path.as_posix()
        payload["source_promotion_decision_sha256"] = sha256_file(source_promotion_decision_path)
    write_json(manifest_path, payload)
    return PaperObservationSession(
        session_id=selected_session_id,
        session_dir=session_dir,
        manifest_path=manifest_path,
        observation_ledger_path=observation_ledger_path,
        payload=payload,
    )


def _default_session_id() -> str:
    value = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return f"paper-observation-{value}"


def _validate_session_id(value: str) -> str:
    selected = value.strip()
    if not selected:
        raise ValueError("paper observation session_id must be non-empty.")
    path = Path(selected)
    if path.is_absolute() or len(path.parts) != 1 or selected in {".", ".."}:
        raise ValueError("paper observation session_id must be a single path segment.")
    return selected
