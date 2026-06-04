from __future__ import annotations

import glob
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from jsonschema import ValidationError, validators

from sis.storage.jsonl_store import read_json, read_jsonl


EVIDENCE_CARD_SCHEMA = {
    "type": "object",
    "required": [
        "run_id",
        "created_at",
        "scope",
        "data",
        "decision",
        "criteria",
        "blockers",
        "next_actions",
    ],
    "properties": {
        "run_id": {"type": "string"},
        "created_at": {"type": "string"},
        "scope": {
            "type": "object",
            "required": ["venues", "symbols", "timeframes", "scalping_policy"],
        },
        "data": {"type": "object"},
        "decision": {"type": "string"},
        "venue_decisions": {"type": "array"},
        "criteria": {"type": "array"},
        "blockers": {"type": "array"},
        "next_actions": {"type": "array"},
    },
}


@dataclass(frozen=True)
class ValidationIssue:
    path: str
    message: str


@dataclass(frozen=True)
class ValidationSummary:
    checked_files: int
    issues: list[ValidationIssue]


def _load_schema(schema_root: Path, name: str) -> dict[str, Any]:
    return json.loads((schema_root / name).read_text(encoding="utf-8"))


def _build_validator(schema: dict[str, Any]) -> validators.Validator:
    validator_cls = validators.validator_for(schema)
    validator_cls.check_schema(schema)
    return validator_cls(schema)


def _iter_files(path_pattern: str) -> list[Path]:
    return sorted(Path(path) for path in glob.glob(path_pattern))


def _latest_file(paths: list[Path]) -> list[Path]:
    return paths[-1:] if paths else []


def _read_json_list(path: Path) -> list[dict]:
    payload = read_json(path)
    return payload if isinstance(payload, list) else []


def _is_json_list(path: Path) -> bool:
    payload = read_json(path)
    return isinstance(payload, list)


def _is_json_dict(path: Path) -> bool:
    payload = read_json(path)
    return isinstance(payload, dict)


def _validate_json(path: Path, schema: dict[str, Any], issues: list[ValidationIssue]) -> None:
    try:
        payload = cast(Any, read_json(path))
        _build_validator(schema).validate(payload)
    except (json.JSONDecodeError, ValidationError) as exc:
        issues.append(ValidationIssue(path=str(path), message=str(exc)))


def _validate_jsonl(path: Path, schema: dict[str, Any], issues: list[ValidationIssue]) -> None:
    idx = -1
    validator = _build_validator(schema)
    try:
        for idx, row in enumerate(read_jsonl(path)):
            validator.validate(row)
    except (json.JSONDecodeError, ValidationError) as exc:
        issues.append(ValidationIssue(path=f"{path}#row={idx}", message=str(exc)))


def _validate_trade_xyz_strict_row(
    path: Path, row_index: int, row: dict, issues: list[ValidationIssue]
) -> None:
    required_non_null = {
        "venue": "TRADE_XYZ_STRICT_VENUE_MISSING",
        "canonical_symbol": "TRADE_XYZ_STRICT_SYMBOL_MISSING",
        "coin": "TRADE_XYZ_STRICT_COIN_MISSING",
        "asset_id": "TRADE_XYZ_STRICT_ASSET_ID_MISSING",
        "recv_ts_ms": "TRADE_XYZ_STRICT_RECV_TS_MISSING",
        "best_bid": "TRADE_XYZ_STRICT_BEST_BID_MISSING",
        "best_ask": "TRADE_XYZ_STRICT_BEST_ASK_MISSING",
        "mid_price": "TRADE_XYZ_STRICT_MID_PRICE_MISSING",
        "exec_buy_price": "TRADE_XYZ_STRICT_EXEC_BUY_PRICE_MISSING",
        "exec_sell_price": "TRADE_XYZ_STRICT_EXEC_SELL_PRICE_MISSING",
        "spread_bps": "TRADE_XYZ_STRICT_SPREAD_MISSING",
        "bid_depth_10bps_usd": "TRADE_XYZ_STRICT_SIDE_DEPTH_MISSING",
        "ask_depth_10bps_usd": "TRADE_XYZ_STRICT_SIDE_DEPTH_MISSING",
        "mark_price": "TRADE_XYZ_STRICT_MARK_PRICE_MISSING",
        "oracle_price": "TRADE_XYZ_STRICT_ORACLE_PRICE_MISSING",
        "funding_rate": "TRADE_XYZ_STRICT_FUNDING_MISSING",
        "funding_interval_minutes": "TRADE_XYZ_STRICT_FUNDING_INTERVAL_MISSING",
        "open_interest_usd": "TRADE_XYZ_STRICT_OPEN_INTEREST_MISSING",
        "fee_mode": "TRADE_XYZ_STRICT_FEE_MODE_MISSING",
        "taker_fee_bps": "TRADE_XYZ_STRICT_TAKER_FEE_MISSING",
        "maker_fee_bps": "TRADE_XYZ_STRICT_MAKER_FEE_MISSING",
        "block_reasons": "TRADE_XYZ_STRICT_BLOCK_REASONS_MISSING",
        "source_confidence": "TRADE_XYZ_STRICT_SOURCE_CONFIDENCE_MISSING",
        "venue_quality_score": "TRADE_XYZ_STRICT_VENUE_QUALITY_MISSING",
        "raw_payload_ref": "TRADE_XYZ_STRICT_RAW_PAYLOAD_REF_MISSING",
    }
    for key, reason in required_non_null.items():
        if row.get(key) is None:
            issues.append(ValidationIssue(path=f"{path}#row={row_index}", message=reason))


def validate_artifacts(
    data_dir: Path, schema_root: Path, strict: bool = False
) -> ValidationSummary:
    issues: list[ValidationIssue] = []
    checked_files = 0

    instrument_schema = _load_schema(schema_root, "instrument_registry.schema.json")
    quote_schema = _load_schema(
        schema_root, "quote_log_v2.schema.json" if strict else "quote_log_v1.schema.json"
    )
    trade_strict = strict

    registry_files = [data_dir / "registry/trade_xyz_instrument_registry.json"]
    if not strict:
        registry_files.extend(
            [
                data_dir / "registry/gtrade_instrument_registry.json",
                data_dir / "registry/ostium_instrument_registry.json",
            ]
        )
    registry_exists = False
    for path in registry_files:
        if path.exists():
            registry_exists = True
            _validate_json(path, {"type": "array", "items": instrument_schema}, issues)
            checked_files += 1
    if strict and not registry_exists:
        issues.append(
            ValidationIssue(
                path=str(data_dir / "registry/trade_xyz_instrument_registry.json"),
                message="Missing required Trade[XYZ] registry artifact",
            )
        )

    trade_xyz_quote_files = _iter_files(str(data_dir / "raw/quotes/trade_xyz/*.jsonl"))
    quote_files = trade_xyz_quote_files
    if not strict:
        quote_files = (
            quote_files
            + _iter_files(str(data_dir / "raw/quotes/gtrade/*.jsonl"))
            + _iter_files(str(data_dir / "raw/quotes/ostium/*.jsonl"))
        )
    if not quote_files and strict:
        issues.append(
            ValidationIssue(
                path=str(data_dir / "raw/quotes/trade_xyz"),
                message="No Trade[XYZ] quote JSONL artifacts found",
            )
        )
    for path in quote_files:
        _validate_jsonl(path, quote_schema, issues)
        if trade_strict and "raw/quotes/trade_xyz" in str(path):
            for idx, row in enumerate(read_jsonl(path)):
                _validate_trade_xyz_strict_row(path, idx, row, issues)
        checked_files += 1

    if trade_strict:
        summary_path = data_dir / "ops/trade_xyz_quote_collection_summary.json"
        if summary_path.exists():
            summary_schema_path = schema_root / "trade_xyz_quote_collection_summary.schema.json"
            if summary_schema_path.exists():
                _validate_json(
                    summary_path, _load_schema(schema_root, summary_schema_path.name), issues
                )
            elif not _is_json_dict(summary_path):
                issues.append(
                    ValidationIssue(path=str(summary_path), message="summary must be a JSON object")
                )
            checked_files += 1
        else:
            issues.append(
                ValidationIssue(
                    path=str(summary_path), message="Missing Trade[XYZ] quote collection summary"
                )
            )

        normalized_path = data_dir / "normalized/quotes.parquet"
        if normalized_path.exists():
            checked_files += 1
        else:
            issues.append(
                ValidationIssue(
                    path=str(normalized_path), message="Missing normalized quotes parquet"
                )
            )

        if not (schema_root / "quote_log_v2.schema.json").exists():
            issues.append(
                ValidationIssue(path=str(schema_root), message="Missing quote_log_v2 schema")
            )

    backtest_metrics_path = data_dir / "research/backtest_metrics.json"
    if not trade_strict and backtest_metrics_path.exists():
        if not _is_json_list(backtest_metrics_path):
            issues.append(
                ValidationIssue(
                    path=str(backtest_metrics_path),
                    message="backtest_metrics.json must be an array",
                )
            )
        checked_files += 1
    elif trade_strict:
        pass

    evidence_files = _iter_files(str(data_dir / "evidence/evidence_card_*.json"))
    if not evidence_files and trade_strict and False:
        issues.append(
            ValidationIssue(
                path=str(data_dir / "evidence"), message="No evidence card artifacts found"
            )
        )
    for path in [] if trade_strict else _latest_file(evidence_files):
        _validate_json(path, EVIDENCE_CARD_SCHEMA, issues)
        checked_files += 1

    execution_summary_files = [
        data_dir / "ops/execution_snapshot_summary.json",
        data_dir / "ops/execution_venue_comparison_summary.json",
        data_dir / "ops/execution_venue_diagnostics_summary.json",
        data_dir / "ops/execution_gap_history_summary.json",
        data_dir / "ops/execution_state_comparison_history_summary.json",
        data_dir / "ops/execution_snapshot_drift_history_summary.json",
        data_dir / "ops/execution_drift_overview_summary.json",
    ]
    for path in execution_summary_files:
        if path.exists():
            if not _is_json_dict(path):
                issues.append(
                    ValidationIssue(path=str(path), message=f"{path.name} must be a JSON object")
                )
            checked_files += 1
        elif strict and not trade_strict:
            issues.append(
                ValidationIssue(
                    path=str(path),
                    message=f"Missing required execution summary artifact: {path.name}",
                )
            )

    return ValidationSummary(checked_files=checked_files, issues=issues)
