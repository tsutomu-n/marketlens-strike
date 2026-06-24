from __future__ import annotations

from pathlib import Path

import typer

from sis.settings import get_settings
from sis.venues.trade_xyz.collection_status import build_trade_xyz_collection_status


def _csv_items(value: str | None) -> list[str] | None:
    if value is None:
        return None
    return [item.strip().upper() for item in value.split(",") if item.strip()]


def register_quote_collection_status_commands(app: typer.Typer) -> None:
    @app.command("trade-xyz-collection-status")
    def trade_xyz_collection_status_cmd(
        raw_quotes_root: Path | None = typer.Option(
            None,
            "--raw-quotes-root",
            help="Raw quotes root containing trade_xyz/*.jsonl.",
        ),
        symbols: str | None = typer.Option(None, "--symbols", help="Comma-separated symbols."),
        min_days: float = typer.Option(30.0, "--min-days"),
        max_gap_minutes: float = typer.Option(10.0, "--max-gap-minutes"),
        traceable_only: bool = typer.Option(
            True,
            "--traceable-only/--include-untraceable",
            help="Evaluate quote coverage with rows that have raw_payload_ref.",
        ),
        refresh_coverage: bool = typer.Option(
            True,
            "--refresh-coverage/--no-refresh-coverage",
            help="Rebuild quote coverage from current raw quote files before writing status.",
        ),
        refresh_readiness: bool = typer.Option(
            True,
            "--refresh-readiness/--no-refresh-readiness",
            help="Rebuild data readiness from current manifests before writing status.",
        ),
        allow_known_gaps: bool = typer.Option(
            False,
            "--allow-known-gaps/--strict",
            help="Allow documented gaps that are out of pure-backtest scope.",
        ),
        duration_minutes: int = typer.Option(1440, "--duration-minutes"),
        interval_seconds: int = typer.Option(60, "--interval-seconds"),
        stale_after_minutes: float = typer.Option(180.0, "--stale-after-minutes"),
        fail_on_not_ready: bool = typer.Option(False, "--fail-on-not-ready"),
        fail_on_stale: bool = typer.Option(False, "--fail-on-stale"),
        fail_on_lock_stale: bool = typer.Option(False, "--fail-on-lock-stale"),
        fail_on_progress_warning: bool = typer.Option(False, "--fail-on-progress-warning"),
        fail_on_archive_preflight: bool = typer.Option(False, "--fail-on-archive-preflight"),
        fail_on_account_fee_missing: bool = typer.Option(False, "--fail-on-account-fee-missing"),
    ) -> None:
        settings = get_settings()
        requested_symbols = _csv_items(symbols)
        manifest = build_trade_xyz_collection_status(
            data_dir=settings.data_dir,
            raw_quotes_root=raw_quotes_root,
            symbols=requested_symbols,
            min_days=min_days,
            max_gap_minutes=max_gap_minutes,
            traceable_only=traceable_only,
            refresh_coverage=refresh_coverage,
            refresh_readiness=refresh_readiness,
            allow_known_gaps=allow_known_gaps,
            duration_minutes=duration_minutes,
            interval_seconds=interval_seconds,
            stale_after_minutes=stale_after_minutes,
        )
        typer.echo(f"status_path={settings.data_dir / 'ops/trade_xyz_collection_status.json'}")
        typer.echo(f"report_path={manifest['report_path']}")
        typer.echo(f"decision={manifest['decision']}")
        typer.echo(f"backtest_data_ready={manifest['backtest_data_ready']}")
        typer.echo(f"readiness_decision={manifest['readiness_decision']}")
        typer.echo(f"fail_count={manifest['fail_count']}")
        typer.echo(f"known_gap_count={manifest['known_gap_count']}")
        typer.echo(f"failing_requirements={','.join(manifest['readiness_requirements']['fail'])}")
        typer.echo(
            f"known_gap_requirements={','.join(manifest['readiness_requirements']['known_gap'])}"
        )
        readiness_details = manifest["readiness_requirement_details"]
        funding_details = readiness_details.get("funding_events", {})
        oracle_details = readiness_details.get("oracle_timestamp_provenance", {})
        oracle_freshness_proxy = oracle_details.get("oracle_freshness_proxy") or {}
        signal_details = readiness_details.get("signal_candles", {})
        typer.echo(f"funding_events_status={funding_details.get('status')}")
        typer.echo(f"funding_events_skipped={funding_details.get('skipped')}")
        typer.echo(f"oracle_timestamp_provenance_status={oracle_details.get('status')}")
        typer.echo(f"oracle_ts_missing_rate={oracle_details.get('oracle_ts_missing_rate')}")
        typer.echo(
            f"oracle_freshness_proxy_observed_rate={oracle_freshness_proxy.get('observed_rate')}"
        )
        typer.echo(f"signal_candles_status={signal_details.get('status')}")
        typer.echo(
            "signal_candles_missing_symbols="
            f"{','.join(signal_details.get('missing_symbols') or [])}"
        )
        typer.echo(
            "signal_candles_missing_intervals="
            f"{','.join(signal_details.get('missing_intervals') or [])}"
        )
        typer.echo(
            f"signal_candles_request_error_count={signal_details.get('request_error_count')}"
        )
        typer.echo(f"latest_file_stale={manifest['latest_file_stale']}")
        typer.echo(f"collector_running={manifest['collector_process']['running']}")
        typer.echo(f"collector_process_count={manifest['collector_process']['process_count']}")
        typer.echo(f"supervisor_running={manifest['supervisor_process']['running']}")
        typer.echo(f"supervisor_process_count={manifest['supervisor_process']['process_count']}")
        typer.echo(f"cycle_lock_stale={manifest['locks']['cycle']['stale']}")
        typer.echo(f"supervisor_lock_stale={manifest['locks']['supervisor']['stale']}")
        typer.echo(f"aws_cli_available={manifest['runtime_prerequisites']['aws_cli']['available']}")
        typer.echo(f"aws_command_source={manifest['runtime_prerequisites']['aws_cli']['source']}")
        typer.echo(f"lz4_available={manifest['runtime_prerequisites']['lz4']['available']}")
        archive_artifacts = manifest["historical_archive_artifacts"]
        typer.echo(
            f"historical_archive_bulk_plan_exists={archive_artifacts['bulk_plan']['exists']}"
        )
        typer.echo(
            "historical_archive_bulk_plan_estimated_total_object_count="
            f"{archive_artifacts['bulk_plan']['estimated_total_object_count']}"
        )
        typer.echo(
            "historical_archive_bulk_execution_status="
            f"{archive_artifacts['bulk_execution']['status']}"
        )
        typer.echo(
            "historical_archive_bulk_execution_dry_run="
            f"{archive_artifacts['bulk_execution']['dry_run']}"
        )
        typer.echo(
            "historical_archive_bulk_execution_selected_object_count="
            f"{archive_artifacts['bulk_execution']['selected_object_count']}"
        )
        typer.echo(
            "historical_archive_bulk_execution_downloaded_object_count="
            f"{archive_artifacts['bulk_execution']['downloaded_object_count']}"
        )
        typer.echo(
            "historical_archive_bulk_execution_command_error_count="
            f"{archive_artifacts['bulk_execution']['command_error_count']}"
        )
        typer.echo(
            "historical_archive_bulk_normalization_status="
            f"{archive_artifacts['bulk_normalization']['status']}"
        )
        typer.echo(
            "historical_archive_bulk_normalization_normalized_file_count="
            f"{archive_artifacts['bulk_normalization']['normalized_file_count']}"
        )
        typer.echo(
            "account_fee_user_address_configured="
            f"{manifest['account_fee_prerequisites']['configured']}"
        )
        account_fee_artifact = manifest["account_fee_artifact"]
        typer.echo(f"account_fee_manifest_exists={account_fee_artifact['exists']}")
        typer.echo(f"account_fee_manifest_status={account_fee_artifact['status']}")
        typer.echo(
            "account_fee_manifest_user_matches_env="
            f"{account_fee_artifact['matches_configured_user']}"
        )
        typer.echo(f"account_fee_user_taker_fee_bps={account_fee_artifact['user_taker_fee_bps']}")
        typer.echo(f"account_fee_user_maker_fee_bps={account_fee_artifact['user_maker_fee_bps']}")
        typer.echo(f"progress_status={manifest['progress_since_previous_status']['status']}")
        typer.echo(
            f"latest_file_age_seconds={manifest['raw_quote_inventory']['latest_file_age_seconds']}"
        )
        typer.echo(
            "estimated_max_collection_days_required="
            f"{manifest['coverage']['estimated_max_collection_days_required']}"
        )
        typer.echo(
            f"coverage_completion_ratio_by_span={manifest['coverage']['completion_ratio_by_span']}"
        )
        if manifest["next_actions"]:
            typer.echo(f"next_command={manifest['next_actions'][0]['command']}")
            for index, action in enumerate(manifest["next_actions"], start=1):
                typer.echo(f"next_action_{index}_key={action.get('key')}")
                if action.get("status") is not None:
                    typer.echo(f"next_action_{index}_status={action.get('status')}")
                if action.get("blocked_by"):
                    typer.echo(
                        f"next_action_{index}_blocked_by={','.join(action.get('blocked_by', []))}"
                    )
                for command_key in (
                    "plan_command",
                    "preflight_command",
                    "preflight_status",
                    "preflight_return_code",
                    "dry_run_command",
                    "execute_command",
                    "command",
                    "follow_up_command",
                    "final_check_command",
                ):
                    command_value = action.get(command_key)
                    if command_value:
                        typer.echo(f"next_action_{index}_{command_key}={command_value}")
                if action.get("env_var"):
                    typer.echo(f"next_action_{index}_env_var={action.get('env_var')}")
                    typer.echo(f"next_action_{index}_env_configured={action.get('env_configured')}")
                if action.get("user_address_sha256"):
                    typer.echo(
                        f"next_action_{index}_user_address_sha256={action.get('user_address_sha256')}"
                    )
        if fail_on_lock_stale and (
            manifest["locks"]["cycle"]["stale"] or manifest["locks"]["supervisor"]["stale"]
        ):
            raise typer.Exit(code=2)
        if (
            fail_on_progress_warning
            and manifest["progress_since_previous_status"]["status"] == "warning"
        ):
            raise typer.Exit(code=2)
        if (
            fail_on_archive_preflight
            and manifest["historical_archive_preflight"]["status"] == "fail"
        ):
            raise typer.Exit(code=2)
        if fail_on_account_fee_missing and (
            "account_specific_fee" in manifest["readiness_requirements"]["known_gap"]
            or manifest["account_fee_artifact"]["exists"] is not True
            or manifest["account_fee_artifact"]["status"] != "pass"
            or manifest["account_fee_artifact"]["user_taker_fee_bps"] is None
            or manifest["account_fee_artifact"]["user_maker_fee_bps"] is None
            or manifest["account_fee_artifact"]["matches_configured_user"] is False
        ):
            raise typer.Exit(code=2)
        if fail_on_stale and manifest["latest_file_stale"]:
            raise typer.Exit(code=2)
        if fail_on_not_ready and not manifest["backtest_data_ready"]:
            raise typer.Exit(code=2)
