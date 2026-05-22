from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class StatusItem:
    area: str
    item: str
    status: str
    evidence: str


IMPLEMENTATION_STATUS: list[StatusItem] = [
    StatusItem("Epic 0", "Repository setup", "DONE", "pyproject.toml, README.md, sidecars/gtrade"),
    StatusItem("Epic 1", "InstrumentSpec / QuoteLog / CostSnapshot / MarketSession", "DONE", "src/sis/models.py"),
    StatusItem("Epic 1", "Static JSON schemas from handoff", "DONE", "schemas/*.schema.json"),
    StatusItem("Epic 2", "gTrade /trading-variables sidecar", "DONE", "sidecars/gtrade/src/emit_jsonl.ts"),
    StatusItem("Epic 2", "gTrade SPY/QQQ/XAU extraction", "DONE", "sidecars/gtrade/src/emit_jsonl.test.ts"),
    StatusItem("Epic 2", "Quote raw payload preservation", "DONE", "QuoteLog raw_payload plus raw_payload_ref/hash are stored in raw JSONL"),
    StatusItem("Epic 3", "JSONL to Parquet and DuckDB normalization", "DONE", "src/sis/storage/normalize.py"),
    StatusItem("Epic 4", "gTrade registry and initial cost matrix", "DONE", "sidecar fee/spread metadata plus gTrade/Ostium 4h/24h/72h holding costs are reflected"),
    StatusItem("Epic 4", "stale/tradable/spread aggregate calculations", "DONE", "implemented for normalized quote logs"),
    StatusItem("Epic 5", "scalping policy", "DONE", "src/sis/risk/scalping_policy.py"),
    StatusItem("Epic 5", "halt policy config loader", "DONE", "src/sis/risk/halt_policy.py"),
    StatusItem("Epic 5", "session/stale/event/spread/cost/registry/mark-index guards", "DONE", "all FR-006 BLOCK reasons are implemented"),
    StatusItem("Epic 5", "liquidation guard", "PARTIAL", "position-aware guard implemented; venue liquidation reference still required"),
    StatusItem("Epic 6", "Ostium read-only price probe", "DONE", "Builder API prices plus SDK getPairs metadata"),
    StatusItem("Epic 6", "Ostium fees/OI caps/trading metadata", "DONE", "SDK getPairs sidecar metadata merged into registry"),
    StatusItem("Epic 6", "Ostium liquidation reference", "PARTIAL", "read-only open-position sidecar implemented; requires trader position data"),
    StatusItem("Epic 7", "Backtest bridge", "DONE", "research signal CSV input, venue quote virtual execution, and metrics implemented"),
    StatusItem("Epic 8", "Go/No-Go markdown and evidence card", "DONE", "metrics evaluator, thresholds, blockers, and evidence digests implemented"),
]


def implementation_status_items() -> list[StatusItem]:
    return IMPLEMENTATION_STATUS


def implementation_status_markdown() -> str:
    rows = "\n".join(
        f"| {item.area} | {item.item} | {item.status} | {item.evidence} |"
        for item in IMPLEMENTATION_STATUS
    )
    return "\n".join(
        [
            "# Implementation Status",
            "",
            "The handoff zip is not fully implemented. This file separates completed scaffold work from remaining research-engine work.",
            "",
            "| Area | Item | Status | Evidence |",
            "|---|---|---|---|",
            rows,
            "",
            "## Not Yet Complete",
            "",
            "- Ostium liquidation reference verification requires `bun run ostium:probe:positions -- --user 0x...` with a trader that has real open positions.",
            "",
        ]
    )


def write_implementation_status(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(implementation_status_markdown(), encoding="utf-8")
