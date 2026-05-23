from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

import typer
from filelock import FileLock, Timeout
from pydantic import BaseModel, Field
from tenacity import Retrying, retry_if_exception_type, stop_after_attempt, wait_chain, wait_fixed

from sis.market_calendar import market_session_window
from sis.reports.live_evidence_report import (
    default_followup_output_path,
    default_html_output_path,
    default_markdown_output_path,
    render_live_evidence_followup,
    render_live_evidence_html,
    render_live_evidence_report,
)
from sis.reports.quote_diagnostics import build_quote_diagnostics
from sis.settings import get_settings
from sis.storage.jsonl_store import read_json

app = typer.Typer(no_args_is_help=True)


class CollectionGateResult(str, Enum):
    PASS = "pass"
    RETRYABLE_LOW_VOLUME = "retryable_low_volume"
    HARD_FAIL = "hard_fail"


class StepOutcome(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_RETRIES = "completed_with_retries"
    FAILED = "failed"
    SKIPPED = "skipped"


class RunOutcome(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_RETRIES = "completed_with_retries"
    PARTIAL_FAILED = "partial_failed"
    FAILED_PREFLIGHT = "failed_preflight"
    FAILED_COLLECTION = "failed_collection"


TERMINAL_RUN_OUTCOMES = {
    RunOutcome.COMPLETED,
    RunOutcome.COMPLETED_WITH_RETRIES,
    RunOutcome.PARTIAL_FAILED,
    RunOutcome.FAILED_PREFLIGHT,
    RunOutcome.FAILED_COLLECTION,
}


class StepRecord(BaseModel):
    name: str
    status: StepOutcome = StepOutcome.PENDING
    attempt_count: int = 0
    started_at_utc: str | None = None
    ended_at_utc: str | None = None
    error_summary: str | None = None
    command: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class LiveEvidenceManifest(BaseModel):
    run_id: str
    status: RunOutcome = RunOutcome.RUNNING
    requested_schedule_jst: str | None = None
    log_path: str | None = None
    manifest_path: str | None = None
    started_at_utc: str | None = None
    finished_at_utc: str | None = None
    duration_minutes: int
    metadata_interval_seconds: int
    force: bool = False
    data_dir: str = "data"
    step_order: list[str] = Field(default_factory=list)
    steps: list[StepRecord] = Field(default_factory=list)
    row_counts: dict[str, int] = Field(default_factory=dict)
    artifacts: dict[str, str | None] = Field(default_factory=dict)
    diagnostics: list[dict] = Field(default_factory=list)
    decision: str | None = None
    blockers: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    failure_summary: str | None = None


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
    if not path.exists():
        return 0
    with path.open(encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


def expected_metadata_rows(duration_minutes: int, metadata_interval_seconds: int) -> int:
    snapshots = max(1, (duration_minutes * 60) // metadata_interval_seconds)
    return max(1, (snapshots * 8 + 9) // 10)


def evaluate_collection_volume(
    *,
    metadata_rows_delta: int,
    pricing_rows_delta: int,
    min_metadata_rows: int,
) -> CollectionGateResult:
    if pricing_rows_delta <= 0 or metadata_rows_delta <= 0:
        return CollectionGateResult.HARD_FAIL
    if metadata_rows_delta < min_metadata_rows:
        return CollectionGateResult.RETRYABLE_LOW_VOLUME
    return CollectionGateResult.PASS


def default_manifest_path(run_id: str) -> Path:
    return Path("logs/live_evidence/manifests") / f"live_evidence_{run_id}.json"


def load_manifest(path: Path) -> LiveEvidenceManifest:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return LiveEvidenceManifest.model_validate(payload)


def write_manifest(path: Path, manifest: LiveEvidenceManifest) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(manifest.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(path)


def step_for(manifest: LiveEvidenceManifest, name: str) -> StepRecord:
    for step in manifest.steps:
        if step.name == name:
            return step
    step = StepRecord(name=name)
    manifest.steps.append(step)
    if name not in manifest.step_order:
        manifest.step_order.append(name)
    return step


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


def latest_evidence_card_path(data_dir: Path) -> Path | None:
    paths = sorted((data_dir / "evidence").glob("evidence_card_*.json"))
    return paths[-1] if paths else None


def quote_diagnostics_payload(data_dir: Path) -> list[dict]:
    diagnostics = build_quote_diagnostics(
        data_dir / "raw/quotes",
        venue="gtrade",
        stale_thresholds_ms={"gtrade": 3000, "ostium": 5000},
    )
    return [item.__dict__.copy() for item in diagnostics]


def terminal_outcome(status: str | RunOutcome) -> bool:
    try:
        outcome = RunOutcome(status)
    except ValueError:
        return False
    return outcome in TERMINAL_RUN_OUTCOMES


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
        step.status = StepOutcome.COMPLETED_WITH_RETRIES if step.attempt_count > 1 else StepOutcome.COMPLETED
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


def build_artifact_paths(data_dir: Path, day: str) -> dict[str, str | None]:
    evidence_path = latest_evidence_card_path(data_dir)
    return {
        "sidecar_metadata": str(data_dir / f"raw/sidecar/gtrade/{day}.jsonl"),
        "sidecar_pricing": str(data_dir / f"raw/sidecar/gtrade-pricing/{day}.jsonl"),
        "raw_quotes": str(data_dir / f"raw/quotes/gtrade/{day}.jsonl"),
        "normalized_quotes": str(data_dir / "normalized/quotes.parquet"),
        "cost_matrix": str(data_dir / "research/venue_cost_matrix.csv"),
        "backtest_metrics": str(data_dir / "research/backtest_metrics.json"),
        "go_no_go_report": str(data_dir / "research/go_no_go_report.md"),
        "evidence_card": str(evidence_path) if evidence_path else None,
    }


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

    data = build_live_evidence_report_data(
        data_dir=Path(manifest.data_dir),
        log_path=log_path,
        output_path=markdown_output_path,
        manifest_path=manifest_path,
        status=manifest.status.value,
    )
    markdown_output_path.parent.mkdir(parents=True, exist_ok=True)
    html_output_path.parent.mkdir(parents=True, exist_ok=True)
    followup_output_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_output_path.write_text(render_live_evidence_report(data), encoding="utf-8")
    html_output_path.write_text(render_live_evidence_html(data), encoding="utf-8")
    followup_output_path.write_text(render_live_evidence_followup(data), encoding="utf-8")
    print(f"written_markdown: {markdown_output_path}")
    print(f"written_html: {html_output_path}")
    print(f"written_followup: {followup_output_path}")


@app.command()
def main(
    duration_minutes: int = typer.Option(120, "--duration-minutes", min=1),
    metadata_interval_seconds: int = typer.Option(60, "--metadata-interval-seconds", min=1),
    dry_run: bool = typer.Option(False, "--dry-run"),
    force: bool = typer.Option(False, "--force"),
    max_step_retries: int = typer.Option(2, "--max-step-retries", min=0),
    retry_collect_extension_minutes: int = typer.Option(10, "--retry-collect-extension-minutes", min=1),
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
        metadata_path = Path(artifacts["sidecar_metadata"])
        pricing_path = Path(artifacts["sidecar_pricing"])
        quote_path = Path(artifacts["raw_quotes"])
        min_metadata_rows = expected_metadata_rows(duration_minutes, metadata_interval_seconds)

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
            for name in ("uv", "bun"):
                if not shutil_which(name):
                    raise PreflightError(f"Required command not found: {name}")

            outside_symbols: list[str] = []
            for symbol in ("QQQ", "SPY", "XAU"):
                window = market_session_window("gtrade", symbol)
                log_step(f"Preflight: next live window {symbol}")
                print(f"symbol={window.symbol}")
                print(f"now_jst={window.now_jst.isoformat()}")
                print(f"recommended_start_jst={window.recommended_start_jst.isoformat()}")
                print(f"recommended_end_jst={window.recommended_end_jst.isoformat()}")
                if window.now_jst < window.recommended_start_jst or window.now_jst > window.recommended_end_jst:
                    outside_symbols.append(symbol)
            if outside_symbols and not force and not dry_run:
                raise PreflightError(
                    "Current time is outside recommended gTrade live window for: "
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

        metadata_rows_before = row_count(metadata_path)
        pricing_rows_before = row_count(pricing_path)

        def collect_window_for(minutes: int) -> None:
            command = [
                "bun",
                "run",
                "gtrade:collect-window",
                "--",
                "--duration-minutes",
                str(minutes),
                "--metadata-interval-seconds",
                str(metadata_interval_seconds),
            ]
            run_subprocess(command, retryable=True)

        def collect() -> None:
            log_step(
                f"Collecting gTrade window: duration={duration_minutes}min metadata_interval={metadata_interval_seconds}s"
            )
            collect_window_for(duration_minutes)
            metadata_rows_after = row_count(metadata_path)
            pricing_rows_after = row_count(pricing_path)
            metadata_rows_delta = metadata_rows_after - metadata_rows_before
            pricing_rows_delta = pricing_rows_after - pricing_rows_before
            manifest.row_counts.update(
                {
                    "metadata_rows_before": metadata_rows_before,
                    "metadata_rows_after": metadata_rows_after,
                    "metadata_rows_delta": metadata_rows_delta,
                    "metadata_rows_required": min_metadata_rows,
                    "pricing_rows_before": pricing_rows_before,
                    "pricing_rows_after": pricing_rows_after,
                    "pricing_rows_delta": pricing_rows_delta,
                }
            )
            write_manifest(effective_manifest_path, manifest)
            gate = evaluate_collection_volume(
                metadata_rows_delta=metadata_rows_delta,
                pricing_rows_delta=pricing_rows_delta,
                min_metadata_rows=min_metadata_rows,
            )
            log_step("Checking collected sidecar rows")
            for key in (
                "metadata_rows_before",
                "metadata_rows_after",
                "metadata_rows_delta",
                "metadata_rows_required",
                "pricing_rows_before",
                "pricing_rows_after",
                "pricing_rows_delta",
            ):
                print(f"{key}={manifest.row_counts[key]}")
            if gate == CollectionGateResult.PASS:
                return
            if gate == CollectionGateResult.RETRYABLE_LOW_VOLUME:
                log_step(
                    "Collected volume is low but usable; extending collection once before deciding final status"
                )
                collect_window_for(retry_collect_extension_minutes)
                metadata_rows_final = row_count(metadata_path)
                pricing_rows_final = row_count(pricing_path)
                metadata_rows_delta_final = metadata_rows_final - metadata_rows_before
                pricing_rows_delta_final = pricing_rows_final - pricing_rows_before
                manifest.row_counts.update(
                    {
                        "metadata_rows_after": metadata_rows_final,
                        "metadata_rows_delta": metadata_rows_delta_final,
                        "pricing_rows_after": pricing_rows_final,
                        "pricing_rows_delta": pricing_rows_delta_final,
                    }
                )
                write_manifest(effective_manifest_path, manifest)
                gate_after_extension = evaluate_collection_volume(
                    metadata_rows_delta=metadata_rows_delta_final,
                    pricing_rows_delta=pricing_rows_delta_final,
                    min_metadata_rows=min_metadata_rows,
                )
                if gate_after_extension == CollectionGateResult.PASS:
                    return
                raise CollectionVolumeError(
                    "Collection volume remained below threshold after extension."
                )
            raise CollectionFailure("Insufficient gTrade pricing or metadata rows.")

        try:
            run_with_manifest_step(
                manifest,
                effective_manifest_path,
                "collect",
                max_step_retries=max_step_retries,
                command=[
                    "bun",
                    "run",
                    "gtrade:collect-window",
                    "--",
                    "--duration-minutes",
                    str(duration_minutes),
                    "--metadata-interval-seconds",
                    str(metadata_interval_seconds),
                ],
                func=collect,
            )
        except RetryableStepError as exc:
            manifest.status = RunOutcome.FAILED_COLLECTION
            manifest.failure_summary = str(exc)
            manifest.finished_at_utc = utc_now()
            write_manifest(effective_manifest_path, manifest)
            raise
        except PermanentStepError as exc:
            manifest.status = RunOutcome.FAILED_COLLECTION
            manifest.failure_summary = str(exc)
            manifest.finished_at_utc = utc_now()
            write_manifest(effective_manifest_path, manifest)
            raise

        def quote_regen() -> None:
            log_step("Rebuilding quote evidence")
            run_subprocess(["uv", "run", "sis", "log-quotes", "--venue", "gtrade", "--replace"], retryable=True)
            quote_rows = row_count(quote_path)
            manifest.row_counts["raw_quotes"] = quote_rows
            write_manifest(effective_manifest_path, manifest)
            print(f"quote_path={quote_path}")
            print(f"quote_rows={quote_rows}")
            if quote_rows <= 0:
                raise PermanentStepError(f"Insufficient gTrade quote rows. Expected > 0 rows, got {quote_rows}.")

        downstream_commands: list[tuple[str, list[str], bool]] = [
            ("quote_regen", ["uv", "run", "sis", "log-quotes", "--venue", "gtrade", "--replace"], True),
            ("normalize", ["uv", "run", "sis", "normalize-quotes"], True),
            ("build_cost_matrix", ["uv", "run", "sis", "build-cost-matrix"], True),
            ("build_backtest", ["uv", "run", "sis", "build-backtest"], True),
            ("check_go_no_go", ["uv", "run", "sis", "check-go-no-go"], False),
            ("build_evidence_card", ["uv", "run", "sis", "build-evidence-card"], True),
            ("validate_artifacts", ["uv", "run", "sis", "validate-artifacts", "--strict"], True),
        ]

        downstream_failed = False
        failed_step_name: str | None = None

        try:
            run_with_manifest_step(
                manifest,
                effective_manifest_path,
                "quote_regen",
                max_step_retries=max_step_retries,
                command=downstream_commands[0][1],
                func=quote_regen,
            )

            for step_name, command, retryable in downstream_commands[1:3]:
                run_with_manifest_step(
                    manifest,
                    effective_manifest_path,
                    step_name,
                    max_step_retries=max_step_retries,
                    command=command,
                    func=lambda command=command, retryable=retryable: run_subprocess(command, retryable=retryable),
                )

            def diagnostics_step() -> None:
                diagnostics: list[dict] = []
                for symbol in ("QQQ", "SPY", "XAU"):
                    log_step(f"Diagnostics: {symbol}")
                    output = command_output(
                        ["uv", "run", "sis", "diagnose-quotes", "--venue", "gtrade", "--symbol", symbol]
                    )
                    values = parse_key_values(output)
                    values["symbol"] = symbol
                    diagnostics.append(values)
                manifest.diagnostics = diagnostics
                write_manifest(effective_manifest_path, manifest)

            run_with_manifest_step(
                manifest,
                effective_manifest_path,
                "diagnostics",
                max_step_retries=0,
                func=diagnostics_step,
            )

            for step_name, command, retryable in downstream_commands[3:]:
                def do_run(command=command, retryable=retryable, step_name=step_name) -> None:
                    if step_name == "check_go_no_go":
                        output = command_output(command)
                        decision = output.strip().splitlines()[-1] if output.strip() else None
                        manifest.decision = decision
                        write_manifest(effective_manifest_path, manifest)
                        return
                    run_subprocess(command, retryable=retryable)
                    if step_name == "build_evidence_card":
                        manifest.artifacts = build_artifact_paths(data_dir, day)
                        evidence_path = manifest.artifacts.get("evidence_card")
                        if evidence_path:
                            payload = read_json(Path(evidence_path))
                            if isinstance(payload, dict):
                                manifest.decision = payload.get("decision") or manifest.decision
                                manifest.blockers = list(payload.get("blockers", []))
                                manifest.next_actions = list(payload.get("next_actions", []))
                        write_manifest(effective_manifest_path, manifest)

                run_with_manifest_step(
                    manifest,
                    effective_manifest_path,
                    step_name,
                    max_step_retries=max_step_retries if retryable else 0,
                    command=command,
                    func=do_run,
                )
        except PermanentStepError as exc:
            downstream_failed = True
            failed_step_name = next(
                (step.name for step in manifest.steps if step.status == StepOutcome.FAILED),
                None,
            )
            manifest.failure_summary = str(exc)
        except RetryableStepError as exc:
            downstream_failed = True
            failed_step_name = next(
                (step.name for step in manifest.steps if step.status == StepOutcome.FAILED),
                None,
            )
            manifest.failure_summary = str(exc)

        manifest.row_counts.update(
            {
                "sidecar_metadata": row_count(Path(manifest.artifacts["sidecar_metadata"])),
                "sidecar_pricing": row_count(Path(manifest.artifacts["sidecar_pricing"])),
                "raw_quotes": row_count(Path(manifest.artifacts["raw_quotes"])),
            }
        )
        if not manifest.diagnostics:
            manifest.diagnostics = quote_diagnostics_payload(data_dir)
        if not manifest.artifacts.get("evidence_card"):
            manifest.artifacts = build_artifact_paths(data_dir, day)
        evidence_path = manifest.artifacts.get("evidence_card")
        if evidence_path:
            payload = read_json(Path(evidence_path))
            if isinstance(payload, dict):
                manifest.decision = payload.get("decision") or manifest.decision
                manifest.blockers = list(payload.get("blockers", []))
                manifest.next_actions = list(payload.get("next_actions", []))

        used_retries = any(step.attempt_count > 1 for step in manifest.steps)
        if manifest.status not in {RunOutcome.FAILED_PREFLIGHT, RunOutcome.FAILED_COLLECTION}:
            if downstream_failed:
                manifest.status = RunOutcome.PARTIAL_FAILED
                if failed_step_name and not manifest.next_actions:
                    manifest.next_actions = [f"Fix failed step and rerun: {failed_step_name}"]
            else:
                manifest.status = RunOutcome.COMPLETED_WITH_RETRIES if used_retries else RunOutcome.COMPLETED

        manifest.finished_at_utc = utc_now()
        write_manifest(effective_manifest_path, manifest)

        log_step("Live Evidence Refresh Summary")
        for key in ("raw_quotes", "normalized_quotes", "cost_matrix", "backtest_metrics", "go_no_go_report", "evidence_card"):
            print(f"{key}={manifest.artifacts.get(key)}")
        print(f"decision={manifest.decision}")
        print(f"status={manifest.status.value}")
        if manifest.failure_summary:
            print(f"failure_summary={manifest.failure_summary}")

        if manifest.status == RunOutcome.COMPLETED:
            log_step("Live evidence refresh completed")
        elif manifest.status == RunOutcome.COMPLETED_WITH_RETRIES:
            log_step("Live evidence refresh completed with retries")
        else:
            log_step(f"Live evidence refresh finished with status={manifest.status.value}")
    finally:
        try:
            if (
                should_write_reports
                and effective_manifest_path.exists()
                and terminal_outcome(load_manifest(effective_manifest_path).status)
            ):
                write_reports_for_manifest(effective_manifest_path, settle_seconds=report_settle_seconds)
        finally:
            lock.release()

    if manifest.status in {RunOutcome.FAILED_PREFLIGHT, RunOutcome.FAILED_COLLECTION, RunOutcome.PARTIAL_FAILED}:
        raise typer.Exit(code=2)
