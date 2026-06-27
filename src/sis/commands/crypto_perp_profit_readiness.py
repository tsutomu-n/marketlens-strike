from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path

import typer

from sis.crypto_perp.bias_guards import build_bias_guard
from sis.crypto_perp.edge_scorer import build_edge_score
from sis.crypto_perp.events import CryptoPerpEvent
from sis.crypto_perp.features import CryptoPerpFeaturePack, build_feature_pack
from sis.crypto_perp.io import write_json_artifact
from sis.crypto_perp.order_preview import CryptoPerpOrderPreview
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
from sis.crypto_perp.outcomes import CryptoPerpOutcome


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _json_object(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


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
