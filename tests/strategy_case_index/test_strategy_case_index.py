from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

from sis.strategy_case_index.service import StrategyCaseIndexError, build_strategy_case_index


REPO_ROOT = Path(__file__).resolve().parents[2]


def _schema() -> dict:
    return json.loads(
        (REPO_ROOT / "schemas/strategy_case_index.v1.schema.json").read_text(encoding="utf-8")
    )


def _write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _case_lite(
    tmp_path: Path,
    *,
    strategy_id: str,
    case_id: str,
    updated_at: str,
    latest_status: str,
    open_actions: list[str] | None = None,
    blocked_reasons: list[str] | None = None,
) -> Path:
    return _write_json(
        tmp_path / f"data/strategy_cases/{strategy_id}/{case_id}.json",
        {
            "schema_version": "strategy_case_lite.v1",
            "strategy_id": strategy_id,
            "case_id": case_id,
            "updated_at": updated_at,
            "producer": {"tool": "sis", "command": "strategy-case-lite-update"},
            "source_artifacts": [],
            "timeline": [],
            "summary": {
                "artifact_count": 1,
                "timeline_count": 1,
                "latest_status": latest_status,
                "open_actions": open_actions or [],
                "blocked_reasons": blocked_reasons or [],
                "latest_source_hashes": {},
            },
            "paper_execution_allowed": False,
            "live_allowed": False,
            "boundary": {
                "permits_live_order": False,
                "live_conversion_allowed": False,
                "wallet_used": False,
                "signing_used": False,
                "exchange_write_used": False,
            },
        },
    )


def test_strategy_case_index_builds_from_explicit_cases(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    case_a = _case_lite(
        tmp_path,
        strategy_id="ndx-breakout-001",
        case_id="case-a",
        updated_at="2026-06-22T09:00:00Z",
        latest_status="READY_FOR_HUMAN_REVIEW",
        open_actions=["REVISE_STRATEGY"],
    )
    case_b = _case_lite(
        tmp_path,
        strategy_id="ndx-breakout-002",
        case_id="case-b",
        updated_at="2026-06-22T10:00:00Z",
        latest_status="HOLD",
        blocked_reasons=["manual_review_missing"],
    )

    result = build_strategy_case_index(
        case_paths=[case_b, case_a],
        data_dir=None,
        out_dir=tmp_path / "data/strategy_case_index",
        index_id="index-explicit",
    )

    assert result.index.case_count == 2
    assert result.index.strategy_count == 2
    assert [case.case_id for case in result.index.cases] == ["case-a", "case-b"]
    assert result.index.strategies[1].latest_case_id == "case-b"
    payload = json.loads(result.index_path.read_text(encoding="utf-8"))
    Draft202012Validator(_schema()).validate(payload)
    assert "not a DB registry" in result.report_path.read_text(encoding="utf-8")


def test_strategy_case_index_data_dir_discovers_case_lite_and_ignores_unrelated(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    case = _case_lite(
        tmp_path,
        strategy_id="ndx-breakout-001",
        case_id="case-a",
        updated_at="2026-06-22T09:00:00Z",
        latest_status="READY_FOR_HUMAN_REVIEW",
    )
    _write_json(
        tmp_path / "data/strategy_cases/viewer_manifest.json", {"schema_version": "other.v1"}
    )

    result = build_strategy_case_index(
        case_paths=[],
        data_dir=tmp_path / "data/strategy_cases",
        out_dir=tmp_path / "data/strategy_case_index",
        index_id="index-data-dir",
    )

    assert result.index.case_count == 1
    assert result.index.cases[0].case_path == case.relative_to(tmp_path).as_posix()


def test_strategy_case_index_dedupes_same_path_or_hash(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    case = _case_lite(
        tmp_path,
        strategy_id="ndx-breakout-001",
        case_id="case-a",
        updated_at="2026-06-22T09:00:00Z",
        latest_status="READY_FOR_HUMAN_REVIEW",
    )
    duplicate = tmp_path / "data/strategy_cases/copy/case-a-copy.json"
    duplicate.parent.mkdir(parents=True, exist_ok=True)
    duplicate.write_text(case.read_text(encoding="utf-8"), encoding="utf-8")

    result = build_strategy_case_index(
        case_paths=[case, case, duplicate],
        data_dir=None,
        out_dir=tmp_path / "data/strategy_case_index",
        index_id="index-dedupe",
    )

    assert result.index.case_count == 1
    assert result.index.source_artifacts[0].path == "data/strategy_cases/copy/case-a-copy.json"


def test_strategy_case_index_fails_for_explicit_schema_mismatch(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    wrong = _write_json(tmp_path / "data/strategy_cases/wrong.json", {"schema_version": "other.v1"})

    with pytest.raises(StrategyCaseIndexError, match="expected strategy_case_lite.v1"):
        build_strategy_case_index(
            case_paths=[wrong],
            data_dir=None,
            out_dir=tmp_path / "data/strategy_case_index",
        )


def test_strategy_case_index_fails_when_data_dir_has_no_cases(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _write_json(
        tmp_path / "data/strategy_cases/viewer_manifest.json", {"schema_version": "other.v1"}
    )

    with pytest.raises(StrategyCaseIndexError, match="no strategy_case_lite"):
        build_strategy_case_index(
            case_paths=[],
            data_dir=tmp_path / "data/strategy_cases",
            out_dir=tmp_path / "data/strategy_case_index",
        )
