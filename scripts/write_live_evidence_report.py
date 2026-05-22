#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sis.reports.live_evidence_report import (  # noqa: E402
    build_live_evidence_report_data,
    default_followup_output_path,
    default_html_output_path,
    default_markdown_output_path,
    render_live_evidence_followup,
    render_live_evidence_html,
    render_live_evidence_report,
    wait_for_completion,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Wait for a live evidence run to finish, settle, and write markdown + HTML reports."
    )
    parser.add_argument("--log-path", type=Path, required=True, help="Path to logs/live_evidence/live_evidence_*.log")
    parser.add_argument("--markdown-output-path", type=Path, help="AI-facing markdown output path.")
    parser.add_argument("--html-output-path", type=Path, help="Human-facing HTML output path.")
    parser.add_argument("--followup-output-path", type=Path, help="Auto-generated next-work markdown path.")
    parser.add_argument("--data-dir", type=Path, default=Path("data"), help="Artifact root. Defaults to data/.")
    parser.add_argument("--wait", action="store_true", help="Wait until the live evidence run completes or fails.")
    parser.add_argument("--poll-seconds", type=int, default=15, help="Polling interval when --wait is set.")
    parser.add_argument("--timeout-seconds", type=int, default=3 * 60 * 60, help="Max wait time when --wait is set.")
    parser.add_argument("--settle-seconds", type=int, default=180, help="Extra wait after terminal status before reading artifacts.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    markdown_output_path = args.markdown_output_path or default_markdown_output_path(args.log_path)
    html_output_path = args.html_output_path or default_html_output_path(args.log_path)
    followup_output_path = args.followup_output_path or default_followup_output_path(args.log_path)
    status = None
    if args.wait:
        status = wait_for_completion(args.log_path, poll_seconds=args.poll_seconds, timeout_seconds=args.timeout_seconds)
        if args.settle_seconds > 0:
            import time

            time.sleep(args.settle_seconds)
    data = build_live_evidence_report_data(
        data_dir=args.data_dir,
        log_path=args.log_path,
        output_path=markdown_output_path,
        status=status,
    )
    markdown_output_path.parent.mkdir(parents=True, exist_ok=True)
    html_output_path.parent.mkdir(parents=True, exist_ok=True)
    followup_output_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_output_path.write_text(render_live_evidence_report(data), encoding="utf-8")
    html_output_path.write_text(render_live_evidence_html(data), encoding="utf-8")
    followup_output_path.write_text(render_live_evidence_followup(data), encoding="utf-8")
    print(f"written_markdown: {markdown_output_path}")
    print(f"written_html: {html_output_path}")
    print(f"written_followup: {followup_output_path}")
    print(f"status: {data.status}")
    print(f"decision: {data.decision}")
    return 0 if data.status == "completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
