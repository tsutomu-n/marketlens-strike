from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Callable, Literal, cast

import typer

from sis.commands.crypto_perp_account import build_fixture_account_snapshot
from sis.crypto_perp.bitget.account import CryptoPerpAccountSnapshot
from sis.crypto_perp.io import write_json_artifact
from sis.crypto_perp.order_preview import (
    InstrumentOrderConstraints,
    OrderPreviewRequest,
    build_order_preview,
)


def register_crypto_perp_order_preview_commands(
    app: typer.Typer,
    *,
    utc_now_fn: Callable[[], datetime],
) -> None:
    @app.command("crypto-perp-order-preview")
    def crypto_perp_order_preview_cmd(
        out: Path = typer.Option(
            Path("data/crypto_perp/order_preview"),
            "--out",
            help="Output directory for order preview artifacts.",
        ),
        account_snapshot: Path | None = typer.Option(
            None,
            "--account-snapshot",
            help="Optional crypto_perp_account_snapshot.v1 JSON. Fixture account is used if omitted.",
        ),
        event_id: str = typer.Option("event-fixture", "--event-id"),
        decision_id: str = typer.Option("decision-fixture", "--decision-id"),
        symbol: str = typer.Option("BTCUSDT", "--symbol"),
        side: str = typer.Option("buy", "--side"),
        position_side: str = typer.Option("one_way", "--position-side"),
        notional_usd: str = typer.Option("25", "--notional-usd"),
        reference_price: str = typer.Option("100", "--reference-price"),
        limit_price: str = typer.Option("100", "--limit-price"),
    ) -> None:
        if account_snapshot is None:
            snapshot = build_fixture_account_snapshot(utc_now_fn=utc_now_fn)
        else:
            payload = json.loads(account_snapshot.read_text(encoding="utf-8"))
            snapshot = CryptoPerpAccountSnapshot.model_validate(payload)
        try:
            if side not in {"buy", "sell"}:
                raise ValueError("side must be buy or sell")
            if position_side not in {"one_way", "long", "short"}:
                raise ValueError("position_side must be one_way, long, or short")
            side_value = cast(Literal["buy", "sell"], side)
            position_side_value = cast(Literal["one_way", "long", "short"], position_side)
            request = OrderPreviewRequest(
                event_id=event_id,
                decision_id=decision_id,
                symbol=symbol,
                product_type="USDT-FUTURES",
                side=side_value,
                position_side=position_side_value,
                order_type="limit",
                margin_mode="isolated",
                margin_coin="USDT",
                requested_notional_usd=Decimal(notional_usd),
                reference_price=Decimal(reference_price),
                limit_price=Decimal(limit_price),
                leverage=1,
            )
            preview = build_order_preview(
                request=request,
                constraints=InstrumentOrderConstraints(
                    symbol=symbol,
                    product_type="USDT-FUTURES",
                    price_multiplier=Decimal("0.1"),
                    size_multiplier=Decimal("0.001"),
                    min_order_amount=Decimal("5"),
                    min_order_qty=Decimal("0.001"),
                    max_market_order_qty=Decimal("10"),
                ),
                account_snapshot=snapshot,
                created_at=utc_now_fn(),
            )
        except Exception as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        path = out / "order_preview.json"
        write_json_artifact(path, preview.model_dump(mode="json"))
        typer.echo("network_attempted=false")
        typer.echo("exchange_write_used=false")
        typer.echo("status=pass" if preview.preview_status == "READY" else "status=blocked")
        typer.echo(f"preview_status={preview.preview_status}")
        typer.echo(f"would_submit_order={str(preview.would_submit_order).lower()}")
        typer.echo(f"client_oid={preview.client_oid}")
        typer.echo(f"order_preview_path={path.as_posix()}")
