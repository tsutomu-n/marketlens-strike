from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from sis.research.ndx.artifacts import DAG_ID, dag_artifact_hash, utc_now_iso, write_json
from sis.research.ndx.start_conditions import require_layer23_start_conditions


SourceStatus = Literal["resolved_fixture_first", "deferred"]


@dataclass(frozen=True)
class SourceResolutionResult:
    artifact_path: Path
    report_path: Path
    resolved_count: int
    deferred_count: int


REQUIRED_SOURCES: tuple[dict[str, str], ...] = (
    {"source_id": "QQQ", "instrument": "QQQ", "kind": "daily_ohlc", "fixture": "qqq_daily.csv"},
    {"source_id": "SPY", "instrument": "SPY", "kind": "daily_ohlc", "fixture": "spy_daily.csv"},
    {"source_id": "SMH", "instrument": "SMH", "kind": "daily_ohlc", "fixture": "smh_daily.csv"},
    {"source_id": "VIX", "instrument": "VIX", "kind": "daily_level", "fixture": "vix_daily.csv"},
    {
        "source_id": "DGS10",
        "instrument": "DGS10",
        "kind": "daily_level",
        "fixture": "dgs10_daily.csv",
    },
    {
        "source_id": "MEGA_CAP_BASKET",
        "instrument": "mega_cap_basket",
        "kind": "daily_ohlc",
        "fixture": "mega_cap_basket_daily.csv",
    },
)
DEFERRED_SOURCES: tuple[dict[str, str], ...] = (
    {
        "source_id": "NDX_INDEX",
        "reason": "direct NDX source is out of scope for fixture-first preflight",
    },
    {"source_id": "NQ_FUTURES", "reason": "NQ futures price discovery is deferred"},
    {"source_id": "VXN", "reason": "VXN direct volatility source is deferred"},
    {"source_id": "SOX_DIRECT", "reason": "SOX direct index source is deferred; SMH proxy is used"},
    {"source_id": "QQQ_PREMIUM_DISCOUNT", "reason": "ETF premium/discount is deferred"},
    {"source_id": "EVENT_CALENDAR", "reason": "macro/event calendar controls are deferred"},
    {"source_id": "OPEX_CALENDAR", "reason": "options and OPEX calendar effects are deferred"},
)


def build_source_resolution(
    *,
    root: Path,
    artifact_dir: Path,
    out_dir: Path,
) -> SourceResolutionResult:
    start = require_layer23_start_conditions(root=root, artifact_dir=artifact_dir)
    dag_hash = dag_artifact_hash(artifact_dir)
    resolved = [
        {
            **source,
            "status": "resolved_fixture_first",
            "required": True,
            "source_tier": "fixture_required",
        }
        for source in REQUIRED_SOURCES
    ]
    deferred = [
        {
            **source,
            "status": "deferred",
            "required": False,
        }
        for source in DEFERRED_SOURCES
    ]
    payload = {
        "schema_version": "ndx_source_resolution.v1",
        "dag_id": DAG_ID,
        "dag_artifact_hash": dag_hash,
        "layer_2_2_pack_hash": start.pack_hash,
        "created_at": utc_now_iso(),
        "policy": {
            "fixture_first": True,
            "external_api_allowed": False,
            "credentials_allowed": False,
            "dependency_addition_allowed": False,
        },
        "resolved_sources": resolved,
        "deferred_sources": deferred,
    }
    artifact_path = write_json(out_dir / "source_resolution/data_source_resolution.json", payload)
    report_path = _write_report(
        out_dir / "reports/ndx_data_source_resolution.md",
        resolved_count=len(resolved),
        deferred_count=len(deferred),
        dag_hash=dag_hash,
    )
    return SourceResolutionResult(
        artifact_path=artifact_path,
        report_path=report_path,
        resolved_count=len(resolved),
        deferred_count=len(deferred),
    )


def _write_report(path: Path, *, resolved_count: int, deferred_count: int, dag_hash: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# NDX Layer 2.3 Data Source Resolution\n\n"
        f"- dag_id: {DAG_ID}\n"
        f"- dag_artifact_hash: {dag_hash}\n"
        f"- resolved_fixture_first_sources: {resolved_count}\n"
        f"- deferred_sources: {deferred_count}\n"
        "- external_api_allowed: false\n"
        "- credentials_allowed: false\n",
        encoding="utf-8",
    )
    return path
