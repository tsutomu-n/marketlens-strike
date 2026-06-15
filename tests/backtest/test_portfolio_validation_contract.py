from __future__ import annotations

import json
from pathlib import Path

from jsonschema import validate

from sis.backtest.portfolio_validation_contract import (
    build_strategy_backtest_portfolio_validation_contract,
)


def _schema(name: str) -> dict:
    return json.loads(Path("schemas", name).read_text(encoding="utf-8"))


def test_portfolio_validation_contract_does_not_run_optimizer(tmp_path: Path) -> None:
    metrics_path = tmp_path / "metrics.json"
    metrics_path.write_text(
        json.dumps(
            {
                "summary": {
                    "executed_signal_results": [{"canonical_symbol": "QQQ", "signal_return": 0.01}]
                }
            }
        ),
        encoding="utf-8",
    )

    result = build_strategy_backtest_portfolio_validation_contract(
        metrics_path=metrics_path,
        out_dir=tmp_path / "out",
        reports_dir=tmp_path / "reports",
    )

    validate(
        instance=result.payload,
        schema=_schema("strategy_backtest_portfolio_validation_contract.v1.schema.json"),
    )
    assert result.payload["decision"] == "NOT_READY_FOR_PORTFOLIO_VALIDATION_ENGINE"
    assert {row["framework_id"] for row in result.payload["candidate_frameworks"]} == {
        "skfolio",
        "riskfolio-lib",
    }
    assert result.payload["dependency_added"] is False
    assert result.payload["engine_run"] is False
