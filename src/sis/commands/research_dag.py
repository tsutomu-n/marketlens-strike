from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError
import typer

from sis.research.dag.contracts import CoreDag
from sis.research.dag.counter import (
    CounterDagRegistry,
    load_counter_dag_registry,
    validate_counter_dag_refs,
)
from sis.research.dag.data_requirements import build_data_requirements
from sis.research.dag.errors import CoreDagLintError, CoreDagValidationError
from sis.research.dag.exit_gate import ExitGateError, run_exit_gate
from sis.research.dag.export import export_core_dag_artifacts
from sis.research.dag.linter import DagLintIssue
from sis.research.dag.linter import lint_core_dag, raise_for_lint_errors
from sis.research.dag.loader import load_core_dag
from sis.research.dag.review_import import ReviewImportError, import_review_result
from sis.research.dag.review_pack import ReviewPackPrecheckError, build_review_pack
from sis.research.dag.validator import (
    validate_core_dag,
    validate_core_dag_against_research_context,
)
from sis.research.hypothesis.data_source_contracts import DataSourceRegistry
from sis.research.hypothesis.data_source_loader import load_data_source_registry
from sis.research.hypothesis.role_contracts import CausalRoleRegistry
from sis.research.hypothesis.role_validator import validate_roles_against_inventory
from sis.research.hypothesis.temporal_contracts import TemporalAvailability
from sis.research.hypothesis.variable_contracts import VariableInventory
from sis.research.hypothesis.variable_loader import load_variable_inventory
from sis.research.hypothesis.yaml_io import load_yaml_mapping


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


def register_research_dag_commands(app: typer.Typer) -> None:
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
