from __future__ import annotations

from pathlib import Path

from sis.reports.summary_normalizers import normalize_phase_gate_summary, phase_gate_flat_fields
from sis.reports.weekly_review_symbols import backtest_symbol_scope

__all__ = ["current_gate_section_lines"]


def current_gate_section_lines(
    current_phase_gate_summary_path: Path,
    current_phase_gate: dict[str, object],
    symbols: list[str],
) -> list[str]:
    lines = ["## Current Trade[XYZ] Gate Snapshot", ""]
    lines.append(f"- source: {current_phase_gate_summary_path}")
    if current_phase_gate:
        phase_gate = normalize_phase_gate_summary(current_phase_gate)
        phase_gate_flat = phase_gate_flat_fields(phase_gate)
        diagnostics_symbols = current_phase_gate.get("diagnostics_symbols")
        lines.extend(
            [
                f"- decision: {phase_gate_flat.get('phase_gate_decision') or ''}",
                f"- strict_validation_passed: {phase_gate_flat.get('strict_validation_passed')}",
                f"- phase_gate_checked_files: {phase_gate_flat.get('phase_gate_checked_files')}",
            ]
        )
        if isinstance(diagnostics_symbols, list):
            formatted_symbols = ", ".join(
                str(symbol) for symbol in diagnostics_symbols if isinstance(symbol, str)
            )
            lines.append(f"- diagnostics_symbols: {formatted_symbols}")
    else:
        lines.append("- status: unavailable")
    if symbols:
        lines.extend(
            [
                f"- backtest_symbol_scope: {backtest_symbol_scope(symbols)}",
                (
                    "- interpretation: Backtest Metrics Snapshot is a historical/backtest "
                    "input and is not the current Trade[XYZ] symbol universe."
                ),
            ]
        )
    lines.append("")
    return lines
