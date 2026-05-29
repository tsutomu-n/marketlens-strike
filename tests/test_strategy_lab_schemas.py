from __future__ import annotations

import json
from pathlib import Path


def test_strategy_lab_schema_files_exist_and_parse() -> None:
    names = [
        "data_snapshot_manifest.v1.schema.json",
        "feature_snapshot_manifest.v1.schema.json",
        "strategy_experiment_spec.v1.schema.json",
        "strategy_signal.v1.schema.json",
        "evaluation_plan.mls.v1.schema.json",
        "trial_record.v1.schema.json",
        "trade_candidate.v1.schema.json",
        "paper_candidate_pack.v1.schema.json",
        "promotion_decision.v1.schema.json",
        "paper_intent_preview.v1.schema.json",
    ]

    for name in names:
        payload = json.loads(Path("schemas", name).read_text(encoding="utf-8"))
        assert payload["type"] == "object"
