from __future__ import annotations

from pathlib import Path

from sis.paper.fills import PaperFill
from sis.paper.portfolio import PaperPosition


def build_daily_paper_report(
    fills: list[PaperFill],
    positions: list[PaperPosition],
    out_path: Path | None = None,
) -> str:
    lines = [
        "# Daily Paper Report",
        "",
        f"- fills: {len(fills)}",
        f"- open_positions: {len(positions)}",
        f"- symbols: {', '.join(sorted({fill.canonical_symbol for fill in fills})) if fills else ''}",
        "",
        "| Venue | Symbol | Side | Quantity | Avg Entry | Realized PnL |",
        "|---|---|---|---:|---:|---:|",
    ]
    for position in positions:
        lines.append(
            f"| {position.venue} | {position.canonical_symbol} | {position.side} | {position.quantity:.4f} | "
            f"{position.avg_entry_price:.4f} | {position.realized_pnl:.4f} |"
        )
    text = "\n".join(lines) + "\n"
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    return text
