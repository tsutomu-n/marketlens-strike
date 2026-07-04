from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from typing import Any

import typer

from sis.crypto_perp.bias_guards import build_bias_guard
from sis.crypto_perp.edge_scorer import build_edge_score
from sis.crypto_perp.events import CryptoPerpEvent
from sis.crypto_perp.features import CryptoPerpFeaturePack, build_feature_pack
from sis.crypto_perp.io import write_json_artifact
from sis.crypto_perp.io import write_text_artifact
from sis.crypto_perp.models import stable_hash
from sis.crypto_perp.order_preview import CryptoPerpOrderPreview
from sis.crypto_perp.profit_readiness import (
    ProfitReadinessInventory,
    TinyLiveReviewPacket,
    actual_cash_rows_from_ledger,
    build_actual_cash_report_gate_run,
    build_profit_readiness_inventory,
    build_profit_readiness_plan,
    build_profit_readiness_run,
    build_tiny_live_review_packet,
    build_tiny_live_shadow_readiness,
    parse_assignments,
    parse_cash_ledger_entries,
    parse_tournament_rows,
)
from sis.crypto_perp.replay import build_replay_slice
from sis.crypto_perp.source_availability import (
    CryptoPerpSourceAvailability,
    build_source_availability,
)
from sis.crypto_perp.tiny_live_shadow import build_tiny_live_shadow
from sis.crypto_perp.tournament_rows import (
    CryptoPerpTournamentRowsV2,
    build_cost_aware_tournament_rows,
)
from sis.crypto_perp.bitget.account import CryptoPerpAccountSnapshot
from sis.crypto_perp.cash_ledger import CryptoPerpCashLedger, build_cash_ledger
from sis.crypto_perp.outcomes import CryptoPerpOutcome
from sis.crypto_perp.tournament import CryptoPerpTournamentReport
from sis.crypto_perp.tournament_gate import CryptoPerpTournamentGate

TICKER_MANIFEST_SCHEMA_VERSION = "crypto_perp_ticker_manifest.v1"
TICKER_REQUIRED_METADATA_FIELDS = (
    "last_px",
    "bid_px",
    "ask_px",
    "mark_px",
    "index_px",
    "funding_rate",
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _json_object(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _source_ref(path: Path, schema_version: str | None = None) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    ref = {"path": path.as_posix(), "sha256": "sha256:" + stable_hash([text])}
    if schema_version:
        ref["schema_version"] = schema_version
    return ref


def _local_file_source_ref(path: Path, schema_version: str | None = None) -> dict[str, str]:
    ref = {
        "path": path.as_posix(),
        "sha256": "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest(),
    }
    if schema_version:
        ref["schema_version"] = schema_version
    return ref


def _parse_source_refs(values: list[str] | None) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    for value in values or []:
        raw = value.strip()
        if not raw:
            continue
        raw_path, raw_schema = raw, None
        if "=" in raw:
            raw_path, raw_schema = raw.split("=", 1)
        path = Path(raw_path.strip())
        schema_version = raw_schema.strip() if raw_schema else None
        refs.append(_local_file_source_ref(path, schema_version or None))
    return refs


def _string_list(payload: dict[str, object], key: str, path: Path) -> list[str]:
    value = payload.get(key, [])
    if not isinstance(value, list):
        raise ValueError(f"ticker manifest {key} must be a list: {path}")
    return [str(item) for item in value]


def _parse_ticker_manifests(
    paths: list[Path] | None,
) -> tuple[list[dict[str, str]], dict[str, int], dict[str, dict[str, Any]]]:
    refs: list[dict[str, str]] = []
    row_count = 0
    ticker_metadata: dict[str, Any] = {}
    for path in paths or []:
        payload = _json_object(path)
        schema_version = str(payload.get("schema_version", ""))
        if schema_version != TICKER_MANIFEST_SCHEMA_VERSION:
            raise ValueError(
                f"ticker manifest schema_version must be {TICKER_MANIFEST_SCHEMA_VERSION}: {path}"
            )
        if payload.get("supports_cost_adjusted_estimate") is not True:
            raise ValueError(f"ticker manifest does not support cost-adjusted estimate: {path}")
        for field in ("credentials_used", "exchange_write_used", "live_order_submitted"):
            if payload.get(field) is not False:
                raise ValueError(f"ticker manifest {field} must be false: {path}")
        raw_count = payload.get("row_count_after_dedupe")
        if isinstance(raw_count, bool) or not isinstance(raw_count, int):
            raise ValueError(f"ticker manifest row_count_after_dedupe must be an integer: {path}")
        count = raw_count
        if count <= 0:
            raise ValueError(f"ticker manifest row_count_after_dedupe must be positive: {path}")
        row_count += count
        fields_present = _string_list(payload, "fields_present", path)
        window = payload.get("window", {})
        window_values = window if isinstance(window, dict) else {}
        ticker_metadata = {
            "coverage_class": str(payload.get("coverage_class", "")),
            "coverage_start_ms": window_values.get("start_ms"),
            "coverage_end_ms": window_values.get("end_ms"),
            "exchange": str(payload.get("exchange", "")),
            "fields_present": fields_present,
            "market_type": str(payload.get("market_type", "")),
            "missing_fields": sorted(
                field for field in TICKER_REQUIRED_METADATA_FIELDS if field not in fields_present
            ),
            "raw_inputs": _string_list(payload, "raw_inputs", path),
            "supports_cost_adjusted_estimate": payload.get("supports_cost_adjusted_estimate"),
            "supports_edge_action": payload.get("supports_edge_action"),
            "symbols": _string_list(payload, "symbols", path),
            "warnings": _string_list(payload, "warnings", path),
        }
        refs.append(_local_file_source_ref(path, schema_version))
    return (
        refs,
        ({"ticker": row_count} if row_count > 0 else {}),
        ({"ticker": ticker_metadata} if ticker_metadata else {}),
    )


def _render_cash_ledger_markdown(ledger: CryptoPerpCashLedger) -> str:
    return "\n".join(
        [
            "# Crypto Perp Cash Ledger",
            "",
            f"- ledger_id: `{ledger.ledger_id}`",
            f"- observed_at: `{ledger.observed_at}`",
            f"- entry_count: `{len(ledger.entries)}`",
            f"- actual_cash_result_usd: `{ledger.actual_cash_result_usd}`",
            "- network_attempted: `false`",
            "- exchange_write_used: `false`",
            "- live_order_submitted: `false`",
        ]
    )


def _render_review_packet_markdown(packet: TinyLiveReviewPacket) -> str:
    return "\n".join(
        [
            "# Crypto Perp Tiny-Live Review Packet",
            "",
            f"- packet_id: `{packet.packet_id}`",
            f"- packet_status: `{packet.packet_status}`",
            f"- report_id: `{packet.report_id}`",
            f"- gate_id: `{packet.gate_id}`",
            "- requires_explicit_approval: `true`",
            "- live_order_allowed: `false`",
            "- exchange_write_allowed: `false`",
            "- approval_granted: `false`",
        ]
    )


def _parse_available_sources(values: list[str] | None) -> dict[str, bool]:
    available: dict[str, bool] = {}
    for value in values or []:
        source = value.strip()
        if not source:
            continue
        if source.startswith("no-"):
            available[source[3:]] = False
        else:
            available[source] = True
    return available


def _parse_row_counts(values: list[str] | None) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values or []:
        if "=" not in value:
            raise ValueError("row counts must use source=count")
        source, raw_count = value.split("=", 1)
        source = source.strip()
        if not source:
            raise ValueError("row count source must not be empty")
        count = int(raw_count)
        if count < 0:
            raise ValueError("row count must be non-negative")
        counts[source] = count
    return counts


def register_crypto_perp_profit_readiness_commands(app: typer.Typer) -> None:
    @app.command("crypto-perp-profit-readiness-inventory")
    def crypto_perp_profit_readiness_inventory_cmd(
        data_dir: Path = typer.Option(Path("data/crypto_perp"), "--data-dir"),
        out: Path = typer.Option(Path("data/crypto_perp/artifact_inventory/latest"), "--out"),
    ) -> None:
        try:
            artifact = build_profit_readiness_inventory(data_dir=data_dir, created_at=_utc_now())
        except Exception as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc
        path = out / "inventory.json"
        write_json_artifact(path, artifact.model_dump(mode="json"))
        typer.echo("network_attempted=false")
        typer.echo("exchange_write_used=false")
        typer.echo("live_order_submitted=false")
        typer.echo(
            "status=pass"
            if artifact.inventory_status == "READY_FOR_LOCAL_PLAN"
            else "status=blocked"
        )
        typer.echo(f"inventory_status={artifact.inventory_status}")
        typer.echo(f"event_count={artifact.summary['event_count']}")
        typer.echo(f"outcome_count={artifact.summary['outcome_count']}")
        typer.echo(f"known_gap_count={len(artifact.known_gaps)}")
        typer.echo(f"inventory_path={path.as_posix()}")

    @app.command("crypto-perp-profit-readiness-plan")
    def crypto_perp_profit_readiness_plan_cmd(
        inventory: Path = typer.Option(..., "--inventory"),
        out: Path = typer.Option(Path("data/crypto_perp/profit_readiness_plan/latest"), "--out"),
        run_out: Path = typer.Option(
            Path("data/crypto_perp/profit_readiness_run/latest"), "--run-out"
        ),
        notional_usd: str = typer.Option("100", "--notional-usd"),
    ) -> None:
        try:
            artifact = build_profit_readiness_plan(
                inventory=ProfitReadinessInventory.model_validate(_json_object(inventory)),
                created_at=_utc_now(),
                out_dir=run_out,
                notional_usd=Decimal(notional_usd),
            )
        except Exception as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc
        path = out / "plan.json"
        write_json_artifact(path, artifact.model_dump(mode="json"))
        typer.echo("network_attempted=false")
        typer.echo("exchange_write_used=false")
        typer.echo("live_order_submitted=false")
        typer.echo(
            "status=pass" if artifact.plan_status == "READY_FOR_LOCAL_RUN" else "status=blocked"
        )
        typer.echo(f"plan_status={artifact.plan_status}")
        typer.echo(f"runnable_command_count={len(artifact.runnable_commands)}")
        typer.echo(f"blocker_count={len(artifact.blockers)}")
        typer.echo(f"plan_path={path.as_posix()}")

    @app.command("crypto-perp-profit-readiness-run-local")
    def crypto_perp_profit_readiness_run_local_cmd(
        event: Path = typer.Option(..., "--event"),
        outcome: Path = typer.Option(..., "--outcome"),
        out: Path = typer.Option(Path("data/crypto_perp/profit_readiness_run/latest"), "--out"),
        notional_usd: str = typer.Option(..., "--notional-usd"),
        source_ref: list[str] | None = typer.Option(
            None,
            "--source-ref",
            help="Extra local source reference as path[=schema_version]. Repeatable.",
        ),
        ticker_manifest: list[Path] | None = typer.Option(
            None,
            "--ticker-manifest",
            help="Ticker manifest JSON produced by a native ticker_rows artifact. Repeatable.",
        ),
    ) -> None:
        try:
            event_artifact = CryptoPerpEvent.model_validate(_json_object(event))
            outcome_artifact = CryptoPerpOutcome.model_validate(_json_object(outcome))
            (
                ticker_source_refs,
                extra_source_row_counts,
                extra_source_metadata,
            ) = _parse_ticker_manifests(ticker_manifest)
            extra_source_refs = [
                *_parse_source_refs(source_ref),
                *ticker_source_refs,
            ]
            manifest = build_profit_readiness_run(
                event=event_artifact,
                outcome=outcome_artifact,
                created_at=_utc_now(),
                out=out,
                event_path=event,
                outcome_path=outcome,
                notional_usd=Decimal(notional_usd),
                extra_source_refs=extra_source_refs,
                extra_source_row_counts=extra_source_row_counts,
                extra_source_metadata=extra_source_metadata,
            )
            # Rebuild once for concrete artifact objects and write them in the same run directory.
            source = build_source_availability(
                event=event_artifact,
                created_at=manifest.created_at,
                available_sources={"outcome": True},
                row_counts={"outcome": 1, **extra_source_row_counts},
                source_refs=[
                    _source_ref(outcome, outcome_artifact.schema_version),
                    *extra_source_refs,
                ],
                source_metadata=extra_source_metadata,
            )
            replay = build_replay_slice(
                event=event_artifact,
                created_at=manifest.created_at,
                included_sources=["event", "outcome"],
                row_counts={"event": 1, "outcome": 1},
            )
            feature = build_feature_pack(
                event=event_artifact, source_availability=source, created_at=manifest.created_at
            )
            edge = build_edge_score(
                feature_pack=feature, source_availability=source, created_at=manifest.created_at
            )
            rows = build_cost_aware_tournament_rows(
                outcomes=[outcome_artifact],
                created_at=manifest.created_at,
                notional_usd=Decimal(notional_usd),
                source_refs=[_source_ref(outcome, outcome_artifact.schema_version)],
            )
            guard = build_bias_guard(
                rows=rows.rows,
                created_at=manifest.created_at,
                source_refs=[
                    {
                        "path": (out / "tournament_rows_v2.json").as_posix(),
                        "sha256": rows.artifact_id,
                        "schema_version": rows.schema_version,
                    }
                ],
                known_gaps=rows.known_gaps,
            )
        except Exception as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc
        write_json_artifact(out / "source_availability.json", source.model_dump(mode="json"))
        write_json_artifact(out / "replay_slice.json", replay.model_dump(mode="json"))
        write_json_artifact(out / "feature_pack.json", feature.model_dump(mode="json"))
        write_json_artifact(out / "edge_score.json", edge.model_dump(mode="json"))
        write_json_artifact(out / "tournament_rows_v2.json", rows.model_dump(mode="json"))
        write_json_artifact(out / "bias_guard.json", guard.model_dump(mode="json"))
        write_json_artifact(out / "manifest.json", manifest.model_dump(mode="json"))
        typer.echo("network_attempted=false")
        typer.echo("exchange_write_used=false")
        typer.echo("live_order_submitted=false")
        typer.echo("status=pass" if manifest.status == "complete" else "status=blocked")
        typer.echo(f"run_status={manifest.status}")
        typer.echo(f"known_gap_count={len(manifest.known_gaps)}")
        typer.echo(f"manifest_path={(out / 'manifest.json').as_posix()}")

    @app.command("crypto-perp-cash-ledger")
    def crypto_perp_cash_ledger_cmd(
        entries: Path = typer.Option(..., "--entries"),
        ledger_id: str = typer.Option(..., "--ledger-id"),
        observed_at: str = typer.Option(..., "--observed-at"),
        out: Path = typer.Option(Path("data/crypto_perp/cash_ledger/latest"), "--out"),
    ) -> None:
        try:
            entry_list = parse_cash_ledger_entries(entries)
            ledger = build_cash_ledger(
                ledger_id=ledger_id,
                observed_at=observed_at,
                entries=entry_list,
                source_refs=[_source_ref(entries)],
            )
        except Exception as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc
        write_json_artifact(out / "cash_ledger.json", ledger.model_dump(mode="json"))
        write_text_artifact(out / "cash_ledger.md", _render_cash_ledger_markdown(ledger))
        typer.echo("network_attempted=false")
        typer.echo("exchange_write_used=false")
        typer.echo("live_order_submitted=false")
        typer.echo("status=pass")
        typer.echo(f"entry_count={len(ledger.entries)}")
        typer.echo(f"actual_cash_result_usd={ledger.actual_cash_result_usd}")
        typer.echo(f"cash_ledger_path={(out / 'cash_ledger.json').as_posix()}")

    @app.command("crypto-perp-actual-cash-rows-build")
    def crypto_perp_actual_cash_rows_build_cmd(
        ledger: Path = typer.Option(..., "--ledger"),
        assignment: Path = typer.Option(..., "--assignment"),
        out: Path = typer.Option(Path("data/crypto_perp/actual_cash_rows/latest"), "--out"),
    ) -> None:
        try:
            ledger_artifact = CryptoPerpCashLedger.model_validate(_json_object(ledger))
            assignments = parse_assignments(assignment)
            rows_path = out / "actual_cash_rows.jsonl"
            rows, summary = actual_cash_rows_from_ledger(
                ledger=ledger_artifact,
                assignments=assignments,
                created_at=_utc_now(),
                rows_path=rows_path,
                source_refs=[
                    _source_ref(ledger, ledger_artifact.schema_version),
                    _source_ref(assignment),
                ],
            )
        except Exception as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc
        rows_path.parent.mkdir(parents=True, exist_ok=True)
        rows_path.write_text(
            "\n".join(json.dumps(row.model_dump(mode="json"), ensure_ascii=False) for row in rows)
            + "\n",
            encoding="utf-8",
        )
        write_json_artifact(out / "actual_cash_rows_summary.json", summary.model_dump(mode="json"))
        typer.echo("network_attempted=false")
        typer.echo("exchange_write_used=false")
        typer.echo("live_order_submitted=false")
        typer.echo("status=pass")
        typer.echo(f"row_count={len(rows)}")
        typer.echo(f"actual_cash_rows_path={rows_path.as_posix()}")
        typer.echo(f"summary_path={(out / 'actual_cash_rows_summary.json').as_posix()}")

    @app.command("crypto-perp-actual-cash-report-gate")
    def crypto_perp_actual_cash_report_gate_cmd(
        rows: Path = typer.Option(..., "--rows"),
        report_id: str = typer.Option(..., "--report-id"),
        min_events: int = typer.Option(..., "--min-events", min=1),
        out: Path = typer.Option(Path("data/crypto_perp/actual_cash_report_gate/latest"), "--out"),
    ) -> None:
        try:
            row_list = parse_tournament_rows(rows)
            artifacts = {
                "tournament_report": (out / "tournament_report.json").as_posix(),
                "tournament_gate": (out / "tournament_gate.json").as_posix(),
                "manifest": (out / "manifest.json").as_posix(),
            }
            report, gate, manifest = build_actual_cash_report_gate_run(
                rows=row_list,
                report_id=report_id,
                min_events=min_events,
                created_at=_utc_now(),
                source_refs=[_source_ref(rows)],
                artifacts=artifacts,
            )
        except Exception as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc
        write_json_artifact(out / "tournament_report.json", report.model_dump(mode="json"))
        write_json_artifact(out / "tournament_gate.json", gate.model_dump(mode="json"))
        write_json_artifact(out / "manifest.json", manifest.model_dump(mode="json"))
        typer.echo("network_attempted=false")
        typer.echo("exchange_write_used=false")
        typer.echo("live_order_submitted=false")
        typer.echo(
            "status=pass" if manifest.status == "ready_for_human_review" else "status=blocked"
        )
        typer.echo(f"gate_status={gate.gate_status}")
        typer.echo(f"manifest_status={manifest.status}")
        typer.echo(f"manifest_path={(out / 'manifest.json').as_posix()}")

    @app.command("crypto-perp-tiny-live-review-packet")
    def crypto_perp_tiny_live_review_packet_cmd(
        report: Path = typer.Option(..., "--report"),
        gate: Path = typer.Option(..., "--gate"),
        out: Path = typer.Option(Path("data/crypto_perp/tiny_live_review_packet/latest"), "--out"),
    ) -> None:
        try:
            report_artifact = CryptoPerpTournamentReport.model_validate(_json_object(report))
            gate_artifact = CryptoPerpTournamentGate.model_validate(_json_object(gate))
            packet = build_tiny_live_review_packet(
                report=report_artifact,
                gate=gate_artifact,
                created_at=_utc_now(),
                source_refs=[
                    _source_ref(report, report_artifact.schema_version),
                    _source_ref(gate, gate_artifact.schema_version),
                ],
            )
        except Exception as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc
        write_json_artifact(out / "review_packet.json", packet.model_dump(mode="json"))
        write_text_artifact(out / "review_packet.md", _render_review_packet_markdown(packet))
        typer.echo("network_attempted=false")
        typer.echo("exchange_write_used=false")
        typer.echo("live_order_submitted=false")
        typer.echo("requires_explicit_approval=true")
        typer.echo(
            "status=pass" if packet.packet_status == "READY_FOR_HUMAN_REVIEW" else "status=blocked"
        )
        typer.echo(f"packet_status={packet.packet_status}")
        typer.echo(f"review_packet_path={(out / 'review_packet.json').as_posix()}")

    @app.command("crypto-perp-tiny-live-shadow-readiness")
    def crypto_perp_tiny_live_shadow_readiness_cmd(
        packet: Path = typer.Option(..., "--packet"),
        account: Path = typer.Option(..., "--account"),
        order_preview: Path = typer.Option(..., "--order-preview"),
        out: Path = typer.Option(
            Path("data/crypto_perp/tiny_live_shadow_readiness/latest"), "--out"
        ),
    ) -> None:
        try:
            packet_artifact = TinyLiveReviewPacket.model_validate(_json_object(packet))
            account_artifact = CryptoPerpAccountSnapshot.model_validate(_json_object(account))
            preview_artifact = CryptoPerpOrderPreview.model_validate(_json_object(order_preview))
            readiness = build_tiny_live_shadow_readiness(
                packet=packet_artifact,
                account_snapshot=account_artifact,
                order_preview=preview_artifact,
                created_at=_utc_now(),
                source_refs=[
                    _source_ref(packet, packet_artifact.schema_version),
                    _source_ref(account, account_artifact.schema_version),
                    _source_ref(order_preview, preview_artifact.schema_version),
                ],
            )
        except Exception as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc
        write_json_artifact(out / "shadow_readiness.json", readiness.model_dump(mode="json"))
        typer.echo("network_attempted=false")
        typer.echo("exchange_write_used=false")
        typer.echo("live_order_submitted=false")
        typer.echo("live_order_allowed=false")
        typer.echo("exchange_write_allowed=false")
        typer.echo("requires_explicit_approval=true")
        typer.echo(
            "status=pass" if readiness.status == "READY_FOR_TINY_LIVE_SHADOW" else "status=blocked"
        )
        typer.echo(f"readiness_status={readiness.status}")
        typer.echo(f"shadow_readiness_path={(out / 'shadow_readiness.json').as_posix()}")

    @app.command("crypto-perp-source-availability")
    def crypto_perp_source_availability_cmd(
        event: Path = typer.Option(..., "--event", help="Source crypto_perp_event.v1 JSON."),
        out: Path = typer.Option(
            Path("data/crypto_perp/source_availability"),
            "--out",
            help="Output directory for source availability artifact.",
        ),
        available_source: list[str] | None = typer.Option(
            None,
            "--available-source",
            help="Source id to mark available. Prefix with no- to mark unavailable.",
        ),
        row_count: list[str] | None = typer.Option(
            None,
            "--row-count",
            help="Source row count as source=count.",
        ),
    ) -> None:
        try:
            artifact = build_source_availability(
                event=CryptoPerpEvent.model_validate(_json_object(event)),
                created_at=_utc_now(),
                available_sources=_parse_available_sources(available_source),
                row_counts=_parse_row_counts(row_count),
            )
        except Exception as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc
        path = out / "source_availability.json"
        write_json_artifact(path, artifact.model_dump(mode="json"))
        typer.echo("network_attempted=false")
        typer.echo("exchange_write_used=false")
        typer.echo("live_order_submitted=false")
        typer.echo("status=pass")
        typer.echo(f"event_id={artifact.event_id}")
        typer.echo(f"can_compute_actual_cash={str(artifact.can_compute_actual_cash).lower()}")
        typer.echo(f"known_gap_count={len(artifact.known_gaps)}")
        typer.echo(f"source_availability_path={path.as_posix()}")

    @app.command("crypto-perp-replay-slice")
    def crypto_perp_replay_slice_cmd(
        event: Path = typer.Option(..., "--event", help="Source crypto_perp_event.v1 JSON."),
        out: Path = typer.Option(
            Path("data/crypto_perp/replay_slice"),
            "--out",
            help="Output directory for replay slice artifact.",
        ),
        included_source: list[str] = typer.Option(
            ["event"],
            "--included-source",
            help="Included source id.",
        ),
        row_count: list[str] | None = typer.Option(None, "--row-count"),
        min_ts: str | None = typer.Option(None, "--min-ts"),
        max_ts: str | None = typer.Option(None, "--max-ts"),
    ) -> None:
        try:
            artifact = build_replay_slice(
                event=CryptoPerpEvent.model_validate(_json_object(event)),
                created_at=_utc_now(),
                included_sources=included_source,
                row_counts=_parse_row_counts(row_count),
                min_ts=min_ts,
                max_ts=max_ts,
            )
        except Exception as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc
        path = out / "replay_slice.json"
        write_json_artifact(path, artifact.model_dump(mode="json"))
        typer.echo("network_attempted=false")
        typer.echo("exchange_write_used=false")
        typer.echo("live_order_submitted=false")
        typer.echo("status=pass")
        typer.echo(f"event_id={artifact.event_id}")
        typer.echo("future_data_included=false")
        typer.echo(f"replay_slice_path={path.as_posix()}")

    @app.command("crypto-perp-feature-pack")
    def crypto_perp_feature_pack_cmd(
        event: Path = typer.Option(..., "--event"),
        source_availability: Path = typer.Option(..., "--source-availability"),
        out: Path = typer.Option(Path("data/crypto_perp/feature_pack"), "--out"),
        trade_sign_imbalance: str | None = typer.Option(None, "--trade-sign-imbalance"),
        ofi: str | None = typer.Option(None, "--ofi"),
        depth_10bps: str | None = typer.Option(None, "--depth-10bps"),
    ) -> None:
        try:
            artifact = build_feature_pack(
                event=CryptoPerpEvent.model_validate(_json_object(event)),
                source_availability=CryptoPerpSourceAvailability.model_validate(
                    _json_object(source_availability)
                ),
                created_at=_utc_now(),
                trade_sign_imbalance=(
                    Decimal(trade_sign_imbalance) if trade_sign_imbalance is not None else None
                ),
                ofi=Decimal(ofi) if ofi is not None else None,
                depth_10bps=Decimal(depth_10bps) if depth_10bps is not None else None,
            )
        except Exception as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc
        path = out / "feature_pack.json"
        write_json_artifact(path, artifact.model_dump(mode="json"))
        typer.echo("network_attempted=false")
        typer.echo("exchange_write_used=false")
        typer.echo("live_order_submitted=false")
        typer.echo("status=pass")
        typer.echo(f"event_id={artifact.event_id}")
        typer.echo("sets_entry_action=false")
        typer.echo(f"known_gap_count={len(artifact.known_gaps)}")
        typer.echo(f"feature_pack_path={path.as_posix()}")

    @app.command("crypto-perp-edge-score")
    def crypto_perp_edge_score_cmd(
        feature_pack: Path = typer.Option(..., "--feature-pack"),
        source_availability: Path = typer.Option(..., "--source-availability"),
        out: Path = typer.Option(Path("data/crypto_perp/edge_score"), "--out"),
        min_abs_event_return_bps: str = typer.Option("30", "--min-abs-event-return-bps"),
    ) -> None:
        try:
            artifact = build_edge_score(
                feature_pack=CryptoPerpFeaturePack.model_validate(_json_object(feature_pack)),
                source_availability=CryptoPerpSourceAvailability.model_validate(
                    _json_object(source_availability)
                ),
                created_at=_utc_now(),
                min_abs_event_return_bps=Decimal(min_abs_event_return_bps),
            )
        except Exception as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc
        path = out / "edge_score.json"
        write_json_artifact(path, artifact.model_dump(mode="json"))
        typer.echo("network_attempted=false")
        typer.echo("exchange_write_used=false")
        typer.echo("live_order_submitted=false")
        typer.echo("status=pass")
        typer.echo(f"selected_action={artifact.selected_action}")
        typer.echo(f"known_gap_count={len(artifact.known_gaps)}")
        typer.echo(f"edge_score_path={path.as_posix()}")

    @app.command("crypto-perp-tournament-rows-v2")
    def crypto_perp_tournament_rows_v2_cmd(
        outcome: list[Path] = typer.Option(..., "--outcome"),
        out: Path = typer.Option(Path("data/crypto_perp/tournament_rows_v2"), "--out"),
        notional_usd: str = typer.Option(..., "--notional-usd"),
        fee_rate: str = typer.Option("0.0006", "--fee-rate"),
        funding_rate: str = typer.Option("0", "--funding-rate"),
        slippage_bps: str = typer.Option("0", "--slippage-bps"),
        operator_time_minutes: str = typer.Option("0", "--operator-time-minutes"),
        operator_hourly_cost_usd: str = typer.Option("0", "--operator-hourly-cost-usd"),
    ) -> None:
        try:
            artifact = build_cost_aware_tournament_rows(
                outcomes=[CryptoPerpOutcome.model_validate(_json_object(path)) for path in outcome],
                created_at=_utc_now(),
                notional_usd=Decimal(notional_usd),
                fee_rate=Decimal(fee_rate),
                funding_rate=Decimal(funding_rate),
                slippage_bps=Decimal(slippage_bps),
                operator_time_minutes=Decimal(operator_time_minutes),
                operator_hourly_cost_usd=Decimal(operator_hourly_cost_usd),
            )
        except Exception as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc
        path = out / "tournament_rows_v2.json"
        write_json_artifact(path, artifact.model_dump(mode="json"))
        typer.echo("network_attempted=false")
        typer.echo("exchange_write_used=false")
        typer.echo("live_order_submitted=false")
        typer.echo("status=pass")
        typer.echo(f"primary_metric={artifact.primary_metric}")
        typer.echo(f"leader_action={artifact.summary.get('leader_action') or 'NONE'}")
        typer.echo(f"known_gap_count={len(artifact.known_gaps)}")
        typer.echo(f"tournament_rows_v2_path={path.as_posix()}")

    @app.command("crypto-perp-bias-guard")
    def crypto_perp_bias_guard_cmd(
        rows_v2: Path = typer.Option(..., "--rows-v2"),
        out: Path = typer.Option(Path("data/crypto_perp/bias_guard"), "--out"),
        min_events_for_pbo: int = typer.Option(30, "--min-events-for-pbo", min=1),
        fold_count: int = typer.Option(0, "--fold-count", min=0),
        lookahead_violation: bool = typer.Option(False, "--lookahead-violation"),
        recursive_warmup_violation: bool = typer.Option(False, "--recursive-warmup-violation"),
        max_profit_concentration: str = typer.Option("0.60", "--max-profit-concentration"),
    ) -> None:
        try:
            row_set = CryptoPerpTournamentRowsV2.model_validate(_json_object(rows_v2))
            artifact = build_bias_guard(
                rows=row_set.rows,
                created_at=_utc_now(),
                min_events_for_pbo=min_events_for_pbo,
                fold_count=fold_count,
                lookahead_violation=lookahead_violation,
                recursive_warmup_violation=recursive_warmup_violation,
                max_profit_concentration=Decimal(max_profit_concentration),
                source_refs=[
                    {
                        "path": rows_v2.as_posix(),
                        "sha256": row_set.artifact_id,
                        "schema_version": row_set.schema_version,
                    }
                ],
                known_gaps=row_set.known_gaps,
            )
        except Exception as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc
        path = out / "bias_guard.json"
        write_json_artifact(path, artifact.model_dump(mode="json"))
        typer.echo("network_attempted=false")
        typer.echo("exchange_write_used=false")
        typer.echo("live_order_submitted=false")
        typer.echo("status=pass" if artifact.guard_status == "PASS" else "status=blocked")
        typer.echo(f"guard_status={artifact.guard_status}")
        typer.echo(f"pbo_status={artifact.pbo_status}")
        typer.echo(f"stop_reason_count={len(artifact.stop_reasons)}")
        typer.echo(f"bias_guard_path={path.as_posix()}")

    @app.command("crypto-perp-tiny-live-shadow")
    def crypto_perp_tiny_live_shadow_cmd(
        account: Path = typer.Option(..., "--account"),
        order_preview: Path = typer.Option(..., "--order-preview"),
        out: Path = typer.Option(Path("data/crypto_perp/tiny_live_shadow"), "--out"),
        max_notional_usd: str = typer.Option("25", "--max-notional-usd"),
    ) -> None:
        try:
            artifact = build_tiny_live_shadow(
                account_snapshot=CryptoPerpAccountSnapshot.model_validate(_json_object(account)),
                order_preview=CryptoPerpOrderPreview.model_validate(_json_object(order_preview)),
                created_at=_utc_now(),
                max_notional_usd=Decimal(max_notional_usd),
            )
        except Exception as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc
        path = out / "tiny_live_shadow.json"
        write_json_artifact(path, artifact.model_dump(mode="json"))
        typer.echo("network_attempted=false")
        typer.echo("exchange_write_used=false")
        typer.echo("live_order_submitted=false")
        typer.echo("permits_live_order=false")
        typer.echo("status=pass" if artifact.preflight_status == "PASS" else "status=blocked")
        typer.echo(f"preflight_status={artifact.preflight_status}")
        typer.echo(f"blocker_count={len(artifact.blockers)}")
        typer.echo(f"tiny_live_shadow_path={path.as_posix()}")
