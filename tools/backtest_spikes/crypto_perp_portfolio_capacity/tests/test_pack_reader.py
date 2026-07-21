from __future__ import annotations

from pathlib import Path

import pytest

from ..pack_reader import (
    CandidatePackError,
    load_candidate_pack,
)

from .fixtures import write_pack


def test_reader_accepts_complete_pack_and_builds_intents(tmp_path: Path) -> None:
    pack = load_candidate_pack(write_pack(tmp_path))

    assert pack.decision.pack_id == "pack-1"
    assert pack.rows.row_set_id == "row-set-1"
    assert len(pack.signals) == 1
    assert pack.outcomes["outcome-1"].horizons[0].reference_price == 100


@pytest.mark.parametrize(
    ("case_id", "kwargs", "expected_code"),
    [
        ("G15", {"missing_action": True}, "MISSING_ACTION_ROW"),
        ("G17", {"notional_mismatch": True}, "ASSUMPTION_MISMATCH"),
        ("G18", {"formula_mismatch": True}, "BEFORE_COST_PROXY_FORMULA_MISMATCH"),
    ],
)
def test_invalid_pack_contracts_fail_closed(
    tmp_path: Path,
    case_id: str,
    kwargs: dict[str, bool],
    expected_code: str,
) -> None:
    with pytest.raises(CandidatePackError, match=expected_code):
        load_candidate_pack(write_pack(tmp_path / case_id, **kwargs))


def test_g16_component_hash_mismatch_fails_closed(tmp_path: Path) -> None:
    pack_dir = write_pack(tmp_path)
    signal_path = pack_dir / "signal_rows.jsonl"
    signal_path.write_text(signal_path.read_text(encoding="utf-8") + "{}\n", encoding="utf-8")

    with pytest.raises(CandidatePackError, match="PACK_COMPONENT_HASH_MISMATCH"):
        load_candidate_pack(pack_dir)
