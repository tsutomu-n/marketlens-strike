from __future__ import annotations

from sis.backtest.artifact_io import sha256_file
from sis.strategy_idea_candidates.models import StrategyIdeaCandidateSet
from sis.strategy_idea_candidates.service import write_strategy_idea_candidate_set

from .fixtures import valid_candidate_set_payload


def test_candidate_set_writer_is_deterministic(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    candidate_set = StrategyIdeaCandidateSet.model_validate(valid_candidate_set_payload())

    first = write_strategy_idea_candidate_set(
        candidate_set=candidate_set,
        out_dir=tmp_path / "data/strategy_idea_candidates/run-a",
    )
    second = write_strategy_idea_candidate_set(
        candidate_set=candidate_set,
        out_dir=tmp_path / "data/strategy_idea_candidates/run-b",
    )

    assert first.candidate_set_path.read_text(
        encoding="utf-8"
    ) == second.candidate_set_path.read_text(encoding="utf-8")
    assert first.report_path.read_text(encoding="utf-8") == second.report_path.read_text(
        encoding="utf-8"
    )
    assert sha256_file(first.candidate_set_path) == sha256_file(second.candidate_set_path)
    assert "success_only_reporting: `false`" in first.report_path.read_text(encoding="utf-8")
    assert "paper / live 実行許可ではありません" in first.report_path.read_text(encoding="utf-8")
