from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import json
import os
from pathlib import Path
from typing import Literal, cast

import typer
from pydantic import ValidationError

from sis.commands.strategy_authoring import _resolve_workspace_path
from sis.crypto_perp.bitget.account import (
    CredentialScopeAttestation,
    CryptoPerpAccountSnapshot,
    build_account_snapshot,
)
from sis.crypto_perp.bitget.auth import missing_bitget_credential_env
from sis.crypto_perp.bitget.probe import run_provider_probe
from sis.crypto_perp.config import load_crypto_perp_lab_config
from sis.crypto_perp.event_card import build_event_card
from sis.crypto_perp.events import CryptoPerpEvent
from sis.crypto_perp.io import write_json_artifact, write_text_artifact
from sis.crypto_perp.models import ConfigValidationArtifact, CryptoPerpProducer, stable_hash
from sis.crypto_perp.order_preview import (
    InstrumentOrderConstraints,
    OrderPreviewRequest,
    build_order_preview,
)
from sis.crypto_perp.reason_codes import CryptoPerpReasonCode
from sis.crypto_perp.rendering import render_event_card_markdown
from sis.settings import get_settings


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _config_hash(config_path: Path) -> str:
    return "sha256:" + stable_hash([config_path.read_text(encoding="utf-8")])


def _load_config_for_cli(config_path: Path):
    settings = get_settings()
    resolved = _resolve_workspace_path(config_path, settings.data_dir)
    return load_crypto_perp_lab_config(resolved), resolved


def _write_config_validation(config_path: Path, out_dir: Path) -> ConfigValidationArtifact:
    config, resolved = _load_config_for_cli(config_path)
    artifact = ConfigValidationArtifact(
        artifact_id=stable_hash(
            ["crypto-perp-config-validate", config.config_id, _config_hash(resolved)]
        ),
        created_at=_utc_now(),
        producer=CryptoPerpProducer(command="crypto-perp-config-validate"),
        config_id=config.config_id,
        config_hash=_config_hash(resolved),
    )
    payload = artifact.model_dump(mode="json")
    write_json_artifact(out_dir / "config_validation.json", payload)
    write_text_artifact(
        out_dir / "config_validation.md",
        "\n".join(
            [
                "# Crypto Perp Config Validation",
                "",
                f"- config_id: `{artifact.config_id}`",
                f"- validation_status: `{artifact.validation_status}`",
                "- boundary: all normal flags false",
            ]
        ),
    )
    return artifact


def _env_enabled(name: str) -> bool:
    return os.getenv(name) == "1"


def _fixture_credential_attestation() -> CredentialScopeAttestation:
    return CredentialScopeAttestation(
        read_enabled=True,
        trade_enabled=False,
        withdrawal_disabled_confirmed=True,
        ip_restriction_confirmed=True,
        attested_by="local-fixture",
        attested_at=_utc_now(),
    )


def _fixture_account_snapshot() -> CryptoPerpAccountSnapshot:
    return build_account_snapshot(
        observed_at=_utc_now(),
        account_payload={
            "marginCoin": "USDT",
            "available": "100",
            "accountEquity": "100",
            "unrealizedPL": "0",
            "marginMode": "isolated",
            "posMode": "one_way_mode",
        },
        positions_payload=[],
        open_orders_payload=[],
        credential_scope_attestation=_fixture_credential_attestation(),
    )


def register_crypto_perp_commands(app: typer.Typer) -> None:
    @app.command("crypto-perp-config-validate")
    def crypto_perp_config_validate_cmd(
        config: Path = typer.Option(
            ...,
            "--config",
            help="crypto_perp_lab_config.v1 YAML/JSON.",
        ),
        out: Path = typer.Option(
            Path("data/crypto_perp/config_validation"),
            "--out",
            help="Output directory for config validation artifacts.",
        ),
    ) -> None:
        try:
            artifact = _write_config_validation(config, out)
        except (ValueError, ValidationError) as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        typer.echo("status=pass")
        typer.echo(f"config_id={artifact.config_id}")
        typer.echo(f"validation_status={artifact.validation_status}")
        typer.echo(f"validation_path={(out / 'config_validation.json').as_posix()}")
        typer.echo(f"report_path={(out / 'config_validation.md').as_posix()}")

    @app.command("crypto-perp-probe")
    def crypto_perp_probe_cmd(
        config: Path = typer.Option(
            Path("configs/crypto_perp/bitget_personal_edge_lab.yaml"),
            "--config",
            help="crypto_perp_lab_config.v1 YAML/JSON.",
        ),
        out: Path = typer.Option(
            Path("data/crypto_perp/provider_probe"),
            "--out",
            help="Output directory for provider probe artifacts.",
        ),
        raw_root: Path = typer.Option(
            Path("data/crypto_perp/raw"),
            "--raw-root",
            help="Root directory for immutable raw public snapshots.",
        ),
        network: bool = typer.Option(
            False,
            "--network/--no-network",
            help="Attempt public network only when env opt-in is also set.",
        ),
    ) -> None:
        lab_config, _resolved = _load_config_for_cli(config)
        env_name = lab_config.network_policy.public_network_env_var
        typer.echo(f"config_id={lab_config.config_id}")
        if not network or not _env_enabled(env_name):
            typer.echo("network_attempted=false")
            typer.echo("status=blocked")
            typer.echo(f"block_reason={CryptoPerpReasonCode.PUBLIC_NETWORK_OPT_IN_REQUIRED.value}")
            raise typer.Exit(2)
        try:
            result = run_provider_probe(
                config=lab_config,
                out_dir=out,
                raw_root=raw_root,
                network_attempted=True,
                started_at=_utc_now(),
            )
        except Exception as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        typer.echo("network_attempted=true")
        typer.echo("credentials_used=false")
        typer.echo("status=pass")
        typer.echo(f"probe_id={result.probe.probe_id}")
        typer.echo(f"probe_path={result.probe_path.as_posix()}")
        typer.echo(f"report_path={result.report_path.as_posix()}")

    @app.command("crypto-perp-refresh")
    def crypto_perp_refresh_cmd(
        config: Path = typer.Option(
            Path("configs/crypto_perp/bitget_personal_edge_lab.yaml"),
            "--config",
            help="crypto_perp_lab_config.v1 YAML/JSON.",
        ),
        through: str = typer.Option(
            "config",
            "--through",
            help="Refresh stage. M01 supports config only; later tasks add probe/events.",
        ),
    ) -> None:
        lab_config, _resolved = _load_config_for_cli(config)
        typer.echo(f"config_id={lab_config.config_id}")
        if through == "config":
            typer.echo("status=pass")
            typer.echo("through=config")
            return
        typer.echo("status=blocked")
        block_reason = (
            CryptoPerpReasonCode.EVENT_REFRESH_NOT_IMPLEMENTED_M04
            if through == "events"
            else CryptoPerpReasonCode.MARKET_REFRESH_NOT_IMPLEMENTED_M02
        )
        typer.echo(f"block_reason={block_reason.value}")
        raise typer.Exit(2)

    @app.command("crypto-perp-watchdeck")
    def crypto_perp_watchdeck_cmd(
        config: Path = typer.Option(
            Path("configs/crypto_perp/bitget_personal_edge_lab.yaml"),
            "--config",
            help="crypto_perp_lab_config.v1 YAML/JSON.",
        ),
        event_path: Path | None = typer.Option(
            None,
            "--event",
            help="Render a crypto_perp_event.v1 JSON artifact as an event card.",
        ),
        top: int = typer.Option(20, "--top", help="Maximum cards to display."),
    ) -> None:
        if event_path is not None:
            try:
                event_payload = json.loads(event_path.read_text(encoding="utf-8"))
                event = CryptoPerpEvent.model_validate(event_payload)
            except Exception as exc:
                typer.echo("status=fail")
                typer.echo(f"error={exc}")
                raise typer.Exit(2) from exc
            typer.echo(render_event_card_markdown(build_event_card(event)))
            return

        lab_config, _resolved = _load_config_for_cli(config)
        if top <= 0:
            typer.echo("status=fail")
            typer.echo("error=top must be positive")
            raise typer.Exit(2)
        typer.echo(f"config_id={lab_config.config_id}")
        typer.echo("status=blocked")
        typer.echo(f"block_reason={CryptoPerpReasonCode.WATCHDECK_NOT_IMPLEMENTED_M04.value}")
        raise typer.Exit(2)

    @app.command("crypto-perp-account-probe")
    def crypto_perp_account_probe_cmd(
        config: Path = typer.Option(
            Path("configs/crypto_perp/bitget_personal_edge_lab.yaml"),
            "--config",
            help="crypto_perp_lab_config.v1 YAML/JSON.",
        ),
        out: Path = typer.Option(
            Path("data/crypto_perp/account_probe"),
            "--out",
            help="Output directory for account snapshot artifacts.",
        ),
        fixture: bool = typer.Option(
            True,
            "--fixture/--no-fixture",
            help="Use a local read-only fixture. Real credentialed network read is blocked in M08.",
        ),
    ) -> None:
        lab_config, _resolved = _load_config_for_cli(config)
        if not fixture:
            env_name = lab_config.network_policy.credentialed_read_env_var
            typer.echo(f"config_id={lab_config.config_id}")
            if not _env_enabled(env_name):
                typer.echo("network_attempted=false")
                typer.echo("status=blocked")
                typer.echo("block_reason=CREDENTIALED_READ_OPT_IN_REQUIRED")
                raise typer.Exit(2)
            missing = missing_bitget_credential_env()
            if missing:
                typer.echo("network_attempted=false")
                typer.echo("status=blocked")
                typer.echo(f"missing_env={','.join(missing)}")
                raise typer.Exit(2)
            typer.echo("network_attempted=false")
            typer.echo("status=blocked")
            typer.echo("block_reason=CREDENTIALED_READ_NETWORK_NOT_IMPLEMENTED_M08")
            raise typer.Exit(2)

        snapshot = _fixture_account_snapshot()
        path = out / "account_snapshot.json"
        write_json_artifact(path, snapshot.model_dump(mode="json"))
        typer.echo("network_attempted=false")
        typer.echo("credentials_used=false")
        typer.echo("status=pass")
        typer.echo(f"account_snapshot_id={snapshot.account_snapshot_id}")
        typer.echo(f"account_snapshot_path={path.as_posix()}")

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
            snapshot = _fixture_account_snapshot()
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
                created_at=_utc_now(),
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
