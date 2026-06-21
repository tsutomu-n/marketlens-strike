from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
from typing import Literal, cast

import typer
from pydantic import ValidationError

from sis.commands.strategy_authoring import _resolve_workspace_path
from sis.crypto_perp.bitget.account import (
    CredentialScopeAttestation,
    CryptoPerpAccountSnapshot,
    build_account_snapshot,
)
from sis.crypto_perp.bitget.auth import missing_bitget_credential_env
from sis.crypto_perp.bitget.probe import ProviderProbeArtifact, run_provider_probe
from sis.crypto_perp.config import load_crypto_perp_lab_config
from sis.crypto_perp.decisions import CryptoPerpDecision, build_decision
from sis.crypto_perp.event_card import build_event_card
from sis.crypto_perp.events import CryptoPerpEvent
from sis.crypto_perp.io import write_json_artifact, write_text_artifact
from sis.crypto_perp.models import ConfigValidationArtifact, CryptoPerpProducer, stable_hash
from sis.crypto_perp.order_preview import (
    InstrumentOrderConstraints,
    OrderPreviewRequest,
    build_order_preview,
)
from sis.crypto_perp.outcomes import CryptoPerpOutcome, OutcomePriceWindow, build_outcome
from sis.crypto_perp.probe_audit import CryptoPerpProbeAudit, build_probe_audit
from sis.crypto_perp.reason_codes import CryptoPerpReasonCode
from sis.crypto_perp.rendering import render_event_card_markdown
from sis.crypto_perp.tournament import (
    CryptoPerpTournamentReport,
    TournamentEventResult,
    build_tournament_report,
)
from sis.settings import get_settings


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _config_hash(config_path: Path) -> str:
    return "sha256:" + stable_hash([config_path.read_text(encoding="utf-8")])


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_config_for_cli(config_path: Path):
    settings = get_settings()
    resolved = _resolve_workspace_path(config_path, settings.data_dir)
    return load_crypto_perp_lab_config(resolved), resolved


def _write_config_validation(config_path: Path, out_dir: Path) -> ConfigValidationArtifact:
    config, resolved = _load_config_for_cli(config_path)
    artifact = ConfigValidationArtifact(
        artifact_id=stable_hash(
            ["crypto-perp-config-validate", config.config_id, _config_hash(resolved)]
        ),
        created_at=_utc_now(),
        producer=CryptoPerpProducer(command="crypto-perp-config-validate"),
        config_id=config.config_id,
        config_hash=_config_hash(resolved),
    )
    payload = artifact.model_dump(mode="json")
    write_json_artifact(out_dir / "config_validation.json", payload)
    write_text_artifact(
        out_dir / "config_validation.md",
        "\n".join(
            [
                "# Crypto Perp Config Validation",
                "",
                f"- config_id: `{artifact.config_id}`",
                f"- validation_status: `{artifact.validation_status}`",
                "- boundary: all normal flags false",
            ]
        ),
    )
    return artifact


def _env_enabled(name: str) -> bool:
    return os.getenv(name) == "1"


def _fixture_credential_attestation() -> CredentialScopeAttestation:
    return CredentialScopeAttestation(
        read_enabled=True,
        trade_enabled=False,
        withdrawal_disabled_confirmed=True,
        ip_restriction_confirmed=True,
        attested_by="local-fixture",
        attested_at=_utc_now(),
    )


def _fixture_account_snapshot() -> CryptoPerpAccountSnapshot:
    return build_account_snapshot(
        observed_at=_utc_now(),
        account_payload={
            "marginCoin": "USDT",
            "available": "100",
            "accountEquity": "100",
            "unrealizedPL": "0",
            "marginMode": "isolated",
            "posMode": "one_way_mode",
        },
        positions_payload=[],
        open_orders_payload=[],
        credential_scope_attestation=_fixture_credential_attestation(),
    )


def _read_tournament_rows(path: Path) -> list[TournamentEventResult]:
    text = path.read_text(encoding="utf-8")
    rows_payload: object
    try:
        rows_payload = json.loads(text)
    except json.JSONDecodeError:
        rows_payload = [json.loads(line) for line in text.splitlines() if line.strip()]
    if isinstance(rows_payload, dict):
        rows_payload = rows_payload.get("rows")
    if not isinstance(rows_payload, list):
        raise ValueError("rows input must be a JSON array, JSON object with rows, or JSONL")
    return [TournamentEventResult.model_validate(row) for row in rows_payload]


def _render_tournament_report_markdown(report: CryptoPerpTournamentReport) -> str:
    lines = [
        "# Crypto Perp Tournament Report",
        "",
        f"- report_id: `{report.report_id}`",
        f"- tournament_status: `{report.tournament_status}`",
        f"- primary_metric: `{report.primary_metric}`",
        f"- event_count: `{report.event_count}`",
        f"- leader_action: `{report.leader_action or 'NONE'}`",
        "",
        "## Scores",
        "",
        "| action | actual_cash_result_usd | largest_loss_usd | event_count | near_miss_count | operator_time_minutes |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for score in report.scores:
        lines.append(
            "| "
            f"{score.action} | "
            f"{score.actual_cash_result_usd} | "
            f"{score.largest_loss_usd} | "
            f"{score.event_count} | "
            f"{score.near_miss_count} | "
            f"{score.operator_time_minutes} |"
        )
    if report.inconclusive_reasons:
        lines.extend(["", "## Inconclusive Reasons", ""])
        lines.extend(f"- `{reason}`" for reason in report.inconclusive_reasons)
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- permits_live_order: `false`",
            "- exchange_write_used: `false`",
            "- automatic_trading: `false`",
        ]
    )
    return "\n".join(lines)


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


def _render_probe_audit_markdown(audit: CryptoPerpProbeAudit) -> str:
    lines = [
        "# Crypto Perp Probe Audit",
        "",
        f"- probe_id: `{audit.probe_id}`",
        f"- audit_status: `{audit.audit_status}`",
        f"- raw_snapshot_count: `{audit.raw_snapshot_count}`",
        "- permits_live_order: `false`",
        "- exchange_write_used: `false`",
    ]
    if audit.known_gaps:
        lines.extend(["", "## Known Gaps", ""])
        lines.extend(f"- `{gap}`" for gap in audit.known_gaps)
    lines.extend(["", "## Next Actions", ""])
    lines.extend(f"- `{action}`" for action in audit.next_actions)
    return "\n".join(lines)


def register_crypto_perp_commands(app: typer.Typer) -> None:
    @app.command("crypto-perp-config-validate")
    def crypto_perp_config_validate_cmd(
        config: Path = typer.Option(
            ...,
            "--config",
            help="crypto_perp_lab_config.v1 YAML/JSON.",
        ),
        out: Path = typer.Option(
            Path("data/crypto_perp/config_validation"),
            "--out",
            help="Output directory for config validation artifacts.",
        ),
    ) -> None:
        try:
            artifact = _write_config_validation(config, out)
        except (ValueError, ValidationError) as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        typer.echo("status=pass")
        typer.echo(f"config_id={artifact.config_id}")
        typer.echo(f"validation_status={artifact.validation_status}")
        typer.echo(f"validation_path={(out / 'config_validation.json').as_posix()}")
        typer.echo(f"report_path={(out / 'config_validation.md').as_posix()}")

    @app.command("crypto-perp-probe")
    def crypto_perp_probe_cmd(
        config: Path = typer.Option(
            Path("configs/crypto_perp/bitget_personal_edge_lab.yaml"),
            "--config",
            help="crypto_perp_lab_config.v1 YAML/JSON.",
        ),
        out: Path = typer.Option(
            Path("data/crypto_perp/provider_probe"),
            "--out",
            help="Output directory for provider probe artifacts.",
        ),
        raw_root: Path = typer.Option(
            Path("data/crypto_perp/raw"),
            "--raw-root",
            help="Root directory for immutable raw public snapshots.",
        ),
        network: bool = typer.Option(
            False,
            "--network/--no-network",
            help="Attempt public network only when env opt-in is also set.",
        ),
    ) -> None:
        lab_config, _resolved = _load_config_for_cli(config)
        env_name = lab_config.network_policy.public_network_env_var
        typer.echo(f"config_id={lab_config.config_id}")
        if not network or not _env_enabled(env_name):
            typer.echo("network_attempted=false")
            typer.echo("status=blocked")
            typer.echo(f"block_reason={CryptoPerpReasonCode.PUBLIC_NETWORK_OPT_IN_REQUIRED.value}")
            raise typer.Exit(2)
        try:
            result = run_provider_probe(
                config=lab_config,
                out_dir=out,
                raw_root=raw_root,
                network_attempted=True,
                started_at=_utc_now(),
            )
        except Exception as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        typer.echo("network_attempted=true")
        typer.echo("credentials_used=false")
        typer.echo("status=pass")
        typer.echo(f"probe_id={result.probe.probe_id}")
        typer.echo(f"probe_path={result.probe_path.as_posix()}")
        typer.echo(f"report_path={result.report_path.as_posix()}")

    @app.command("crypto-perp-probe-audit")
    def crypto_perp_probe_audit_cmd(
        probe: Path = typer.Option(
            ...,
            "--probe",
            help="Source crypto_perp_provider_probe.v1 JSON artifact.",
        ),
        out: Path = typer.Option(
            Path("data/crypto_perp/probe_audit"),
            "--out",
            help="Output directory for probe audit artifacts.",
        ),
        check_raw_exists: bool = typer.Option(
            True,
            "--check-raw-exists/--no-check-raw-exists",
            help="Verify raw snapshot paths referenced by the probe exist locally.",
        ),
    ) -> None:
        try:
            payload = json.loads(probe.read_text(encoding="utf-8"))
            probe_artifact = ProviderProbeArtifact.model_validate(payload)
            audit = build_probe_audit(
                probe=probe_artifact,
                check_raw_exists=check_raw_exists,
            )
        except Exception as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        json_path = out / "probe_audit.json"
        report_path = out / "probe_audit.md"
        write_json_artifact(json_path, audit.model_dump(mode="json"))
        write_text_artifact(report_path, _render_probe_audit_markdown(audit))
        typer.echo("network_attempted=false")
        typer.echo("exchange_write_used=false")
        typer.echo(
            "status=pass" if audit.audit_status == "READY_FOR_EVENT_REFRESH" else "status=blocked"
        )
        typer.echo(f"audit_status={audit.audit_status}")
        typer.echo(f"known_gap_count={len(audit.known_gaps)}")
        typer.echo(f"probe_audit_path={json_path.as_posix()}")
        typer.echo(f"report_path={report_path.as_posix()}")

    @app.command("crypto-perp-refresh")
    def crypto_perp_refresh_cmd(
        config: Path = typer.Option(
            Path("configs/crypto_perp/bitget_personal_edge_lab.yaml"),
            "--config",
            help="crypto_perp_lab_config.v1 YAML/JSON.",
        ),
        through: str = typer.Option(
            "config",
            "--through",
            help="Refresh stage. M01 supports config only; later tasks add probe/events.",
        ),
    ) -> None:
        lab_config, _resolved = _load_config_for_cli(config)
        typer.echo(f"config_id={lab_config.config_id}")
        if through == "config":
            typer.echo("status=pass")
            typer.echo("through=config")
            return
        typer.echo("status=blocked")
        block_reason = (
            CryptoPerpReasonCode.EVENT_REFRESH_NOT_IMPLEMENTED_M04
            if through == "events"
            else CryptoPerpReasonCode.MARKET_REFRESH_NOT_IMPLEMENTED_M02
        )
        typer.echo(f"block_reason={block_reason.value}")
        raise typer.Exit(2)

    @app.command("crypto-perp-watchdeck")
    def crypto_perp_watchdeck_cmd(
        config: Path = typer.Option(
            Path("configs/crypto_perp/bitget_personal_edge_lab.yaml"),
            "--config",
            help="crypto_perp_lab_config.v1 YAML/JSON.",
        ),
        event_path: Path | None = typer.Option(
            None,
            "--event",
            help="Render a crypto_perp_event.v1 JSON artifact as an event card.",
        ),
        top: int = typer.Option(20, "--top", help="Maximum cards to display."),
    ) -> None:
        if event_path is not None:
            try:
                event_payload = json.loads(event_path.read_text(encoding="utf-8"))
                event = CryptoPerpEvent.model_validate(event_payload)
            except Exception as exc:
                typer.echo("status=fail")
                typer.echo(f"error={exc}")
                raise typer.Exit(2) from exc
            typer.echo(render_event_card_markdown(build_event_card(event)))
            return

        lab_config, _resolved = _load_config_for_cli(config)
        if top <= 0:
            typer.echo("status=fail")
            typer.echo("error=top must be positive")
            raise typer.Exit(2)
        typer.echo(f"config_id={lab_config.config_id}")
        typer.echo("status=blocked")
        typer.echo(f"block_reason={CryptoPerpReasonCode.WATCHDECK_NOT_IMPLEMENTED_M04.value}")
        raise typer.Exit(2)

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

    @app.command("crypto-perp-account-probe")
    def crypto_perp_account_probe_cmd(
        config: Path = typer.Option(
            Path("configs/crypto_perp/bitget_personal_edge_lab.yaml"),
            "--config",
            help="crypto_perp_lab_config.v1 YAML/JSON.",
        ),
        out: Path = typer.Option(
            Path("data/crypto_perp/account_probe"),
            "--out",
            help="Output directory for account snapshot artifacts.",
        ),
        fixture: bool = typer.Option(
            True,
            "--fixture/--no-fixture",
            help="Use a local read-only fixture. Real credentialed network read is blocked in M08.",
        ),
    ) -> None:
        lab_config, _resolved = _load_config_for_cli(config)
        if not fixture:
            env_name = lab_config.network_policy.credentialed_read_env_var
            typer.echo(f"config_id={lab_config.config_id}")
            if not _env_enabled(env_name):
                typer.echo("network_attempted=false")
                typer.echo("status=blocked")
                typer.echo("block_reason=CREDENTIALED_READ_OPT_IN_REQUIRED")
                raise typer.Exit(2)
            missing = missing_bitget_credential_env()
            if missing:
                typer.echo("network_attempted=false")
                typer.echo("status=blocked")
                typer.echo(f"missing_env={','.join(missing)}")
                raise typer.Exit(2)
            typer.echo("network_attempted=false")
            typer.echo("status=blocked")
            typer.echo("block_reason=CREDENTIALED_READ_NETWORK_NOT_IMPLEMENTED_M08")
            raise typer.Exit(2)

        snapshot = _fixture_account_snapshot()
        path = out / "account_snapshot.json"
        write_json_artifact(path, snapshot.model_dump(mode="json"))
        typer.echo("network_attempted=false")
        typer.echo("credentials_used=false")
        typer.echo("status=pass")
        typer.echo(f"account_snapshot_id={snapshot.account_snapshot_id}")
        typer.echo(f"account_snapshot_path={path.as_posix()}")

    @app.command("crypto-perp-order-preview")
    def crypto_perp_order_preview_cmd(
        out: Path = typer.Option(
            Path("data/crypto_perp/order_preview"),
            "--out",
            help="Output directory for order preview artifacts.",
        ),
        account_snapshot: Path | None = typer.Option(
            None,
            "--account-snapshot",
            help="Optional crypto_perp_account_snapshot.v1 JSON. Fixture account is used if omitted.",
        ),
        event_id: str = typer.Option("event-fixture", "--event-id"),
        decision_id: str = typer.Option("decision-fixture", "--decision-id"),
        symbol: str = typer.Option("BTCUSDT", "--symbol"),
        side: str = typer.Option("buy", "--side"),
        position_side: str = typer.Option("one_way", "--position-side"),
        notional_usd: str = typer.Option("25", "--notional-usd"),
        reference_price: str = typer.Option("100", "--reference-price"),
        limit_price: str = typer.Option("100", "--limit-price"),
    ) -> None:
        if account_snapshot is None:
            snapshot = _fixture_account_snapshot()
        else:
            payload = json.loads(account_snapshot.read_text(encoding="utf-8"))
            snapshot = CryptoPerpAccountSnapshot.model_validate(payload)
        try:
            if side not in {"buy", "sell"}:
                raise ValueError("side must be buy or sell")
            if position_side not in {"one_way", "long", "short"}:
                raise ValueError("position_side must be one_way, long, or short")
            side_value = cast(Literal["buy", "sell"], side)
            position_side_value = cast(Literal["one_way", "long", "short"], position_side)
            request = OrderPreviewRequest(
                event_id=event_id,
                decision_id=decision_id,
                symbol=symbol,
                product_type="USDT-FUTURES",
                side=side_value,
                position_side=position_side_value,
                order_type="limit",
                margin_mode="isolated",
                margin_coin="USDT",
                requested_notional_usd=Decimal(notional_usd),
                reference_price=Decimal(reference_price),
                limit_price=Decimal(limit_price),
                leverage=1,
            )
            preview = build_order_preview(
                request=request,
                constraints=InstrumentOrderConstraints(
                    symbol=symbol,
                    product_type="USDT-FUTURES",
                    price_multiplier=Decimal("0.1"),
                    size_multiplier=Decimal("0.001"),
                    min_order_amount=Decimal("5"),
                    min_order_qty=Decimal("0.001"),
                    max_market_order_qty=Decimal("10"),
                ),
                account_snapshot=snapshot,
                created_at=_utc_now(),
            )
        except Exception as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        path = out / "order_preview.json"
        write_json_artifact(path, preview.model_dump(mode="json"))
        typer.echo("network_attempted=false")
        typer.echo("exchange_write_used=false")
        typer.echo("status=pass" if preview.preview_status == "READY" else "status=blocked")
        typer.echo(f"preview_status={preview.preview_status}")
        typer.echo(f"would_submit_order={str(preview.would_submit_order).lower()}")
        typer.echo(f"client_oid={preview.client_oid}")
        typer.echo(f"order_preview_path={path.as_posix()}")

    @app.command("crypto-perp-tournament-report")
    def crypto_perp_tournament_report_cmd(
        rows: Path = typer.Option(
            ...,
            "--rows",
            help="Tournament rows as JSON array, JSON object with rows, or JSONL.",
        ),
        out: Path = typer.Option(
            Path("data/crypto_perp/tournament"),
            "--out",
            help="Output directory for tournament report artifacts.",
        ),
        report_id: str = typer.Option("crypto-perp-tournament", "--report-id"),
        min_events: int = typer.Option(10, "--min-events", min=1),
        known_gap: list[str] | None = typer.Option(
            None,
            "--known-gap",
            help="Known evidence gap to carry into the report.",
        ),
    ) -> None:
        try:
            row_list = _read_tournament_rows(rows)
            source_text = rows.read_text(encoding="utf-8")
            report = build_tournament_report(
                report_id=report_id,
                generated_at=_utc_now(),
                rows=row_list,
                min_events=min_events,
                source_refs=[
                    {
                        "path": rows.as_posix(),
                        "sha256": "sha256:" + stable_hash([source_text]),
                    }
                ],
                known_gaps=known_gap or [],
            )
        except Exception as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        json_path = out / "tournament_report.json"
        report_path = out / "tournament_report.md"
        write_json_artifact(json_path, report.model_dump(mode="json"))
        write_text_artifact(report_path, _render_tournament_report_markdown(report))
        typer.echo("network_attempted=false")
        typer.echo("exchange_write_used=false")
        typer.echo(
            "status=pass" if report.tournament_status == "COMPLETE" else "status=inconclusive"
        )
        typer.echo(f"tournament_status={report.tournament_status}")
        typer.echo(f"leader_action={report.leader_action or 'NONE'}")
        typer.echo(f"primary_metric={report.primary_metric}")
        typer.echo(f"event_count={report.event_count}")
        typer.echo(f"tournament_report_path={json_path.as_posix()}")
        typer.echo(f"report_path={report_path.as_posix()}")
