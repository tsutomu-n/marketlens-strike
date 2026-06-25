from __future__ import annotations

from pathlib import Path
import subprocess
from typing import Protocol

import typer

from sis.models import InstrumentSpec
from sis.settings import get_settings
from sis.storage.jsonl_store import write_json
from sis.venues.trade_xyz.collection_config import DEFAULT_COLLECTION_CONFIG_PATH
from sis.venues.trade_xyz.collection_config import load_trade_xyz_data_collection_config
from sis.venues.trade_xyz.ws_envelope import SUPPORTED_WS_SUBSCRIPTIONS
from sis.venues.trade_xyz.ws_recorder import run_trade_xyz_ws_capture
from sis.venues.trade_xyz.ws_recorder import WsCaptureConfig
from sis.venues.trade_xyz.ws_recorder import WsSubscriptionTarget


class ResolveActiveTradeXyzInstruments(Protocol):
    def __call__(
        self,
        *,
        data_dir: Path,
        registry_path: Path | None,
        symbols: str | None,
        max_symbols: int | None,
    ) -> tuple[Path, list[InstrumentSpec]]: ...


def register_quote_ws_collection_commands(
    app: typer.Typer,
    *,
    resolve_active_trade_xyz_instruments_fn: ResolveActiveTradeXyzInstruments,
) -> None:
    @app.command("collect-trade-xyz-ws")
    def collect_trade_xyz_ws_cmd(
        collection_config: Path = typer.Option(
            DEFAULT_COLLECTION_CONFIG_PATH,
            "--collection-config",
            help="Non-secret Trade[XYZ] data collection defaults.",
        ),
        registry_path: Path | None = typer.Option(
            None,
            "--registry-path",
            help="Instrument registry JSON written by `uv run sis probe trade-xyz`.",
        ),
        symbols: str | None = typer.Option(None, "--symbols", help="Comma-separated symbols."),
        max_symbols: int | None = typer.Option(None, "--max-symbols"),
        subscriptions: str | None = typer.Option(
            None,
            "--subscriptions",
            help="Comma-separated subscriptions. Supported: bbo,trades,activeAssetCtx,l2Book,allMids.",
        ),
        ws_url: str | None = typer.Option(None, "--ws-url"),
        duration_minutes: int | None = typer.Option(None, "--duration-minutes"),
        heartbeat_seconds: int | None = typer.Option(None, "--heartbeat-seconds"),
        output_dir: Path | None = typer.Option(None, "--output-dir"),
        write_control_messages: bool = typer.Option(
            True,
            "--write-control-messages/--drop-control-messages",
        ),
        dry_run: bool = typer.Option(False, "--dry-run"),
    ) -> None:
        settings = get_settings()
        config = load_trade_xyz_data_collection_config(collection_config)
        requested_subscriptions = (
            [item.strip() for item in subscriptions.split(",") if item.strip()]
            if subscriptions
            else list(config.ws_default_subscriptions)
        )
        invalid_subscriptions = [
            item for item in requested_subscriptions if item not in SUPPORTED_WS_SUBSCRIPTIONS
        ]
        if invalid_subscriptions:
            typer.echo("unsupported subscriptions: " + ",".join(invalid_subscriptions))
            raise typer.Exit(code=2)
        resolved_registry_path, active_trade_xyz = resolve_active_trade_xyz_instruments_fn(
            data_dir=settings.data_dir,
            registry_path=registry_path,
            symbols=symbols,
            max_symbols=max_symbols,
        )
        targets: list[WsSubscriptionTarget] = []
        for subscription_name in requested_subscriptions:
            if subscription_name == "allMids":
                targets.append(WsSubscriptionTarget(subscription=subscription_name))
                continue
            for instrument in active_trade_xyz:
                coin = instrument.coin or f"xyz:{instrument.canonical_symbol}"
                targets.append(
                    WsSubscriptionTarget(
                        subscription=subscription_name,
                        canonical_symbol=instrument.canonical_symbol,
                        coin=coin,
                    )
                )
        effective_output_dir = output_dir or (settings.data_dir / config.ws_output_root)
        effective_duration_minutes = duration_minutes or config.ws_duration_minutes
        effective_heartbeat_seconds = heartbeat_seconds or config.ws_heartbeat_seconds
        effective_ws_url = ws_url or config.ws_url
        capture_config = WsCaptureConfig(
            ws_url=effective_ws_url,
            dex="xyz",
            output_root=effective_output_dir,
            duration_seconds=max(1, effective_duration_minutes * 60),
            heartbeat_seconds=effective_heartbeat_seconds,
            reconnect_max_attempts=config.ws_reconnect_max_attempts,
            reconnect_initial_delay_seconds=config.ws_reconnect_initial_delay_seconds,
            reconnect_max_delay_seconds=config.ws_reconnect_max_delay_seconds,
            write_control_messages=write_control_messages and config.ws_write_control_messages,
            dry_run=dry_run,
        )
        if dry_run:
            typer.echo("dry_run=true")
            typer.echo(f"registry_path={resolved_registry_path}")
            typer.echo(f"symbols={','.join(item.canonical_symbol for item in active_trade_xyz)}")
            typer.echo(f"subscriptions={','.join(requested_subscriptions)}")
            typer.echo(f"ws_url={effective_ws_url}")
            typer.echo(f"heartbeat_seconds={effective_heartbeat_seconds}")
            typer.echo(f"duration_minutes={effective_duration_minutes}")
            typer.echo(f"output_dir={effective_output_dir}")
            return
        manifest = run_trade_xyz_ws_capture(config=capture_config, targets=targets)
        git_head = None
        try:
            git_head = subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                text=True,
            ).strip()
        except Exception:
            git_head = None
        manifest["command"] = "collect-trade-xyz-ws"
        manifest["registry_path"] = str(resolved_registry_path)
        manifest["git_head"] = git_head
        write_json(
            settings.data_dir / "manifests/trade_xyz_ws_capture_manifest.json",
            manifest,
        )
        typer.echo(
            f"manifest_path={settings.data_dir / 'manifests/trade_xyz_ws_capture_manifest.json'}"
        )
        typer.echo(f"row_count={manifest['row_count']}")
        typer.echo(f"reconnect_count={manifest['reconnect_count']}")
        typer.echo(f"error_count={manifest['error_count']}")
