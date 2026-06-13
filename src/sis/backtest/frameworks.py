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
        "adoption_note": "Schedule-driven equities framework candidate; keep on hold until package maturity and Python 3.13 install smoke are verified.",
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
