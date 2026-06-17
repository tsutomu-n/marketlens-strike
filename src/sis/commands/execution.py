from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Protocol

import typer
from loguru import logger

from sis.execution.base import (
    AdapterActionResult,
    AdapterOrderStatus,
    ExecutionAdapter,
    OrderIntent,
)
from sis.paper.portfolio import PaperPosition
from sis.reports.execution_adapter_status import (
    build_action_status_report,
    build_balance_status_report,
    build_fill_status_report,
    build_order_status_report,
    build_reconcile_positions_report,
)
from sis.settings import get_settings
from sis.state.reconciliation import reconcile_positions
from sis.state.store import StateStore
from sis.storage.jsonl_store import write_json
from sis.venues.read_only_probe import build_venue_read_only_probe_report
from sis.venues.read_only_probe import build_venue_read_only_probe_summary


class _StateStoreFactory(Protocol):
    def __call__(self, settings_data_dir: Path, state_path: Path | None) -> StateStore: ...


class _ExecutionSnapshotWriter(Protocol):
    def __call__(
        self,
        settings_data_dir: Path,
        *,
        venue: str | None = None,
        fills_limit: int = 5,
        order_limit: int = 5,
    ) -> tuple[Path, Path, str]: ...


class _SimpleWriter(Protocol):
    def __call__(self, settings_data_dir: Path) -> tuple[Path, Path, str]: ...


class _ReadOnlySurfaceWriter(Protocol):
    def __call__(
        self,
        settings_data_dir: Path,
        *,
        state_path: Path | None = None,
    ) -> tuple[Path, Path, str]: ...


def register_execution_commands(
    app: typer.Typer,
    *,
    adapter_for_venue_fn: Callable[[Path, str], ExecutionAdapter],
    state_store_fn: _StateStoreFactory,
    write_execution_snapshot_fn: _ExecutionSnapshotWriter,
    write_execution_venue_comparison_fn: _SimpleWriter,
    write_execution_venue_diagnostics_fn: _SimpleWriter,
    write_execution_read_only_surfaces_fn: _ReadOnlySurfaceWriter,
    recommended_read_order_fn: Callable[[Path], list[str]],
) -> None:
    @app.command("execution-snapshot")
    def execution_snapshot_cmd(
        venue: str | None = typer.Option(None, "--venue"),
        fills_limit: int = typer.Option(5, "--fills-limit"),
        order_limit: int = typer.Option(5, "--order-limit"),
    ) -> None:
        settings = get_settings()
        out, summary_out, text = write_execution_snapshot_fn(
            settings.data_dir,
            venue=venue,
            fills_limit=fills_limit,
            order_limit=order_limit,
        )
        logger.info("written: {}", out)
        logger.info("written: {}", summary_out)
        typer.echo(text)
        for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
            typer.echo(f"recommended_read_order_{index}={item}")

    @app.command("execution-venue-comparison")
    def execution_venue_comparison_cmd() -> None:
        settings = get_settings()
        out, summary_out, text = write_execution_venue_comparison_fn(settings.data_dir)
        logger.info("written: {}", out)
        logger.info("written: {}", summary_out)
        typer.echo(text)
        for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
            typer.echo(f"recommended_read_order_{index}={item}")

    @app.command("execution-venue-diagnostics")
    def execution_venue_diagnostics_cmd() -> None:
        settings = get_settings()
        out, summary_out, text = write_execution_venue_diagnostics_fn(settings.data_dir)
        logger.info("written: {}", out)
        logger.info("written: {}", summary_out)
        typer.echo(text)
        for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
            typer.echo(f"recommended_read_order_{index}={item}")

    @app.command("execution-read-only-surfaces")
    def execution_read_only_surfaces_cmd(
        state_path: Path | None = typer.Option(
            None,
            "--state-path",
            help="Optional sqlite state path. Defaults to data/state/marketlens.sqlite.",
        ),
    ) -> None:
        settings = get_settings()
        out, summary_out, text = write_execution_read_only_surfaces_fn(
            settings.data_dir,
            state_path=state_path,
        )
        logger.info("written: {}", out)
        logger.info("written: {}", summary_out)
        typer.echo(text)
        typer.echo(f"execution_read_only_surfaces_path={out}")
        typer.echo(f"execution_read_only_surfaces_summary_path={summary_out}")
        for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
            typer.echo(f"recommended_read_order_{index}={item}")

    @app.command("order-status")
    def order_status_cmd(
        venue: str = typer.Option(..., "--venue"),
        order_id: str = typer.Option(..., "--order-id"),
    ) -> None:
        settings = get_settings()
        adapter = adapter_for_venue_fn(settings.data_dir, venue)
        status: AdapterOrderStatus = adapter.read_order_status(order_id)
        build_order_status_report(
            status=status,
            out_path=settings.data_dir / "reports/execution_order_status.md",
            summary_path=settings.data_dir / "ops/execution_order_status_summary.json",
        )
        typer.echo(f"venue={status.venue}")
        typer.echo(f"order_id={status.order_id}")
        typer.echo(f"status={status.status}")
        typer.echo(f"symbol={status.canonical_symbol}")
        typer.echo(f"side={status.side}")
        typer.echo(f"quantity={status.quantity}")
        typer.echo(f"notes={','.join(status.notes)}")
        for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
            typer.echo(f"recommended_read_order_{index}={item}")

    @app.command("estimate-order")
    def estimate_order_cmd(
        venue: str = typer.Option(..., "--venue"),
        symbol: str = typer.Option(..., "--symbol"),
        side: str = typer.Option(..., "--side"),
        quantity: float = typer.Option(1.0, "--quantity"),
        timeframe: str = typer.Option("4h", "--timeframe"),
    ) -> None:
        settings = get_settings()
        adapter = adapter_for_venue_fn(settings.data_dir, venue)
        estimate = adapter.estimate_order(
            OrderIntent(
                venue=venue,
                canonical_symbol=symbol.upper(),
                side=side.lower(),
                quantity=quantity,
                timeframe=timeframe,
            )
        )
        typer.echo(f"venue={estimate.venue}")
        typer.echo(f"symbol={estimate.canonical_symbol}")
        typer.echo(f"side={estimate.side}")
        typer.echo(f"estimated_cost_bps={estimate.estimated_cost_bps}")
        typer.echo(f"price_reference={estimate.price_reference}")
        typer.echo(f"notes={','.join(estimate.notes)}")
        for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
            typer.echo(f"recommended_read_order_{index}={item}")

    @app.command("balance-status")
    def balance_status_cmd(
        venue: str = typer.Option(..., "--venue"),
    ) -> None:
        settings = get_settings()
        adapter = adapter_for_venue_fn(settings.data_dir, venue)
        balance = adapter.read_balance()
        build_balance_status_report(
            venue=venue.strip().lower(),
            balance=balance,
            out_path=settings.data_dir / "reports/execution_balance_status.md",
            summary_path=settings.data_dir / "ops/execution_balance_status_summary.json",
        )
        for key in sorted(balance):
            typer.echo(f"{key}={balance[key]}")
        for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
            typer.echo(f"recommended_read_order_{index}={item}")

    @app.command("bitget-demo-smoke")
    def bitget_demo_smoke_cmd() -> None:
        settings = get_settings()
        adapter = adapter_for_venue_fn(settings.data_dir, "bitget_demo")
        healthcheck = adapter.healthcheck()
        status = "configured" if healthcheck.get("available") else "blocked"
        generated_at = datetime.now(timezone.utc).isoformat()
        summary = {
            "schema_version": "bitget_demo_smoke_summary.v1",
            "generated_at": generated_at,
            "status": status,
            "venue": "bitget_demo",
            "available": bool(healthcheck.get("available")),
            "credential_status": healthcheck.get("credential_status"),
            "missing_env": healthcheck.get("missing_env", []),
            "rest_base_url": healthcheck.get("rest_base_url"),
            "ws_public_endpoint": healthcheck.get("ws_public_endpoint"),
            "ws_private_endpoint": healthcheck.get("ws_private_endpoint"),
            "paptrading_header": healthcheck.get("paptrading_header"),
            "external_write_enabled": False,
            "exchange_write_used": False,
            "read_only_network_probe": healthcheck.get("read_only_network_probe"),
        }
        summary_path = settings.data_dir / "ops/bitget_demo_smoke_summary.json"
        report_path = settings.data_dir / "reports/bitget_demo_smoke.md"
        write_json(summary_path, summary)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            "\n".join(
                [
                    "# Bitget Demo Smoke",
                    "",
                    f"generated_at: {generated_at}",
                    f"status: {status}",
                    "venue: bitget_demo",
                    f"available: {summary['available']}",
                    f"credential_status: {summary['credential_status']}",
                    f"missing_env: {','.join(summary['missing_env'])}",
                    f"rest_base_url: {summary['rest_base_url']}",
                    f"ws_public_endpoint: {summary['ws_public_endpoint']}",
                    f"ws_private_endpoint: {summary['ws_private_endpoint']}",
                    f"paptrading_header: {summary['paptrading_header']}",
                    "external_write_enabled: False",
                    "exchange_write_used: False",
                    f"read_only_network_probe: {summary['read_only_network_probe']}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        typer.echo(f"status={status}")
        typer.echo(f"venue={summary['venue']}")
        typer.echo(f"available={summary['available']}")
        typer.echo(f"credential_status={summary['credential_status']}")
        typer.echo(f"missing_env={','.join(summary['missing_env'])}")
        typer.echo(f"paptrading_header={summary['paptrading_header']}")
        typer.echo(f"external_write_enabled={summary['external_write_enabled']}")
        typer.echo(f"exchange_write_used={summary['exchange_write_used']}")
        typer.echo(f"read_only_network_probe={summary['read_only_network_probe']}")
        typer.echo(f"summary_path={summary_path}")
        typer.echo(f"report_path={report_path}")
        for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
            typer.echo(f"recommended_read_order_{index}={item}")
        if status != "configured":
            raise typer.Exit(2)

    @app.command("venue-read-only-probe")
    def venue_read_only_probe_cmd() -> None:
        settings = get_settings()
        summary_path = settings.data_dir / "ops/venue_read_only_probe_summary.json"
        report_path = settings.data_dir / "reports/venue_read_only_probe.md"
        try:
            summary = build_venue_read_only_probe_summary()
            report = build_venue_read_only_probe_report(summary)
            write_json(summary_path, summary)
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(report, encoding="utf-8")
        except Exception as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        typer.echo(f"status={summary['status']}")
        typer.echo(f"run_id={summary['run_id']}")
        typer.echo(f"venue_count={summary['venue_count']}")
        typer.echo(f"external_api_used={summary['external_api_used']}")
        typer.echo(f"credentials_used={summary['credentials_used']}")
        typer.echo(f"wallet_used={summary['wallet_used']}")
        typer.echo(f"signing_used={summary['signing_used']}")
        typer.echo(f"exchange_write_used={summary['exchange_write_used']}")
        typer.echo(f"network_attempted={summary['network_attempted']}")
        typer.echo(f"summary_path={summary_path}")
        typer.echo(f"report_path={report_path}")
        for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
            typer.echo(f"recommended_read_order_{index}={item}")

    @app.command("fill-status")
    def fill_status_cmd(
        venue: str = typer.Option(..., "--venue"),
        limit: int = typer.Option(20, "--limit"),
    ) -> None:
        settings = get_settings()
        adapter = adapter_for_venue_fn(settings.data_dir, venue)
        fills = adapter.read_fills(limit=limit)
        build_fill_status_report(
            venue=venue.strip().lower(),
            fills=fills,
            limit=limit,
            out_path=settings.data_dir / "reports/execution_fill_status.md",
            summary_path=settings.data_dir / "ops/execution_fill_status_summary.json",
        )
        typer.echo(f"venue={venue.strip().lower()}")
        typer.echo(f"fills_count={len(fills)}")
        for index, fill in enumerate(fills, start=1):
            typer.echo(f"fill_{index}_id={fill.fill_id}")
            typer.echo(f"fill_{index}_order_id={fill.order_id}")
            typer.echo(f"fill_{index}_symbol={fill.canonical_symbol}")
            typer.echo(f"fill_{index}_side={fill.side}")
            typer.echo(f"fill_{index}_quantity={fill.quantity}")
            typer.echo(f"fill_{index}_price={fill.price}")
            typer.echo(f"fill_{index}_status={fill.status}")
            typer.echo(f"fill_{index}_ts_fill={fill.ts_fill}")
        for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
            typer.echo(f"recommended_read_order_{index}={item}")

    @app.command("cancel-order")
    def cancel_order_cmd(
        venue: str = typer.Option(..., "--venue"),
        order_id: str = typer.Option(..., "--order-id"),
    ) -> None:
        settings = get_settings()
        adapter = adapter_for_venue_fn(settings.data_dir, venue)
        result: AdapterActionResult = adapter.cancel_order(order_id)
        build_action_status_report(
            title="Execution Cancel Order",
            report_key="cancel_order_report_path",
            result=result,
            out_path=settings.data_dir / "reports/execution_cancel_order.md",
            summary_path=settings.data_dir / "ops/execution_cancel_order_summary.json",
        )
        typer.echo(f"venue={result.venue}")
        typer.echo(f"action={result.action}")
        typer.echo(f"target={result.target}")
        typer.echo(f"success={result.success}")
        typer.echo(f"status={result.status}")
        typer.echo(f"notes={','.join(result.notes)}")
        for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
            typer.echo(f"recommended_read_order_{index}={item}")

    @app.command("close-position")
    def close_position_cmd(
        venue: str = typer.Option(..., "--venue"),
        symbol: str = typer.Option(..., "--symbol"),
        side: str | None = typer.Option(None, "--side"),
    ) -> None:
        settings = get_settings()
        adapter = adapter_for_venue_fn(settings.data_dir, venue)
        result: AdapterActionResult = adapter.close_position(symbol.upper(), side)
        build_action_status_report(
            title="Execution Close Position",
            report_key="close_position_report_path",
            result=result,
            out_path=settings.data_dir / "reports/execution_close_position.md",
            summary_path=settings.data_dir / "ops/execution_close_position_summary.json",
        )
        typer.echo(f"venue={result.venue}")
        typer.echo(f"action={result.action}")
        typer.echo(f"target={result.target}")
        typer.echo(f"success={result.success}")
        typer.echo(f"status={result.status}")
        typer.echo(f"notes={','.join(result.notes)}")
        for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
            typer.echo(f"recommended_read_order_{index}={item}")

    @app.command("reconcile-positions")
    def reconcile_positions_cmd(
        venue: str = typer.Option(..., "--venue"),
        state_path: Path | None = typer.Option(
            None,
            "--state-path",
            help="Optional sqlite state path. Defaults to data/state/marketlens.sqlite.",
        ),
    ) -> None:
        settings = get_settings()
        store = state_store_fn(settings.data_dir, state_path)
        payload = store.get_json("paper_positions")
        internal_positions = (
            [PaperPosition.model_validate(item) for item in payload]
            if isinstance(payload, list)
            else []
        )
        adapter = adapter_for_venue_fn(settings.data_dir, venue)
        result = reconcile_positions(internal_positions, adapter.read_positions())
        out = {
            "venue": venue,
            "matched": result.matched,
            "missing_in_adapter": result.missing_in_adapter,
            "missing_in_internal": result.missing_in_internal,
        }
        run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        store.record_reconciliation(run_id, datetime.now(timezone.utc).isoformat(), out)
        build_reconcile_positions_report(
            venue=venue.strip().lower(),
            result=result,
            run_id=run_id,
            state_store_path=str(store.path),
            out_path=settings.data_dir / "reports/execution_reconcile_positions.md",
            summary_path=settings.data_dir / "ops/execution_reconcile_positions_summary.json",
        )
        typer.echo(f"matched={result.matched}")
        typer.echo(f"missing_in_adapter={len(result.missing_in_adapter)}")
        typer.echo(f"missing_in_internal={len(result.missing_in_internal)}")
        for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
            typer.echo(f"recommended_read_order_{index}={item}")
