from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
from typing import cast

import typer

from sis.crypto_perp.bias_guards import CryptoPerpBiasGuard
from sis.crypto_perp.io import write_json_artifact, write_text_artifact
from sis.crypto_perp.models import stable_hash
from sis.crypto_perp.risk_taker_review import (
    CryptoPerpRiskTakerReview,
    OperatorJurisdictionStatus,
    SourceFreshnessStatus,
    build_risk_taker_review,
)
from sis.crypto_perp.source_availability import CryptoPerpSourceAvailability
from sis.crypto_perp.tournament_rows import CryptoPerpTournamentRowsV2


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


def _operator_jurisdiction_status(value: str) -> OperatorJurisdictionStatus:
    allowed_values = ("allowed", "prohibited", "unknown")
    if value not in allowed_values:
        raise ValueError("operator_jurisdiction_status must be allowed, prohibited, or unknown")
    return cast(OperatorJurisdictionStatus, value)


def _source_freshness_status(value: str) -> SourceFreshnessStatus:
    allowed_values = ("fresh", "stale", "unknown")
    if value not in allowed_values:
        raise ValueError("source_freshness_status must be fresh, stale, or unknown")
    return cast(SourceFreshnessStatus, value)


def _render_risk_taker_review_markdown(review: CryptoPerpRiskTakerReview) -> str:
    lines = [
        "# Crypto Perp Risk-Taker Review",
        "",
        f"- review_id: `{review.review_id}`",
        f"- review_status: `{review.review_status}`",
        f"- recommended_action: `{review.recommended_action}`",
        f"- leader_action: `{review.leader_action or 'NONE'}`",
        f"- operator_jurisdiction_status: `{review.operator_jurisdiction_status}`",
        f"- source_freshness_status: `{review.source_freshness_status}`",
        f"- after_cost_edge_over_no_trade_usd: `{review.after_cost_edge_over_no_trade_usd}`",
        f"- stress_edge_over_no_trade_usd: `{review.stress_edge_over_no_trade_usd}`",
        f"- dollars_per_hour: `{review.dollars_per_hour}`",
        f"- largest_loss_usd: `{review.largest_loss_usd}`",
        f"- profit_concentration: `{review.profit_concentration}`",
        f"- liquidation_buffer_bps: `{review.liquidation_buffer_bps}`",
        "- network_attempted: `false`",
        "- exchange_write_used: `false`",
        "- live_order_submitted: `false`",
        "- permits_live_order: `false`",
        "",
        "## Conditions",
        "",
    ]
    lines.extend(
        f"- `{condition.condition_id}` passed `{str(condition.passed).lower()}` "
        f"observed `{condition.observed}` required `{condition.required}`"
        for condition in review.conditions
    )
    if review.known_gaps:
        lines.extend(["", "## Known Gaps", ""])
        lines.extend(f"- `{gap}`" for gap in review.known_gaps)
    return "\n".join(lines)


def _stdout_status(review: CryptoPerpRiskTakerReview) -> str:
    if review.review_status == "READY_FOR_HUMAN_RISK_REVIEW":
        return "needs_human_review"
    if review.review_status == "NEEDS_ACTUAL_CASH":
        return "needs_actual_cash"
    if review.review_status == "INCONCLUSIVE_DATA":
        return "inconclusive"
    return "blocked"


def register_crypto_perp_risk_taker_review_commands(app: typer.Typer) -> None:
    @app.command("crypto-perp-risk-taker-review")
    def crypto_perp_risk_taker_review_cmd(
        rows_v2: Path = typer.Option(
            ...,
            "--rows-v2",
            help="Source crypto_perp_tournament_rows.v2 JSON artifact.",
        ),
        source_availability: Path = typer.Option(
            ...,
            "--source-availability",
            help="Source crypto_perp_source_availability.v1 JSON artifact.",
        ),
        bias_guard: Path = typer.Option(
            ...,
            "--bias-guard",
            help="Source crypto_perp_bias_guard.v1 JSON artifact.",
        ),
        operator_jurisdiction_status: str = typer.Option(
            ...,
            "--operator-jurisdiction-status",
            help="Operator jurisdiction status: allowed, prohibited, or unknown.",
        ),
        source_freshness_status: str = typer.Option(
            ...,
            "--source-freshness-status",
            help="Source freshness status: fresh, stale, or unknown.",
        ),
        venue_terms_checked_at: str | None = typer.Option(
            None,
            "--venue-terms-checked-at",
            help="Optional ISO-8601 time when venue terms were checked.",
        ),
        liquidation_buffer_bps: str | None = typer.Option(
            None,
            "--liquidation-buffer-bps",
            help="Optional liquidation buffer in basis points.",
        ),
        out: Path = typer.Option(
            Path("data/crypto_perp/risk_taker_review/latest"),
            "--out",
            help="Output directory for risk-taker review artifacts.",
        ),
    ) -> None:
        try:
            row_set = CryptoPerpTournamentRowsV2.model_validate(_json_object(rows_v2))
            source = CryptoPerpSourceAvailability.model_validate(_json_object(source_availability))
            guard = CryptoPerpBiasGuard.model_validate(_json_object(bias_guard))
            review = build_risk_taker_review(
                rows_v2=row_set,
                source_availability=source,
                bias_guard=guard,
                created_at=_utc_now(),
                operator_jurisdiction_status=_operator_jurisdiction_status(
                    operator_jurisdiction_status
                ),
                source_freshness_status=_source_freshness_status(source_freshness_status),
                venue_terms_checked_at=venue_terms_checked_at,
                liquidation_buffer_bps=(
                    Decimal(liquidation_buffer_bps) if liquidation_buffer_bps is not None else None
                ),
                source_refs=[
                    _source_ref(rows_v2, row_set.schema_version),
                    _source_ref(source_availability, source.schema_version),
                    _source_ref(bias_guard, guard.schema_version),
                ],
            )
        except Exception as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        json_path = out / "risk_taker_review.json"
        markdown_path = out / "risk_taker_review.md"
        write_json_artifact(json_path, review.model_dump(mode="json"))
        write_text_artifact(markdown_path, _render_risk_taker_review_markdown(review))
        typer.echo("network_attempted=false")
        typer.echo("exchange_write_used=false")
        typer.echo("live_order_submitted=false")
        typer.echo("permits_live_order=false")
        typer.echo(f"status={_stdout_status(review)}")
        typer.echo(f"review_status={review.review_status}")
        typer.echo(f"recommended_action={review.recommended_action}")
        typer.echo(f"leader_action={review.leader_action or 'NONE'}")
        typer.echo(f"known_gap_count={len(review.known_gaps)}")
        typer.echo(f"risk_taker_review_path={json_path.as_posix()}")
        typer.echo(f"report_path={markdown_path.as_posix()}")
