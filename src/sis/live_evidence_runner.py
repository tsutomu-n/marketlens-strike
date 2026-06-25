from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import typer
from filelock import FileLock, Timeout
from tenacity import Retrying, retry_if_exception_type, stop_after_attempt, wait_chain, wait_fixed

from sis.live_evidence_manifest import (
    LiveEvidenceManifest,
    RunOutcome,
    StepOutcome,
    apply_latest_execution_lineage,
    default_manifest_path,
    load_manifest,
    step_for,
    terminal_outcome,
    write_manifest,
)
from sis.live_evidence_artifacts import (
    build_artifact_paths as _build_artifact_paths,
    latest_evidence_card_path as _latest_evidence_card_path,
    row_count as _row_count,
)
from sis.live_evidence_collection_gates import (
    CollectionGateResult,
    evaluate_collection_volume as _evaluate_collection_volume,
    expected_metadata_rows as _expected_metadata_rows,
)
from sis.live_evidence_operation_summaries import read_live_evidence_operation_summaries
from sis.live_evidence_restart_pointers import build_live_evidence_restart_pointers
from sis.market_calendar import market_session_window
from sis.reports.loaders import safe_read_json_dict
from sis.reports.live_evidence_report import (
    default_followup_output_path,
    default_html_output_path,
    default_markdown_output_path,
    render_live_evidence_followup,
    render_live_evidence_html,
    render_live_evidence_report,
)
from sis.reports.quote_diagnostics import build_quote_diagnostics
from sis.reports.summary_normalizers import (
    audit_summary_fields,
    execution_drift_overview_flat_fields,
    normalize_phase_gate_summary,
    normalize_readiness_summary,
    phase_gate_flat_fields,
    readiness_flat_fields,
)
from sis.settings import get_settings

app = typer.Typer(no_args_is_help=True)


def _apply_evidence_card_summary(manifest: LiveEvidenceManifest, payload: dict) -> None:
    manifest.decision = payload.get("decision") or manifest.decision
    manifest.blockers = list(payload.get("blockers", []))
    manifest.next_actions = list(payload.get("next_actions", []))
    phase_gate_summary = payload.get("phase_gate_summary")
    if isinstance(phase_gate_summary, dict):
        manifest.phase_gate_summary = phase_gate_summary


class LiveEvidenceRunnerError(RuntimeError):
    pass


class RetryableStepError(LiveEvidenceRunnerError):
    pass


class PermanentStepError(LiveEvidenceRunnerError):
    pass


class PreflightError(PermanentStepError):
    pass


class CollectionFailure(PermanentStepError):
    pass


class CollectionVolumeError(RetryableStepError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def today_utc() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def row_count(path: Path) -> int:
    return _row_count(path)


def latest_evidence_card_path(data_dir: Path) -> Path | None:
    return _latest_evidence_card_path(data_dir)


def build_artifact_paths(data_dir: Path, day: str) -> dict[str, str | None]:
    return _build_artifact_paths(data_dir, day)


def _require_artifact_path(artifacts: dict[str, str | None], key: str) -> Path:
    value = artifacts.get(key)
    if not isinstance(value, str) or not value:
        raise PermanentStepError(f"Missing required artifact path: {key}")
    return Path(value)


def expected_metadata_rows(duration_minutes: int, metadata_interval_seconds: int) -> int:
    return _expected_metadata_rows(duration_minutes, metadata_interval_seconds)


def evaluate_collection_volume(
    *,
    metadata_rows_delta: int,
    pricing_rows_delta: int,
    min_metadata_rows: int,
) -> CollectionGateResult:
    return _evaluate_collection_volume(
        metadata_rows_delta=metadata_rows_delta,
        pricing_rows_delta=pricing_rows_delta,
        min_metadata_rows=min_metadata_rows,
    )


def log_step(message: str) -> None:
    print(f"\n[{utc_now()}] {message}")


def command_output(command: list[str]) -> str:
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if result.returncode != 0:
        raise PermanentStepError(f"Command failed ({result.returncode}): {' '.join(command)}")
    return result.stdout


def retrying(max_step_retries: int) -> Retrying:
    return Retrying(
        stop=stop_after_attempt(max_step_retries + 1),
        wait=wait_chain(wait_fixed(30), wait_fixed(90)),
        retry=retry_if_exception_type(RetryableStepError),
        reraise=True,
    )


def run_subprocess(command: list[str], *, retryable: bool) -> None:
    result = subprocess.run(command, check=False)
    if result.returncode == 0:
        return
    error = f"Command failed ({result.returncode}): {' '.join(command)}"
    if retryable:
        raise RetryableStepError(error)
    raise PermanentStepError(error)


def quote_diagnostics_payload(data_dir: Path) -> list[dict]:
    diagnostics = build_quote_diagnostics(
        data_dir / "raw/quotes",
        venue="gtrade",
        stale_thresholds_ms={"gtrade": 3000, "ostium": 5000},
    )
    return [item.__dict__.copy() for item in diagnostics]


def run_with_manifest_step(
    manifest: LiveEvidenceManifest,
    manifest_path: Path,
    step_name: str,
    *,
    max_step_retries: int,
    command: list[str] | None = None,
    func,
) -> None:
    step = step_for(manifest, step_name)
    step.command = command or []
    step.started_at_utc = utc_now()
    step.status = StepOutcome.RUNNING
    write_manifest(manifest_path, manifest)

    try:
        for attempt in retrying(max_step_retries):
            with attempt:
                step.attempt_count = attempt.retry_state.attempt_number
                write_manifest(manifest_path, manifest)
                func()
        step.status = (
            StepOutcome.COMPLETED_WITH_RETRIES if step.attempt_count > 1 else StepOutcome.COMPLETED
        )
        step.error_summary = None
    except RetryableStepError as exc:
        step.status = StepOutcome.FAILED
        step.error_summary = str(exc)
        raise
    except PermanentStepError as exc:
        step.status = StepOutcome.FAILED
        step.error_summary = str(exc)
        raise
    finally:
        step.ended_at_utc = utc_now()
        write_manifest(manifest_path, manifest)


def parse_key_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value
    return values


def default_manifest_summary_path(run_id: str) -> Path:
    return Path("logs/live_evidence/summaries") / f"live_evidence_summary_{run_id}.json"


def write_manifest_summary(manifest_path: Path, summary_path: Path | None = None) -> Path:
    manifest = load_manifest(manifest_path)
    if summary_path is None:
        manifests_dir = manifest_path.parent
        if manifests_dir.name == "manifests":
            out_path = (
                manifests_dir.parent / "summaries" / f"live_evidence_summary_{manifest.run_id}.json"
            )
        else:
            out_path = default_manifest_summary_path(manifest.run_id)
    else:
        out_path = summary_path
    data_dir = Path(manifest.data_dir)
    summaries = read_live_evidence_operation_summaries(data_dir=data_dir, manifest=manifest)
    execution_summary = summaries.execution_summary
    execution_comparison_summary = summaries.execution_comparison_summary
    execution_diagnostics_summary = summaries.execution_diagnostics_summary
    execution_gap_history_summary = summaries.execution_gap_history_summary
    execution_state_comparison_summary = summaries.execution_state_comparison_summary
    execution_snapshot_drift_summary = summaries.execution_snapshot_drift_summary
    execution_drift_overview_summary = summaries.execution_drift_overview_summary
    readiness_summary = summaries.readiness_summary
    latest_execution_lineage = summaries.latest_execution_lineage
    normalized_phase_gate_summary = normalize_phase_gate_summary(manifest.phase_gate_summary)
    normalized_readiness_summary = normalize_readiness_summary(readiness_summary)
    normalized_execution_drift_overview_summary = execution_drift_overview_summary
    phase_gate_fields = phase_gate_flat_fields(normalized_phase_gate_summary)
    readiness_fields = readiness_flat_fields(normalized_readiness_summary)
    execution_drift_fields = execution_drift_overview_flat_fields(
        normalized_execution_drift_overview_summary
    )
    restart_pointers = build_live_evidence_restart_pointers(
        data_dir=data_dir,
        run_id=manifest.run_id,
    )
    payload = {
        "run_id": manifest.run_id,
        "status": manifest.status.value,
        "started_at_utc": manifest.started_at_utc,
        "finished_at_utc": manifest.finished_at_utc,
        "decision": manifest.decision,
        "blockers": list(manifest.blockers),
        "next_actions": list(manifest.next_actions),
        "row_counts": dict(manifest.row_counts),
        "phase_gate_summary": normalized_phase_gate_summary,
        **phase_gate_fields,
        "readiness_summary": normalized_readiness_summary,
        **readiness_fields,
        **latest_execution_lineage,
        "execution_summary": execution_summary,
        "execution_comparison_summary": execution_comparison_summary,
        "execution_diagnostics_summary": execution_diagnostics_summary,
        "execution_gap_history_summary": execution_gap_history_summary,
        "execution_state_comparison_summary": execution_state_comparison_summary,
        "execution_snapshot_drift_summary": execution_snapshot_drift_summary,
        "execution_drift_overview_summary": normalized_execution_drift_overview_summary,
        **execution_drift_fields,
        "restart_pointers": restart_pointers,
        "artifacts": {
            **dict(manifest.artifacts),
            **restart_pointers,
        },
        "manifest_path": str(manifest_path),
        "step_count": len(manifest.steps),
        "failed_steps": [step.name for step in manifest.steps if step.status == StepOutcome.FAILED],
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path


def write_reports_for_manifest(
    manifest_path: Path,
    *,
    settle_seconds: int,
) -> None:
    if settle_seconds > 0:
        time.sleep(settle_seconds)
    manifest = load_manifest(manifest_path)
    log_path = Path(manifest.log_path) if manifest.log_path else None
    stem_source = log_path if log_path is not None else manifest_path
    markdown_output_path = default_markdown_output_path(stem_source)
    html_output_path = default_html_output_path(stem_source)
    followup_output_path = default_followup_output_path(stem_source)

    from sis.reports.live_evidence_report import build_live_evidence_report_data

    data_dir = Path(manifest.data_dir)
    summaries = read_live_evidence_operation_summaries(data_dir=data_dir, manifest=manifest)
    audit_dashboard_path = data_dir / "ops/audit_dashboard_summary.json"
    audit_bundle_path = data_dir / "ops/audit_bundle_manifest.json"
    audit_dashboard = safe_read_json_dict(audit_dashboard_path)
    audit_bundle = safe_read_json_dict(audit_bundle_path)
    phase_gate_summary = summaries.phase_gate_summary
    execution_summary = summaries.execution_summary
    execution_comparison_summary = summaries.execution_comparison_summary
    execution_diagnostics_summary = summaries.execution_diagnostics_summary
    execution_gap_history_summary = summaries.execution_gap_history_summary
    execution_state_comparison_summary = summaries.execution_state_comparison_summary
    execution_snapshot_drift_summary = summaries.execution_snapshot_drift_summary
    execution_drift_overview_summary = summaries.execution_drift_overview_summary
    readiness_summary = summaries.readiness_summary
    latest_execution_lineage = summaries.latest_execution_lineage
    audit_summary = audit_summary_fields(
        audit_dashboard if isinstance(audit_dashboard, dict) else {},
        audit_bundle if isinstance(audit_bundle, dict) else {},
    )
    manifest.phase_gate_summary = normalize_phase_gate_summary(phase_gate_summary)
    manifest.execution_summary = execution_summary
    manifest.execution_comparison_summary = execution_comparison_summary
    manifest.execution_diagnostics_summary = execution_diagnostics_summary
    manifest.execution_gap_history_summary = execution_gap_history_summary
    manifest.execution_state_comparison_summary = execution_state_comparison_summary
    manifest.execution_snapshot_drift_summary = execution_snapshot_drift_summary
    manifest.execution_drift_overview_summary = execution_drift_overview_summary
    manifest.readiness_summary = normalize_readiness_summary(readiness_summary)
    apply_latest_execution_lineage(manifest, latest_execution_lineage)
    write_manifest(manifest_path, manifest)

    data = build_live_evidence_report_data(
        data_dir=Path(manifest.data_dir),
        log_path=log_path,
        output_path=markdown_output_path,
        manifest_path=manifest_path,
        status=manifest.status.value,
        audit_summary=audit_summary,
    )
    markdown_output_path.parent.mkdir(parents=True, exist_ok=True)
    html_output_path.parent.mkdir(parents=True, exist_ok=True)
    followup_output_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_output_path.write_text(render_live_evidence_report(data), encoding="utf-8")
    html_output_path.write_text(render_live_evidence_html(data), encoding="utf-8")
    followup_output_path.write_text(render_live_evidence_followup(data), encoding="utf-8")
    summary_output_path = write_manifest_summary(manifest_path)
    print(f"written_markdown: {markdown_output_path}")
    print(f"written_html: {html_output_path}")
    print(f"written_followup: {followup_output_path}")
    print(f"written_summary: {summary_output_path}")


@app.command()
def main(
    duration_minutes: int = typer.Option(120, "--duration-minutes", min=1),
    metadata_interval_seconds: int = typer.Option(60, "--metadata-interval-seconds", min=1),
    dry_run: bool = typer.Option(False, "--dry-run"),
    force: bool = typer.Option(False, "--force"),
    max_step_retries: int = typer.Option(2, "--max-step-retries", min=0),
    retry_collect_extension_minutes: int = typer.Option(
        10, "--retry-collect-extension-minutes", min=1
    ),
    run_id: str | None = typer.Option(None, "--run-id"),
    requested_schedule_jst: str | None = typer.Option(None, "--requested-schedule-jst"),
    manifest_path: Path | None = typer.Option(None, "--manifest-path"),
    log_path: Path | None = typer.Option(None, "--log-path"),
    report_settle_seconds: int = typer.Option(180, "--report-settle-seconds", min=0),
) -> None:
    settings = get_settings()
    data_dir = settings.data_dir
    should_write_reports = not dry_run
    effective_run_id = run_id or datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    effective_manifest_path = manifest_path or default_manifest_path(effective_run_id)
    if not dry_run:
        typer.echo(
            "live evidence execution is disabled because legacy gTrade/Ostium collectors "
            "were zipped and removed. Use `uv run sis probe trade-xyz` and "
            "`uv run sis collect-trade-xyz-quotes` for active Trade[XYZ] quote collection."
        )
        raise typer.Exit(code=2)
    manifest = LiveEvidenceManifest(
        run_id=effective_run_id,
        requested_schedule_jst=requested_schedule_jst,
        log_path=str(log_path) if log_path else None,
        manifest_path=str(effective_manifest_path),
        started_at_utc=utc_now(),
        duration_minutes=duration_minutes,
        metadata_interval_seconds=metadata_interval_seconds,
        force=force,
        data_dir=str(data_dir),
    )
    write_manifest(effective_manifest_path, manifest)

    lock_path = Path("logs/live_evidence/locks/live_evidence.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock = FileLock(str(lock_path))
    try:
        lock.acquire(timeout=0)
    except Timeout as exc:
        manifest.status = RunOutcome.FAILED_PREFLIGHT
        manifest.finished_at_utc = utc_now()
        manifest.failure_summary = "Another live evidence run is already active."
        write_manifest(effective_manifest_path, manifest)
        raise typer.Exit(code=2) from exc

    try:
        day = today_utc()
        artifacts = build_artifact_paths(data_dir, day)
        manifest.artifacts = artifacts

        log_step("Live evidence refresh configuration")
        print(f"mode={'dry-run' if dry_run else 'execute'}")
        print(f"duration_minutes={duration_minutes}")
        print(f"metadata_interval_seconds={metadata_interval_seconds}")
        print(f"force={str(force).lower()}")
        print(f"run_id={effective_run_id}")
        print(f"manifest_path={effective_manifest_path}")
        print(f"data_dir={data_dir}")

        def preflight() -> None:
            log_step("Preflight: command availability")
            for name in ("uv",):
                if not shutil_which(name):
                    raise PreflightError(f"Required command not found: {name}")

            outside_symbols: list[str] = []
            for symbol in ("QQQ", "SPY", "XAU"):
                window = market_session_window("trade_xyz", symbol)
                log_step(f"Preflight: next live window {symbol}")
                print(f"symbol={window.symbol}")
                print(f"now_jst={window.now_jst.isoformat()}")
                print(f"recommended_start_jst={window.recommended_start_jst.isoformat()}")
                print(f"recommended_end_jst={window.recommended_end_jst.isoformat()}")
                if (
                    window.now_jst < window.recommended_start_jst
                    or window.now_jst > window.recommended_end_jst
                ):
                    outside_symbols.append(symbol)
            if outside_symbols and not force and not dry_run:
                raise PreflightError(
                    "Current time is outside recommended Trade[XYZ] live window for: "
                    + " ".join(outside_symbols)
                    + ". Use --force to collect anyway."
                )
            if outside_symbols and force:
                log_step("Continuing outside recommended window because --force was set")
                print(f"outside_window_symbols={' '.join(outside_symbols)}")
            elif outside_symbols and dry_run:
                log_step("Dry run: outside recommended window; collection would require --force")
                print(f"outside_window_symbols={' '.join(outside_symbols)}")

        import shutil

        def shutil_which(name: str) -> str | None:
            return shutil.which(name)

        try:
            run_with_manifest_step(
                manifest,
                effective_manifest_path,
                "preflight",
                max_step_retries=0,
                func=preflight,
            )
        except PermanentStepError as exc:
            manifest.status = RunOutcome.FAILED_PREFLIGHT
            manifest.failure_summary = str(exc)
            manifest.finished_at_utc = utc_now()
            write_manifest(effective_manifest_path, manifest)
            raise

        if dry_run:
            manifest.status = RunOutcome.COMPLETED
            manifest.finished_at_utc = utc_now()
            write_manifest(effective_manifest_path, manifest)
            log_step("Dry run complete")
            print("No data collection performed.")
            return

    finally:
        try:
            if (
                should_write_reports
                and effective_manifest_path.exists()
                and terminal_outcome(load_manifest(effective_manifest_path).status)
            ):
                write_reports_for_manifest(
                    effective_manifest_path, settle_seconds=report_settle_seconds
                )
        finally:
            lock.release()

    if manifest.status in {
        RunOutcome.FAILED_PREFLIGHT,
        RunOutcome.FAILED_COLLECTION,
        RunOutcome.PARTIAL_FAILED,
    }:
        raise typer.Exit(code=2)
