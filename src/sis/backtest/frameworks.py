from __future__ import annotations

from importlib import metadata, util
from typing import Any


FRAMEWORK_CANDIDATES = (
    {
        "framework_id": "vectorbt",
        "module": "vectorbt",
        "distribution": "vectorbt",
        "adapter_role": "vectorized_research_candidate",
        "adoption_note": "Import smoke passed in temporary uv env; license metadata must be verified before dependency adoption.",
    },
    {
        "framework_id": "bt",
        "module": "bt",
        "distribution": "bt",
        "adapter_role": "portfolio_allocation_candidate",
        "adoption_note": "Portfolio allocation and rebalance comparison candidate; requires temporary import smoke and license metadata review.",
    },
    {
        "framework_id": "backtesting",
        "module": "backtesting",
        "distribution": "backtesting",
        "adapter_role": "simple_ohlc_candidate",
        "adoption_note": "AGPL-3.0 metadata observed; requires license review before dependency adoption.",
    },
    {
        "framework_id": "zipline_reloaded",
        "module": "zipline",
        "distribution": "zipline-reloaded",
        "adapter_role": "large_event_driven_candidate",
        "adoption_note": "Temporary uv install failed on bcolz-zipline build in this environment; not ready for adoption.",
    },
    {
        "framework_id": "backtrader",
        "module": "backtrader",
        "distribution": "backtrader",
        "adapter_role": "event_driven_candidate",
        "adoption_note": "GPLv3+ metadata observed; requires license review and no-live isolation before dependency adoption.",
    },
    {
        "framework_id": "quantstats",
        "module": "quantstats",
        "distribution": "quantstats",
        "adapter_role": "report_only_candidate",
        "adoption_note": "Return, drawdown, and tear sheet report candidate; evaluate as report support rather than a standard engine.",
    },
    {
        "framework_id": "empyrical_reloaded",
        "module": "empyrical",
        "distribution": "empyrical-reloaded",
        "adapter_role": "metrics_only_candidate",
        "adoption_note": "Risk and performance metrics support candidate; evaluate for metric consistency and report normalization.",
    },
    {
        "framework_id": "pyfolio_reloaded",
        "module": "pyfolio",
        "distribution": "pyfolio-reloaded",
        "adapter_role": "report_only_candidate",
        "adoption_note": "Portfolio analysis report candidate; evaluate only as report support after temporary import smoke.",
    },
    {
        "framework_id": "qstrader",
        "module": "qstrader",
        "distribution": "qstrader",
        "adapter_role": "schedule_event_driven_candidate",
        "adoption_note": "Schedule-driven equities framework candidate; Python 3.13 temporary import smoke passed, but local-input runner boundary and lock stability remain required.",
    },
)

REFERENCE_ONLY_FRAMEWORK_CANDIDATES = (
    {
        "framework_id": "nautilus_trader",
        "module": "nautilus_trader",
        "distribution": "nautilus-trader",
        "adapter_role": "reference_only_backtesting_architecture",
        "adoption_note": "Reference-only review target for event-driven backtesting design; not an adapter, runner, or dependency adoption target.",
    },
    {
        "framework_id": "freqtrade",
        "module": "freqtrade",
        "distribution": "freqtrade",
        "adapter_role": "reference_only_lookahead_analysis",
        "adoption_note": "Reference-only review target for lookahead-analysis workflow; not an adapter, runner, or dependency adoption target.",
    },
    {
        "framework_id": "qlib",
        "module": "qlib",
        "distribution": "pyqlib",
        "adapter_role": "reference_only_research_platform",
        "adoption_note": "Reference-only review target for research workflow design; not an adapter, runner, or dependency adoption target.",
    },
    {
        "framework_id": "finrl",
        "module": "finrl",
        "distribution": "finrl",
        "adapter_role": "reference_only_rl_research",
        "adoption_note": "Reference-only review target for RL research workflow; not an adapter, runner, or dependency adoption target.",
    },
    {
        "framework_id": "hftbacktest",
        "module": "hftbacktest",
        "distribution": "hftbacktest",
        "adapter_role": "reference_only_microstructure_replay",
        "adoption_note": "Reference-only review target for L2/L3/tick replay, feed/order latency, and queue-position modeling; not an adapter, runner, or dependency adoption target.",
    },
    {
        "framework_id": "skfolio",
        "module": "skfolio",
        "distribution": "skfolio",
        "adapter_role": "reference_only_portfolio_validation",
        "adoption_note": "Reference-only review target for portfolio validation methodology; not an adapter, runner, or dependency adoption target.",
    },
)


def framework_adapter_status() -> list[dict[str, Any]]:
    adapters: list[dict[str, Any]] = []
    for candidate in FRAMEWORK_CANDIDATES:
        module = str(candidate["module"])
        distribution = str(candidate["distribution"])
        installed = util.find_spec(module) is not None
        version = None
        license_text = None
        requires_python = None
        license_classifiers: list[str] = []
        if installed:
            try:
                version = metadata.version(distribution)
                meta = metadata.metadata(distribution)
                license_text = meta.get("License")
                requires_python = meta.get("Requires-Python")
                license_classifiers = [
                    item
                    for item in meta.get_all("Classifier") or []
                    if item.startswith("License ::")
                ]
            except metadata.PackageNotFoundError:
                installed = False
        adapters.append(
            {
                **candidate,
                "status": "installed" if installed else "not_installed",
                "version": version,
                "license": license_text,
                "requires_python": requires_python,
                "license_classifiers": license_classifiers,
                "runs_in_this_command": False,
            }
        )
    return adapters


def framework_reference_only_status() -> list[dict[str, Any]]:
    return [
        {
            **candidate,
            "candidate_kind": "reference_only",
            "status": "reference_only",
            "version": None,
            "license": None,
            "requires_python": None,
            "license_classifiers": [],
            "runs_in_this_command": False,
        }
        for candidate in REFERENCE_ONLY_FRAMEWORK_CANDIDATES
    ]
