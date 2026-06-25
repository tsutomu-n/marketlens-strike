from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from typing import Literal, cast

import typer

from sis.crypto_perp.decisions import CryptoPerpDecision, build_decision
from sis.crypto_perp.events import CryptoPerpEvent
from sis.crypto_perp.io import write_json_artifact, write_text_artifact
from sis.crypto_perp.outcomes import CryptoPerpOutcome, OutcomePriceWindow, build_outcome


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _render_decision_markdown(decision: CryptoPerpDecision) -> str:
    return "\n".join(
        [
            "# Crypto Perp Prospective Decision",
            "",
            f"- decision_id: `{decision.decision_id}`",
            f"- event_id: `{decision.event_id}`",
            f"- action: `{decision.action}`",
            f"- decision_at: `{decision.decision_at}`",
            f"- information_cutoff_at: `{decision.information_cutoff_at}`",
            f"- size_cap_usd: `{decision.size_cap_usd}`",
            f"- actor: `{decision.actor_type}:{decision.actor_id}`",
            "- outcome_seen: `false`",
            "- permits_live_order: `false`",
            "- exchange_write_used: `false`",
        ]
    )


def _render_outcome_markdown(outcome: CryptoPerpOutcome) -> str:
    lines = [
        "# Crypto Perp Matured Outcome",
        "",
        f"- outcome_id: `{outcome.outcome_id}`",
        f"- event_id: `{outcome.event_id}`",
        f"- settled_at: `{outcome.settled_at}`",
        "- permits_live_order: `false`",
        "- exchange_write_used: `false`",
        "",
        "## Horizons",
        "",
        "| horizon_minutes | matured | raw_return | long_return_before_cost | short_return_before_cost | high_low_order |",
        "|---:|---|---:|---:|---:|---|",
    ]
    for horizon in outcome.horizons:
        lines.append(
            "| "
            f"{horizon.horizon_minutes} | "
            f"{horizon.matured} | "
            f"{horizon.raw_return} | "
            f"{horizon.long_return_before_cost} | "
            f"{horizon.short_return_before_cost} | "
            f"{horizon.high_first_low_first} |"
        )
    if outcome.known_gaps:
        lines.extend(["", "## Known Gaps", ""])
        lines.extend(f"- `{gap}`" for gap in outcome.known_gaps)
    return "\n".join(lines)


def register_crypto_perp_record_commands(app: typer.Typer) -> None:
    @app.command("crypto-perp-decision-record")
    def crypto_perp_decision_record_cmd(
        event_path: Path = typer.Option(
            ...,
            "--event",
            help="Source crypto_perp_event.v1 JSON artifact.",
        ),
        action: str = typer.Option(
            ...,
            "--action",
            help="Prospective action: REVERSAL_SHORT, CONTINUATION_LONG, NO_TRADE, UNKNOWN, or CAPTURE_ONLY.",
        ),
        out: Path = typer.Option(
            Path("data/crypto_perp/decisions"),
            "--out",
            help="Output directory for decision artifacts.",
        ),
        actor_type: str = typer.Option("human", "--actor-type"),
        actor_id: str = typer.Option("operator", "--actor-id"),
        size_cap_usd: str = typer.Option("0", "--size-cap-usd"),
        reason_code: list[str] | None = typer.Option(
            None,
            "--reason-code",
            help="Reason code to record. Can be repeated.",
        ),
        notes: str = typer.Option("", "--notes"),
        review_seconds: int = typer.Option(0, "--review-seconds", min=0),
    ) -> None:
        try:
            event_payload = json.loads(event_path.read_text(encoding="utf-8"))
            event = CryptoPerpEvent.model_validate(event_payload)
            if actor_type not in {"system", "human"}:
                raise ValueError("actor_type must be system or human")
            actor_type_value = cast(Literal["system", "human"], actor_type)
            decision = build_decision(
                event_id=event.event_id,
                action=action,
                actor_type=actor_type_value,
                actor_id=actor_id,
                decision_at=_utc_now(),
                information_cutoff_at=event.information_cutoff_at,
                size_cap_usd=size_cap_usd,
                reason_codes=reason_code or [],
                notes=notes,
                review_seconds=review_seconds,
                source_event_path=event_path.as_posix(),
                source_event_sha256=_file_sha256(event_path),
                producer_command="crypto-perp-decision-record",
            )
        except Exception as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        json_path = out / f"{decision.decision_id}.json"
        report_path = out / f"{decision.decision_id}.md"
        write_json_artifact(json_path, decision.model_dump(mode="json"))
        write_text_artifact(report_path, _render_decision_markdown(decision))
        typer.echo("network_attempted=false")
        typer.echo("exchange_write_used=false")
        typer.echo("status=pass")
        typer.echo(f"decision_id={decision.decision_id}")
        typer.echo(f"event_id={decision.event_id}")
        typer.echo(f"action={decision.action.value}")
        typer.echo(f"decision_path={json_path.as_posix()}")
        typer.echo(f"report_path={report_path.as_posix()}")

    @app.command("crypto-perp-outcome-record")
    def crypto_perp_outcome_record_cmd(
        out: Path = typer.Option(
            Path("data/crypto_perp/outcomes"),
            "--out",
            help="Output directory for outcome artifacts.",
        ),
        event_path: Path | None = typer.Option(
            None,
            "--event",
            help="Optional source crypto_perp_event.v1 JSON artifact.",
        ),
        event_id: str | None = typer.Option(None, "--event-id"),
        horizon_minutes: int = typer.Option(..., "--horizon-minutes", min=1),
        reference_price: str = typer.Option(..., "--reference-price"),
        close_price: str = typer.Option(..., "--close-price"),
        high_price: str = typer.Option(..., "--high-price"),
        low_price: str = typer.Option(..., "--low-price"),
        market_return: str = typer.Option("0", "--market-return"),
        matured: bool = typer.Option(True, "--matured/--not-matured"),
        observed_high_low_order: str | None = typer.Option(
            None,
            "--observed-high-low-order",
            help="Optional HIGH_FIRST or LOW_FIRST when known from higher resolution evidence.",
        ),
        near_miss_ref: list[str] | None = typer.Option(None, "--near-miss-ref"),
        known_gap: list[str] | None = typer.Option(None, "--known-gap"),
    ) -> None:
        try:
            source_refs: list[dict[str, str]] = []
            resolved_event_id = event_id
            if event_path is not None:
                event_payload = json.loads(event_path.read_text(encoding="utf-8"))
                event = CryptoPerpEvent.model_validate(event_payload)
                resolved_event_id = event.event_id
                source_refs.append(
                    {
                        "path": event_path.as_posix(),
                        "sha256": _file_sha256(event_path),
                        "schema_version": "crypto_perp_event.v1",
                    }
                )
            if not resolved_event_id:
                raise ValueError("event_id is required when --event is omitted")
            if observed_high_low_order not in {None, "HIGH_FIRST", "LOW_FIRST"}:
                raise ValueError("observed_high_low_order must be HIGH_FIRST or LOW_FIRST")
            order_value = cast(Literal["HIGH_FIRST", "LOW_FIRST"] | None, observed_high_low_order)
            outcome = build_outcome(
                event_id=resolved_event_id,
                settled_at=_utc_now(),
                horizons=[
                    OutcomePriceWindow(
                        horizon_minutes=horizon_minutes,
                        matured=matured,
                        reference_price=Decimal(reference_price),
                        close_price=Decimal(close_price),
                        high_price=Decimal(high_price),
                        low_price=Decimal(low_price),
                        market_return=Decimal(market_return),
                        observed_high_low_order=order_value,
                    )
                ],
                near_miss_refs=near_miss_ref or [],
                known_gaps=known_gap or [],
                source_refs=source_refs,
                producer_command="crypto-perp-outcome-record",
            )
        except Exception as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        json_path = out / f"{outcome.outcome_id}.json"
        report_path = out / f"{outcome.outcome_id}.md"
        write_json_artifact(json_path, outcome.model_dump(mode="json"))
        write_text_artifact(report_path, _render_outcome_markdown(outcome))
        typer.echo("network_attempted=false")
        typer.echo("exchange_write_used=false")
        typer.echo("status=pass")
        typer.echo(f"outcome_id={outcome.outcome_id}")
        typer.echo(f"event_id={outcome.event_id}")
        typer.echo(f"outcome_path={json_path.as_posix()}")
        typer.echo(f"report_path={report_path.as_posix()}")
