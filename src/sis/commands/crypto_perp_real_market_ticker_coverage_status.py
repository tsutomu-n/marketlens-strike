from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import typer

from sis.crypto_perp.real_market_ticker_coverage_status import (
    write_real_market_ticker_coverage_status,
)

DEFAULT_PUBLIC_SOURCE_ROOT = Path(
    "data/strategy_idea_candidates/btc-perp/bitget_public_source/source_root"
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def register_crypto_perp_real_market_ticker_coverage_status_commands(
    app: typer.Typer,
) -> None:
    @app.command("crypto-perp-real-market-ticker-coverage-status")
    def crypto_perp_real_market_ticker_coverage_status_cmd(
        source_root: Path = typer.Option(
            DEFAULT_PUBLIC_SOURCE_ROOT,
            "--source-root",
            help="Local Bitget public source_root containing candles and ticker_rows.",
        ),
        symbol: str = typer.Option("BTCUSDT", "--symbol"),
        target_event_count: int = typer.Option(30, "--target-event-count", min=1),
        ticker_max_staleness_seconds: int = typer.Option(
            900,
            "--ticker-max-staleness-seconds",
            min=0,
        ),
        lookback_minutes: int = typer.Option(60, "--lookback-minutes", min=1),
        horizon_minutes: int = typer.Option(60, "--horizon-minutes", min=1),
        interval_minutes: int = typer.Option(5, "--interval-minutes", min=1),
        out: Path = typer.Option(
            Path("data/crypto_perp/real_market_no_cash/ticker_coverage_status/latest"),
            "--out",
            help="Output directory for ticker coverage status artifacts.",
        ),
    ) -> None:
        try:
            result = write_real_market_ticker_coverage_status(
                source_root=source_root,
                out_dir=out,
                created_at=_utc_now(),
                symbol=symbol,
                target_event_count=target_event_count,
                ticker_max_staleness_seconds=ticker_max_staleness_seconds,
                lookback_minutes=lookback_minutes,
                horizon_minutes=horizon_minutes,
                interval_minutes=interval_minutes,
            )
        except Exception as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        payload = result.payload
        flags = payload["boundary_flags"]
        typer.echo("status=pass")
        typer.echo(f"decision={result.decision}")
        typer.echo(f"coverage_passed={str(result.coverage_passed).lower()}")
        typer.echo(f"ticker_covered_candidate_count={result.ticker_covered_candidate_count}")
        typer.echo(f"target_event_count={result.target_event_count}")
        typer.echo(f"coverage_shortfall={payload['coverage_shortfall']}")
        typer.echo(f"diagnosis={payload['diagnosis']}")
        typer.echo(f"valid_bid_ask_row_count={payload['valid_bid_ask_row_count']}")
        typer.echo(f"matured_ticker_row_count={payload['matured_ticker_row_count']}")
        typer.echo(
            f"future_unmatured_ticker_row_count={payload['future_unmatured_ticker_row_count']}"
        )
        typer.echo(f"latest_candle_ts_ms={payload['latest_candle_ts_ms']}")
        typer.echo(f"latest_matured_event_cutoff_ms={payload['latest_matured_event_cutoff_ms']}")
        typer.echo(f"latest_ticker_ts_received_ms={payload['latest_ticker_ts_received_ms']}")
        typer.echo(f"json_path={result.json_path.as_posix()}")
        typer.echo(f"markdown_path={result.markdown_path.as_posix()}")
        typer.echo(f"next_command={payload['next_actions'][0]['command']}")
        typer.echo(f"network_attempted={str(flags['network_attempted']).lower()}")
        typer.echo(
            f"credentialed_exchange_api_used={str(flags['credentialed_exchange_api_used']).lower()}"
        )
        typer.echo(f"paper_permission_granted={str(flags['paper_permission_granted']).lower()}")
        typer.echo(f"paper_order_created={str(flags['paper_order_created']).lower()}")
        typer.echo(f"actual_cash_used={str(flags['actual_cash_used']).lower()}")
        typer.echo(f"wallet_used={str(flags['wallet_used']).lower()}")
        typer.echo(f"signing_used={str(flags['signing_used']).lower()}")
        typer.echo(f"exchange_write_used={str(flags['exchange_write_used']).lower()}")
        typer.echo(f"live_order_submitted={str(flags['live_order_submitted']).lower()}")
        typer.echo(f"profit_proven={str(flags['profit_proven']).lower()}")
