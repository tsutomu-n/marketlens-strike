from __future__ import annotations

from pathlib import Path
from typing import Protocol


class OperationChainReportBuilder(Protocol):
    def __call__(
        self,
        *,
        operation_chain_path: Path,
        out_path: Path,
        summary_path: Path,
    ) -> str: ...


def write_operation_chain_report(
    *,
    settings_data_dir: Path,
    report_filename: str,
    summary_filename: str,
    build_report: OperationChainReportBuilder,
) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports" / report_filename
    summary_out = settings_data_dir / "ops" / summary_filename
    text = build_report(
        operation_chain_path=settings_data_dir / "ops/operation_manifests.jsonl",
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text
