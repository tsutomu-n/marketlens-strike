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
    StatusItem("Epic 4", "gTrade registry and initial cost matrix", "PARTIAL", "live fee/spread aggregation is not complete"),
    StatusItem("Epic 4", "stale/tradable/spread aggregate calculations", "NOT_DONE", "requires quote collection window"),
    StatusItem("Epic 5", "scalping policy", "DONE", "src/sis/risk/scalping_policy.py"),
    StatusItem("Epic 5", "halt policy config loader", "PARTIAL", "guards are not fully enforced"),
    StatusItem("Epic 5", "session/stale/spread/mark-index/liquidation guards", "NOT_DONE", "risk guards not implemented"),
    StatusItem("Epic 6", "Ostium read-only price probe", "PARTIAL", "symbol and quote probe only"),
    StatusItem("Epic 6", "Ostium fees/OI caps/liquidation reference", "NOT_DONE", "requires SDK/API probe"),
    StatusItem("Epic 7", "Backtest bridge", "NOT_DONE", "not implemented"),
    StatusItem("Epic 8", "Go/No-Go markdown and evidence card", "PARTIAL", "status report only; metrics evaluator not complete"),
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
            "- Full halt/risk guard enforcement.",
            "- gTrade stale/tradable/spread aggregation over a collection window.",
            "- Ostium fees, OI caps, trading hours detail, and liquidation reference probe.",
            "- Backtest bridge, virtual execution, cost integration, and metrics.",
            "- Final Go/No-Go metrics evaluator.",
            "",
        ]
    )


def write_implementation_status(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(implementation_status_markdown(), encoding="utf-8")

