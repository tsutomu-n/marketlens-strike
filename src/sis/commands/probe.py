from __future__ import annotations

from pathlib import Path

import typer
from loguru import logger

from sis.settings import get_settings
from sis.storage.jsonl_store import read_json, write_json
from sis.venues.archive.gtrade.registry import GTRADE_TARGETS
from sis.venues.archive.ostium.probe import OSTIUM_PRICES_ENDPOINT, write_ostium_live_probe_outputs
from sis.venues.archive.ostium.registry import OSTIUM_TARGETS
from sis.venues.trade_xyz.client import TradeXyzClient
from sis.venues.trade_xyz.registry import build_trade_xyz_registry, write_trade_xyz_registry
from sis.venues.trade_xyz.report import (
    build_trade_xyz_universe_report,
    write_trade_xyz_universe_report,
    write_trade_xyz_universe_summary,
)


def register_probe_commands(app: typer.Typer) -> None:
    probe_app = typer.Typer(no_args_is_help=True)
    app.add_typer(probe_app, name="probe")

    @probe_app.command("gtrade")
    def probe_gtrade() -> None:
        settings = get_settings()
        out = settings.data_dir / "registry/gtrade_instrument_registry.json"
        write_json(out, [item.model_dump(mode="json") for item in GTRADE_TARGETS])
        logger.info("written: {}", out)

    @probe_app.command("ostium")
    def probe_ostium(
        read_only_live: bool = typer.Option(
            False,
            "--read-only-live",
            help="Fetch Ostium Builder API prices with a GET-only probe before writing the registry.",
        ),
        endpoint: str = typer.Option(OSTIUM_PRICES_ENDPOINT, "--endpoint", help="Ostium prices endpoint."),
        pairs_metadata_path: Path | None = typer.Option(
            None,
            "--pairs-metadata-path",
            help="Optional Ostium SDK getPairs sidecar JSON path.",
        ),
    ) -> None:
        settings = get_settings()
        out = settings.data_dir / "registry/ostium_instrument_registry.json"
        if read_only_live:
            targets, quotes = write_ostium_live_probe_outputs(
                data_dir=settings.data_dir,
                endpoint=endpoint,
                pairs_metadata_path=pairs_metadata_path,
            )
        else:
            targets = OSTIUM_TARGETS
            quotes = []
        write_json(out, [item.model_dump(mode="json") for item in targets])
        logger.info("written: {}", out)
        if read_only_live:
            typer.echo(f"Ostium registry and {len(quotes)} quote rows written from read-only probe.")
        else:
            typer.echo("Ostium registry written with requires_probe fields; pass --read-only-live to probe.")

    @probe_app.command("trade-xyz")
    def probe_trade_xyz(
        seed_path: Path = typer.Option(
            Path("configs/instrument_registry.seed.json"),
            "--seed-path",
            help="Seed file containing venues.trade_xyz rows.",
        ),
        all_mids_path: Path | None = typer.Option(
            None,
            "--all-mids-path",
            help="Optional fixture path for allMids payload JSON.",
        ),
        meta_path: Path | None = typer.Option(
            None,
            "--meta-path",
            help="Optional fixture path for meta payload JSON.",
        ),
    ) -> None:
        settings = get_settings()
        if all_mids_path and meta_path:
            all_mids_payload = read_json(all_mids_path)
            meta_payload = read_json(meta_path)
            if not isinstance(all_mids_payload, dict) or not isinstance(meta_payload, dict):
                raise typer.BadParameter("all-mids-path/meta-path must contain JSON objects")
            build_result = build_trade_xyz_registry(
                seed_path,
                all_mids_payload={str(k): str(v) for k, v in all_mids_payload.items()},
                meta_payload=meta_payload,
            )
        else:
            with TradeXyzClient() as client:
                build_result = build_trade_xyz_registry(seed_path, client=client)

        registry_path = settings.data_dir / "registry/trade_xyz_instrument_registry.json"
        report_path = settings.data_dir / "reports/trade_xyz_universe_report.md"
        summary_path = settings.data_dir / "reports/trade_xyz_universe_summary.json"

        write_trade_xyz_registry(registry_path, build_result)
        write_trade_xyz_universe_report(report_path, build_trade_xyz_universe_report(build_result))
        write_trade_xyz_universe_summary(summary_path, build_result)
        typer.echo(f"registry_path={registry_path}")
        typer.echo(f"report_path={report_path}")
        typer.echo(f"summary_path={summary_path}")
