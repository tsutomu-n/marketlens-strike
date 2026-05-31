from __future__ import annotations

from dataclasses import dataclass

from sis.backtest.engine.config import BacktestConfig, CostConfig, ExecutionConfig


@dataclass(frozen=True)
class ScenarioConfig:
    name: str
    config: BacktestConfig


def _with_costs(
    config: BacktestConfig, *, name: str, fee_multiplier: float, slippage: float
) -> ScenarioConfig:
    return ScenarioConfig(
        name=name,
        config=config.model_copy(
            update={
                "cost": CostConfig(
                    fee_model_ref=config.cost.fee_model_ref,
                    fee_scenario=config.cost.fee_scenario,
                    fee_multiplier=fee_multiplier,
                    funding_policy=config.cost.funding_policy,
                ),
                "execution": ExecutionConfig(
                    side_mode=config.execution.side_mode,
                    fill_model=config.execution.fill_model,
                    extra_slippage_bps=slippage,
                    force_close_on_end=config.execution.force_close_on_end,
                ),
            }
        ),
    )


def default_scenarios(config: BacktestConfig) -> list[ScenarioConfig]:
    return [
        _with_costs(config, name="base", fee_multiplier=1.0, slippage=0.0),
        _with_costs(config, name="fee_2x", fee_multiplier=2.0, slippage=0.0),
        _with_costs(config, name="slippage_5bps", fee_multiplier=1.0, slippage=5.0),
        _with_costs(config, name="conservative", fee_multiplier=2.0, slippage=10.0),
    ]
