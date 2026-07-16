from __future__ import annotations

import os
from pathlib import Path
from typing import cast

import typer

from sis.crypto_perp.market_capture import (
    MarketCaptureConfig,
    OperationalChannel,
    run_bitget_public_market_capture,
)


def register_crypto_perp_market_capture_commands(app: typer.Typer) -> None:
    @app.command("crypto-perp-market-capture")
    def crypto_perp_market_capture_cmd(
        symbol: list[str] = typer.Option(
            ...,
            "--symbol",
            help="Bitget native symbol; repeatable.",
        ),
        channel: list[str] | None = typer.Option(
            None,
            "--channel",
            help="Operational public channel: books15 or trades. Repeatable.",
        ),
        duration_minutes: int = typer.Option(30, "--duration-minutes", min=1),
        heartbeat_seconds: int = typer.Option(30, "--heartbeat-seconds", min=1),
        pong_timeout_seconds: int = typer.Option(10, "--pong-timeout-seconds", min=1),
        reconnect_max_attempts: int = typer.Option(
            5,
            "--reconnect-max-attempts",
            min=1,
        ),
        segment_seconds: int = typer.Option(60, "--segment-seconds", min=1),
        max_rows_per_segment: int = typer.Option(
            10_000,
            "--max-rows-per-segment",
            min=1,
        ),
        out: Path = typer.Option(Path("data/crypto_perp/captures"), "--out"),
        network: bool = typer.Option(
            False,
            "--network",
            help="Explicitly allow the public Bitget WebSocket connection for this run.",
        ),
    ) -> None:
        if not network or os.getenv("SIS_ALLOW_PUBLIC_NETWORK") != "1":
            typer.echo("status=fail")
            typer.echo("error=PUBLIC_NETWORK_OPT_IN_REQUIRED")
            raise typer.Exit(2)
        raw_channels = channel or ["books15", "trades"]
        unsupported = sorted(set(raw_channels).difference({"books15", "trades"}))
        if unsupported:
            typer.echo("status=fail")
            typer.echo("error=UNSUPPORTED_OPERATIONAL_CHANNEL:" + ",".join(unsupported))
            raise typer.Exit(2)
        try:
            config = MarketCaptureConfig(
                symbols=symbol,
                channels=[cast(OperationalChannel, item) for item in raw_channels],
                duration_seconds=duration_minutes * 60,
                heartbeat_seconds=heartbeat_seconds,
                pong_timeout_seconds=pong_timeout_seconds,
                reconnect_max_attempts=reconnect_max_attempts,
                segment_seconds=segment_seconds,
                max_rows_per_segment=max_rows_per_segment,
                output_root=out,
            )
            result = run_bitget_public_market_capture(config)
        except Exception as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc
        typer.echo("network_attempted=true")
        typer.echo("external_api_called=true")
        typer.echo("wallet_used=false")
        typer.echo("signing_used=false")
        typer.echo("exchange_write_used=false")
        typer.echo("live_order_submitted=false")
        typer.echo("permits_live_order=false")
        typer.echo(f"status={result.run_status.lower()}")
        typer.echo(f"run_id={result.run_id}")
        typer.echo(f"row_count={result.row_count}")
        typer.echo(f"bytes_written={result.bytes_written}")
        typer.echo(
            f"projected_gzip_bytes_per_day={result.projected_gzip_bytes_per_day}"
        )
        typer.echo(f"reconnect_count={result.reconnect_count}")
        typer.echo(
            "run_path="
            + (out / f"run_id={result.run_id}" / "market_capture_run.json").as_posix()
        )
