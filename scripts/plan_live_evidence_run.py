#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sis.live_evidence_plan import build_live_evidence_plan  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plan the next shared live evidence collection window for gTrade symbols."
    )
    parser.add_argument(
        "--symbol", dest="symbols", action="append", help="Symbol to include. Repeatable."
    )
    parser.add_argument("--duration-minutes", type=int, default=120)
    parser.add_argument("--metadata-interval-seconds", type=int, default=120)
    parser.add_argument(
        "--schedule", action="store_true", help="Schedule the computed run immediately."
    )
    parser.add_argument("--launcher-out", default="logs/live_evidence/next_schedule_launcher.out")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    symbols = args.symbols or ["QQQ", "SPY", "XAU"]
    plan = build_live_evidence_plan(symbols)

    print(f"venue={plan.venue}")
    print(f"symbols={' '.join(plan.symbols)}")
    for window in plan.windows:
        print(
            f"{window.symbol}: market_status={window.market_status} "
            f"recommended_start_jst={window.recommended_start_jst.isoformat()} "
            f"recommended_end_jst={window.recommended_end_jst.isoformat()}"
        )
    print(f"target_start_jst={plan.target_start_jst.isoformat()}")
    print(f"schedule_spec_jst={plan.target_spec_jst}")
    print(
        "schedule_command="
        f"bash scripts/schedule_live_evidence.sh {plan.target_spec_jst} "
        f"{args.duration_minutes} {args.metadata_interval_seconds}"
    )

    if not args.schedule:
        return 0

    launcher_out = Path(args.launcher_out)
    launcher_out.parent.mkdir(parents=True, exist_ok=True)
    with launcher_out.open("w", encoding="utf-8") as stream:
        process = subprocess.Popen(
            [
                "setsid",
                "bash",
                "scripts/schedule_live_evidence.sh",
                plan.target_spec_jst,
                str(args.duration_minutes),
                str(args.metadata_interval_seconds),
            ],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=stream,
            stderr=subprocess.STDOUT,
            start_new_session=False,
            env=os.environ.copy(),
        )
    print(f"scheduled_pid={process.pid}")
    print(f"launcher_out={launcher_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
