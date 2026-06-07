from __future__ import annotations

from pathlib import Path

from research.helpers import CONFIG_DIR
from support.cli import invoke_cli
from support.cli import normalized_stdout


def test_research_dag_validate_cli_accepts_ndx_config() -> None:
    result = invoke_cli(["research-dag-validate", "--config", str(CONFIG_DIR / "core_dag.yaml")])
    stdout = normalized_stdout(result)

    assert result.exit_code == 0
    assert "status=pass" in stdout
    assert "dag_id=HYP-NDX-001" in stdout


def test_research_dag_validate_cli_returns_exit_2_for_invalid_config(tmp_path) -> None:
    config_dir = tmp_path / "cfg"
    config_dir.mkdir()
    invalid_config = config_dir / "invalid_core_dag.yaml"
    invalid_config.write_text(
        "\n".join(
            [
                "schema_version: core_dag.v1",
                "dag_id: BAD",
                "name: bad",
                "scope_id: S",
                "nodes:",
                "  - id: a",
                "    role: confounder",
                "edges:",
                "  - from: missing",
                "    to: a",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = invoke_cli(["research-dag-validate", "--config", str(invalid_config)])

    assert result.exit_code == 2
    assert "status=fail" in normalized_stdout(result)


def test_research_dag_validate_cli_requires_companion_configs(tmp_path) -> None:
    config_dir = tmp_path / "cfg"
    config_dir.mkdir()
    core_config = config_dir / "core_dag.yaml"
    core_config.write_text(
        "\n".join(
            [
                "schema_version: core_dag.v1",
                "dag_id: MISSING-COMPANIONS",
                "name: missing_companions",
                "scope_id: S",
                "nodes:",
                "  - id: a",
                "    role: confounder",
                "edges:",
                "  - from: a",
                "    to: a",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = invoke_cli(["research-dag-validate", "--config", str(core_config)])

    assert result.exit_code == 2
    assert "required companion config missing" in normalized_stdout(result)


def test_research_dag_export_cli_writes_expected_artifacts(tmp_path) -> None:
    out_dir = tmp_path / "data/research/ndx"
    result = invoke_cli(
        [
            "research-dag-export",
            "--config",
            str(CONFIG_DIR / "core_dag.yaml"),
            "--out",
            str(out_dir),
        ]
    )

    assert result.exit_code == 0, result.stdout
    assert (out_dir / "core_dag.json").exists()
    assert (out_dir / "core_dag.mmd").exists()
    assert (out_dir / "data_requirements.yaml").exists()
    assert (Path(tmp_path) / "data/reports/ndx_core_dag_report.md").exists()
