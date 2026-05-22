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
    StatusItem("Epic 3", "JSONL to Parquet and DuckDB normalization", "DONE", "src/sis/storage/normalize.py"),
    StatusItem("Epic 4", "gTrade registry and initial cost matrix", "PARTIAL", "holding/borrowing costs are not complete"),
    StatusItem("Epic 4", "stale/tradable/spread aggregate calculations", "DONE", "implemented for normalized quote logs"),
    StatusItem("Epic 5", "scalping policy", "DONE", "src/sis/risk/scalping_policy.py"),
    StatusItem("Epic 5", "halt policy config loader", "DONE", "src/sis/risk/halt_policy.py"),
    StatusItem("Epic 5", "session/stale/spread/mark-index guards", "DONE", "quote-level guards implemented"),
    StatusItem("Epic 5", "liquidation guard", "PARTIAL", "position-aware guard implemented; venue liquidation reference still required"),
    StatusItem("Epic 6", "Ostium read-only price probe", "PARTIAL", "symbol and quote probe only"),
    StatusItem("Epic 6", "Ostium fees/OI caps/liquidation reference", "NOT_DONE", "requires SDK/API probe"),
    StatusItem("Epic 7", "Backtest bridge", "PARTIAL", "venue quote virtual execution and metrics implemented"),
    StatusItem("Epic 8", "Go/No-Go markdown and evidence card", "PARTIAL", "metrics are included but final evaluator is not complete"),
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
            "- Ostium fees, OI caps, trading hours detail, and liquidation reference probe.",
            "- Research signal generation and final Go/No-Go metrics evaluator.",
            "",
        ]
    )


def write_implementation_status(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(implementation_status_markdown(), encoding="utf-8")
