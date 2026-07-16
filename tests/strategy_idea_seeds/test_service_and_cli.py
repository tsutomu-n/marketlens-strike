from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from typer.testing import CliRunner
import yaml

from sis.cli import app
from sis.strategy_idea_seeds.common.ids import sha256_file
from sis.strategy_idea_seeds.common.models import SeedRunManifest, StrategyIdeaSeedSet
from sis.strategy_idea_seeds.service import build_technical_seeds
from sis.strategy_idea_seeds.technical.models import GenerationAttempt, TechnicalPayload
from support.cli import normalized_stdout

from .conftest import MECHANISM_PACK, OPERATOR_CATALOG, REPO_ROOT


runner = CliRunner()
CREATED_AT = datetime(2026, 7, 16, tzinfo=timezone.utc)


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _jsonl(path: Path):
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def _build(fixture_source_root: Path, out: Path, *, created_at=CREATED_AT):
    return build_technical_seeds(
        source_root=fixture_source_root,
        mechanism_pack_path=MECHANISM_PACK,
        operator_catalog_path=OPERATOR_CATALOG,
        out_dir=out,
        created_at=created_at,
    )


def _schema(name: str):
    return _json(REPO_ROOT / "schemas" / name)


def _registry() -> Registry:
    seed_schema = _schema("strategy_idea_seed.v1.schema.json")
    return Registry().with_resource(
        "strategy_idea_seed.v1.schema.json",
        Resource.from_contents(seed_schema),
    )


def test_fixture_e2e_generates_historical_and_data_required_seeds(
    fixture_source_root,
    tmp_path: Path,
) -> None:
    result = _build(fixture_source_root, tmp_path / "run")
    seeds = result.seed_set.seeds
    directions = {seed.profit_intent.direction_hint.value for seed in seeds}
    captures = {seed.profit_intent.capture_archetype.value for seed in seeds}
    readiness = {seed.data_readiness.value for seed in seeds}

    assert {"LONG", "SHORT"} <= directions
    assert {"CONTINUATION", "REVERSAL"} <= captures
    assert {"HISTORICAL_SOURCE", "DATA_REQUIRED"} <= readiness
    assert all(not any(seed.boundary.model_dump().values()) for seed in seeds)
    assert result.manifest.attempt_count == len(_jsonl(result.attempts_path))
    assert result.manifest.seed_count == len(seeds) == len(_jsonl(result.payloads_path))
    assert result.manifest.reason_counts["SEED_MATERIALIZED"] == len(seeds)
    for artifact in result.manifest.artifacts:
        artifact_path = result.manifest_path.parent / artifact.path
        assert artifact_path.exists()
        assert artifact.sha256 == sha256_file(artifact_path)


def test_fixture_and_artifacts_validate_with_pydantic_and_json_schema(
    fixture_source_root,
    tmp_path: Path,
) -> None:
    result = _build(fixture_source_root, tmp_path / "run")
    seed_set_payload = _json(result.seed_set_path)
    manifest_payload = _json(result.manifest_path)
    attempts = _jsonl(result.attempts_path)
    payloads = _jsonl(result.payloads_path)

    StrategyIdeaSeedSet.model_validate(seed_set_payload)
    SeedRunManifest.model_validate(manifest_payload)
    for attempt in attempts:
        GenerationAttempt.model_validate(attempt)
    for payload in payloads:
        TechnicalPayload.model_validate(payload)

    registry = _registry()
    Draft202012Validator(
        _schema("strategy_idea_seed_set.v1.schema.json"),
        registry=registry,
    ).validate(seed_set_payload)
    Draft202012Validator(
        _schema("strategy_idea_seed_run_manifest.v1.schema.json"),
        registry=registry,
    ).validate(manifest_payload)
    attempt_validator = Draft202012Validator(_schema("strategy_idea_seed_attempt.v1.schema.json"))
    payload_validator = Draft202012Validator(
        _schema("strategy_idea_seed_technical_payload.v1.schema.json")
    )
    for attempt in attempts:
        attempt_validator.validate(attempt)
    for payload in payloads:
        payload_validator.validate(payload)


def test_same_fixture_twice_produces_stable_ids_and_meaning(
    fixture_source_root,
    tmp_path: Path,
) -> None:
    first = _build(fixture_source_root, tmp_path / "first", created_at=CREATED_AT)
    second = _build(
        fixture_source_root,
        tmp_path / "second",
        created_at=datetime(2026, 7, 17, tzinfo=timezone.utc),
    )

    assert [seed.seed_record_id for seed in first.seed_set.seeds] == [
        seed.seed_record_id for seed in second.seed_set.seeds
    ]
    assert first.seed_set.semantic_hash == second.seed_set.semantic_hash
    assert {row["technical_exact_signature"] for row in _jsonl(first.payloads_path)} == {
        row["technical_exact_signature"] for row in _jsonl(second.payloads_path)
    }


def test_candidate_backtest_paper_live_artifacts_are_not_generated(
    fixture_source_root,
    tmp_path: Path,
) -> None:
    result = _build(fixture_source_root, tmp_path / "run")
    relative_paths = {
        path.relative_to(result.manifest_path.parent).as_posix()
        for path in result.manifest_path.parent.rglob("*")
        if path.is_file()
    }

    assert relative_paths == {
        "seed_run_manifest.json",
        "source_capabilities.json",
        "technical/technical_attempts.jsonl",
        "technical/technical_payloads.jsonl",
        "review/strategy_idea_seed_set.json",
        "review/strategy_idea_seed_set.md",
    }
    assert not any(
        forbidden in path
        for path in relative_paths
        for forbidden in ("candidate", "backtest", "paper", "live")
    )


def test_public_cli_builds_required_artifacts(fixture_source_root, tmp_path: Path) -> None:
    out = tmp_path / "run"
    result = runner.invoke(
        app,
        [
            "strategy-idea-seeds-technical-build",
            "--source-root",
            str(fixture_source_root),
            "--mechanism-pack",
            str(MECHANISM_PACK),
            "--operator-catalog",
            str(OPERATOR_CATALOG),
            "--out",
            str(out),
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "status=pass" in result.stdout
    assert "attempt_count=" in result.stdout
    assert "seed_count=" in result.stdout
    assert "data_required_count=" in result.stdout
    assert (
        f"seed_set_path={(out / 'review/strategy_idea_seed_set.json').as_posix()}" in result.stdout
    )
    assert (out / "seed_run_manifest.json").exists()


def test_public_cli_help() -> None:
    result = runner.invoke(app, ["strategy-idea-seeds-technical-build", "--help"])
    stdout = normalized_stdout(result)

    assert result.exit_code == 0
    assert "--source-root" in stdout
    assert "--mechanism-pack" in stdout
    assert "--operator-catalog" in stdout


def test_zero_seed_is_successful_and_reasons_are_artifacted(
    fixture_source_root,
    tmp_path: Path,
) -> None:
    payload = yaml.safe_load(MECHANISM_PACK.read_text(encoding="utf-8"))
    payload["mechanisms"] = [payload["mechanisms"][0]]
    payload["mechanisms"][0]["thresholds"] = [
        {"value": "invalid", "value_type": "number", "unit": "ratio"}
    ]
    invalid_pack = tmp_path / "invalid-pack.yaml"
    invalid_pack.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    out = tmp_path / "run"

    result = runner.invoke(
        app,
        [
            "strategy-idea-seeds-technical-build",
            "--source-root",
            str(fixture_source_root),
            "--mechanism-pack",
            str(invalid_pack),
            "--operator-catalog",
            str(OPERATOR_CATALOG),
            "--out",
            str(out),
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "status=pass" in result.stdout
    assert "seed_count=0" in result.stdout
    manifest = _json(out / "seed_run_manifest.json")
    assert manifest["reason_counts"]["INVALID_TYPE"] == manifest["attempt_count"]
    assert _json(out / "review/strategy_idea_seed_set.json")["seeds"] == []


def test_budgeted_run_records_next_cursor(
    fixture_source_root,
    tmp_path: Path,
) -> None:
    payload = yaml.safe_load(MECHANISM_PACK.read_text(encoding="utf-8"))
    payload["attempt_budget"] = 3
    budgeted_pack = tmp_path / "budgeted-pack.yaml"
    budgeted_pack.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    result = build_technical_seeds(
        source_root=fixture_source_root,
        mechanism_pack_path=budgeted_pack,
        operator_catalog_path=OPERATOR_CATALOG,
        out_dir=tmp_path / "run",
        created_at=CREATED_AT,
    )

    assert result.manifest.attempt_count == 16
    assert result.manifest.seed_count == 3
    assert result.manifest.next_cursor == 3
    assert result.manifest.reason_counts["PRUNED_BUDGET"] == 13


def test_seed_domain_does_not_import_candidate_backtest_paper_or_live_packages() -> None:
    source_root = REPO_ROOT / "src/sis/strategy_idea_seeds"
    forbidden = (
        "sis.strategy_idea_candidates",
        "sis.backtest",
        "sis.paper",
        "sis.crypto_perp.live",
    )

    for path in source_root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert not any(value in text for value in forbidden), path
