from __future__ import annotations

import html
from typing import Any

from sis.reports.live_evidence_sections import (
    latest_execution_lineage_flat_values as _latest_execution_lineage_flat_values,
    latest_execution_lineage_html_metrics as _latest_execution_lineage_html_metrics,
    quick_navigation_html_metrics as _quick_navigation_html_metrics,
    related_report_html_metrics as _related_report_html_metrics,
    remediation_html_metrics as _remediation_html_metrics,
    restart_pointer_html_metrics as _restart_pointer_html_metrics,
)
from sis.reports.summary_normalizers import (
    audit_summary_fields,
    execution_comparison_flat_fields,
    execution_diagnostics_flat_fields,
    execution_drift_overview_flat_fields,
    execution_gap_history_flat_fields,
    execution_snapshot_drift_flat_fields,
    execution_snapshot_flat_fields,
    execution_state_comparison_flat_fields,
    phase_gate_flat_fields,
    readiness_flat_fields,
)


def render_live_evidence_html(data: Any) -> str:
    phase_gate_flat = phase_gate_flat_fields(data.phase_gate_summary)
    readiness_flat = readiness_flat_fields(data.readiness_summary)
    latest_execution_flat = _latest_execution_lineage_flat_values(data)
    execution_summary_flat = execution_snapshot_flat_fields(data.execution_summary)
    execution_comparison_flat = execution_comparison_flat_fields(data.execution_comparison_summary)
    execution_diagnostics_flat = execution_diagnostics_flat_fields(
        data.execution_diagnostics_summary
    )
    execution_gap_history_flat = execution_gap_history_flat_fields(
        data.execution_gap_history_summary
    )
    execution_state_comparison_flat = execution_state_comparison_flat_fields(
        data.execution_state_comparison_summary
    )
    execution_snapshot_drift_flat = execution_snapshot_drift_flat_fields(
        data.execution_snapshot_drift_summary
    )
    execution_drift_flat = execution_drift_overview_flat_fields(
        data.execution_drift_overview_summary
    )
    remediation_metrics = _remediation_html_metrics(data.readiness_summary)
    restart_pointer_metrics = _restart_pointer_html_metrics(data.readiness_summary)
    quick_navigation_metrics = _quick_navigation_html_metrics(
        data.readiness_summary,
        data.phase_gate_summary,
    )
    related_report_metrics = _related_report_html_metrics(
        data.readiness_summary,
        data.phase_gate_summary,
    )

    def esc(value: object) -> str:
        return html.escape("" if value is None else str(value))

    venue_rows = "\n".join(
        (
            "<tr>"
            f"<td>{esc(item.get('venue'))}</td>"
            f"<td>{esc(item.get('decision'))}</td>"
            f"<td>{esc(item.get('main_blocker'))}</td>"
            "</tr>"
        )
        for item in data.venue_decisions
        if isinstance(item, dict)
    )
    diag_rows = "\n".join(
        (
            "<tr>"
            f"<td>{esc(item.symbol)}</td>"
            f"<td>{item.rows}</td>"
            f"<td>{item.market_open_rows}</td>"
            f"<td>{item.tradable_rate:.4f}</td>"
            f"<td>{item.stale_rate:.4f}</td>"
            f"<td>{item.missing_mark_price_rate:.4f}</td>"
            f"<td>{item.missing_index_price_rate:.4f}</td>"
            f"<td>{esc(item.oracle_age_p90_ms)}</td>"
            f"<td>{esc(item.spread_p90_bps)}</td>"
            "</tr>"
        )
        for item in data.quote_diagnostics
    )
    cost_rows = "\n".join(
        (
            "<tr>"
            f"<td>{esc(row.get('venue'))}</td>"
            f"<td>{esc(row.get('symbol'))}</td>"
            f"<td>{esc(row.get('stale_rate'))}</td>"
            f"<td>{esc(row.get('tradable_rate'))}</td>"
            f"<td>{esc(row.get('spread_p90_bps'))}</td>"
            f"<td>{esc(row.get('holding_cost_4h_bps'))}</td>"
            f"<td>{esc(row.get('notes'))}</td>"
            "</tr>"
        )
        for row in data.cost_rows
    )
    backtest_rows = "\n".join(
        (
            "<tr>"
            f"<td>{esc(row.get('venue'))}</td>"
            f"<td>{esc(row.get('canonical_symbol'))}</td>"
            f"<td>{esc(row.get('trade_count'))}</td>"
            f"<td>{esc(row.get('avg_trade_return'))}</td>"
            f"<td>{esc(row.get('cost_drag_bps'))}</td>"
            f"<td>{esc(row.get('stale_rejected_count'))}</td>"
            f"<td>{esc(row.get('halt_rejected_count'))}</td>"
            "</tr>"
        )
        for row in data.backtest_metrics
    )
    blocker_items = "".join(f"<li>{esc(item)}</li>" for item in data.blockers) or "<li>none</li>"
    next_action_items = (
        "".join(f"<li>{esc(item)}</li>" for item in data.next_actions) or "<li>none</li>"
    )
    validation_items = (
        "".join(
            f"<li>{esc(issue.path)}: {esc(issue.message)}</li>" for issue in data.validation.issues
        )
        or "<li>none</li>"
    )
    log_tail = html.escape("\n".join(data.log_tail))
    audit_summary_flat = audit_summary_fields(data.audit_summary, data.audit_summary)

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Live Evidence Detailed Report</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f4f1e8;
      --surface: #fffdfa;
      --ink: #1e1b16;
      --muted: #6b6258;
      --line: #d8d0c3;
      --accent: #14532d;
      --warn: #9a3412;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: ui-sans-serif, system-ui, sans-serif; background: var(--bg); color: var(--ink); }}
    main {{ max-width: 1200px; margin: 0 auto; padding: 32px 20px 64px; }}
    h1, h2 {{ margin: 0 0 12px; }}
    section {{ margin-top: 24px; background: var(--surface); border: 1px solid var(--line); padding: 20px; }}
    .meta {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; }}
    .metric {{ border: 1px solid var(--line); padding: 12px; background: #fff; }}
    .metric .label {{ color: var(--muted); font-size: 12px; text-transform: uppercase; }}
    .metric .value {{ margin-top: 6px; font-size: 18px; font-weight: 600; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    th, td {{ border: 1px solid var(--line); padding: 8px; text-align: left; vertical-align: top; }}
    th {{ background: #f9f6ef; }}
    pre {{ margin: 0; overflow: auto; background: #171411; color: #f7f2ea; padding: 16px; }}
    .ok {{ color: var(--accent); }}
    .warn {{ color: var(--warn); }}
    ul {{ margin: 0; padding-left: 20px; }}
  </style>
</head>
<body>
  <main>
    <h1>Live Evidence Detailed Report</h1>
    <section>
      <h2>Status</h2>
      <div class="meta">
        <div class="metric"><div class="label">Run Status</div><div class="value">{esc(data.status)}</div></div>
        <div class="metric"><div class="label">Decision</div><div class="value">{esc(data.decision)}</div></div>
        <div class="metric"><div class="label">Started At UTC</div><div class="value">{esc(data.started_at_utc)}</div></div>
        <div class="metric"><div class="label">Finished At UTC</div><div class="value">{esc(data.finished_at_utc)}</div></div>
      </div>
    </section>
    <section>
      <h2>Audit Summary</h2>
      <div class="meta">
        <div class="metric"><div class="label">Overall Status</div><div class="value">{esc(audit_summary_flat.get("overall_status"))}</div></div>
        <div class="metric"><div class="label">Latest Operation</div><div class="value">{esc(audit_summary_flat.get("latest_operation"))}</div></div>
        <div class="metric"><div class="label">Bundle History Snapshot Count</div><div class="value">{esc(audit_summary_flat.get("bundle_history_snapshot_count"))}</div></div>
      </div>
    </section>
    <section>
      <h2>Phase Gate Summary</h2>
      <div class="meta">
        <div class="metric"><div class="label">Decision</div><div class="value">{esc(phase_gate_flat.get("phase_gate_decision"))}</div></div>
        <div class="metric"><div class="label">Phase 2 Entry Allowed</div><div class="value">{esc(phase_gate_flat.get("phase2_entry_allowed"))}</div></div>
        <div class="metric"><div class="label">Reason</div><div class="value">{esc(phase_gate_flat.get("phase_gate_reason"))}</div></div>
        <div class="metric"><div class="label">Strict Validation</div><div class="value">{esc(phase_gate_flat.get("strict_validation_passed"))}</div></div>
        <div class="metric"><div class="label">Strict Validation Issues</div><div class="value">{esc(phase_gate_flat.get("phase_gate_strict_validation_issue_count"))}</div></div>
        <div class="metric"><div class="label">Checked Files</div><div class="value">{esc(phase_gate_flat.get("phase_gate_checked_files"))}</div></div>
      </div>
    </section>
    <section>
      <h2>Readiness Summary</h2>
      <div class="meta">
        <div class="metric"><div class="label">Next Phase Candidate</div><div class="value">{esc(readiness_flat.get("readiness_next_phase_candidate"))}</div></div>
        <div class="metric"><div class="label">Execution Ready</div><div class="value">{esc(readiness_flat.get("readiness_execution_ready"))}</div></div>
      </div>
    </section>
    <section>
      <h2>Current Remediation Queue</h2>
      <div class="meta">
{remediation_metrics}
      </div>
    </section>
    <section>
      <h2>Restart Pointers</h2>
      <div class="meta">
{restart_pointer_metrics}
      </div>
    </section>
    <section>
      <h2>Quick Navigation</h2>
      <div class="meta">
{quick_navigation_metrics}
      </div>
    </section>
    <section>
      <h2>Related Reports</h2>
      <div class="meta">
{related_report_metrics}
      </div>
    </section>
    <section>
      <h2>Latest Execution Lineage</h2>
      <div class="meta">
{_latest_execution_lineage_html_metrics(latest_execution_flat)}
      </div>
    </section>
    <section>
      <h2>Execution Snapshot</h2>
      <div class="meta">
        <div class="metric"><div class="label">Overall Status</div><div class="value">{esc(execution_summary_flat.get("execution_overall_status"))}</div></div>
        <div class="metric"><div class="label">Venue Count</div><div class="value">{esc(execution_summary_flat.get("execution_venue_count"))}</div></div>
        <div class="metric"><div class="label">Report Path</div><div class="value">{esc(execution_summary_flat.get("execution_report_path"))}</div></div>
      </div>
    </section>
    <section>
      <h2>Execution Venue Comparison</h2>
      <div class="meta">
        <div class="metric"><div class="label">All Registries Present</div><div class="value">{esc(execution_comparison_flat.get("execution_comparison_all_registries_present"))}</div></div>
        <div class="metric"><div class="label">Report Path</div><div class="value">{esc(execution_comparison_flat.get("execution_comparison_report_path"))}</div></div>
      </div>
    </section>
    <section>
      <h2>Execution Venue Diagnostics</h2>
      <div class="meta">
        <div class="metric"><div class="label">Overall Status</div><div class="value">{esc(execution_diagnostics_flat.get("execution_diagnostics_status"))}</div></div>
        <div class="metric"><div class="label">Balance Gap</div><div class="value">{esc(execution_diagnostics_flat.get("execution_balance_gap_detected"))}</div></div>
        <div class="metric"><div class="label">Fills Gap</div><div class="value">{esc(execution_diagnostics_flat.get("execution_fills_gap_detected"))}</div></div>
        <div class="metric"><div class="label">Report Path</div><div class="value">{esc(execution_diagnostics_flat.get("execution_diagnostics_report_path"))}</div></div>
      </div>
    </section>
    <section>
      <h2>Execution Gap History</h2>
      <div class="meta">
        <div class="metric"><div class="label">Entry Count</div><div class="value">{esc(execution_gap_history_flat.get("execution_gap_history_entry_count"))}</div></div>
        <div class="metric"><div class="label">Latest Status</div><div class="value">{esc(execution_gap_history_flat.get("execution_gap_history_latest_status"))}</div></div>
        <div class="metric"><div class="label">Latest Diagnostics Status</div><div class="value">{esc(execution_gap_history_flat.get("execution_gap_history_latest_diagnostics_status"))}</div></div>
        <div class="metric"><div class="label">Report Path</div><div class="value">{esc(execution_gap_history_flat.get("execution_gap_history_report_path"))}</div></div>
      </div>
    </section>
    <section>
      <h2>Execution State Comparison History</h2>
      <div class="meta">
        <div class="metric"><div class="label">Entry Count</div><div class="value">{esc(execution_state_comparison_flat.get("execution_state_comparison_entry_count"))}</div></div>
        <div class="metric"><div class="label">Latest Status Match</div><div class="value">{esc(execution_state_comparison_flat.get("execution_state_comparison_latest_status_match"))}</div></div>
        <div class="metric"><div class="label">Mismatching Count</div><div class="value">{esc(execution_state_comparison_flat.get("execution_state_comparison_mismatching_count"))}</div></div>
        <div class="metric"><div class="label">Report Path</div><div class="value">{esc(execution_state_comparison_flat.get("execution_state_comparison_report_path"))}</div></div>
      </div>
    </section>
    <section>
      <h2>Execution Snapshot Drift History</h2>
      <div class="meta">
        <div class="metric"><div class="label">Entry Count</div><div class="value">{esc(execution_snapshot_drift_flat.get("execution_snapshot_drift_entry_count"))}</div></div>
        <div class="metric"><div class="label">Latest State Match</div><div class="value">{esc(execution_snapshot_drift_flat.get("execution_snapshot_drift_latest_status_match"))}</div></div>
        <div class="metric"><div class="label">Mismatching Snapshot Count</div><div class="value">{esc(execution_snapshot_drift_flat.get("execution_snapshot_drift_mismatching_snapshot_count"))}</div></div>
        <div class="metric"><div class="label">Report Path</div><div class="value">{esc(execution_snapshot_drift_flat.get("execution_snapshot_drift_report_path"))}</div></div>
      </div>
    </section>
    <section>
      <h2>Execution Drift Overview</h2>
      <div class="meta">
        <div class="metric"><div class="label">Overall Status</div><div class="value">{esc(execution_drift_flat.get("execution_drift_overview_status"))}</div></div>
        <div class="metric"><div class="label">Diagnostics Alignment</div><div class="value">{esc(execution_drift_flat.get("execution_drift_overview_diagnostics_alignment_match"))}</div></div>
        <div class="metric"><div class="label">State Comparison Mismatch Count</div><div class="value">{esc(execution_drift_flat.get("execution_drift_overview_state_comparison_mismatching_count"))}</div></div>
        <div class="metric"><div class="label">Snapshot Drift Mismatch Count</div><div class="value">{esc(execution_drift_flat.get("execution_drift_overview_snapshot_drift_mismatching_snapshot_count"))}</div></div>
      </div>
    </section>
    <section>
      <h2>Artifacts</h2>
      <div class="meta">
        <div class="metric"><div class="label">Sidecar Metadata Rows</div><div class="value">{data.row_counts["sidecar_metadata"]}</div></div>
        <div class="metric"><div class="label">Sidecar Pricing Rows</div><div class="value">{data.row_counts["sidecar_pricing"]}</div></div>
        <div class="metric"><div class="label">Raw Quote Rows</div><div class="value">{data.row_counts["raw_quotes"]}</div></div>
        <div class="metric"><div class="label">Evidence Card</div><div class="value">{esc(data.artifacts.evidence_card)}</div></div>
      </div>
    </section>
    <section>
      <h2>Venue Decisions</h2>
      <table>
        <thead><tr><th>Venue</th><th>Decision</th><th>Main Blocker</th></tr></thead>
        <tbody>{venue_rows}</tbody>
      </table>
    </section>
    <section>
      <h2>GTrade Diagnostics</h2>
      <table>
        <thead><tr><th>Symbol</th><th>Rows</th><th>Open Rows</th><th>Tradable Rate</th><th>Stale Rate</th><th>Missing Mark</th><th>Missing Index</th><th>Oracle p90 ms</th><th>Spread p90 bps</th></tr></thead>
        <tbody>{diag_rows}</tbody>
      </table>
    </section>
    <section>
      <h2>Cost Matrix Snapshot</h2>
      <table>
        <thead><tr><th>Venue</th><th>Symbol</th><th>Stale Rate</th><th>Tradable Rate</th><th>Spread p90 bps</th><th>Holding 4h bps</th><th>Notes</th></tr></thead>
        <tbody>{cost_rows}</tbody>
      </table>
    </section>
    <section>
      <h2>Backtest Snapshot</h2>
      <table>
        <thead><tr><th>Venue</th><th>Symbol</th><th>Trade Count</th><th>Avg Trade Return</th><th>Cost Drag bps</th><th>Stale Rejected</th><th>Halt Rejected</th></tr></thead>
        <tbody>{backtest_rows}</tbody>
      </table>
    </section>
    <section>
      <h2>Validation</h2>
      <p>checked_files={data.validation.checked_files}, issue_count={len(data.validation.issues)}</p>
      <ul>{validation_items}</ul>
    </section>
    <section>
      <h2>Blockers</h2>
      <ul>{blocker_items}</ul>
    </section>
    <section>
      <h2>Next Actions</h2>
      <ul>{next_action_items}</ul>
    </section>
    <section>
      <h2>Log Tail</h2>
      <pre>{log_tail}</pre>
    </section>
  </main>
</body>
</html>
"""
