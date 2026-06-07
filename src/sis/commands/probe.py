from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import typer

from sis.settings import get_settings
from sis.storage.jsonl_store import read_json
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
        perp_dexs_path: Path | None = typer.Option(
            None,
            "--perp-dexs-path",
            help="Optional fixture path for perpDexs payload JSON.",
        ),
    ) -> None:
        settings = get_settings()
        if all_mids_path and meta_path:
            all_mids_payload = read_json(all_mids_path)
            meta_payload = read_json(meta_path)
            if not isinstance(all_mids_payload, dict) or not isinstance(meta_payload, dict):
                raise typer.BadParameter("all-mids-path/meta-path must contain JSON objects")
            perp_dexs_payload = read_json(perp_dexs_path) if perp_dexs_path else None
            if perp_dexs_payload is not None and not isinstance(perp_dexs_payload, list):
                raise typer.BadParameter("perp-dexs-path must contain a JSON array")
            build_result = build_trade_xyz_registry(
                seed_path,
                all_mids_payload={str(k): str(v) for k, v in all_mids_payload.items()},
                meta_payload=cast(dict[str, Any], meta_payload),
                perp_dexs_payload=perp_dexs_payload,
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
