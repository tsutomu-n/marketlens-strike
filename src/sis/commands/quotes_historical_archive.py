from __future__ import annotations

from datetime import date
from pathlib import Path
import shlex

import typer

from sis.settings import get_settings
from sis.venues.trade_xyz.historical_archive import (
    HistoricalL2ArchiveRequest,
    build_hyperliquid_historical_archive_bulk_plan,
    collect_hyperliquid_historical_asset_ctxs_archive,
    collect_hyperliquid_historical_l2_archive,
    check_hyperliquid_historical_archive_preflight,
    execute_hyperliquid_historical_archive_bulk_plan,
    normalize_historical_archive_bulk_to_trade_xyz_quotes,
    normalize_historical_archive_to_trade_xyz_quotes,
)


def register_quote_historical_archive_commands(app: typer.Typer) -> None:
    @app.command("collect-trade-xyz-historical-l2-archive")
    def collect_trade_xyz_historical_l2_archive_cmd(
        coin: str = typer.Option(
            ...,
            "--coin",
            help="Hyperliquid archive coin name. For HIP-3, use the exact archive coin name if different from UI symbol.",
        ),
        archive_date: str = typer.Option(..., "--date", help="UTC archive date, YYYY-MM-DD."),
        hour: int = typer.Option(..., "--hour", help="UTC archive hour, 0-23."),
        acknowledge_requester_pays: bool = typer.Option(
            False,
            "--acknowledge-requester-pays",
            help="Required for non-dry-run download because Hyperliquid archive transfer can cost money.",
        ),
        decompress: bool = typer.Option(True, "--decompress/--no-decompress"),
        dry_run: bool = typer.Option(
            True,
            "--dry-run/--execute",
            help="Plan the requester-pays S3 download by default. Use --execute to download.",
        ),
    ) -> None:
        settings = get_settings()
        try:
            parsed_archive_date = date.fromisoformat(archive_date)
            manifest = collect_hyperliquid_historical_l2_archive(
                data_dir=settings.data_dir,
                request=HistoricalL2ArchiveRequest(
                    coin=coin,
                    date=parsed_archive_date,
                    hour=hour,
                ),
                acknowledge_requester_pays=acknowledge_requester_pays,
                decompress=decompress,
                dry_run=dry_run,
            )
        except (ValueError, RuntimeError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(code=2) from exc
        typer.echo(
            "manifest_path="
            f"{settings.data_dir / 'manifests/trade_xyz_historical_l2_archive_manifest.json'}"
        )
        typer.echo(f"status={manifest['status']}")
        typer.echo(f"source={manifest['source']}")
        typer.echo(f"s3_uri={manifest['s3_uri']}")
        typer.echo(f"aws_available={manifest['aws_available']}")
        typer.echo(f"raw_lz4_path={manifest['raw_lz4_path']}")
        if manifest["decompressed_path"] is not None:
            typer.echo(f"decompressed_path={manifest['decompressed_path']}")

    @app.command("collect-trade-xyz-historical-asset-ctxs-archive")
    def collect_trade_xyz_historical_asset_ctxs_archive_cmd(
        archive_date: str = typer.Option(..., "--date", help="UTC archive date, YYYY-MM-DD."),
        acknowledge_requester_pays: bool = typer.Option(
            False,
            "--acknowledge-requester-pays",
            help="Required for non-dry-run download because Hyperliquid archive transfer can cost money.",
        ),
        decompress: bool = typer.Option(True, "--decompress/--no-decompress"),
        dry_run: bool = typer.Option(
            True,
            "--dry-run/--execute",
            help="Plan the requester-pays S3 download by default. Use --execute to download.",
        ),
    ) -> None:
        settings = get_settings()
        try:
            manifest = collect_hyperliquid_historical_asset_ctxs_archive(
                data_dir=settings.data_dir,
                archive_date=date.fromisoformat(archive_date),
                acknowledge_requester_pays=acknowledge_requester_pays,
                decompress=decompress,
                dry_run=dry_run,
            )
        except (ValueError, RuntimeError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(code=2) from exc
        typer.echo(
            "manifest_path="
            f"{settings.data_dir / 'manifests/trade_xyz_historical_asset_ctxs_archive_manifest.json'}"
        )
        typer.echo(f"status={manifest['status']}")
        typer.echo(f"source={manifest['source']}")
        typer.echo(f"s3_uri={manifest['s3_uri']}")
        typer.echo(f"aws_available={manifest['aws_available']}")
        typer.echo(f"raw_lz4_path={manifest['raw_lz4_path']}")
        if manifest["decompressed_path"] is not None:
            typer.echo(f"decompressed_path={manifest['decompressed_path']}")

    @app.command("normalize-trade-xyz-historical-archive-quotes")
    def normalize_trade_xyz_historical_archive_quotes_cmd(
        l2_jsonl_path: Path = typer.Option(
            ...,
            "--l2-jsonl-path",
            help="Decompressed historical l2Book JSONL archive file.",
        ),
        asset_ctxs_path: Path | None = typer.Option(
            None,
            "--asset-ctxs-path",
            help="Optional decompressed historical asset_ctxs CSV/JSON file for mark/oracle/funding context.",
        ),
        registry_path: Path | None = typer.Option(
            None,
            "--registry-path",
            help="Instrument registry JSON written by `uv run sis probe trade-xyz`.",
        ),
        canonical_symbol: str | None = typer.Option(
            None,
            "--symbol",
            help="Canonical Trade[XYZ] symbol. Required when --coin cannot resolve registry entry.",
        ),
        coin: str | None = typer.Option(None, "--coin", help="Archive coin name."),
        output_path: Path | None = typer.Option(None, "--output-path"),
        normalize: bool = typer.Option(
            False,
            "--normalize/--no-normalize",
            help="Also rebuild data/normalized/quotes.parquet after writing raw quote rows.",
        ),
    ) -> None:
        settings = get_settings()
        try:
            manifest = normalize_historical_archive_to_trade_xyz_quotes(
                data_dir=settings.data_dir,
                l2_jsonl_path=l2_jsonl_path,
                registry_path=registry_path,
                asset_ctxs_path=asset_ctxs_path,
                canonical_symbol=canonical_symbol,
                coin=coin,
                output_path=output_path,
                normalize=normalize,
            )
        except (FileNotFoundError, ValueError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(code=2) from exc
        typer.echo(
            "manifest_path="
            f"{settings.data_dir / 'manifests/trade_xyz_historical_archive_quote_normalization_manifest.json'}"
        )
        typer.echo(f"rows_written={manifest['rows_written']}")
        typer.echo(f"asset_ctx_matched={manifest['asset_ctx_matched']}")
        typer.echo(f"raw_quote_output_path={manifest['raw_quote_output_path']}")
        if manifest["normalized_quotes_path"] is not None:
            typer.echo(f"normalized_quotes_path={manifest['normalized_quotes_path']}")

    @app.command("plan-trade-xyz-historical-archive-bulk")
    def plan_trade_xyz_historical_archive_bulk_cmd(
        coins: str = typer.Option(..., "--coins", help="Comma-separated archive coin names."),
        start_date: str = typer.Option(..., "--start-date", help="UTC start date, YYYY-MM-DD."),
        end_date: str = typer.Option(..., "--end-date", help="UTC end date, YYYY-MM-DD."),
        hours: str | None = typer.Option(
            None,
            "--hours",
            help="Comma-separated UTC hours. Defaults to all 0-23.",
        ),
        include_asset_ctxs: bool = typer.Option(
            True,
            "--include-asset-ctxs/--no-asset-ctxs",
            help="Include daily asset_ctxs archive objects in the plan.",
        ),
    ) -> None:
        settings = get_settings()
        requested_coins = [item.strip() for item in coins.split(",") if item.strip()]
        requested_hours = (
            [int(item.strip()) for item in hours.split(",") if item.strip()]
            if hours is not None
            else None
        )
        try:
            manifest = build_hyperliquid_historical_archive_bulk_plan(
                data_dir=settings.data_dir,
                coins=requested_coins,
                start_date=date.fromisoformat(start_date),
                end_date=date.fromisoformat(end_date),
                hours=requested_hours,
                include_asset_ctxs=include_asset_ctxs,
            )
        except ValueError as exc:
            typer.echo(str(exc))
            raise typer.Exit(code=2) from exc
        typer.echo(
            "manifest_path="
            f"{settings.data_dir / 'manifests/trade_xyz_historical_archive_bulk_plan_manifest.json'}"
        )
        typer.echo(f"date_count={manifest['date_count']}")
        typer.echo(f"estimated_l2_object_count={manifest['estimated_l2_object_count']}")
        typer.echo(
            f"estimated_asset_ctx_object_count={manifest['estimated_asset_ctx_object_count']}"
        )
        typer.echo(f"estimated_total_object_count={manifest['estimated_total_object_count']}")
        typer.echo("requester_pays_ack_required=True")

    @app.command("check-trade-xyz-historical-archive-preflight")
    def check_trade_xyz_historical_archive_preflight_cmd(
        fail_on_error: bool = typer.Option(False, "--fail-on-error"),
    ) -> None:
        settings = get_settings()
        manifest = check_hyperliquid_historical_archive_preflight(
            data_dir=settings.data_dir,
        )
        typer.echo(
            "manifest_path="
            f"{settings.data_dir / 'manifests/trade_xyz_historical_archive_preflight_manifest.json'}"
        )
        typer.echo(f"status={manifest['status']}")
        typer.echo(f"return_code={manifest['return_code']}")
        typer.echo(f"aws_command_source={manifest['aws_command_source']}")
        typer.echo(f"preflight_command={shlex.join(manifest['preflight_command'])}")
        if manifest["stderr"]:
            typer.echo(f"stderr={manifest['stderr']}")
        if fail_on_error and manifest["status"] != "pass":
            raise typer.Exit(code=2)

    @app.command("execute-trade-xyz-historical-archive-bulk")
    def execute_trade_xyz_historical_archive_bulk_cmd(
        plan_path: Path | None = typer.Option(
            None,
            "--plan-path",
            help="Bulk plan manifest. Defaults to data/manifests/trade_xyz_historical_archive_bulk_plan_manifest.json.",
        ),
        acknowledge_requester_pays: bool = typer.Option(
            False,
            "--acknowledge-requester-pays",
            help="Required with --execute because Hyperliquid archive transfer can cost money.",
        ),
        dry_run: bool = typer.Option(
            True,
            "--dry-run/--execute",
            help="Preview selected downloads by default. Use --execute to run aws commands.",
        ),
        max_objects: int | None = typer.Option(
            None,
            "--max-objects",
            help="Limit selected objects so requester-pays downloads can be batched.",
        ),
        include_l2: bool = typer.Option(True, "--include-l2/--no-l2"),
        include_asset_ctxs: bool = typer.Option(True, "--include-asset-ctxs/--no-asset-ctxs"),
        skip_existing: bool = typer.Option(True, "--skip-existing/--include-existing"),
        decompress: bool = typer.Option(True, "--decompress/--no-decompress"),
    ) -> None:
        settings = get_settings()
        try:
            manifest = execute_hyperliquid_historical_archive_bulk_plan(
                data_dir=settings.data_dir,
                plan_path=plan_path,
                acknowledge_requester_pays=acknowledge_requester_pays,
                dry_run=dry_run,
                max_objects=max_objects,
                include_l2=include_l2,
                include_asset_ctxs=include_asset_ctxs,
                skip_existing=skip_existing,
                decompress=decompress,
            )
        except (FileNotFoundError, ValueError, RuntimeError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(code=2) from exc
        typer.echo(
            "manifest_path="
            f"{settings.data_dir / 'manifests/trade_xyz_historical_archive_bulk_execution_manifest.json'}"
        )
        typer.echo(f"status={manifest['status']}")
        typer.echo(f"dry_run={manifest['dry_run']}")
        typer.echo(f"selected_object_count={manifest['selected_object_count']}")
        typer.echo(f"downloaded_object_count={manifest['downloaded_object_count']}")
        typer.echo(f"decompressed_object_count={manifest['decompressed_object_count']}")
        typer.echo(f"command_error_count={manifest['command_error_count']}")

    @app.command("normalize-trade-xyz-historical-archive-bulk")
    def normalize_trade_xyz_historical_archive_bulk_cmd(
        plan_path: Path | None = typer.Option(
            None,
            "--plan-path",
            help="Bulk plan manifest. Defaults to data/manifests/trade_xyz_historical_archive_bulk_plan_manifest.json.",
        ),
        registry_path: Path | None = typer.Option(
            None,
            "--registry-path",
            help="Instrument registry JSON written by `uv run sis probe trade-xyz`.",
        ),
        max_files: int | None = typer.Option(
            None,
            "--max-files",
            help="Limit decompressed l2Book files to normalize in this run.",
        ),
        skip_existing_raw_quotes: bool = typer.Option(
            True,
            "--skip-existing-raw-quotes/--overwrite-raw-quotes",
            help="Skip archive raw quote files that already exist.",
        ),
        normalize: bool = typer.Option(
            True,
            "--normalize/--no-normalize",
            help="Rebuild data/normalized/quotes.parquet after writing raw quote rows.",
        ),
    ) -> None:
        settings = get_settings()
        try:
            manifest = normalize_historical_archive_bulk_to_trade_xyz_quotes(
                data_dir=settings.data_dir,
                plan_path=plan_path,
                registry_path=registry_path,
                max_files=max_files,
                skip_existing_raw_quotes=skip_existing_raw_quotes,
                normalize=normalize,
            )
        except (FileNotFoundError, ValueError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(code=2) from exc
        typer.echo(
            "manifest_path="
            f"{settings.data_dir / 'manifests/trade_xyz_historical_archive_bulk_quote_normalization_manifest.json'}"
        )
        typer.echo(f"status={manifest['status']}")
        typer.echo(f"normalized_file_count={manifest['normalized_file_count']}")
        typer.echo(f"rows_written={manifest['rows_written']}")
        typer.echo(f"normalized_row_count={manifest['normalized_row_count']}")
        typer.echo(f"error_count={manifest['error_count']}")
