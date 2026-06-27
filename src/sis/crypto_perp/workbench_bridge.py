from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from sis.crypto_perp.clock import ensure_utc_aware
from sis.crypto_perp.models import stable_hash
from sis.crypto_perp.tournament import CryptoPerpTournamentReport, TOURNAMENT_SCHEMA_VERSION
from sis.strategy_inputs.models import (
    ExecutionReality,
    InputRevisionPolicy,
    InputSourceType,
    InputSurvivorshipPolicy,
    ProducerInfo,
    StrategyInputContract,
    StrategyInputSource,
    StrategyScope,
)


_NON_ACTUAL_CASH_GAPS = {
    "OUTCOME_BEFORE_COST_PROXY_NOT_ACTUAL_CASH",
    "FEES_FUNDING_AND_FILL_SLIPPAGE_NOT_INCLUDED",
    "ESTIMATE_NOT_ACTUAL_CASH",
    "ACTUAL_CASH_RESULT_NOT_AVAILABLE",
}


def _has_non_actual_cash_gap(report: CryptoPerpTournamentReport) -> bool:
    return any(gap in _NON_ACTUAL_CASH_GAPS for gap in report.known_gaps)


def _includes_cash_execution_reality(report: CryptoPerpTournamentReport) -> bool:
    return (
        report.actual_cash
        and report.cash_metric_basis == "actual_cash"
        and not _has_non_actual_cash_gap(report)
    )


def build_tournament_strategy_input_contract(
    *,
    report: CryptoPerpTournamentReport,
    report_path: str | Path,
    report_sha256: str,
    instruments: Sequence[str],
    timeframe: str,
    created_at: datetime | str,
) -> StrategyInputContract:
    created = ensure_utc_aware("created_at", created_at)
    contract_id = f"crypto-perp-tournament-{stable_hash([report.report_id, report_sha256])[:16]}"
    includes_cash_execution_reality = _includes_cash_execution_reality(report)
    return StrategyInputContract(
        contract_id=contract_id,
        created_at=created,
        producer=ProducerInfo(command="crypto-perp-workbench-bridge"),
        strategy_scope=StrategyScope(
            strategy_family="crypto_perp_truth_cycle",
            instruments=list(instruments),
            timeframe=timeframe,
            intended_use="research_backtest_only",
        ),
        sources=[
            StrategyInputSource(
                source_id="crypto_perp_tournament_report",
                source_type=InputSourceType.RUNTIME_OBSERVATION,
                path=Path(report_path).as_posix(),
                required=True,
                declared_sha256=report_sha256,
                schema_version=TOURNAMENT_SCHEMA_VERSION,
                generated_at=report.generated_at,
                available_at=created,
                revision_policy=InputRevisionPolicy.SNAPSHOT_IMMUTABLE,
                survivorship_policy=InputSurvivorshipPolicy.NOT_APPLICABLE,
                execution_reality=ExecutionReality(
                    includes_fills=includes_cash_execution_reality,
                    includes_slippage=includes_cash_execution_reality,
                    includes_latency=includes_cash_execution_reality,
                    assumed_order_type=(
                        "crypto_perp_cash_ledger_or_live_measurement"
                        if includes_cash_execution_reality
                        else "crypto_perp_estimate_or_before_cost_proxy"
                    ),
                ),
            )
        ],
        known_gaps=list(dict.fromkeys([*report.known_gaps, *report.inconclusive_reasons])),
    )
