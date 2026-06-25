from __future__ import annotations

import os
from decimal import Decimal
from pathlib import Path

import typer

from sis.commands.crypto_perp import _utc_now
from sis.commands.crypto_perp_account import build_fixture_account_snapshot
from sis.crypto_perp.io import write_json_artifact
from sis.crypto_perp.order_preview import (
    InstrumentOrderConstraints,
    OrderPreviewRequest,
    build_order_preview,
)
from sis.crypto_perp.tiny_live import (
    TINY_LIVE_CONFIRMATION_PHRASE,
    build_mock_tiny_live_measurement,
)


def register_crypto_perp_live_commands(app: typer.Typer) -> None:
    @app.command("crypto-perp-tiny-live-measurement")
    def crypto_perp_tiny_live_measurement_cmd(
        out: Path = typer.Option(
            Path("data/crypto_perp/live_measurement"),
            "--out",
            help="Output directory for mock tiny live measurement artifacts.",
        ),
        mock: bool = typer.Option(
            True,
            "--mock/--real-network",
            help="Only mock mode is implemented here. Real network requires separate approval.",
        ),
        confirm_live: bool = typer.Option(
            False,
            "--confirm-live",
            help="Explicit live-measurement confirmation flag.",
        ),
        confirmation_phrase: str = typer.Option("", "--confirmation-phrase"),
    ) -> None:
        if not mock:
            typer.echo("status=blocked")
            typer.echo("block_reason=REAL_NETWORK_TINY_LIVE_REQUIRES_SEPARATE_APPROVAL")
            raise typer.Exit(2)

        read_only_account = build_fixture_account_snapshot(utc_now_fn=_utc_now)
        account = read_only_account.model_copy(
            update={
                "credential_scope_attestation": read_only_account.credential_scope_attestation.model_copy(
                    update={"trade_enabled": True}
                )
            }
        )
        preview = build_order_preview(
            request=OrderPreviewRequest(
                event_id="event-fixture",
                decision_id="decision-fixture",
                symbol="BTCUSDT",
                product_type="USDT-FUTURES",
                side="buy",
                position_side="one_way",
                order_type="limit",
                margin_mode="isolated",
                margin_coin="USDT",
                requested_notional_usd=Decimal("25"),
                reference_price=Decimal("100"),
                limit_price=Decimal("100"),
                leverage=1,
            ),
            constraints=InstrumentOrderConstraints(
                symbol="BTCUSDT",
                product_type="USDT-FUTURES",
                price_multiplier=Decimal("0.1"),
                size_multiplier=Decimal("0.001"),
                min_order_amount=Decimal("5"),
                min_order_qty=Decimal("0.001"),
                max_market_order_qty=Decimal("10"),
            ),
            account_snapshot=read_only_account,
            created_at=_utc_now(),
        )
        measurement = build_mock_tiny_live_measurement(
            env=os.environ,
            confirm_live=confirm_live,
            confirmation_phrase=confirmation_phrase,
            account_snapshot=account,
            order_preview=preview,
            measured_at=_utc_now(),
        )
        path = out / "live_measurement.json"
        write_json_artifact(path, measurement.model_dump(mode="json"))
        typer.echo("execution_mode=mock")
        typer.echo(f"status={'pass' if measurement.preflight_status == 'PASS' else 'blocked'}")
        typer.echo(f"preflight_status={measurement.preflight_status}")
        typer.echo(f"live_order_submitted={str(measurement.live_order_submitted).lower()}")
        typer.echo(f"auto_trading_enabled={str(measurement.auto_trading_enabled).lower()}")
        typer.echo(f"confirmation_phrase_required={TINY_LIVE_CONFIRMATION_PHRASE}")
        typer.echo(f"live_measurement_path={path.as_posix()}")
