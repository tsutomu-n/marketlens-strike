from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Literal, cast

import polars as pl
from pydantic import ValidationError
import typer
from loguru import logger

from sis.reports.cost_matrix import build_cost_matrix_from_quotes, build_cost_matrix_report
from sis.research.dag.contracts import CoreDag
from sis.research.dag.counter import (
    CounterDagRegistry,
    load_counter_dag_registry,
    validate_counter_dag_refs,
)
from sis.research.dag.data_requirements import build_data_requirements
from sis.research.dag.errors import CoreDagLintError, CoreDagValidationError
from sis.research.dag.export import export_core_dag_artifacts
from sis.research.dag.linter import DagLintIssue
from sis.research.dag.linter import lint_core_dag, raise_for_lint_errors
from sis.research.dag.loader import load_core_dag
from sis.research.dag.exit_gate import ExitGateError, run_exit_gate
from sis.research.dag.review_import import ReviewImportError, import_review_result
from sis.research.dag.review_pack import ReviewPackPrecheckError, build_review_pack
from sis.research.dag.validator import (
    validate_core_dag,
    validate_core_dag_against_research_context,
)
from sis.research.event_calendar import build_event_calendar
from sis.research.feature_panel import build_feature_panel
from sis.research.ndx.diagnostics import build_ndx_diagnostics
from sis.research.ndx.feature_panel import build_ndx_feature_panel
from sis.research.ndx.residual_model import build_open_gap_residuals
from sis.research.ndx.residual_validation import run_residual_validation_gate
from sis.research.ndx.source_resolution import build_source_resolution
from sis.research.ndx.start_conditions import Layer23StartConditionError
from sis.research.hypothesis.role_contracts import CausalRoleRegistry
from sis.research.hypothesis.role_validator import validate_roles_against_inventory
from sis.research.hypothesis.data_source_contracts import DataSourceRegistry
from sis.research.hypothesis.data_source_loader import load_data_source_registry
from sis.research.hypothesis.temporal_contracts import TemporalAvailability
from sis.research.hypothesis.variable_contracts import VariableInventory
from sis.research.hypothesis.variable_loader import load_variable_inventory
from sis.research.hypothesis.yaml_io import load_yaml_mapping
from sis.research.macro_ingest import build_macro_panel
from sis.research.price_ingest import build_market_panel
from sis.research.providers import FredMacroProvider
from sis.research.research_quality import build_research_quality_report
from sis.research.signal_builder import (
    DEFAULT_GENERATOR_ID,
    build_signals,
    build_signals_from_experiment_spec,
    load_strategy_experiment_spec,
)
from sis.research.strategy_lab.candidates import TradeCandidate
from sis.research.strategy_lab.paper_candidate_pack import PaperCandidatePack
from sis.research.strategy_lab.paper_intent_preview import PaperIntentPreview
from sis.research.strategy_lab.promotion_decision import PromotionDecision
from sis.research.strategy_lab.signal_artifact import (
    StrategySignalManifest,
    read_strategy_signal_manifest,
    require_single_signal_identity,
    run_id_from_pack_id,
    run_id_from_trial_group,
    signal_artifact_run_id,
    strategy_signal_manifest_path,
)
from sis.research.strategy_lab.signal_registry import default_signal_generator_registry
from sis.research.strategy_lab.trial_ledger import TrialLedger, TrialRecord
from sis.real_market.alpaca_smoke import run_alpaca_live_smoke
from sis.settings import get_settings


def _parse_optional_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)


def _required_companion_config(config_path: Path, name: str) -> Path:
    path = config_path.parent / name
    if not path.exists():
        raise FileNotFoundError(f"required companion config missing: {path}")
    return path


def _load_temporal_availability(config_path: Path) -> TemporalAvailability:
    return TemporalAvailability.model_validate(
        load_yaml_mapping(_required_companion_config(config_path, "temporal_availability.yaml"))
    )


def _load_causal_roles(config_path: Path) -> CausalRoleRegistry:
    return CausalRoleRegistry.model_validate(
        load_yaml_mapping(_required_companion_config(config_path, "causal_roles.yaml"))
    )


def _load_data_sources(config_path: Path) -> DataSourceRegistry:
    return load_data_source_registry(_required_companion_config(config_path, "data_sources.yaml"))


def _validate_research_dag_config(
    config_path: Path,
) -> tuple[CoreDag, VariableInventory, CounterDagRegistry, DataSourceRegistry, list[DagLintIssue]]:
    dag = load_core_dag(config_path)
    inventory = load_variable_inventory(
        _required_companion_config(config_path, "variable_inventory.yaml")
    )
    roles = _load_causal_roles(config_path)
    temporal = _load_temporal_availability(config_path)
    counter_dags = load_counter_dag_registry(
        _required_companion_config(config_path, "counter_dags.yaml")
    )
    data_sources = _load_data_sources(config_path)

    validate_roles_against_inventory(roles, inventory)
    validate_core_dag(dag)
    validate_core_dag_against_research_context(
        dag,
        inventory=inventory,
        roles=roles,
        temporal=temporal,
    )
    dag_with_requirements = dag.model_copy(
        update={"data_requirements": build_data_requirements(dag, inventory, data_sources)}
    )
    lint_issues = lint_core_dag(
        dag_with_requirements,
        temporal=temporal,
        data_sources=data_sources,
    )
    raise_for_lint_errors(lint_issues)
    validate_counter_dag_refs(dag, counter_dags)
    return dag, inventory, counter_dags, data_sources, lint_issues


def _report_path_for_dag_export(out_dir: Path) -> Path:
    return out_dir.parent.parent / "reports/ndx_core_dag_report.md"


def _build_signals_or_exit(data_dir: Path, *, generator_id: str) -> Path:
    try:
        return build_signals(data_dir, generator_id=generator_id)
    except KeyError as exc:
        registered = ", ".join(default_signal_generator_registry().registered_ids())
        typer.echo(f"{exc.args[0]}; registered_generator_ids={registered}")
        raise typer.Exit(2) from exc


def _read_signal_manifest(data_dir: Path) -> StrategySignalManifest | None:
    path = strategy_signal_manifest_path(data_dir)
    return read_strategy_signal_manifest(path) if path.exists() else None


def _require_unique_signal_ids(frame: pl.DataFrame) -> None:
    if frame.is_empty():
        return
    if "signal_id" not in frame.columns:
        raise ValueError("Strategy signal artifact missing signal_id column.")
    seen: set[str] = set()
    duplicates: list[str] = []
    for value in frame.get_column("signal_id").to_list():
        signal_id = str(value or "").strip()
        if not signal_id:
            raise ValueError("Strategy signal artifact contains empty signal_id.")
        if signal_id in seen and signal_id not in duplicates:
            duplicates.append(signal_id)
        seen.add(signal_id)
    if duplicates:
        sample = ", ".join(duplicates[:5])
        raise ValueError(f"Strategy signal artifact contains duplicate signal_id values: {sample}")


def _current_signal_context(
    data_dir: Path,
) -> tuple[pl.DataFrame, StrategySignalManifest | None, str]:
    signals_path = data_dir / "research/strategy_signals.parquet"
    if not signals_path.exists():
        raise FileNotFoundError(f"Strategy signal artifact not found: {signals_path}")
    frame = pl.read_parquet(signals_path)
    _require_unique_signal_ids(frame)
    manifest = _read_signal_manifest(data_dir)
    if frame.is_empty():
        if manifest is None:
            raise ValueError(
                "Empty strategy signal artifact requires strategy_signal_manifest.json."
            )
        return frame, manifest, manifest.signal_artifact_run_id
    run_id = signal_artifact_run_id(frame)
    if manifest is not None:
        if manifest.signal_count != frame.height:
            raise ValueError(
                "Strategy signal manifest signal_count does not match artifact: "
                f"{manifest.signal_count} != {frame.height}"
            )
        if manifest.signal_artifact_run_id != run_id:
            raise ValueError(
                "Strategy signal manifest run_id does not match artifact: "
                f"{manifest.signal_artifact_run_id} != {run_id}"
            )
    return frame, manifest, run_id


def _record_run_id(record: TrialRecord) -> str:
    value = record.metrics.get("signal_artifact_run_id")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return run_id_from_trial_group(record.trial_group_id)


def _latest_records_by_trial_id(records: list[TrialRecord]) -> list[TrialRecord]:
    by_id: dict[str, TrialRecord] = {}
    for record in records:
        by_id[record.trial_id] = record
    return sorted(by_id.values(), key=lambda item: (item.trial_index, item.trial_id))


def _scorecard_summary_from_trial_group(data_dir: Path, trial_group_id: str) -> dict[str, Any]:
    ledger = TrialLedger(data_dir / "research/trial_ledger.jsonl")
    records = [record for record in ledger.read_all() if record.trial_group_id == trial_group_id]
    if not records:
        return {}
    latest = _latest_records_by_trial_id(records)[-1]
    scorecard = latest.metrics.get("strategy_scorecard")
    if not isinstance(scorecard, dict):
        return {}
    keys = (
        "schema_version",
        "derived_feature_count",
        "signal_count",
        "side_counts",
        "block_reason_counts",
        "execution_block_reason_counts",
        "exit_reason_counts",
        "passed_thresholds",
        "failed_thresholds",
        "backtest_passed",
        "paper_only",
        "live_order_submitted",
    )
    return {key: scorecard[key] for key in keys if key in scorecard}


def _parse_rank_thresholds(value: str) -> list[float | None]:
    text = value.strip()
    if not text:
        return [None]
    thresholds: list[float | None] = []
    for item in text.split(","):
        candidate = item.strip()
        if not candidate:
            continue
        threshold = float(candidate)
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("rank thresholds must be between 0.0 and 1.0")
        thresholds.append(threshold)
    return thresholds or [None]


def _parameter_hash(
    *,
    run_id: str,
    rank_threshold: float | None,
    candidate_limit: int,
    split_method: str,
    era_unit: str,
) -> str:
    if (
        rank_threshold is None
        and candidate_limit == 1
        and split_method == "single_window"
        and era_unit == "trading_day"
    ):
        return f"generator-default-{run_id}"
    payload = json.dumps(
        {
            "rank_threshold": rank_threshold,
            "candidate_limit": candidate_limit,
            "split_method": split_method,
            "era_unit": era_unit,
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def _trial_id_for_parameters(run_id: str, parameter_hash: str) -> str:
    default_hash = f"generator-default-{run_id}"
    return (
        f"trial-{run_id}" if parameter_hash == default_hash else f"trial-{run_id}-{parameter_hash}"
    )


def _thresholded_signal_frame(frame: pl.DataFrame, rank_threshold: float | None) -> pl.DataFrame:
    if frame.is_empty() or rank_threshold is None:
        return frame
    return frame.filter(pl.col("rank_score").fill_null(-1.0) >= rank_threshold)


def _selected_signal_rows(frame: pl.DataFrame, *, candidate_limit: int) -> list[dict[str, Any]]:
    if frame.is_empty():
        return []
    sorted_frame = frame.sort(["ts_signal", "signal_id"], descending=[True, False])
    if candidate_limit > 0:
        sorted_frame = sorted_frame.head(candidate_limit)
    return sorted_frame.to_dicts()


def _candidate_selection_policy(candidate_limit: int) -> str:
    if candidate_limit == 1:
        return "latest_signal_by_ts"
    if candidate_limit == 0:
        return "all_threshold_passing_by_ts_desc"
    return f"top_{candidate_limit}_signals_by_ts_desc"


def _signal_rows_by_id(frame: pl.DataFrame) -> dict[str, dict[str, Any]]:
    if frame.is_empty():
        return {}
    return {str(row["signal_id"]): row for row in frame.to_dicts()}


def _signal_rows_for_record(frame: pl.DataFrame, record: TrialRecord) -> list[dict[str, Any]]:
    signal_by_id = _signal_rows_by_id(frame)
    selected_ids = record.metrics.get("selected_signal_ids")
    if not isinstance(selected_ids, list):
        fallback = record.metrics.get("selected_signal_id")
        selected_ids = [fallback] if isinstance(fallback, str) and fallback else []
    rows: list[dict[str, Any]] = []
    for signal_id in selected_ids:
        row = signal_by_id.get(str(signal_id))
        if row is not None:
            rows.append(row)
    return rows


def _era_key(value: object, era_unit: str) -> str:
    if isinstance(value, datetime):
        ts = value
    else:
        ts = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    if era_unit in {"session", "trading_day"}:
        return ts.date().isoformat()
    if era_unit == "week":
        year, week, _ = ts.isocalendar()
        return f"{year}-W{week:02d}"
    if era_unit == "month":
        return f"{ts.year:04d}-{ts.month:02d}"
    return ts.date().isoformat()


def _era_signal_counts(frame: pl.DataFrame, era_unit: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    if frame.is_empty():
        return counts
    for row in frame.select("ts_signal").to_dicts():
        key = _era_key(row["ts_signal"], era_unit)
        counts[key] = counts.get(key, 0) + 1
    return counts


def _float_or_none(value: object) -> float | None:
    return float(value) if isinstance(value, int | float) else None


def _tail_bucket_value(
    value: object, *, selected: bool
) -> Literal["top", "middle", "bottom", "none"]:
    fallback = "top" if selected else "none"
    text = str(value or fallback)
    if text in {"top", "middle", "bottom", "none"}:
        return cast(Literal["top", "middle", "bottom", "none"], text)
    return "none"


def register_research_commands(
    app: typer.Typer,
    recommended_read_order_fn: Callable[[Path], list[str]],
) -> None:
    @app.command("research-dag-validate")
    def research_dag_validate_cmd(
        config: Path = typer.Option(
            ...,
            "--config",
            exists=True,
            dir_okay=False,
            help="Core DAG YAML config path.",
        ),
    ) -> None:
        try:
            dag, _, counter_dags, _, lint_issues = _validate_research_dag_config(config)
        except (
            CoreDagValidationError,
            CoreDagLintError,
            FileNotFoundError,
            ValidationError,
            ValueError,
        ) as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        typer.echo("status=pass")
        typer.echo(f"dag_id={dag.dag_id}")
        typer.echo(f"node_count={len(dag.nodes)}")
        typer.echo(f"edge_count={len(dag.edges)}")
        typer.echo(f"counter_dag_count={len(counter_dags.counter_dags)}")
        lint_errors = [issue for issue in lint_issues if issue.severity == "error"]
        typer.echo(f"lint_errors={len(lint_errors)}")
        warnings = [issue for issue in lint_issues if issue.severity == "warning"]
        typer.echo(f"warning_count={len(warnings)}")
        for issue in warnings:
            typer.echo(f"warning={issue.rule_id}:{issue.message}")

    @app.command("research-dag-export")
    def research_dag_export_cmd(
        config: Path = typer.Option(
            ...,
            "--config",
            exists=True,
            dir_okay=False,
            help="Core DAG YAML config path.",
        ),
        out: Path = typer.Option(
            ...,
            "--out",
            file_okay=False,
            help="Output directory for DAG artifacts.",
        ),
    ) -> None:
        try:
            dag, inventory, counter_dags, data_sources, lint_issues = _validate_research_dag_config(
                config
            )
            result = export_core_dag_artifacts(
                dag,
                inventory=inventory,
                counter_dags=counter_dags,
                lint_issues=lint_issues,
                out_dir=out,
                report_path=_report_path_for_dag_export(out),
                data_sources=data_sources,
            )
        except (
            CoreDagValidationError,
            CoreDagLintError,
            FileNotFoundError,
            ValidationError,
            ValueError,
        ) as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        typer.echo("status=pass")
        typer.echo(f"core_dag_json={result.json_path}")
        typer.echo(f"core_dag_mermaid={result.mermaid_path}")
        typer.echo(f"counter_dags_report={result.counter_dags_path}")
        typer.echo(f"data_requirements={result.data_requirements_path}")
        typer.echo(f"report={result.report_path}")

    @app.command("research-layer22-validate")
    def research_layer22_validate_cmd(
        root: Path = typer.Option(
            ...,
            "--root",
            exists=True,
            file_okay=False,
            help="Layer 2.2 research config root directory.",
        ),
    ) -> None:
        research_dag_validate_cmd(root / "core_dag.yaml")

    @app.command("research-layer22-export")
    def research_layer22_export_cmd(
        root: Path = typer.Option(
            ...,
            "--root",
            exists=True,
            file_okay=False,
            help="Layer 2.2 research config root directory.",
        ),
        out: Path = typer.Option(
            ...,
            "--out",
            file_okay=False,
            help="Output directory for DAG artifacts.",
        ),
    ) -> None:
        research_dag_export_cmd(root / "core_dag.yaml", out)

    @app.command("research-layer22-review-pack")
    def research_layer22_review_pack_cmd(
        root: Path = typer.Option(
            ...,
            "--root",
            exists=True,
            file_okay=False,
            help="Layer 2.2 research config root directory.",
        ),
        out: Path = typer.Option(
            ...,
            "--out",
            file_okay=False,
            help="Output directory for manual LLM review pack artifacts.",
        ),
    ) -> None:
        try:
            result = build_review_pack(root=root, out_dir=out)
        except ReviewPackPrecheckError as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(3) from exc
        except (FileNotFoundError, ValidationError, ValueError) as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        typer.echo("status=pass")
        typer.echo(f"pack_hash={result.pack_hash}")
        typer.echo(f"review_pack={result.pack_path}")
        typer.echo(f"review_input={result.input_path}")
        typer.echo(f"review_prompt={result.prompt_path}")

    @app.command("research-layer22-review-import")
    def research_layer22_review_import_cmd(
        pack: Path = typer.Option(
            ...,
            "--pack",
            exists=True,
            dir_okay=False,
            help="llm_review_input.json path.",
        ),
        result: Path = typer.Option(
            ...,
            "--result",
            exists=True,
            dir_okay=False,
            help="Manual LLM review JSON result path.",
        ),
    ) -> None:
        try:
            imported = import_review_result(pack_path=pack, result_path=result)
        except ReviewImportError as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        typer.echo("status=pass")
        typer.echo(f"review_id={imported.review.review_id}")
        typer.echo(f"normalized_review={imported.normalized_path}")
        typer.echo(f"report={imported.report_path}")

    @app.command("research-layer22-exit-gate")
    def research_layer22_exit_gate_cmd(
        root: Path = typer.Option(
            ...,
            "--root",
            exists=True,
            file_okay=False,
            help="Layer 2.2 research config root directory.",
        ),
        pack: Path = typer.Option(
            ...,
            "--pack",
            exists=True,
            dir_okay=False,
            help="llm_review_input.json path.",
        ),
        review: Path = typer.Option(
            ...,
            "--review",
            exists=True,
            dir_okay=False,
            help="normalized_review.json path.",
        ),
        out: Path = typer.Option(
            ...,
            "--out",
            file_okay=False,
            help="Output directory for exit decision artifacts.",
        ),
        human_resolutions: Path | None = typer.Option(
            None,
            "--human-resolutions",
            exists=True,
            dir_okay=False,
            help="Optional layer_2_2_human_resolutions.json path.",
        ),
        require_second_review: bool = typer.Option(
            False,
            "--require-second-review",
            help="Force the exit gate to require a second manual review before approval.",
        ),
    ) -> None:
        try:
            gate = run_exit_gate(
                root=root,
                pack_path=pack,
                review_path=review,
                out_dir=out,
                human_resolutions_path=human_resolutions,
                require_second_review=require_second_review,
            )
        except ExitGateError as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        typer.echo("status=pass")
        typer.echo(f"decision={gate.decision.decision}")
        typer.echo(f"decision_path={gate.decision_path}")
        if gate.freeze_manifest_path is not None:
            typer.echo(f"freeze_manifest={gate.freeze_manifest_path}")
        typer.echo(f"report={gate.report_path}")
        if gate.decision.decision == "REVISE_2_2":
            raise typer.Exit(3)
        if gate.decision.decision == "REJECT_SEED":
            raise typer.Exit(4)

    @app.command("research-ndx-source-resolve")
    def research_ndx_source_resolve_cmd(
        root: Path = typer.Option(
            Path("configs/research_layer_2_2/ndx"),
            "--root",
            exists=True,
            file_okay=False,
            help="Layer 2.2 NDX config root used for start-condition verification.",
        ),
        artifact_dir: Path = typer.Option(
            Path("data/research/ndx"),
            "--artifact-dir",
            file_okay=False,
            help="Layer 2.2 NDX artifact directory.",
        ),
        out: Path = typer.Option(
            Path("data/research/ndx"),
            "--out",
            file_okay=False,
            help="Output directory for NDX Layer 2.3 artifacts.",
        ),
    ) -> None:
        try:
            result = build_source_resolution(root=root, artifact_dir=artifact_dir, out_dir=out)
        except (Layer23StartConditionError, FileNotFoundError, ValueError, ValidationError) as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc
        typer.echo("status=pass")
        typer.echo(f"data_source_resolution={result.artifact_path}")
        typer.echo(f"report={result.report_path}")
        typer.echo(f"resolved_count={result.resolved_count}")
        typer.echo(f"deferred_count={result.deferred_count}")

    @app.command("research-ndx-feature-panel")
    def research_ndx_feature_panel_cmd(
        root: Path = typer.Option(
            Path("configs/research_layer_2_2/ndx"),
            "--root",
            exists=True,
            file_okay=False,
            help="Layer 2.2 NDX config root used for start-condition verification.",
        ),
        artifact_dir: Path = typer.Option(
            Path("data/research/ndx"),
            "--artifact-dir",
            file_okay=False,
            help="Layer 2.2 NDX artifact directory.",
        ),
        input_root: Path = typer.Option(
            ...,
            "--input-root",
            exists=True,
            file_okay=False,
            help="Directory containing fixture-first NDX source CSV files.",
        ),
        out: Path = typer.Option(
            Path("data/research/ndx"),
            "--out",
            file_okay=False,
            help="Output directory for NDX feature panel artifacts.",
        ),
    ) -> None:
        try:
            result = build_ndx_feature_panel(
                root=root,
                artifact_dir=artifact_dir,
                input_root=input_root,
                out_dir=out,
            )
        except (Layer23StartConditionError, FileNotFoundError, ValueError, ValidationError) as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc
        typer.echo("status=pass")
        typer.echo(f"feature_panel={result.panel_path}")
        typer.echo(f"feature_manifest={result.manifest_path}")
        typer.echo(f"report={result.report_path}")
        typer.echo(f"row_count={result.row_count}")

    @app.command("research-ndx-residual")
    def research_ndx_residual_cmd(
        feature_panel: Path = typer.Option(
            ...,
            "--feature-panel",
            exists=True,
            dir_okay=False,
            help="NDX feature panel parquet path.",
        ),
        feature_manifest: Path = typer.Option(
            Path("data/research/ndx/ndx_feature_manifest.json"),
            "--feature-manifest",
            exists=True,
            dir_okay=False,
            help="NDX feature manifest JSON path.",
        ),
        out: Path = typer.Option(
            Path("data/research/ndx"),
            "--out",
            file_okay=False,
            help="Output directory for NDX residual artifacts.",
        ),
        min_window: int = typer.Option(
            6,
            "--min-window",
            min=6,
            help="Minimum strictly prior rows for rolling OLS.",
        ),
    ) -> None:
        try:
            result = build_open_gap_residuals(
                feature_panel_path=feature_panel,
                feature_manifest_path=feature_manifest,
                out_dir=out,
                min_window=min_window,
            )
        except (FileNotFoundError, ValueError, ValidationError) as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc
        typer.echo("status=pass")
        typer.echo(f"open_gap_residuals={result.residuals_path}")
        typer.echo(f"residual_manifest={result.manifest_path}")
        typer.echo(f"report={result.report_path}")
        typer.echo(f"row_count={result.row_count}")

    @app.command("research-ndx-diagnostics")
    def research_ndx_diagnostics_cmd(
        residuals: Path = typer.Option(
            ...,
            "--residuals",
            exists=True,
            dir_okay=False,
            help="NDX open gap residual parquet path.",
        ),
        residual_manifest: Path = typer.Option(
            Path("data/research/ndx/open_gap_residual_manifest.json"),
            "--residual-manifest",
            exists=True,
            dir_okay=False,
            help="NDX open gap residual manifest JSON path.",
        ),
        out: Path = typer.Option(
            Path("data/reports"),
            "--out",
            file_okay=False,
            help="Output directory for NDX diagnostics and pre-reports.",
        ),
    ) -> None:
        try:
            result = build_ndx_diagnostics(
                residuals_path=residuals,
                residual_manifest_path=residual_manifest,
                out_dir=out,
            )
        except (FileNotFoundError, ValueError, ValidationError) as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc
        typer.echo("status=pass")
        typer.echo(f"diagnostics={result.diagnostics_path}")
        typer.echo(f"neutralized_residuals={result.neutralized_path}")
        typer.echo(f"neutralization_report={result.neutralization_report_path}")
        typer.echo(f"refutation_report={result.refutation_report_path}")
        typer.echo(f"row_count={result.row_count}")

    @app.command("research-ndx-residual-validate")
    def research_ndx_residual_validate_cmd(
        root: Path = typer.Option(
            Path("configs/research_layer_2_2/ndx"),
            "--root",
            exists=True,
            file_okay=False,
            help="Layer 2.2 NDX config root used for start-condition verification.",
        ),
        artifact_dir: Path = typer.Option(
            Path("data/research/ndx"),
            "--artifact-dir",
            file_okay=False,
            help="Layer 2.3 NDX artifact directory.",
        ),
        reports_dir: Path = typer.Option(
            Path("data/reports"),
            "--reports-dir",
            file_okay=False,
            help="Directory containing Layer 2.3 NDX diagnostic reports.",
        ),
        out: Path = typer.Option(
            Path("data/research/ndx"),
            "--out",
            file_okay=False,
            help="Output directory for NDX Layer 2.4 residual validation artifacts.",
        ),
    ) -> None:
        try:
            result = run_residual_validation_gate(
                root=root,
                artifact_dir=artifact_dir,
                reports_dir=reports_dir,
                out_dir=out,
            )
        except (FileNotFoundError, ValueError, ValidationError) as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc
        typer.echo("status=pass")
        typer.echo(f"decision={result.decision}")
        typer.echo(f"reason_codes={','.join(result.reason_codes)}")
        typer.echo(f"residual_validation_summary={result.summary_path}")
        typer.echo(f"residual_validation_decision={result.decision_path}")
        typer.echo(f"report={result.report_path}")
        typer.echo(f"counter_dag_refutation_report={result.counter_dag_report_path}")

    @app.command("build-cost-matrix")
    def build_cost_matrix() -> None:
        settings = get_settings()
        out = settings.data_dir / "research/venue_cost_matrix.csv"
        build_cost_matrix_from_quotes(
            settings.data_dir / "normalized/quotes.parquet",
            out,
        )
        build_cost_matrix_report(
            cost_matrix_path=out,
            out_path=settings.data_dir / "reports/venue_cost_matrix.md",
            summary_path=settings.data_dir / "ops/venue_cost_matrix_summary.json",
        )
        logger.info("written: {}", out)
        for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
            typer.echo(f"recommended_read_order_{index}={item}")

    @app.command("ingest-research-data")
    def ingest_research_data() -> None:
        settings = get_settings()
        market_panel = build_market_panel(settings.data_dir)
        macro_provider = (
            FredMacroProvider(api_key=settings.fred_api_key) if settings.fred_api_key else None
        )
        macro_panel = build_macro_panel(settings.data_dir, provider=macro_provider)
        logger.info("written: {}", market_panel)
        logger.info("written: {}", macro_panel)
        for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
            typer.echo(f"recommended_read_order_{index}={item}")

    @app.command("build-event-calendar")
    def build_event_calendar_cmd(
        csv_path: Path | None = typer.Option(
            None,
            "--csv-path",
            help="Optional event calendar CSV path. Defaults to data/research/event_calendar.csv.",
        ),
    ) -> None:
        settings = get_settings()
        out = build_event_calendar(settings.data_dir, csv_path=csv_path)
        logger.info("written: {}", out)
        for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
            typer.echo(f"recommended_read_order_{index}={item}")

    @app.command("build-feature-panel")
    def build_feature_panel_cmd() -> None:
        settings = get_settings()
        out = build_feature_panel(settings.data_dir)
        logger.info("written: {}", out)
        for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
            typer.echo(f"recommended_read_order_{index}={item}")

    @app.command("build-signals")
    def build_signals_cmd(
        generator_id: str = typer.Option(
            DEFAULT_GENERATOR_ID,
            "--generator-id",
            help="Registered Strategy Lab signal generator ID.",
        ),
    ) -> None:
        settings = get_settings()
        out = _build_signals_or_exit(settings.data_dir, generator_id=generator_id)
        logger.info("written: {}", out)
        for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
            typer.echo(f"recommended_read_order_{index}={item}")

    @app.command("strategy-preview")
    def strategy_preview_cmd(
        generator_id: str = typer.Option(
            DEFAULT_GENERATOR_ID,
            "--generator-id",
            help="Registered Strategy Lab signal generator ID.",
        ),
    ) -> None:
        settings = get_settings()
        legacy_path = _build_signals_or_exit(settings.data_dir, generator_id=generator_id)
        report_path = settings.data_dir / "reports/strategy_signals_preview.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            "# Strategy Signals Preview\n\n"
            f"- generator_id: {generator_id}\n"
            f"- canonical_artifact: {settings.data_dir / 'research/strategy_signals.parquet'}\n"
            f"- legacy_export: {legacy_path}\n",
            encoding="utf-8",
        )
        typer.echo(f"legacy_export={legacy_path}")
        typer.echo(f"report_path={report_path}")

    @app.command("strategy-experiment-run")
    def strategy_experiment_run_cmd(
        spec_path: Path = typer.Option(
            ...,
            "--spec",
            help="StrategyExperimentSpec YAML/JSON file to run through the registered generator flow.",
        ),
        max_variants: int = typer.Option(
            64,
            "--max-variants",
            min=1,
            help="Maximum cartesian parameter_grid variants to materialize.",
        ),
    ) -> None:
        settings = get_settings()
        try:
            spec = load_strategy_experiment_spec(spec_path)
            legacy_path = build_signals_from_experiment_spec(
                settings.data_dir,
                spec=spec,
                max_variants=max_variants,
            )
        except KeyError as exc:
            registered = ", ".join(default_signal_generator_registry().registered_ids())
            typer.echo(f"{exc.args[0]}; registered_generator_ids={registered}")
            raise typer.Exit(2) from exc
        except (FileNotFoundError, ValueError, TypeError, ValidationError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(2) from exc
        report_path = settings.data_dir / "reports/strategy_experiment_run.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            "# Strategy Experiment Run\n\n"
            f"- spec_path: {spec_path}\n"
            f"- strategy_id: {spec.strategy_id}\n"
            f"- generator_id: {spec.generator_id}\n"
            f"- max_variants: {max_variants}\n"
            f"- canonical_artifact: {settings.data_dir / 'research/strategy_signals.parquet'}\n"
            f"- legacy_export: {legacy_path}\n"
            "- paper_only: true\n"
            "- live_order_submitted: false\n",
            encoding="utf-8",
        )
        typer.echo(f"legacy_export={legacy_path}")
        typer.echo(f"report_path={report_path}")

    @app.command("evaluate-strategy-lab")
    def evaluate_strategy_lab_cmd(
        rank_thresholds: str = typer.Option(
            "",
            "--rank-thresholds",
            help="Comma-separated rank_score thresholds for paper-only parameter sweep.",
        ),
        candidate_limit: int = typer.Option(
            1,
            "--candidate-limit",
            min=0,
            help="Selected signal limit per trial. Use 0 to select all threshold-passing signals.",
        ),
        split_method: Literal["single_window", "walk_forward", "purged_walk_forward"] = (
            typer.Option(
                "single_window",
                "--split-method",
                help="Paper-only evaluation split metadata.",
            )
        ),
        era_unit: Literal["session", "trading_day", "week", "month"] = typer.Option(
            "trading_day",
            "--era-unit",
            help="Era unit for walk-forward style signal-count metrics.",
        ),
    ) -> None:
        settings = get_settings()
        signals_path = settings.data_dir / "research/strategy_signals.parquet"
        if not signals_path.exists():
            typer.echo(f"Strategy signal artifact not found: {signals_path}")
            raise typer.Exit(2)
        try:
            parsed_thresholds = _parse_rank_thresholds(rank_thresholds)
            frame, manifest, run_id = _current_signal_context(settings.data_dir)
            signal_identity = require_single_signal_identity(frame)
        except (ValueError, TypeError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(2) from exc
        except FileNotFoundError as exc:
            typer.echo(str(exc))
            raise typer.Exit(2) from exc
        if not frame.is_empty():
            metadata = signal_identity
        elif manifest is not None:
            metadata = {
                "strategy_id": manifest.strategy_id,
                "strategy_family": manifest.strategy_family,
                "strategy_version": manifest.strategy_version,
            }
        else:
            typer.echo("Strategy signal manifest not found for empty signal artifact.")
            raise typer.Exit(2)
        records: list[TrialRecord] = []
        for trial_index, rank_threshold in enumerate(parsed_thresholds):
            candidate_frame = _thresholded_signal_frame(frame, rank_threshold)
            selected_rows = _selected_signal_rows(candidate_frame, candidate_limit=candidate_limit)
            selected_signal_ids = [str(row["signal_id"]) for row in selected_rows]
            selected = bool(selected_signal_ids)
            parameter_hash = _parameter_hash(
                run_id=run_id,
                rank_threshold=rank_threshold,
                candidate_limit=candidate_limit,
                split_method=split_method,
                era_unit=era_unit,
            )
            metrics: dict[str, Any] = {
                "signal_count": frame.height,
                "candidate_signal_count": candidate_frame.height,
                "signal_artifact_run_id": run_id,
                "candidate_selection_policy": _candidate_selection_policy(candidate_limit),
                "candidate_limit": candidate_limit,
                "rank_threshold": rank_threshold,
                "split_method": split_method,
                "era_unit": era_unit,
                "era_signal_counts": _era_signal_counts(candidate_frame, era_unit),
            }
            metrics["era_count"] = len(metrics["era_signal_counts"])
            if selected_signal_ids:
                metrics["selected_signal_id"] = selected_signal_ids[0]
                metrics["selected_signal_ids"] = selected_signal_ids
            records.append(
                TrialRecord(
                    schema_version="trial_record.v1",
                    trial_id=_trial_id_for_parameters(run_id, parameter_hash),
                    trial_group_id=f"trial-group-{run_id}",
                    trial_index=trial_index,
                    strategy_id=str(metadata.get("strategy_id")),
                    strategy_family=str(metadata.get("strategy_family")),
                    strategy_version=str(metadata.get("strategy_version")),
                    evaluation_plan_id="initial_walkforward",
                    data_snapshot_id="data-snap-current",
                    feature_snapshot_id="feature-snap-current",
                    parameter_hash=parameter_hash,
                    parameter_count=1,
                    parameter_space_hash="registered-generator-default-space",
                    random_seed=None,
                    git_sha=None,
                    signal_count=frame.height,
                    candidate_count=candidate_frame.height,
                    paper_candidate_count=len(selected_signal_ids),
                    executed_count=0,
                    blocked_count=0,
                    no_signal_count=0 if selected else 1,
                    blocked_reason_counts={},
                    metrics=metrics,
                    baseline_strategy_id=None,
                    baseline_delta_metrics={},
                    selected_for_next_stage=selected,
                    rejection_reasons=[] if selected else ["no_signals"],
                )
            )
        ledger_path = settings.data_dir / "research/trial_ledger.jsonl"
        ledger = TrialLedger(ledger_path)
        existing_trial_ids = {existing.trial_id for existing in ledger.read_all()}
        for record in records:
            if record.trial_id not in existing_trial_ids:
                ledger.append(record)
                existing_trial_ids.add(record.trial_id)
        report_path = settings.data_dir / "reports/strategy_trial_report.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        latest_record = records[-1]
        report_path.write_text(
            "# Strategy Trial Report\n\n"
            f"- trial_group_id: trial-group-{run_id}\n"
            f"- trial_count: {len(records)}\n"
            f"- latest_trial_id: {latest_record.trial_id}\n"
            f"- signal_count: {latest_record.signal_count}\n"
            f"- selected_for_next_stage: {latest_record.selected_for_next_stage}\n",
            encoding="utf-8",
        )
        typer.echo(f"trial_ledger={ledger_path}")
        typer.echo(f"report_path={report_path}")

    @app.command("build-paper-candidate-pack")
    def build_paper_candidate_pack_cmd(
        trial_ledger: Path | None = typer.Option(None, "--trial-ledger"),
        trial_group_id: str | None = typer.Option(
            None,
            "--trial-group-id",
            help="Optional trial_group_id. Defaults to the latest group in the ledger.",
        ),
    ) -> None:
        settings = get_settings()
        ledger_path = trial_ledger or (settings.data_dir / "research/trial_ledger.jsonl")
        records = TrialLedger(ledger_path).read_all()
        if not records:
            typer.echo(f"Trial ledger has no records: {ledger_path}")
            raise typer.Exit(2)
        selected_group_id = trial_group_id or records[-1].trial_group_id
        group_records = [record for record in records if record.trial_group_id == selected_group_id]
        if not group_records:
            typer.echo(f"Trial group not found in ledger: {selected_group_id}")
            raise typer.Exit(2)
        records_for_pack = _latest_records_by_trial_id(group_records)
        try:
            signal_frame, signal_manifest, current_run_id = _current_signal_context(
                settings.data_dir
            )
        except (FileNotFoundError, ValueError) as exc:
            signal_frame = pl.DataFrame()
            signal_manifest = _read_signal_manifest(settings.data_dir)
            current_run_id = signal_manifest.signal_artifact_run_id if signal_manifest else ""
            if any(record.selected_for_next_stage for record in records_for_pack):
                typer.echo(str(exc))
                raise typer.Exit(2) from exc
        now = datetime.now(timezone.utc)
        candidates: list[TradeCandidate] = []
        selected_ids: list[str] = []
        rejected_ids: list[str] = []
        for record in records_for_pack:
            if record.selected_for_next_stage:
                record_run_id = _record_run_id(record)
                if record_run_id != current_run_id:
                    typer.echo(
                        "Trial run_id does not match current strategy signal artifact: "
                        f"{record_run_id} != {current_run_id}"
                    )
                    raise typer.Exit(2)
                selected_signal_rows = _signal_rows_for_record(signal_frame, record)
                if not selected_signal_rows:
                    typer.echo(
                        f"Selected trial has no matching selected signals: {record.trial_id}"
                    )
                    raise typer.Exit(2)
            else:
                selected_signal_rows = [{}]
            for signal in selected_signal_rows:
                status = "candidate" if record.selected_for_next_stage else "blocked"
                if record.selected_for_next_stage:
                    signal_id = str(signal.get("signal_id") or "")
                    candidate_id = f"candidate-{record.trial_id}-{signal_id}"
                else:
                    signal_id = None
                    candidate_id = f"candidate-{record.trial_id}-no-signal"
                    if "no_signals" in record.rejection_reasons:
                        status = "no_signal"
                side = str(
                    signal.get("side") or ("long" if record.selected_for_next_stage else "none")
                )
                if side not in {"long", "short"}:
                    side = "none"
                candidate_side = cast(Literal["long", "short", "none"], side)
                reason_codes = list(signal.get("reason_codes") or [])
                if record.selected_for_next_stage and not reason_codes:
                    reason_codes = ["trial_selected"]
                if signal:
                    execution_symbol = str(signal.get("execution_symbol") or "XYZ100")
                    real_market_symbol = str(signal.get("real_market_symbol") or "QQQ")
                    execution_venue = signal.get("execution_venue") or "trade_xyz"
                    timeframe = str(signal.get("timeframe") or "4h")
                    feature_snapshot_ref = (
                        signal.get("feature_snapshot_ref") or record.feature_snapshot_id
                    )
                elif signal_manifest is not None:
                    binding = signal_manifest.symbol_bindings[0]
                    execution_symbol = binding.execution_symbol
                    real_market_symbol = binding.real_market_symbol
                    execution_venue = binding.execution_venue
                    timeframe = "4h"
                    feature_snapshot_ref = record.feature_snapshot_id
                else:
                    typer.echo(
                        "Strategy signal manifest not found for blocked/no-signal candidate."
                    )
                    raise typer.Exit(2)
                candidates.append(
                    TradeCandidate(
                        schema_version="trade_candidate.v1",
                        candidate_id=candidate_id,
                        generated_at=now,
                        signal_id=signal_id,
                        strategy_id=record.strategy_id,
                        trial_id=record.trial_id,
                        execution_venue=execution_venue,
                        execution_symbol=execution_symbol,
                        real_market_symbol=real_market_symbol,
                        side=candidate_side,
                        timeframe=timeframe,
                        status=status,
                        raw_score=_float_or_none(signal.get("raw_score")),
                        rank_score=_float_or_none(signal.get("rank_score"))
                        if record.selected_for_next_stage
                        else None,
                        percentile_rank=_float_or_none(signal.get("percentile_rank"))
                        if record.selected_for_next_stage
                        else None,
                        tail_bucket=_tail_bucket_value(
                            signal.get("tail_bucket"), selected=record.selected_for_next_stage
                        ),
                        confidence=(_float_or_none(signal.get("confidence")) or 0.8)
                        if record.selected_for_next_stage
                        else 0.0,
                        entry_reason_codes=reason_codes if record.selected_for_next_stage else [],
                        block_reasons=[]
                        if record.selected_for_next_stage
                        else record.rejection_reasons,
                        feature_snapshot_ref=feature_snapshot_ref,
                        quote_ref=signal.get("quote_ref"),
                        tracking_ref=signal.get("tracking_ref"),
                    )
                )
                (selected_ids if record.selected_for_next_stage else rejected_ids).append(
                    candidate_id
                )
        pack_run_id = run_id_from_trial_group(selected_group_id)
        pack = PaperCandidatePack(
            schema_version="paper_candidate_pack.v1",
            pack_id=f"paper-pack-{pack_run_id}",
            generated_at=now,
            evaluation_plan_id=records_for_pack[-1].evaluation_plan_id,
            data_snapshot_id=records_for_pack[-1].data_snapshot_id,
            feature_snapshot_id=records_for_pack[-1].feature_snapshot_id,
            trial_group_id=selected_group_id,
            candidates=candidates,
            selected_candidate_ids=selected_ids,
            rejected_candidate_ids=rejected_ids,
            selection_policy={
                "selected_for_next_stage": True,
                "trial_group_id": selected_group_id,
                "candidate_selection_policy": "selected_signal_ids",
            },
            reason_codes=["from_trial_ledger"],
            block_reasons=[],
        )
        out = settings.data_dir / "research/paper_candidate_pack.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(pack.model_dump_json(indent=2), encoding="utf-8")
        report_path = settings.data_dir / "reports/paper_candidate_pack.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            "# Paper Candidate Pack\n\n"
            f"- candidates: {len(candidates)}\n"
            f"- selected: {len(selected_ids)}\n",
            encoding="utf-8",
        )
        typer.echo(f"paper_candidate_pack={out}")

    @app.command("promotion-decision")
    def promotion_decision_cmd(
        source_pack: Path | None = typer.Option(None, "--source-pack"),
        decision: str = typer.Option("hold", "--decision"),
    ) -> None:
        settings = get_settings()
        if decision not in {"promote", "reject", "hold"}:
            typer.echo("decision must be one of: promote, reject, hold")
            raise typer.Exit(2)
        promotion_value = cast(Literal["promote", "reject", "hold"], decision)
        pack_path = source_pack or (settings.data_dir / "research/paper_candidate_pack.json")
        required = ["trial_ledger", "paper_candidate_pack"]
        observed = ["paper_candidate_pack"] if pack_path.exists() else []
        if (settings.data_dir / "research/trial_ledger.jsonl").exists():
            observed.append("trial_ledger")
        if not pack_path.exists():
            typer.echo(f"PaperCandidatePack not found: {pack_path}")
            raise typer.Exit(2)
        pack = PaperCandidatePack.model_validate(json.loads(pack_path.read_text(encoding="utf-8")))
        source_pack_id = pack.pack_id
        promotion_run_id = run_id_from_pack_id(source_pack_id)
        scorecard_summary = (
            _scorecard_summary_from_trial_group(settings.data_dir, pack.trial_group_id)
            if pack.trial_group_id
            else {}
        )
        if scorecard_summary:
            required.append("strategy_scorecard")
            observed.append("strategy_scorecard")
        promotion = PromotionDecision(
            schema_version="promotion_decision.v1",
            promotion_id=f"promotion-{promotion_run_id}",
            generated_at=datetime.now(timezone.utc),
            source_pack_id=source_pack_id,
            reviewer=None,
            from_stage="strategy_lab",
            to_stage="paper_observation",
            decision=promotion_value,
            required_evidence=required,
            observed_evidence=observed,
            approval_reasons=["operator_promoted"] if promotion_value == "promote" else [],
            rejection_reasons=[] if promotion_value == "promote" else ["not_promoted"],
            scorecard_summary=scorecard_summary,
        )
        out = settings.data_dir / "research/promotion_decision.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(promotion.model_dump_json(indent=2), encoding="utf-8")
        report_path = settings.data_dir / "reports/promotion_decision.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            f"# Promotion Decision\n\n- decision: {promotion.decision}\n", encoding="utf-8"
        )
        typer.echo(f"promotion_decision={out}")

    @app.command("build-paper-intent-preview")
    def build_paper_intent_preview_cmd(
        source_pack: Path | None = typer.Option(None, "--source-pack"),
        promotion_decision: Path | None = typer.Option(None, "--promotion-decision"),
    ) -> None:
        settings = get_settings()
        pack_path = source_pack or (settings.data_dir / "research/paper_candidate_pack.json")
        decision_path = promotion_decision or (
            settings.data_dir / "research/promotion_decision.json"
        )
        if not decision_path.exists():
            typer.echo(f"PromotionDecision not found: {decision_path}")
            raise typer.Exit(2)
        if not pack_path.exists():
            typer.echo(f"PaperCandidatePack not found: {pack_path}")
            raise typer.Exit(2)
        pack = PaperCandidatePack.model_validate(json.loads(pack_path.read_text(encoding="utf-8")))
        promotion = PromotionDecision.model_validate(
            json.loads(decision_path.read_text(encoding="utf-8"))
        )
        if promotion.source_pack_id != pack.pack_id:
            typer.echo(
                "PromotionDecision source_pack_id does not match PaperCandidatePack pack_id: "
                f"{promotion.source_pack_id} != {pack.pack_id}"
            )
            raise typer.Exit(2)
        intents: list[PaperIntentPreview] = []
        if promotion.decision == "promote":
            selected = {
                candidate.candidate_id: candidate
                for candidate in pack.candidates
                if candidate.candidate_id in pack.selected_candidate_ids
            }
            for candidate_id, candidate in selected.items():
                intents.append(
                    PaperIntentPreview(
                        schema_version="paper_intent_preview.v1",
                        intent_id=f"intent-{candidate_id}",
                        generated_at=datetime.now(timezone.utc),
                        valid_until=datetime.now(timezone.utc) + timedelta(minutes=15),
                        source_pack_id=pack.pack_id,
                        candidate_id=candidate_id,
                        strategy_id=candidate.strategy_id,
                        execution_venue=candidate.execution_venue,
                        execution_symbol=candidate.execution_symbol,
                        real_market_symbol=candidate.real_market_symbol,
                        action="enter" if candidate.side in {"long", "short"} else "skip",
                        side=candidate.side,
                        order_style="paper_taker" if candidate.side != "none" else "skip",
                        price_reference="mark",
                        notional_usd=1000.0 if candidate.side != "none" else None,
                        quantity=None,
                        source_quote_ts=None,
                        source_tracking_ts=None,
                        source_feature_ts=None,
                        source_phase_gate_run_id=None,
                        scorecard_summary=promotion.scorecard_summary,
                    )
                )
        out = settings.data_dir / "bot/paper_intent_preview.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps([intent.model_dump(mode="json") for intent in intents], indent=2),
            encoding="utf-8",
        )
        report_path = settings.data_dir / "reports/paper_intent_preview.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            "# Paper Intent Preview\n\n"
            f"- intents: {len(intents)}\n"
            f"- scorecard_schema_version: {promotion.scorecard_summary.get('schema_version')}\n",
            encoding="utf-8",
        )
        typer.echo(f"paper_intent_preview={out}")

    @app.command("check-research-quality")
    def check_research_quality_cmd() -> None:
        settings = get_settings()
        out = build_research_quality_report(settings.data_dir)
        logger.info("written: {}", out)
        for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
            typer.echo(f"recommended_read_order_{index}={item}")

    @app.command("alpaca-smoke")
    def alpaca_smoke_cmd(
        symbol: str = typer.Option("NVDA", "--symbol", help="Alpaca stock symbol."),
        timeframe: str = typer.Option("15m", "--timeframe", help="Alpaca bars timeframe."),
        start: str | None = typer.Option(
            None,
            "--start",
            help="Optional ISO start time for historical connectivity smoke.",
        ),
        end: str | None = typer.Option(
            None,
            "--end",
            help="Optional ISO end time for historical connectivity smoke.",
        ),
        limit: int = typer.Option(1, "--limit", min=1, help="Number of bars to request."),
        feed: str = typer.Option("iex", "--feed", help="Alpaca data feed."),
        timeout: float = typer.Option(10.0, "--timeout", min=0.1, help="Request timeout seconds."),
        raw_payload_path: Path | None = typer.Option(
            None,
            "--raw-payload-path",
            help="Optional raw payload output path. Defaults under data/raw/real_market/alpaca.",
        ),
    ) -> None:
        settings = get_settings()
        summary = run_alpaca_live_smoke(
            data_dir=settings.data_dir,
            symbol=symbol,
            timeframe=timeframe,
            start=_parse_optional_datetime(start),
            end=_parse_optional_datetime(end),
            limit=limit,
            feed=feed,
            timeout=timeout,
            raw_payload_path=raw_payload_path,
        )
        typer.echo(f"status={summary['status']}")
        typer.echo(f"provider_connectivity_status={summary['provider_connectivity_status']}")
        typer.echo(f"data_availability_status={summary['data_availability_status']}")
        typer.echo(f"symbol={summary['symbol']}")
        typer.echo(f"timeframe={summary['timeframe']}")
        typer.echo(f"effective_timeframe={summary['effective_timeframe']}")
        typer.echo(f"feed={summary['feed']}")
        typer.echo(f"requested_window={summary['requested_window']}")
        typer.echo(f"request_endpoint={summary['request_endpoint']}")
        typer.echo(f"start={summary['start']}")
        typer.echo(f"end={summary['end']}")
        typer.echo(f"bar_count={summary['bar_count']}")
        typer.echo(f"latest_bar_ts={summary.get('latest_bar_ts')}")
        typer.echo(f"market_session={summary.get('market_session')}")
        typer.echo(f"source_confidence={summary['source_confidence']}")
        typer.echo(f"source_confidence_reason={summary.get('source_confidence_reason')}")
        live_suitability_reasons = summary.get("live_suitability_reasons")
        formatted_reasons = (
            ",".join(str(reason) for reason in live_suitability_reasons)
            if isinstance(live_suitability_reasons, list)
            else ""
        )
        typer.echo(f"live_suitability_reasons={formatted_reasons}")
        typer.echo(f"summary_path={summary['summary_path']}")
        typer.echo(f"report_path={summary['report_path']}")
        typer.echo(f"raw_payload_path={summary['raw_payload_path']}")
        for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
            typer.echo(f"recommended_read_order_{index}={item}")
        if summary.get("status") != "pass":
            typer.echo(f"error_class={summary.get('error_class')}")
            typer.echo(f"error_message={summary.get('error_message')}")
            raise typer.Exit(2)
