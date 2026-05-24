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
    StatusItem("Epic 5", "liquidation guard", "DONE", "position-aware guard plus Ostium liquidation reference sidecar are implemented"),
    StatusItem("Epic 6", "Ostium read-only price probe", "DONE", "Builder API prices plus SDK getPairs metadata"),
    StatusItem("Epic 6", "Ostium fees/OI caps/trading metadata", "DONE", "SDK getPairs sidecar metadata merged into registry"),
    StatusItem("Epic 6", "Ostium liquidation reference", "DONE", "read-only getOpenPositions sidecar supports trader address and bounded ALL sampling"),
    StatusItem("Epic 7", "Backtest bridge", "DONE", "research signal CSV input, venue quote virtual execution, cost matrix integration, and metrics implemented"),
    StatusItem("Epic 8", "Go/No-Go markdown and evidence card", "DONE", "metrics evaluator, thresholds, blockers, and evidence digests implemented"),
    StatusItem("Epic 9", "Research layer foundation", "DONE", "src/sis/research/* plus ingest/build/check CLI commands and reproducible research artifacts"),
    StatusItem("Epic 10", "Decision engine foundation", "DONE", "src/sis/core/*, src/sis/risk/risk_gate.py, backtest decision logs, and decision summary artifacts"),
    StatusItem("Epic 11", "Paper trading foundation", "DONE", "src/sis/paper/* provides virtual fills, portfolio state updates, parquet writers, and daily report generation"),
    StatusItem("Epic 12", "Execution adapter foundation", "DONE", "src/sis/execution/* provides read-only adapter interfaces, order estimates, and health checks"),
    StatusItem("Epic 13", "State and ops foundation", "DONE", "src/sis/state/* and src/sis/ops/* provide reconciliation, sqlite state storage, kill switch, healthcheck, and limit checks"),
    StatusItem("Epic 14", "Stateful paper run pipeline", "DONE", "paper-step and paper-report produce orders/fills/positions/daily_pnl/report artifacts and persist paper state in sqlite"),
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
            "The handoff implementation is complete; current Go/No-Go may still be conditional because it depends on live quote evidence.",
            "",
            "| Area | Item | Status | Evidence |",
            "|---|---|---|---|",
            rows,
            "",
            "## Live Evidence Still Required",
            "",
            "- Recollect a sufficient quote window with fresh venue timestamps until `stale_rate` satisfies the Go/No-Go threshold.",
            "- Recollect during tradable sessions until `tradable_rate` satisfies the Go/No-Go threshold.",
            "",
            "Use the replay-safe refresh path:",
            "",
            "```bash",
            "rtk bun run gtrade:probe",
            "rtk uv run sis log-quotes --venue gtrade --replace",
            "rtk uv run sis normalize-quotes",
            "rtk uv run sis build-cost-matrix",
            "rtk uv run sis build-backtest",
            "rtk uv run sis check-go-no-go",
            "rtk uv run sis build-evidence-card",
            "```",
            "",
        ]
    )


def write_implementation_status(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(implementation_status_markdown(), encoding="utf-8")
