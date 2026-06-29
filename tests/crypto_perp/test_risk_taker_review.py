from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from jsonschema import Draft202012Validator
from pydantic import BaseModel
from typer.testing import CliRunner

from sis.cli import app
from sis.crypto_perp.bias_guards import BiasGuardCheck, CryptoPerpBiasGuard
from sis.crypto_perp.models import CryptoPerpProducer
from sis.crypto_perp.risk_taker_review import (
    CryptoPerpRiskTakerReview,
    OperatorJurisdictionStatus,
    SourceFreshnessStatus,
    build_risk_taker_review,
)
from sis.crypto_perp.source_availability import (
    CryptoPerpSourceAvailability,
    SourceId,
    SourceAvailabilityStatus,
)
from sis.crypto_perp.tournament import TournamentAction
from sis.crypto_perp.tournament_rows import CostAwareTournamentRow, CryptoPerpTournamentRowsV2


REPO_ROOT = Path(__file__).resolve().parents[2]
runner = CliRunner()
TS = datetime(2026, 6, 28, 8, 0, tzinfo=timezone.utc)


def _row(
    *,
    event_id: str,
    action: TournamentAction,
    cost: str,
    stress: str | None = None,
    actual: str | None = None,
    operator_time: str = "0",
) -> CostAwareTournamentRow:
    return CostAwareTournamentRow(
        event_id=event_id,
        action=action,
        before_cost_proxy_usd=Decimal(cost),
        fee_estimate_usd=Decimal("0"),
        funding_estimate_usd=Decimal("0"),
        slippage_estimate_usd=Decimal("0"),
        operator_time_cost_usd=Decimal("0"),
        cost_adjusted_cash_estimate_usd=Decimal(cost),
        stress_cash_estimate_usd=Decimal(stress if stress is not None else cost),
        evidence_level="actual_cash" if actual is not None else "cost_adjusted_estimate",
        actual_cash_result_usd=Decimal(actual) if actual is not None else None,
        market_adjusted_return=Decimal("0"),
        operator_time_minutes=Decimal(operator_time),
        known_gaps=[]
        if actual is not None or action == "NO_TRADE"
        else ["ESTIMATE_NOT_ACTUAL_CASH"],
    )


def _rows_v2(
    *,
    actual_cash: bool = True,
    no_trade_leads: bool = False,
    negative_stress: bool = False,
) -> CryptoPerpTournamentRowsV2:
    long_actuals = ("8", "7") if actual_cash else (None, None)
    long_costs = ("1", "1") if no_trade_leads else ("8", "7")
    no_trade_costs = ("2", "2") if no_trade_leads else ("0", "0")
    long_stress = ("-2", "-1") if negative_stress else ("6", "6")
    rows = [
        _row(event_id="event-1", action="REVERSAL_SHORT", cost="-2", stress="-2"),
        _row(event_id="event-2", action="REVERSAL_SHORT", cost="-1", stress="-1"),
        _row(
            event_id="event-1",
            action="CONTINUATION_LONG",
            cost=long_costs[0],
            stress=long_stress[0],
            actual=long_actuals[0],
            operator_time="30",
        ),
        _row(
            event_id="event-2",
            action="CONTINUATION_LONG",
            cost=long_costs[1],
            stress=long_stress[1],
            actual=long_actuals[1],
            operator_time="30",
        ),
        _row(
            event_id="event-1",
            action="NO_TRADE",
            cost=no_trade_costs[0],
            stress=no_trade_costs[0],
            actual="0" if actual_cash else None,
        ),
        _row(
            event_id="event-2",
            action="NO_TRADE",
            cost=no_trade_costs[1],
            stress=no_trade_costs[1],
            actual="0" if actual_cash else None,
        ),
    ]
    known_gaps: list[str] = []
    for row in rows:
        known_gaps.extend(row.known_gaps)
    return CryptoPerpTournamentRowsV2(
        artifact_id="rows-artifact",
        created_at=TS,
        producer=CryptoPerpProducer(command="test"),
        source_refs=[],
        row_set_id="rows-1",
        event_set=["event-1", "event-2"],
        rows=rows,
        known_gaps=list(dict.fromkeys(known_gaps)),
        summary={"leader_action": "CONTINUATION_LONG"},
    )


def _source(*, fresh_enough: bool = True, actual_cash: bool = True) -> CryptoPerpSourceAvailability:
    required_sources: tuple[SourceId, ...] = ("event", "bars", "ticker", "funding", "outcome")
    statuses = [
        SourceAvailabilityStatus(
            source_id=source_id,
            available=True,
            row_count=1,
            reason="available",
            source_refs=[],
        )
        for source_id in required_sources
    ]
    statuses.append(
        SourceAvailabilityStatus(
            source_id="cash_ledger",
            available=actual_cash,
            row_count=1 if actual_cash else 0,
            reason="available" if actual_cash else "CASH_LEDGER_SOURCE_MISSING",
            source_refs=[],
        )
    )
    return CryptoPerpSourceAvailability(
        artifact_id="source-artifact",
        created_at=TS,
        producer=CryptoPerpProducer(command="test"),
        source_refs=[],
        event_id="event-1",
        information_cutoff_at=TS,
        source_statuses=statuses,
        can_compute_ofi=fresh_enough,
        can_compute_trade_sign_imbalance=fresh_enough,
        can_compute_depth=fresh_enough,
        can_compute_cost_adjusted_estimate=fresh_enough,
        can_compute_actual_cash=actual_cash,
        known_gaps=[] if fresh_enough else ["BARS_SOURCE_MISSING"],
        summary={"can_compute_cost_adjusted_estimate": fresh_enough},
    )


def _guard(*, blocked: bool = False) -> CryptoPerpBiasGuard:
    return CryptoPerpBiasGuard(
        artifact_id="bias-artifact",
        created_at=TS,
        producer=CryptoPerpProducer(command="test"),
        source_refs=[],
        guard_id="guard-1",
        guard_status="BLOCKED" if blocked else "PASS",
        pbo_status="ESTIMATED",
        event_count=2,
        min_events_for_pbo=2,
        fold_count=2,
        max_profit_concentration=Decimal("0.60"),
        checks=[
            BiasGuardCheck(
                check_id="sample",
                passed=not blocked,
                observed="PASS" if not blocked else "BLOCKED",
                required="PASS",
            )
        ],
        stop_reasons=["BIAS_GUARD_FAILED_sample"] if blocked else [],
        known_gaps=[],
        summary={"guard_status": "BLOCKED" if blocked else "PASS"},
    )


def _review(
    *,
    rows_v2: CryptoPerpTournamentRowsV2 | None = None,
    source_availability: CryptoPerpSourceAvailability | None = None,
    bias_guard: CryptoPerpBiasGuard | None = None,
    operator_jurisdiction_status: OperatorJurisdictionStatus = "allowed",
    source_freshness_status: SourceFreshnessStatus = "fresh",
    liquidation_buffer_bps: Decimal | None = Decimal("150"),
) -> CryptoPerpRiskTakerReview:
    return build_risk_taker_review(
        rows_v2=rows_v2 or _rows_v2(),
        source_availability=source_availability or _source(),
        bias_guard=bias_guard or _guard(),
        created_at="2026-06-28T09:00:00Z",
        operator_jurisdiction_status=operator_jurisdiction_status,
        source_freshness_status=source_freshness_status,
        venue_terms_checked_at="2026-06-28T08:59:00Z",
        liquidation_buffer_bps=liquidation_buffer_bps,
    )


def _write_json(path: Path, payload: BaseModel | dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = payload.model_dump(mode="json") if isinstance(payload, BaseModel) else payload
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_risk_taker_review_ready_for_human_review_with_actual_cash() -> None:
    review = _review()

    assert review.review_status == "READY_FOR_HUMAN_RISK_REVIEW"
    assert review.recommended_action == "PREPARE_HUMAN_REVIEW"
    assert review.leader_action == "CONTINUATION_LONG"
    assert review.after_cost_edge_over_no_trade_usd == Decimal("15")
    assert review.stress_edge_over_no_trade_usd == Decimal("12")
    assert review.dollars_per_hour == Decimal("15")
    assert review.boundary.permits_live_order is False


def test_risk_taker_review_blocks_prohibited_and_unknown_jurisdiction() -> None:
    statuses: tuple[OperatorJurisdictionStatus, ...] = ("prohibited", "unknown")
    for status in statuses:
        review = _review(operator_jurisdiction_status=status)

        assert review.review_status == "BLOCKED_BY_VENUE"
        assert review.recommended_action == "KEEP_RESEARCH_LOCAL"


def test_risk_taker_review_marks_stale_or_unknown_source_freshness_inconclusive() -> None:
    statuses: tuple[SourceFreshnessStatus, ...] = ("stale", "unknown")
    for status in statuses:
        review = _review(source_freshness_status=status)

        assert review.review_status == "INCONCLUSIVE_DATA"
        assert review.recommended_action == "COLLECT_MISSING_SOURCES"


def test_risk_taker_review_needs_actual_cash_for_estimate_only_positive_edge() -> None:
    review = _review(
        rows_v2=_rows_v2(actual_cash=False), source_availability=_source(actual_cash=False)
    )

    assert review.review_status == "NEEDS_ACTUAL_CASH"
    assert review.recommended_action == "BUILD_ACTUAL_CASH_LEDGER"
    assert "ACTUAL_CASH_RESULT_NOT_AVAILABLE" in review.known_gaps


def test_risk_taker_review_kills_no_trade_leader_negative_stress_and_bias_block() -> None:
    assert _review(rows_v2=_rows_v2(no_trade_leads=True)).review_status == "KILL"
    assert _review(rows_v2=_rows_v2(negative_stress=True)).review_status == "KILL"
    assert _review(bias_guard=_guard(blocked=True)).review_status == "KILL"


def test_risk_taker_review_inconclusive_when_required_inputs_missing() -> None:
    assert (
        _review(source_availability=_source(fresh_enough=False)).review_status
        == "INCONCLUSIVE_DATA"
    )
    assert _review(liquidation_buffer_bps=None).review_status == "INCONCLUSIVE_DATA"


def test_risk_taker_review_schema_accepts_artifact() -> None:
    review = _review()
    schema = json.loads(
        (REPO_ROOT / "schemas/crypto_perp_risk_taker_review.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(review.model_dump(mode="json"))


def test_risk_taker_review_cli_writes_json_and_markdown(tmp_path: Path) -> None:
    rows_path = _write_json(tmp_path / "rows.json", _rows_v2())
    source_path = _write_json(tmp_path / "source.json", _source())
    bias_path = _write_json(tmp_path / "bias.json", _guard())

    result = runner.invoke(
        app,
        [
            "crypto-perp-risk-taker-review",
            "--rows-v2",
            str(rows_path),
            "--source-availability",
            str(source_path),
            "--bias-guard",
            str(bias_path),
            "--operator-jurisdiction-status",
            "allowed",
            "--source-freshness-status",
            "fresh",
            "--venue-terms-checked-at",
            "2026-06-28T08:59:00Z",
            "--liquidation-buffer-bps",
            "150",
            "--out",
            str(tmp_path / "review"),
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "network_attempted=false" in result.stdout
    assert "exchange_write_used=false" in result.stdout
    assert "live_order_submitted=false" in result.stdout
    assert "permits_live_order=false" in result.stdout
    payload = json.loads((tmp_path / "review/risk_taker_review.json").read_text(encoding="utf-8"))
    markdown = (tmp_path / "review/risk_taker_review.md").read_text(encoding="utf-8")
    assert payload["review_status"] == "READY_FOR_HUMAN_RISK_REVIEW"
    assert "READY_FOR_HUMAN_RISK_REVIEW" in markdown
    assert "permits_live_order: `false`" in markdown


def test_risk_taker_review_cli_rejects_invalid_artifact(tmp_path: Path) -> None:
    rows_path = _write_json(tmp_path / "rows.json", {"schema_version": "wrong"})
    source_path = _write_json(tmp_path / "source.json", _source())
    bias_path = _write_json(tmp_path / "bias.json", _guard())

    result = runner.invoke(
        app,
        [
            "crypto-perp-risk-taker-review",
            "--rows-v2",
            str(rows_path),
            "--source-availability",
            str(source_path),
            "--bias-guard",
            str(bias_path),
            "--operator-jurisdiction-status",
            "allowed",
            "--source-freshness-status",
            "fresh",
            "--liquidation-buffer-bps",
            "150",
            "--out",
            str(tmp_path / "review"),
        ],
    )

    assert result.exit_code == 2
    assert "status=fail" in result.stdout
