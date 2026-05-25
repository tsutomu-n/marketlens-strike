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
    StatusItem("Epic 12", "Execution adapter foundation", "DONE", "src/sis/execution/* provides read-only adapter interfaces, balance/fill snapshots, order status lists, order estimates, and health checks"),
    StatusItem("Epic 13", "State and ops foundation", "DONE", "src/sis/state/* and src/sis/ops/* provide reconciliation, sqlite state storage, kill switch, healthcheck, and limit checks"),
    StatusItem("Epic 14", "Stateful paper run pipeline", "DONE", "paper-step and paper-report produce orders/fills/positions/daily_pnl/report artifacts and persist paper state in sqlite"),
    StatusItem("Epic 15", "Execution and ops CLI surface", "DONE", "estimate-order, balance-status, fill-status, execution-snapshot, reconcile-positions, healthcheck, and kill-switch commands expose execution/state/ops foundations"),
    StatusItem("Epic 16", "Order status and close/cancel foundation", "DONE", "execution adapters and CLI expose read-only order-status, fill-status, cancel-order, and close-position foundations"),
    StatusItem("Epic 17", "Scheduler and reporting foundation", "DONE", "schedule-run, render-alert, and weekly-review commands provide scheduler, alert, and review report artifacts"),
    StatusItem("Epic 18", "Daemon and state recovery foundation", "DONE", "daemon-manifest, export-state, restore-state, and lifecycle-report provide daemon/state recovery/lifecycle artifacts"),
    StatusItem("Epic 19", "Monitoring and comparison foundation", "DONE", "monitoring-status and comparison-report provide monitoring snapshot and paper-vs-backtest comparison artifacts"),
    StatusItem("Epic 20", "Daemon dry-run and operation manifest chain", "DONE", "daemon-dry-run writes schedule/daemon snapshot artifacts and appends ops/operation_manifests.jsonl"),
    StatusItem("Epic 21", "Ops review aggregation", "DONE", "ops-review aggregates operation_manifests, monitoring snapshot, and daemon dry-run status into report and summary artifacts"),
    StatusItem("Epic 22", "Operations dashboard aggregation", "DONE", "operations-dashboard consolidates monitoring, ops review, decision summary, and report coverage into a restart-friendly dashboard"),
    StatusItem("Epic 23", "Operations artifact refresh orchestration", "DONE", "refresh-operations-artifacts regenerates weekly/comparison/lifecycle/monitoring/ops-review/dashboard artifacts in one run"),
    StatusItem("Epic 24", "Scheduled paper operations runbook", "DONE", "paper-operations-runbook generates a restart-friendly paper ops runbook and refresh-operations-artifacts includes it"),
    StatusItem("Epic 25", "Paper operations cycle orchestration", "DONE", "paper-operations-cycle runs paper-step and regenerates operations artifacts plus cycle summary in one command"),
    StatusItem("Epic 26", "Paper operations cycle manifest chain", "DONE", "paper-operations-cycle appends an operation manifest entry so cycle history participates in ops review and dashboard aggregation"),
    StatusItem("Epic 27", "Paper cycle history aggregation", "DONE", "paper-cycle-history summarizes paper_operations_cycle entries, and refresh/cycle commands regenerate the history artifact"),
    StatusItem("Epic 28", "Operations bundle manifest", "DONE", "operations-bundle summarizes monitoring, ops review, dashboard, runbook, and cycle history summaries into one manifest and is regenerated by refresh/cycle"),
    StatusItem("Epic 29", "Operations snapshot manifest chain", "DONE", "operations-bundle and higher-level refresh/cycle flows append operations_snapshot entries to the operation chain"),
    StatusItem("Epic 30", "Operations timeline report", "DONE", "operations-timeline summarizes operation chain history, and refresh/cycle flows regenerate the timeline artifact"),
    StatusItem("Epic 31", "Operations audit pack", "DONE", "operations-audit-pack consolidates bundle/timeline/history/runbook summaries into an audit pack and is regenerated by refresh/cycle"),
    StatusItem("Epic 32", "Operations audit snapshot manifest chain", "DONE", "operations-audit-pack and higher-level refresh/cycle flows append operations_audit_snapshot entries to the operation chain"),
    StatusItem("Epic 33", "Audit timeline report", "DONE", "audit-timeline isolates operations_snapshot and operations_audit_snapshot history, and refresh/cycle flows regenerate the audit timeline artifact"),
    StatusItem("Epic 34", "Audit dashboard", "DONE", "audit-dashboard summarizes bundle, audit pack, and audit timeline summaries, and refresh/cycle flows regenerate the audit dashboard artifact"),
    StatusItem("Epic 35", "Audit bundle manifest chain", "DONE", "audit-bundle summarizes audit dashboard, audit timeline, and audit pack summaries, and refresh/cycle flows append audit_bundle_snapshot entries"),
    StatusItem("Epic 36", "Audit bundle history", "DONE", "audit-bundle-history summarizes audit_bundle_snapshot entries, and refresh/cycle flows regenerate the history artifact"),
    StatusItem("Epic 37", "Execution gap history", "DONE", "execution-gap-history summarizes diagnostics/readiness transitions from cycle and snapshot chain entries, and refresh/cycle flows regenerate the history artifact"),
    StatusItem("Epic 38", "Execution state comparison history", "DONE", "execution-state-comparison-history compares execution diagnostics versus gap-history diagnostics across cycle and snapshot chain entries, and refresh/cycle flows regenerate the comparison artifact"),
    StatusItem("Epic 39", "Execution snapshot drift history", "DONE", "execution-snapshot-drift-history isolates snapshot-chain drift between diagnostics, gap-history diagnostics, and state-comparison mismatch notes, and refresh/cycle flows regenerate the artifact"),
    StatusItem("Epic 40", "Execution drift overview", "DONE", "execution-drift-overview consolidates gap-history, state-comparison, and snapshot-drift summaries into one restart-friendly artifact and refresh/cycle flows regenerate it"),
    StatusItem("Epic 41", "Remediation planner dry run", "DONE", "remediation-planner aggregates phase gate and runbook recommendations into a dry-run command plan and refresh-operations-artifacts appends its manifest entry"),
    StatusItem("Epic 42", "Remediation execution plan dry run", "DONE", "remediation-execution-plan expands planner recommendations into staged preflight/execute/post-check actions and refresh-operations-artifacts appends its manifest entry"),
    StatusItem("Epic 43", "Remediation session dry run", "DONE", "remediation-session turns execution plan actions into a pending pass/fail session artifact and refresh-operations-artifacts appends its manifest entry"),
    StatusItem("Epic 44", "Remediation session checkpoint", "DONE", "remediation-session-checkpoint merges pass/fail/retry updates into a persistent checkpoint artifact and refresh-operations-artifacts appends its manifest entry"),
    StatusItem("Epic 45", "Remediation scoreboard", "DONE", "remediation-scoreboard summarizes checkpoint progress into overall completion/blocking status and refresh-operations-artifacts appends its manifest entry"),
    StatusItem("Epic 46", "Remediation evaluator", "DONE", "remediation-evaluator inspects checkpoint verification signals against current summaries and refresh-operations-artifacts appends its manifest entry"),
    StatusItem("Epic 47", "Remediation evidence", "DONE", "remediation-evidence collects manual-review actions, unresolved verification signals, and candidate artifact paths, and refresh-operations-artifacts appends its manifest entry"),
    StatusItem("Epic 48", "Remediation command results", "DONE", "remediation-command-results records observed signals and evidence paths from session checkpoints, and evaluator can auto-pass exact observed verification signals"),
    StatusItem("Epic 49", "Remediation evidence ingest", "DONE", "remediation-evidence-ingest records exit-code/stdout/stderr observations into session checkpoints, regenerates command-results, and appends its manifest entry"),
    StatusItem("Epic 50", "Remediation evaluator manifest-note fallback", "DONE", "remediation-evaluator can reconstruct verification signals from ops/operation_manifests.jsonl notes when stdout/stderr observations are absent"),
    StatusItem("Epic 51", "Remediation evaluator timeline-summary fallback", "DONE", "remediation-evaluator can reconstruct verification signals from ops/operations_timeline_summary.json and ops/audit_timeline_summary.json when command observations and manifest notes are absent"),
    StatusItem("Epic 52", "Remediation evaluator dashboard-bundle fallback", "DONE", "remediation-evaluator can reconstruct verification signals from operations/audit dashboard and bundle summary artifacts when command observations, timeline summaries, and manifest notes are absent"),
    StatusItem("Epic 53", "Remediation evaluator free-form issue and blocker previews", "DONE", "remediation-evaluator can auto-pass strict validation issue previews and phase-gate blocker/next-action list signals from summary artifacts"),
    StatusItem("Epic 54", "Remediation evaluator markdown-report fallback", "DONE", "remediation-evaluator can reconstruct issue previews, blocker explanations, and next actions from phase-gate markdown reports when summary/timeline/dashboard fallback is insufficient"),
    StatusItem("Epic 55", "Remediation evaluator ops-review fallback", "DONE", "remediation-evaluator can reuse ops-review summary and markdown preview lines as an additional diagnostics/readiness fallback source"),
    StatusItem("Epic 56", "Remediation evaluator current-state-index fallback", "DONE", "remediation-evaluator can reuse current-state-index summary and markdown preview lines as a restart-friendly fallback source for diagnostics, phase-gate, and live-evidence state"),
    StatusItem("Epic 57", "Remediation evaluator live-evidence fallback", "DONE", "remediation-evaluator can reuse live-evidence summary and markdown report lines via current-state artifact pointers as a fallback source for blockers, next actions, diagnostics, and live decision state"),
    StatusItem("Epic 58", "Execution adapter command artifacts", "DONE", "balance-status, fill-status, order-status, cancel-order, close-position, and reconcile-positions now write restart-friendly report and summary artifacts without changing their existing stdout surface"),
    StatusItem("Epic 59", "Execution adapter artifact aggregation", "DONE", "operations-dashboard, current-state-index, and readiness-snapshot now surface latest execution adapter command artifacts when those summaries exist"),
    StatusItem("Epic 60", "Ops command artifacts", "DONE", "healthcheck, kill-switch, schedule-run, and render-alert now write restart-friendly report and summary artifacts without changing their existing stdout surface"),
    StatusItem("Epic 61", "State and daemon command artifacts", "DONE", "daemon-manifest, export-state, and restore-state now write restart-friendly report and summary artifacts without changing their existing stdout surface"),
    StatusItem("Epic 62", "State and daemon artifact aggregation", "DONE", "operations-dashboard, current-state-index, and readiness-snapshot now surface latest daemon-manifest, export-state, and restore-state artifacts when those summaries exist"),
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
