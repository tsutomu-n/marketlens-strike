from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
from typing import cast

import typer

from sis.crypto_perp.io import write_json_artifact, write_text_artifact
from sis.crypto_perp.portfolio_capacity.inventory import build_portfolio_capacity_inventory
from sis.crypto_perp.portfolio_capacity.models import (
    ActionPolicy,
    MetricScenario,
    PortfolioCapacityPolicy,
    SameTimestampCashPolicy,
)
from sis.crypto_perp.portfolio_capacity.pack_reader import (
    build_portfolio_capacity_case,
    load_candidate_pack,
)
from sis.crypto_perp.portfolio_capacity.reference_path import run_reference_portfolio_path
from sis.crypto_perp.portfolio_capacity.rendering import render_portfolio_capacity_report
from sis.crypto_perp.portfolio_capacity.vectorbt_diff import run_vectorbt_differential

_ACTION_POLICIES = {
    "CURRENT_SELECTOR",
    "ALWAYS_CONTINUATION",
    "ALWAYS_REVERSAL",
    "NO_TRADE",
}
_METRIC_SCENARIOS = {"BASE", "STRESS"}
_SAME_TIMESTAMP_POLICIES = {"NO_SAME_TIMESTAMP_REUSE", "EXIT_THEN_ENTRY"}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _choice(value: str, allowed: set[str], name: str) -> str:
    normalized = value.strip().upper()
    if normalized not in allowed:
        raise ValueError(f"{name} must be one of: {', '.join(sorted(allowed))}")
    return normalized


def register_crypto_perp_portfolio_capacity_commands(app: typer.Typer) -> None:
    @app.command("crypto-perp-portfolio-capacity")
    def crypto_perp_portfolio_capacity_cmd(
        candidate_pack_dir: Path = typer.Option(
            Path("data/crypto_perp/backtest_candidate_pack/latest"),
            "--candidate-pack-dir",
            help="Directory containing one complete Crypto Perp Backtest Candidate Pack.",
        ),
        initial_cash_usd: str = typer.Option("3000", "--initial-cash-usd"),
        max_open_positions: int = typer.Option(
            1,
            "--max-open-positions",
            min=1,
            help=(
                "Maximum concurrent positions when --unlimited-open-positions "
                "is not set."
            ),
        ),
        unlimited_open_positions: bool = typer.Option(
            False,
            "--unlimited-open-positions",
            help="Disable the global concurrent-position limit.",
        ),
        max_open_positions_per_symbol: int = typer.Option(
            1,
            "--max-open-positions-per-symbol",
            min=1,
        ),
        action_policy: str = typer.Option("CURRENT_SELECTOR", "--action-policy"),
        metric_scenario: str = typer.Option("STRESS", "--metric-scenario"),
        same_timestamp_cash_policy: str = typer.Option(
            "NO_SAME_TIMESTAMP_REUSE",
            "--same-timestamp-cash-policy",
        ),
        with_vectorbt_diff: bool = typer.Option(
            False,
            "--with-vectorbt-diff/--without-vectorbt-diff",
            help="Run the optional VectorBT gross-PnL/fixed-cost differential.",
        ),
        out: Path = typer.Option(
            Path("data/crypto_perp/portfolio_capacity/latest"),
            "--out",
        ),
    ) -> None:
        try:
            created = _utc_now()
            loaded = load_candidate_pack(candidate_pack_dir)
            policy = PortfolioCapacityPolicy(
                initial_cash_usd=Decimal(initial_cash_usd),
                max_open_positions=(
                    None if unlimited_open_positions else max_open_positions
                ),
                max_open_positions_per_symbol=max_open_positions_per_symbol,
                action_policy=cast(
                    ActionPolicy,
                    _choice(action_policy, _ACTION_POLICIES, "action_policy"),
                ),
                metric_scenario=cast(
                    MetricScenario,
                    _choice(metric_scenario, _METRIC_SCENARIOS, "metric_scenario"),
                ),
                same_timestamp_cash_policy=cast(
                    SameTimestampCashPolicy,
                    _choice(
                        same_timestamp_cash_policy,
                        _SAME_TIMESTAMP_POLICIES,
                        "same_timestamp_cash_policy",
                    ),
                ),
            )
            inventory = build_portfolio_capacity_inventory(loaded)
            case = build_portfolio_capacity_case(
                loaded,
                policy=policy,
                created_at=created,
            )
            result = run_reference_portfolio_path(case, created_at=created)
            vectorbt_result = (
                run_vectorbt_differential(case, result, created_at=created)
                if with_vectorbt_diff
                else None
            )
        except Exception as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        out.mkdir(parents=True, exist_ok=True)
        inventory_path = out / "runtime_inventory.json"
        case_path = out / "case.json"
        result_path = out / "result.json"
        timeline_path = out / "timeline.jsonl"
        report_path = out / "report.md"
        write_json_artifact(inventory_path, inventory)
        write_json_artifact(case_path, case.model_dump(mode="json"))
        write_json_artifact(result_path, result.model_dump(mode="json"))
        timeline_path.write_text(
            "".join(
                json.dumps(row.model_dump(mode="json"), ensure_ascii=False) + "\n"
                for row in result.timeline
            ),
            encoding="utf-8",
        )
        vectorbt_path: Path | None = None
        if vectorbt_result is not None:
            vectorbt_path = out / "vectorbt_differential.json"
            write_json_artifact(vectorbt_path, vectorbt_result.model_dump(mode="json"))
        write_text_artifact(
            report_path,
            render_portfolio_capacity_report(case, result, vectorbt_result),
        )
        typer.echo("network_attempted=false")
        typer.echo("external_api_called=false")
        typer.echo("actual_cash_used=false")
        typer.echo("profit_proven=false")
        typer.echo("wallet_used=false")
        typer.echo("exchange_write_used=false")
        typer.echo("live_order_submitted=false")
        typer.echo("permits_live_order=false")
        typer.echo("status=pass")
        typer.echo(f"run_status={result.run_status}")
        typer.echo(f"accepted_trade_count={result.accepted_trade_count}")
        typer.echo(f"rejected_trade_count={result.rejected_trade_count}")
        typer.echo(
            "simulated_account_pnl_estimate_usd="
            f"{result.simulated_account_pnl_estimate_usd}"
        )
        typer.echo(
            f"economic_result_estimate_usd={result.economic_result_estimate_usd}"
        )
        typer.echo(f"runtime_inventory_path={inventory_path.as_posix()}")
        typer.echo(f"case_path={case_path.as_posix()}")
        typer.echo(f"result_path={result_path.as_posix()}")
        typer.echo(f"timeline_path={timeline_path.as_posix()}")
        if vectorbt_path is not None:
            typer.echo(f"vectorbt_differential_path={vectorbt_path.as_posix()}")
        typer.echo(f"report_path={report_path.as_posix()}")
