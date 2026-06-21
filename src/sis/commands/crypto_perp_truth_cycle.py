from __future__ import annotations

from pathlib import Path

import typer

from sis.crypto_perp.io import write_json_artifact, write_text_artifact
from sis.crypto_perp.truth_cycle_status import (
    CryptoPerpTruthCycleStatus,
    build_truth_cycle_status,
)
from sis.strategy_daily_brief.service import build_strategy_daily_brief
from sis.strategy_workbench_viewer.service import build_strategy_workbench_viewer


def _render_truth_cycle_status_markdown(status: CryptoPerpTruthCycleStatus) -> str:
    lines = [
        "# Crypto Perp Truth-Cycle Status",
        "",
        f"- cycle_status: `{status.cycle_status}`",
        f"- human_summary: {status.summary.get('human_summary', '')}",
        f"- recommended_next_command: `{status.recommended_next_command}`",
        "- permits_live_order: `false`",
        "- exchange_write_used: `false`",
        "- live_order_submitted: `false`",
        "",
        "## Stages",
        "",
    ]
    lines.extend(
        f"- `{stage.stage_id}`: `{stage.status}`"
        + (f" ({stage.artifact_path})" if stage.artifact_path else "")
        for stage in status.stages
    )
    if status.stage_checklist:
        lines.extend(["", "## Stage Checklist", ""])
        lines.append(
            "| stage | status | blocks_progress | expected_cli_option | artifact_path | expected_artifact_hint |"
        )
        lines.append("|---|---|---|---|---|---|")
        lines.extend(
            "| "
            f"`{item.stage_id}` | `{item.status}` | `{str(item.blocks_progress).lower()}` | "
            f"`{item.expected_cli_option or ''}` | `{item.artifact_path or ''}` | "
            f"{item.expected_artifact_hint} |"
            for item in status.stage_checklist
        )
    if status.stop_reasons:
        lines.extend(["", "## Stop Reasons", ""])
        lines.extend(f"- `{reason}`" for reason in status.stop_reasons)
    if status.next_steps:
        lines.extend(["", "## Next Steps", ""])
        lines.extend(
            "- "
            f"`{step.step_id}`: {step.purpose} "
            f"command=`{step.command}` "
            f"requires_explicit_approval=`{str(step.requires_explicit_approval).lower()}` "
            f"network_allowed=`{str(step.network_allowed).lower()}` "
            f"exchange_write_allowed=`{str(step.exchange_write_allowed).lower()}` "
            f"live_order_allowed=`{str(step.live_order_allowed).lower()}`"
            for step in status.next_steps
        )
    if status.known_gaps:
        lines.extend(["", "## Known Gaps", ""])
        lines.extend(f"- `{gap}`" for gap in status.known_gaps)
    return "\n".join(lines)


def _render_dogfood_pack_markdown(
    *,
    status: CryptoPerpTruthCycleStatus,
    status_path: Path,
    status_report_path: Path,
    daily_brief_path: Path,
    daily_brief_report_path: Path,
    viewer_manifest_path: Path,
    viewer_html_path: Path,
) -> str:
    lines = [
        "# Crypto Perp Truth-Cycle Dogfood Pack",
        "",
        "This pack is local fixture-only. It does not use network, credentials, wallet, signing, exchange write, or live orders.",
        "",
        "## Current Fixture Status",
        "",
        f"- cycle_status: `{status.cycle_status}`",
        f"- human_summary: {status.summary.get('human_summary', '')}",
        f"- recommended_next_command: `{status.recommended_next_command}`",
        f"- first_stop_reason: `{status.stop_reasons[0] if status.stop_reasons else 'none'}`",
        f"- next_step_count: `{len(status.next_steps)}`",
        f"- stage_checklist_blocker_count: `{status.summary.get('stage_checklist_blocker_count', 0)}`",
        "",
        "## Review Order",
        "",
        "1. Open `truth_cycle_status.md` and confirm `cycle_status`, `human_summary`, and `stop_reasons`.",
        "2. Open `strategy_daily_brief.md` and confirm `crypto_perp_truth_cycle_follow_up_count` is not hidden.",
        "3. Open `strategy_workbench_viewer.html` and confirm `human_summary` and `first_stop_reason` are visible.",
        "4. Do not proceed to public probe, credentialed read-only, or tiny live measurement from this fixture pack.",
        "",
        "## Stop Decision",
        "",
        "- If `cycle_status` is `MISSING_PROBE_AUDIT`, stop and verify the provider probe / probe audit artifact path first.",
        "- If `cycle_status` is `NEEDS_ACTUAL_CASH`, stop and rebuild rows from actual cash evidence before considering measurement.",
        "- If `cycle_status` is `READY_FOR_HUMAN_TINY_LIVE_REVIEW`, stop for separate human approval; this pack is still not live permission.",
        "",
        "## Next Steps",
        "",
        *[
            "- "
            f"`{step.step_id}`: {step.purpose} "
            f"command=`{step.command}` "
            f"requires_explicit_approval=`{str(step.requires_explicit_approval).lower()}` "
            f"network_allowed=`{str(step.network_allowed).lower()}` "
            f"exchange_write_allowed=`{str(step.exchange_write_allowed).lower()}` "
            f"live_order_allowed=`{str(step.live_order_allowed).lower()}`"
            for step in status.next_steps
        ],
        "",
        "## Stage Checklist",
        "",
        "| stage | status | blocks_progress | expected_cli_option | artifact_path | expected_artifact_hint |",
        "|---|---|---|---|---|---|",
        *[
            "| "
            f"`{item.stage_id}` | `{item.status}` | `{str(item.blocks_progress).lower()}` | "
            f"`{item.expected_cli_option or ''}` | `{item.artifact_path or ''}` | "
            f"{item.expected_artifact_hint} |"
            for item in status.stage_checklist
        ],
        "",
        "## Artifacts",
        "",
        f"- truth_cycle_status_json: `{status_path.as_posix()}`",
        f"- truth_cycle_status_md: `{status_report_path.as_posix()}`",
        f"- daily_brief_json: `{daily_brief_path.as_posix()}`",
        f"- daily_brief_md: `{daily_brief_report_path.as_posix()}`",
        f"- viewer_manifest_json: `{viewer_manifest_path.as_posix()}`",
        f"- viewer_html: `{viewer_html_path.as_posix()}`",
        "",
        "## Boundary",
        "",
        "- network_attempted: `false`",
        "- exchange_write_used: `false`",
        "- live_order_submitted: `false`",
        "- permits_live_order: `false`",
    ]
    return "\n".join(lines)


def register_crypto_perp_truth_cycle_commands(app: typer.Typer) -> None:
    @app.command("crypto-perp-truth-cycle-status")
    def crypto_perp_truth_cycle_status_cmd(
        probe_audit: Path | None = typer.Option(
            None,
            "--probe-audit",
            help="Optional crypto_perp_probe_audit.v1 JSON artifact.",
        ),
        raw_refresh: Path | None = typer.Option(
            None,
            "--raw-refresh",
            help="Optional crypto_perp_raw_refresh.v1 JSON artifact.",
        ),
        event: Path | None = typer.Option(
            None,
            "--event",
            help="Optional crypto_perp_event.v1 JSON artifact.",
        ),
        decision: Path | None = typer.Option(
            None,
            "--decision",
            help="Optional crypto_perp_decision.v1 JSON artifact.",
        ),
        outcome: Path | None = typer.Option(
            None,
            "--outcome",
            help="Optional crypto_perp_outcome.v1 JSON artifact.",
        ),
        rows_preview: Path | None = typer.Option(
            None,
            "--rows-preview",
            help="Optional crypto_perp_tournament_rows_preview.v1 JSON artifact.",
        ),
        tournament_report: Path | None = typer.Option(
            None,
            "--tournament-report",
            help="Optional crypto_perp_tournament_report.v1 JSON artifact.",
        ),
        tournament_gate: Path | None = typer.Option(
            None,
            "--tournament-gate",
            help="Optional crypto_perp_tournament_gate.v1 JSON artifact.",
        ),
        out: Path = typer.Option(
            Path("data/crypto_perp/truth_cycle_status"),
            "--out",
            help="Output directory for truth-cycle status artifacts.",
        ),
    ) -> None:
        try:
            status = build_truth_cycle_status(
                probe_audit_path=probe_audit,
                raw_refresh_path=raw_refresh,
                event_path=event,
                decision_path=decision,
                outcome_path=outcome,
                rows_preview_path=rows_preview,
                tournament_report_path=tournament_report,
                tournament_gate_path=tournament_gate,
            )
        except Exception as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        json_path = out / "truth_cycle_status.json"
        report_path = out / "truth_cycle_status.md"
        write_json_artifact(json_path, status.model_dump(mode="json"))
        write_text_artifact(report_path, _render_truth_cycle_status_markdown(status))
        typer.echo("network_attempted=false")
        typer.echo("exchange_write_used=false")
        typer.echo("live_order_submitted=false")
        typer.echo("status=pass")
        typer.echo(f"cycle_status={status.cycle_status}")
        typer.echo(f"human_summary={status.summary.get('human_summary', '')}")
        typer.echo(f"recommended_next_command={status.recommended_next_command}")
        typer.echo(f"next_step_count={len(status.next_steps)}")
        if status.next_steps:
            typer.echo(f"first_next_step={status.next_steps[0].step_id}")
        typer.echo(
            f"stage_checklist_blocker_count={status.summary.get('stage_checklist_blocker_count', 0)}"
        )
        typer.echo(f"known_gap_count={len(status.known_gaps)}")
        typer.echo(f"status_path={json_path.as_posix()}")
        typer.echo(f"report_path={report_path.as_posix()}")

    @app.command("crypto-perp-truth-cycle-dogfood-pack")
    def crypto_perp_truth_cycle_dogfood_pack_cmd(
        out: Path = typer.Option(
            Path("data/crypto_perp/truth_cycle_dogfood"),
            "--out",
            help="Output directory for fixture-only truth-cycle dogfood artifacts.",
        ),
        replace_existing: bool = typer.Option(
            False,
            "--replace-existing/--no-replace-existing",
            help="Replace existing Daily Brief and Workbench Viewer artifacts.",
        ),
    ) -> None:
        try:
            status_dir = out / "truth_cycle_status"
            missing_probe_audit = out / "inputs" / "missing_probe_audit.json"
            status = build_truth_cycle_status(probe_audit_path=missing_probe_audit)
            status_path = status_dir / "truth_cycle_status.json"
            status_report_path = status_dir / "truth_cycle_status.md"
            write_json_artifact(status_path, status.model_dump(mode="json"))
            write_text_artifact(status_report_path, _render_truth_cycle_status_markdown(status))

            daily = build_strategy_daily_brief(
                data_dir=out,
                out_dir=out / "reports" / "strategy_daily_brief",
                replace_existing=replace_existing,
            )
            viewer = build_strategy_workbench_viewer(
                artifacts=[
                    status_path,
                    status_report_path,
                    daily.brief_path,
                    daily.report_path,
                ],
                data_dir=out,
                out_dir=out / "reports" / "strategy_workbench_viewer",
                replace_existing=replace_existing,
            )
            pack_path = out / "dogfood_pack.md"
            write_text_artifact(
                pack_path,
                _render_dogfood_pack_markdown(
                    status=status,
                    status_path=status_path,
                    status_report_path=status_report_path,
                    daily_brief_path=daily.brief_path,
                    daily_brief_report_path=daily.report_path,
                    viewer_manifest_path=viewer.manifest_path,
                    viewer_html_path=viewer.html_path,
                ),
            )
        except Exception as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        typer.echo("network_attempted=false")
        typer.echo("exchange_write_used=false")
        typer.echo("live_order_submitted=false")
        typer.echo("status=pass")
        typer.echo(f"cycle_status={status.cycle_status}")
        typer.echo(f"human_summary={status.summary.get('human_summary', '')}")
        typer.echo(f"next_step_count={len(status.next_steps)}")
        if status.next_steps:
            typer.echo(f"first_next_step={status.next_steps[0].step_id}")
        typer.echo(
            f"stage_checklist_blocker_count={status.summary.get('stage_checklist_blocker_count', 0)}"
        )
        typer.echo(f"daily_brief_item_count={daily.brief.summary.total_item_count}")
        typer.echo(f"viewer_artifact_count={viewer.manifest.artifact_count}")
        typer.echo(f"pack_path={pack_path.as_posix()}")
        typer.echo(f"viewer_html_path={viewer.html_path.as_posix()}")
