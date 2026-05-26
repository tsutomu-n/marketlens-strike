from __future__ import annotations

from pathlib import Path

from sis.tracking.models import TrackingRecord


def build_tracking_report(records: list[TrackingRecord]) -> str:
    by_symbol: dict[str, list[TrackingRecord]] = {}
    for row in records:
        by_symbol.setdefault(row.canonical_symbol, []).append(row)

    lines = [
        "# Real Market To Trade[XYZ] Tracking Report",
        "",
        "## Symbol Decisions",
    ]
    for symbol in sorted(by_symbol):
        rows = by_symbol[symbol]
        total = len(rows)
        blocked = sum(1 for row in rows if not row.trade_allowed)
        block_rate = blocked / total if total else 0.0
        spreads = [row.venue_spread_bps for row in rows if row.venue_spread_bps is not None]
        depths = [
            row.venue_depth_10bps_usd for row in rows if row.venue_depth_10bps_usd is not None
        ]
        diffs = [row.mark_real_diff_bps for row in rows if row.mark_real_diff_bps is not None]
        decision = "keep" if block_rate < 0.5 else "watch-only"
        if symbol in {"SP500", "XYZ100"} and block_rate < 0.5:
            decision = "micro-live-candidate"
        if symbol == "EWJ":
            decision = "watch-only"
        lines.extend(
            [
                f"- {symbol}: decision={decision}, block_rate={block_rate:.2%}, samples={total}",
                f"  spread_bps_avg={(sum(spreads) / len(spreads)) if spreads else 'n/a'}",
                f"  depth_10bps_usd_avg={(sum(depths) / len(depths)) if depths else 'n/a'}",
                f"  mark_real_diff_bps_avg={(sum(diffs) / len(diffs)) if diffs else 'n/a'}",
            ]
        )

    return "\n".join(lines) + "\n"


def write_tracking_report(path: Path, report: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report, encoding="utf-8")
