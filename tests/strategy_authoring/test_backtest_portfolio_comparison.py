from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
import sys

from jsonschema import validate
import polars as pl

from sis.backtest.portfolio_comparison import build_strategy_backtest_portfolio_comparison


def _write_bundle(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": "strategy_authoring_bundle_result.v1",
                "bundle_id": "demo_bundle",
                "paper_only": True,
                "live_order_submitted": False,
                "portfolio": {
                    "allocation_method": "fixed_weight",
                    "max_total_allocation_weight": 1.0,
                    "selection_metric": "total_return",
                    "selection_direction": "maximize",
                    "resolved_selection_direction": "maximize",
                },
                "aggregate_metrics": {
                    "member_count": 2,
                    "trade_count": 4,
                    "weighted_total_return": 0.02,
                    "max_drawdown": -0.01,
                    "cost_drag_bps": 1.0,
                    "multi_leg_group_metrics": {},
                },
                "best_member": None,
                "members": [
                    {
                        "member_index": 0,
                        "spec_path": "a.yaml",
                        "strategy_id": "alpha",
                        "allocation_weight": 0.7,
                        "effective_allocation_weight": 0.7,
                        "signal_count": 2,
                        "summary": {"aggregate_metrics": {"total_return": 0.03}},
                    },
                    {
                        "member_index": 1,
                        "spec_path": "b.yaml",
                        "strategy_id": "beta",
                        "allocation_weight": 0.3,
                        "effective_allocation_weight": 0.3,
                        "signal_count": 2,
                        "summary": {"aggregate_metrics": {"total_return": 0.01}},
                    },
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )


def _write_prices(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pl.DataFrame(
        [
            {
                "ts_client": "2026-01-01T00:00:00Z",
                "canonical_symbol": "AAA",
                "mark_price": 100.0,
            },
            {
                "ts_client": "2026-01-02T00:00:00Z",
                "canonical_symbol": "AAA",
                "mark_price": 102.0,
            },
            {
                "ts_client": "2026-01-03T00:00:00Z",
                "canonical_symbol": "AAA",
                "mark_price": 101.0,
            },
        ]
    ).write_parquet(path)


def test_build_strategy_backtest_portfolio_comparison_skips_when_bt_missing(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr("sis.backtest.portfolio_comparison.framework_adapter_status", lambda: [])
    bundle_path = tmp_path / "bundle.json"
    price_path = tmp_path / "quotes.parquet"
    _write_bundle(bundle_path)
    _write_prices(price_path)

    result = build_strategy_backtest_portfolio_comparison(
        bundle_path=bundle_path,
        price_frame_path=price_path,
        out_dir=tmp_path / "out",
        reports_dir=tmp_path / "reports",
    )

    payload = result.payload
    schema = json.loads(
        Path("schemas/strategy_backtest_portfolio_comparison.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    validate(instance=payload, schema=schema)
    assert payload["schema_version"] == "strategy_backtest_portfolio_comparison.v1"
    assert payload["framework_id"] == "bt"
    assert payload["run_status"] == "skipped"
    assert payload["reason_codes"] == ["not_installed_in_current_env"]
    assert payload["runner_mode"] == "not_installed_in_current_env"
    assert payload["dependency_source"] == "not_installed_in_current_env"
    assert payload["engine_run"] is False
    assert payload["dependency_added"] is False
    assert payload["permits_live_order"] is False
    assert payload["wallet_used"] is False
    assert payload["exchange_write_used"] is False
    assert payload["portfolio_return"] is None
    assert payload["rebalance_count"] == 0
    assert len(payload["members"]) == 2


def test_build_strategy_backtest_portfolio_comparison_runs_bt_when_installed(
    tmp_path, monkeypatch
) -> None:
    bundle_path = tmp_path / "bundle.json"
    price_path = tmp_path / "quotes.parquet"
    _write_bundle(bundle_path)
    _write_prices(price_path)

    class FakeAlgo:
        def __init__(self, *args, **kwargs) -> None:
            self.args = args
            self.kwargs = kwargs

    class FakeBacktest:
        def __init__(self, strategy, data, **kwargs) -> None:
            self.strategy = strategy
            self.data = data
            self.kwargs = kwargs

    class FakeResult:
        stats = {
            "strategy_authoring_bt_portfolio": {
                "total_return": 0.04,
                "max_drawdown": -0.02,
            }
        }

        def get_security_weights(self):
            class Weights:
                def fillna(self, _value):
                    return self

                def diff(self):
                    return self

                def abs(self):
                    return self

                def sum(self):
                    return {"alpha_0": 0.2, "beta_1": 0.2}

            return Weights()

    fake_bt = SimpleNamespace(
        Strategy=lambda name, algos: {"name": name, "algos": algos},
        Backtest=FakeBacktest,
        run=lambda *_args, **_kwargs: FakeResult(),
        algos=SimpleNamespace(
            RunAfterDate=FakeAlgo,
            SelectAll=FakeAlgo,
            WeighSpecified=FakeAlgo,
            Rebalance=FakeAlgo,
        ),
    )
    monkeypatch.setitem(sys.modules, "bt", fake_bt)
    monkeypatch.setattr(
        "sis.backtest.portfolio_comparison.framework_adapter_status",
        lambda: [
            {
                "framework_id": "bt",
                "adapter_role": "portfolio_allocation_candidate",
                "status": "installed",
                "version": "1.2.0",
            }
        ],
    )

    result = build_strategy_backtest_portfolio_comparison(
        bundle_path=bundle_path,
        price_frame_path=price_path,
        out_dir=tmp_path / "out",
        reports_dir=tmp_path / "reports",
    )

    payload = result.payload
    assert payload["framework_version"] == "1.2.0"
    assert payload["runner_mode"] == "temporary_or_optional_import"
    assert payload["dependency_source"] == "optional_extra_available"
    assert payload["run_status"] == "completed"
    assert payload["engine_run"] is True
    assert payload["portfolio_return"] == 0.04
    assert payload["max_drawdown"] == -0.02
    assert payload["turnover"] == 0.4
    assert payload["rebalance_count"] == 1
