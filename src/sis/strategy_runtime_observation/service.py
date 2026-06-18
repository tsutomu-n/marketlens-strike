from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from sis.backtest.artifact_io import read_json_object, sha256_file
from sis.strategy_inputs.io import write_json_artifact, write_text_artifact
from sis.strategy_review.provenance import (
    boundary_true_paths,
    detect_json_schema_version,
    repo_relative_path,
)
from sis.strategy_runtime_observation.models import (
    RuntimeObservationIngestStatus,
    RuntimeObservationSourceArtifact,
    RuntimeObservationSourceStage,
    RuntimeObservationSummary,
    StrategyRuntimeObservationManifest,
)
from sis.strategy_runtime_observation.rendering import render_runtime_observation_markdown
from sis.strategy_stage.models import StageProducer


@dataclass(frozen=True)
class RuntimeObservationIngestResult:
    manifest: StrategyRuntimeObservationManifest
    manifest_path: Path
    report_path: Path
    ledger_path: Path


class StrategyRuntimeObservationError(ValueError):
    pass


class StrategyRuntimeObservationOutputExistsError(StrategyRuntimeObservationError):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _source_artifact(artifact_key: str, path: Path) -> RuntimeObservationSourceArtifact:
    return RuntimeObservationSourceArtifact(
        artifact_key=artifact_key,
        path=repo_relative_path(path),
        sha256=sha256_file(path),
        schema_version=detect_json_schema_version(path),
    )


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"runtime observation ledger missing: {path}")
    rows: list[dict[str, Any]] = []
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise StrategyRuntimeObservationError(
                f"invalid JSONL at {path}:{index}: {exc}"
            ) from exc
        if not isinstance(payload, dict):
            raise StrategyRuntimeObservationError(f"expected object JSONL row at {path}:{index}")
        rows.append(payload)
    return rows


def _session_id_from_manifest(path: Path) -> str:
    payload = read_json_object(path)
    if payload.get("schema_version") != "paper_observation_session_manifest.v1":
        raise StrategyRuntimeObservationError("session manifest schema_version mismatch")
    raw_session_id = payload.get("session_id")
    if not isinstance(raw_session_id, str) or not raw_session_id.strip():
        raise StrategyRuntimeObservationError("session manifest missing session_id")
    return raw_session_id.strip()


def _ledger_path_from_manifest(path: Path) -> Path:
    payload = read_json_object(path)
    raw_ledger_path = payload.get("observation_ledger_path")
    if not isinstance(raw_ledger_path, str) or not raw_ledger_path.strip():
        raise StrategyRuntimeObservationError("session manifest missing observation_ledger_path")
    return Path(raw_ledger_path)


def _str_value(row: dict[str, Any], key: str) -> str | None:
    value = row.get(key)
    return value if isinstance(value, str) and value else None


def _float_values(rows: list[dict[str, Any]], key: str) -> list[float]:
    values: list[float] = []
    for row in rows:
        value = row.get(key)
        if isinstance(value, int | float):
            values.append(float(value))
    return values


def _first_float_value(row: dict[str, Any], keys: tuple[str, ...]) -> float | None:
    for key in keys:
        value = row.get(key)
        if isinstance(value, bool) or value is None:
            continue
        if isinstance(value, int | float):
            return float(value)
    return None


def _sum_float_fields(rows: list[dict[str, Any]], keys: tuple[str, ...]) -> float | None:
    values = [value for row in rows if (value := _first_float_value(row, keys)) is not None]
    return sum(values) if values else None


def _avg(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _int_values(rows: list[dict[str, Any]], key: str) -> list[int]:
    values: list[int] = []
    for row in rows:
        value = row.get(key)
        if isinstance(value, int):
            values.append(value)
    return values


def _block_reason_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for row in rows:
        reasons = row.get("block_reasons")
        if isinstance(reasons, list):
            for reason in reasons:
                if isinstance(reason, str) and reason:
                    counter[reason] += 1
    return dict(sorted(counter.items()))


def _order_lifecycle_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for row in rows:
        state = (
            _str_value(row, "order_lifecycle")
            or _str_value(row, "order_status")
            or _str_value(row, "status")
            or "unknown"
        )
        counter[state] += 1
    return dict(sorted(counter.items()))


def _summary(rows: list[dict[str, Any]]) -> RuntimeObservationSummary:
    status_counts = Counter(str(row.get("status", "unknown")) for row in rows)
    fill_rows = [row for row in rows if _str_value(row, "fill_id")]
    order_rows = [row for row in rows if _str_value(row, "order_id")]
    blocked_rows = [row for row in rows if row.get("status") == "blocked"]
    no_fill_rows = [
        row for row in rows if row.get("status") == "blocked" or not _str_value(row, "fill_id")
    ]
    created_values = sorted(
        value for row in rows if (value := _str_value(row, "created_at")) is not None
    )
    spreads = _float_values(rows, "spread_bps")
    quote_ages = _int_values(rows, "quote_age_ms")
    realized_pnl = _sum_float_fields(rows, ("realized_pnl_usd", "paper_pnl_usd", "pnl_usd"))
    gross_pnl = _sum_float_fields(rows, ("gross_pnl_usd",))
    fees = _sum_float_fields(rows, ("fee_usd", "fees_usd", "estimated_fee_usd"))
    slippage_usd = _sum_float_fields(rows, ("slippage_usd", "estimated_slippage_usd"))
    slippage_bps = [
        value
        for row in rows
        if (value := _first_float_value(row, ("slippage_bps", "estimated_slippage_bps")))
        is not None
    ]
    fill_price_drift_bps = [
        value
        for row in rows
        if (
            value := _first_float_value(
                row, ("fill_price_drift_bps", "paper_vs_backtest_fill_price_drift_bps")
            )
        )
        is not None
    ]
    filled_notional = _sum_float_fields(fill_rows, ("filled_notional_usd", "notional_usd"))
    pnl_available = realized_pnl is not None
    intents = {value for row in rows if (value := _str_value(row, "intent_id"))}
    symbols = {
        value
        for row in rows
        if (value := _str_value(row, "execution_symbol") or _str_value(row, "real_market_symbol"))
    }
    return RuntimeObservationSummary(
        ledger_entry_count=len(rows),
        paper_order_count=len(order_rows),
        paper_fill_count=len(fill_rows),
        blocked_count=len(blocked_rows),
        no_fill_count=len(no_fill_rows),
        unique_intent_count=len(intents),
        unique_symbol_count=len(symbols),
        first_observed_at=created_values[0] if created_values else None,
        last_observed_at=created_values[-1] if created_values else None,
        max_observed_spread_bps=max(spreads) if spreads else None,
        max_observed_quote_age_ms=max(quote_ages) if quote_ages else None,
        pnl_available=pnl_available,
        pnl_unavailable_reason=None
        if pnl_available
        else "ledger rows do not include realized_pnl_usd, paper_pnl_usd, or pnl_usd",
        realized_pnl_usd_total=realized_pnl,
        gross_pnl_usd_total=gross_pnl,
        fee_usd_total=fees,
        slippage_usd_total=slippage_usd,
        avg_slippage_bps=_avg(slippage_bps),
        max_abs_slippage_bps=max((abs(value) for value in slippage_bps), default=None),
        avg_fill_price_drift_bps=_avg(fill_price_drift_bps),
        max_abs_fill_price_drift_bps=max(
            (abs(value) for value in fill_price_drift_bps), default=None
        ),
        filled_notional_usd_total=filled_notional,
        block_reasons=_block_reason_counts(rows),
        status_counts=dict(sorted(status_counts.items())),
        order_lifecycle_counts=_order_lifecycle_counts(rows),
    )


def _write_normalized_ledger(path: Path, rows: list[dict[str, Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.parent / f".{path.name}.tmp"
    try:
        with tmp_path.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(
                    json.dumps(row, ensure_ascii=False, sort_keys=True, default=str) + "\n"
                )
        tmp_path.replace(path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()
    return path


def _status(
    rows: list[dict[str, Any]], boundary_violations: list[str]
) -> RuntimeObservationIngestStatus:
    if boundary_violations:
        return RuntimeObservationIngestStatus.BLOCKED_BOUNDARY_VIOLATION
    if not rows:
        return RuntimeObservationIngestStatus.EMPTY_LEDGER
    return RuntimeObservationIngestStatus.INGESTED


def ingest_runtime_observation(
    *,
    strategy_id: str,
    session_manifest_path: Path,
    out_dir: Path,
    source_stage: RuntimeObservationSourceStage,
    ledger_path: Path | None = None,
    replace_existing: bool = False,
    created_at: datetime | None = None,
) -> RuntimeObservationIngestResult:
    if not session_manifest_path.exists():
        raise FileNotFoundError(f"session manifest missing: {session_manifest_path}")
    session_id = _session_id_from_manifest(session_manifest_path)
    selected_ledger_path = ledger_path or _ledger_path_from_manifest(session_manifest_path)
    rows = _read_jsonl(selected_ledger_path)
    session_payload = read_json_object(session_manifest_path)
    boundary_violations = [
        *boundary_true_paths(session_payload),
        *boundary_true_paths(rows),
    ]

    runtime_ledger_path = out_dir / "runtime_observation_ledger.jsonl"
    manifest_path = out_dir / "strategy_runtime_observation_manifest.json"
    report_path = out_dir / "strategy_runtime_observation_summary.md"
    if not replace_existing and (
        runtime_ledger_path.exists() or manifest_path.exists() or report_path.exists()
    ):
        raise StrategyRuntimeObservationOutputExistsError(
            f"output already exists: {repo_relative_path(out_dir)}"
        )
    _write_normalized_ledger(runtime_ledger_path, rows)

    manifest = StrategyRuntimeObservationManifest(
        strategy_id=strategy_id,
        session_id=session_id,
        source_stage=source_stage,
        created_at=created_at or _utc_now(),
        producer=StageProducer(command="strategy-runtime-observation-ingest"),
        ingest_status=_status(rows, boundary_violations),
        source_artifacts=[
            _source_artifact("paper_observation_session_manifest", session_manifest_path),
            _source_artifact("paper_observation_ledger", selected_ledger_path),
        ],
        runtime_observation_ledger_path=repo_relative_path(runtime_ledger_path),
        runtime_observation_ledger_sha256=sha256_file(runtime_ledger_path),
        summary=_summary(rows),
    )
    write_json_artifact(manifest_path, manifest.model_dump(mode="json", exclude_none=True))
    write_text_artifact(report_path, render_runtime_observation_markdown(manifest))
    return RuntimeObservationIngestResult(
        manifest=manifest,
        manifest_path=manifest_path,
        report_path=report_path,
        ledger_path=runtime_ledger_path,
    )
