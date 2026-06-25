from __future__ import annotations

from sis.backtest.compare_completion_results import completion_artifact
from sis.backtest.compare_diagnostics import comparison_diagnostics
from sis.backtest.compare_extension_results import (
    metric_extension,
    portfolio_comparison,
    report_extension,
)
from sis.backtest.compare_framework_results import adapter_spike, external_results, framework_run
from sis.backtest.compare_native_results import method_results, native_result
from sis.backtest.compare_quality_results import (
    benchmark_relative,
    regime_split,
    rolling_stability,
    stress,
)
from sis.backtest.compare_suite_results import suite_results

__all__ = [
    "adapter_spike",
    "benchmark_relative",
    "comparison_diagnostics",
    "completion_artifact",
    "external_results",
    "framework_run",
    "method_results",
    "metric_extension",
    "native_result",
    "portfolio_comparison",
    "regime_split",
    "report_extension",
    "rolling_stability",
    "stress",
    "suite_results",
]
