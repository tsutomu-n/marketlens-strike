from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from sis.storage.jsonl_store import read_jsonl, write_json


@dataclass
class QuoteDiagnostic:
    venue: str
    symbol: str
    stale_threshold_ms: int
    rows: int
    market_open_rows: int
    tradable_rate: float
    stale_rate: float
    missing_mark_price_rate: float
    missing_index_price_rate: float
    missing_spread_rate: float
    stale_missing_oracle_ts_rate: float
    stale_old_oracle_ts_rate: float
    market_status_unknown_rate: float
    market_closed_rate: float
    oracle_age_p50_ms: int | None
    oracle_age_p90_ms: int | None
    spread_p50_bps: float | None
    spread_p90_bps: float | None


def _pct(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def _quantile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    sorted_values = sorted(values)
    idx = int((len(sorted_values) - 1) * q)
    return sorted_values[idx]


def _quantile_int(values: list[int], q: float) -> int | None:
    result = _quantile([float(item) for item in values], q)
    if result is None:
        return None
    return int(result)


def build_quote_diagnostics(
    raw_quotes_root: Path,
    venue: str | None = None,
    symbol: str | None = None,
    stale_thresholds_ms: dict[str, int] | None = None,
) -> list[QuoteDiagnostic]:
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for path in sorted(raw_quotes_root.glob("*/*.jsonl")):
        for row in read_jsonl(path):
            key = (row.get("venue"), row.get("canonical_symbol"))
            if key[0] is None or key[1] is None:
                continue
            grouped[(str(key[0]), str(key[1]))].append(row)

    diagnostics: list[QuoteDiagnostic] = []
    for (row_venue, row_symbol), rows in sorted(grouped.items()):
        if venue and row_venue != venue:
            continue
        if symbol and row_symbol != symbol:
            continue
        threshold_ms = (stale_thresholds_ms or {}).get(row_venue, 3000 if row_venue == "gtrade" else 5000)

        market_open_rows = sum(1 for row in rows if row.get("market_status") == "open")
        tradable_rows = sum(1 for row in rows if row.get("is_tradable") is True)
        stale_rows = 0
        stale_missing_oracle = 0
        stale_old_oracle = 0
        missing_mark = 0
        missing_index = 0
        missing_spread = 0
        market_unknown = 0
        market_closed = 0
        oracle_ages: list[int] = []
        spreads: list[float] = []

        for row in rows:
            ts_client = row.get("ts_client")
            oracle_ts_ms = row.get("oracle_ts_ms")
            market_status = row.get("market_status")
            if market_status == "unknown":
                market_unknown += 1
            elif market_status == "closed":
                market_closed += 1

            if isinstance(ts_client, str) and isinstance(oracle_ts_ms, int):
                # Keep parsing lightweight: rely on ISO lexical layout and unix milliseconds conversion only.
                try:
                    from datetime import datetime

                    ts_ms = int(datetime.fromisoformat(ts_client.replace("Z", "+00:00")).timestamp() * 1000)
                    age = max(0, ts_ms - oracle_ts_ms)
                    oracle_ages.append(age)
                    if age > threshold_ms:
                        stale_rows += 1
                        stale_old_oracle += 1
                except ValueError:
                    stale_rows += 1
                    stale_missing_oracle += 1
            else:
                stale_rows += 1
                stale_missing_oracle += 1

            if row.get("mark_price") is None:
                missing_mark += 1
            if row.get("index_price") is None:
                missing_index += 1
            spread = row.get("spread_bps")
            if spread is None:
                missing_spread += 1
            elif isinstance(spread, (int, float)):
                spreads.append(float(spread))

        diagnostics.append(
            QuoteDiagnostic(
                venue=row_venue,
                symbol=row_symbol,
                stale_threshold_ms=threshold_ms,
                rows=len(rows),
                market_open_rows=market_open_rows,
                tradable_rate=_pct(tradable_rows, len(rows)),
                stale_rate=_pct(stale_rows, len(rows)),
                missing_mark_price_rate=_pct(missing_mark, len(rows)),
                missing_index_price_rate=_pct(missing_index, len(rows)),
                missing_spread_rate=_pct(missing_spread, len(rows)),
                stale_missing_oracle_ts_rate=_pct(stale_missing_oracle, len(rows)),
                stale_old_oracle_ts_rate=_pct(stale_old_oracle, len(rows)),
                market_status_unknown_rate=_pct(market_unknown, len(rows)),
                market_closed_rate=_pct(market_closed, len(rows)),
                oracle_age_p50_ms=_quantile_int(oracle_ages, 0.5),
                oracle_age_p90_ms=_quantile_int(oracle_ages, 0.9),
                spread_p50_bps=_quantile(spreads, 0.5),
                spread_p90_bps=_quantile(spreads, 0.9),
            )
        )
    return diagnostics


def _quick_navigation(out_path: Path | None) -> dict[str, str]:
    if out_path is None:
        return {}
    reports_dir = out_path.parent
    return {
        "quote_diagnostics_report": str(out_path),
        "phase_gate_review_report": str(reports_dir / "phase_gate_review.md"),
        "current_state_index_report": str(reports_dir / "current_state_index.md"),
        "readiness_snapshot_report": str(reports_dir / "readiness_snapshot.md"),
        "live_evidence_report": str(reports_dir.parent / "docs/live_evidence_reports/latest.md"),
    }


def _related_reports(out_path: Path | None) -> dict[str, str]:
    if out_path is None:
        return {}
    reports_dir = out_path.parent
    return {
        "quote_diagnostics_report": str(out_path),
        "paper_operations_runbook_report": str(reports_dir / "paper_operations_runbook.md"),
        "go_no_go_report": str(reports_dir.parent / "research/go_no_go_report.md"),
        "execution_venue_diagnostics_report": str(reports_dir / "execution_venue_diagnostics.md"),
        "execution_gap_history_report": str(reports_dir / "execution_gap_history.md"),
        "execution_state_comparison_report": str(reports_dir / "execution_state_comparison_history.md"),
        "execution_snapshot_drift_report": str(reports_dir / "execution_snapshot_drift_history.md"),
        "execution_drift_overview_report": str(reports_dir / "execution_drift_overview.md"),
        "current_state_index_report": str(reports_dir / "current_state_index.md"),
        "readiness_snapshot_report": str(reports_dir / "readiness_snapshot.md"),
    }


def build_quote_diagnostics_report(
    *,
    raw_quotes_root: Path,
    venue: str | None = None,
    symbol: str | None = None,
    stale_thresholds_ms: dict[str, int] | None = None,
    out_path: Path | None = None,
    summary_path: Path | None = None,
) -> str:
    diagnostics = build_quote_diagnostics(
        raw_quotes_root,
        venue=venue,
        symbol=symbol,
        stale_thresholds_ms=stale_thresholds_ms,
    )
    row_count = sum(item.rows for item in diagnostics)
    venues = sorted({item.venue for item in diagnostics})
    symbols = sorted({item.symbol for item in diagnostics})
    summary = {
        "diagnostic_count": len(diagnostics),
        "row_count": row_count,
        "venues": venues,
        "symbols": symbols,
        "filters": {"venue": venue, "symbol": symbol},
        "entries": [item.__dict__.copy() for item in diagnostics],
        "quick_navigation": _quick_navigation(out_path),
        "related_reports": _related_reports(out_path),
        "quote_diagnostics_report_path": str(out_path) if out_path is not None else None,
    }

    lines = ["# Quote Diagnostics Report", ""]
    if summary["quick_navigation"]:
        lines.extend(["## Quick Navigation", ""])
        lines.extend(f"- {key}: {value}" for key, value in summary["quick_navigation"].items())
        lines.append("")
    if summary["related_reports"]:
        lines.extend(["## Related Reports", ""])
        lines.extend(f"- {key}: {value}" for key, value in summary["related_reports"].items())
        lines.append("")
    lines.extend(
        [
            "## Summary",
            "",
            f"- diagnostic_count: {summary['diagnostic_count']}",
            f"- row_count: {summary['row_count']}",
            f"- venues: {summary['venues']}",
            f"- symbols: {summary['symbols']}",
            f"- filter_venue: {venue}",
            f"- filter_symbol: {symbol}",
            "",
            "## Diagnostics",
            "",
        ]
    )
    if diagnostics:
        for item in diagnostics:
            lines.append(f"- venue={item.venue} symbol={item.symbol}")
            lines.append(f"  - stale_threshold_ms: {item.stale_threshold_ms}")
            lines.append(f"  - rows: {item.rows}")
            lines.append(f"  - market_open_rows: {item.market_open_rows}")
            lines.append(f"  - tradable_rate: {item.tradable_rate:.4f}")
            lines.append(f"  - stale_rate: {item.stale_rate:.4f}")
            lines.append(f"  - missing_mark_price_rate: {item.missing_mark_price_rate:.4f}")
            lines.append(f"  - missing_index_price_rate: {item.missing_index_price_rate:.4f}")
            lines.append(f"  - missing_spread_rate: {item.missing_spread_rate:.4f}")
            lines.append(f"  - oracle_age_p50_ms: {item.oracle_age_p50_ms}")
            lines.append(f"  - oracle_age_p90_ms: {item.oracle_age_p90_ms}")
            lines.append(f"  - spread_p50_bps: {item.spread_p50_bps}")
            lines.append(f"  - spread_p90_bps: {item.spread_p90_bps}")
    else:
        lines.append("- diagnostics: none")

    text = "\n".join(lines).rstrip() + "\n"
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    if summary_path is not None:
        write_json(summary_path, summary)
    return text
