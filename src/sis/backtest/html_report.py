from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import math
from pathlib import Path
from typing import Any

from sis.backtest.artifact_io import read_json_object, sha256_file, write_json_object
from sis.backtest.boundary import with_backtest_paper_only_boundary
from sis.backtest.html_report_rendering import (
    render_strategy_backtest_html as _render_html,
)


@dataclass(frozen=True)
class StrategyBacktestHtmlReportResult:
    html_report_path: Path
    manifest_path: Path
    payload: dict[str, Any]


def _numeric(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        result = float(value)
        return result if math.isfinite(result) else None
    return None


def _object(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _read_optional_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return read_json_object(path)


def _source_artifact(path: Path) -> dict[str, Any]:
    return {
        "path": path.as_posix(),
        "exists": path.exists(),
        "sha256": sha256_file(path) if path.exists() else None,
    }


def _return_label(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.2f}%"


def _money_label(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"${value:,.2f}"


def _date_key(value: Any) -> str:
    if not isinstance(value, str) or not value:
        return "unknown"
    return value[:10]


def _trade_rows(metrics_payload: dict[str, Any]) -> list[dict[str, Any]]:
    summary = _object(metrics_payload.get("summary"))
    rows: list[dict[str, Any]] = []
    for index, raw in enumerate(_list(summary.get("executed_signal_results"))):
        if not isinstance(raw, dict):
            continue
        signal_return = _numeric(raw.get("signal_return"))
        if signal_return is None:
            continue
        rows.append(
            {
                "index": index,
                "ts_signal": raw.get("ts_signal"),
                "date": _date_key(raw.get("ts_signal")),
                "signal_id": raw.get("signal_id"),
                "venue": raw.get("venue"),
                "canonical_symbol": raw.get("canonical_symbol"),
                "side": raw.get("side"),
                "timeframe": raw.get("timeframe"),
                "exit_reason": raw.get("exit_reason"),
                "signal_return": signal_return,
                "signal_return_label": _return_label(signal_return),
                "cost_drag_bps": _numeric(raw.get("cost_drag_bps")),
                "notional_usd": _numeric(raw.get("notional_usd")),
            }
        )
    return rows


def _equity_curve(
    trades: list[dict[str, Any]],
    *,
    initial_capital_usd: float,
) -> list[dict[str, Any]]:
    compounded_return = 0.0
    peak_equity = initial_capital_usd
    rows: list[dict[str, Any]] = []
    for trade in trades:
        signal_return = float(trade["signal_return"])
        compounded_return = (1.0 + compounded_return) * (1.0 + signal_return) - 1.0
        equity = initial_capital_usd * (1.0 + compounded_return)
        peak_equity = max(peak_equity, equity)
        drawdown = equity / peak_equity - 1.0 if peak_equity else 0.0
        rows.append(
            {
                "index": trade["index"],
                "ts_signal": trade.get("ts_signal"),
                "date": trade.get("date"),
                "cumulative_return": compounded_return,
                "cumulative_return_label": _return_label(compounded_return),
                "equity_usd": equity,
                "equity_label": _money_label(equity),
                "pnl_usd": equity - initial_capital_usd,
                "pnl_label": _money_label(equity - initial_capital_usd),
                "drawdown": drawdown,
                "drawdown_label": _return_label(drawdown),
            }
        )
    return rows


def _period_summaries(trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for trade in trades:
        grouped.setdefault(str(trade.get("date") or "unknown"), []).append(trade)
    rows: list[dict[str, Any]] = []
    for period, period_trades in sorted(grouped.items()):
        compounded_return = 0.0
        for trade in period_trades:
            compounded_return = (1.0 + compounded_return) * (
                1.0 + float(trade["signal_return"])
            ) - 1.0
        rows.append(
            {
                "period": period,
                "trade_count": len(period_trades),
                "total_return": compounded_return,
                "total_return_label": _return_label(compounded_return),
                "first_signal": period_trades[0].get("ts_signal"),
                "last_signal": period_trades[-1].get("ts_signal"),
            }
        )
    return rows


def _benchmark_curve(payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    if payload is None:
        return []
    strategy_return = 0.0
    benchmark_return = 0.0
    active_return = 0.0
    rows: list[dict[str, Any]] = []
    for index, raw in enumerate(_list(payload.get("comparisons"))):
        if not isinstance(raw, dict):
            continue
        strategy_step = _numeric(raw.get("strategy_return"))
        benchmark_step = _numeric(raw.get("benchmark_return"))
        active_step = _numeric(raw.get("active_return"))
        if strategy_step is None or benchmark_step is None:
            continue
        strategy_return = (1.0 + strategy_return) * (1.0 + strategy_step) - 1.0
        benchmark_return = (1.0 + benchmark_return) * (1.0 + benchmark_step) - 1.0
        active_step = strategy_step - benchmark_step if active_step is None else active_step
        active_return = (1.0 + active_return) * (1.0 + active_step) - 1.0
        rows.append(
            {
                "index": index,
                "ts_signal": raw.get("ts_signal"),
                "date": _date_key(raw.get("ts_signal")),
                "strategy_return": strategy_return,
                "benchmark_return": benchmark_return,
                "active_return": active_return,
            }
        )
    return rows


def _stress_scenarios(payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    if payload is None:
        return []
    rows: list[dict[str, Any]] = []
    for raw in _list(payload.get("scenarios")):
        if not isinstance(raw, dict):
            continue
        rows.append(
            {
                "scenario_id": raw.get("scenario_id"),
                "stressed_total_return": _numeric(raw.get("stressed_total_return")),
                "stressed_total_return_label": _return_label(
                    _numeric(raw.get("stressed_total_return"))
                ),
                "stressed_max_drawdown": _numeric(raw.get("stressed_max_drawdown")),
                "total_additional_bps_per_trade": _numeric(
                    raw.get("total_additional_bps_per_trade")
                ),
            }
        )
    return rows


def _gate_statuses(
    *,
    validation_payload: dict[str, Any] | None,
    benchmark_payload: dict[str, Any] | None,
    stress_payload: dict[str, Any] | None,
    data_availability_payload: dict[str, Any] | None,
    no_lookahead_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    validation_summary = _object(validation_payload.get("summary") if validation_payload else None)
    benchmark_summary = _object(benchmark_payload.get("summary") if benchmark_payload else None)
    stress_summary = _object(stress_payload.get("summary") if stress_payload else None)
    no_lookahead_summary = _object(
        no_lookahead_payload.get("summary") if no_lookahead_payload else None
    )
    return {
        "pack_validation_decision": validation_payload.get("decision")
        if validation_payload
        else None,
        "pack_validation_failed_count": validation_summary.get("failed_count"),
        "benchmark_active_total_return": benchmark_summary.get("active_total_return"),
        "benchmark_information_ratio": benchmark_summary.get("information_ratio"),
        "stress_worst_total_return": stress_summary.get("worst_stressed_total_return"),
        "data_availability_status": data_availability_payload.get("status")
        if data_availability_payload
        else None,
        "no_lookahead_failed_count": no_lookahead_summary.get("failed_count"),
        "no_lookahead_coverage_status": no_lookahead_summary.get("coverage_status"),
    }


def _result_label(
    *,
    trade_count: int,
    total_return: float | None,
    max_drawdown: float | None,
    gates: dict[str, Any],
    min_trade_count_for_candidate: int,
) -> dict[str, Any]:
    reasons: list[str] = []
    next_checks: list[str] = []
    validation_pass = gates["pack_validation_decision"] == "PASS"
    data_pass = gates["data_availability_status"] == "pass"
    no_lookahead_pass = gates["no_lookahead_failed_count"] == 0
    stress_worst = _numeric(gates["stress_worst_total_return"])
    active_return = _numeric(gates["benchmark_active_total_return"])

    if trade_count < min_trade_count_for_candidate:
        reasons.append(
            f"trade_count={trade_count} が候補最低件数 {min_trade_count_for_candidate} を下回っています。"
        )
        next_checks.append(
            "out-of-sample の trade を増やしてから、安定した結果として扱うか確認する。"
        )
        return {
            "code": "insufficient_evidence",
            "label": "検証不足",
            "description": "signal / trade が少なく、結果を一般化するには弱い状態です。",
            "reasons": reasons,
            "next_checks": next_checks,
        }

    if total_return is None or total_return <= 0:
        reasons.append("total_return がプラスではありません。")
    if max_drawdown is not None and max_drawdown < -0.2:
        reasons.append("max_drawdown が -20% より悪化しています。")
    if reasons:
        next_checks.append("drawdown、cost drag、rejected signal の理由を確認する。")
        return {
            "code": "weak",
            "label": "弱い",
            "description": "return または安定性が弱く、そのまま次段階へ進める根拠は薄い状態です。",
            "reasons": reasons,
            "next_checks": next_checks,
        }

    missing_gate_reasons: list[str] = []
    if not validation_pass:
        missing_gate_reasons.append("pack validation が PASS ではありません。")
    if not data_pass:
        missing_gate_reasons.append("data availability が pass ではありません。")
    if not no_lookahead_pass:
        missing_gate_reasons.append("no-lookahead replay に失敗または欠損があります。")
    if stress_worst is None or stress_worst < 0:
        missing_gate_reasons.append("worst stress scenario がマイナスまたは欠損です。")
    if active_return is None or active_return < 0:
        missing_gate_reasons.append("benchmark active return がマイナスまたは欠損です。")
    if missing_gate_reasons:
        next_checks.extend(
            [
                "benchmark-relative、stress、no-lookahead、data availability artifact を実行または確認する。",
                "cost、stress、benchmark 比較に耐えているか確認する。",
            ]
        )
        return {
            "code": "needs_more_validation",
            "label": "要追加検証",
            "description": "単発の backtest は悪くありませんが、追加検証のどこかが不足しています。",
            "reasons": missing_gate_reasons,
            "next_checks": next_checks,
        }

    return {
        "code": "paper_observation_candidate",
        "label": "paper観察候補",
        "description": "次に観察候補として読む余地があります。ただし paper 実行許可ではありません。",
        "reasons": [
            "pack validation、data availability、no-lookahead、stress、benchmark、trade-count gate を通過しています。"
        ],
        "next_checks": [
            "人間が artifact と operator review output を読む。",
            "paper observation は別 artifact として記録する。この report は注文送信も許可もしない。",
        ],
    }


def build_strategy_backtest_html_report(
    *,
    metrics_path: Path,
    validation_path: Path,
    benchmark_relative_path: Path,
    stress_path: Path,
    rolling_stability_path: Path,
    regime_split_path: Path,
    data_availability_path: Path,
    no_lookahead_path: Path,
    comparison_path: Path,
    out_dir: Path,
    reports_dir: Path,
    min_trade_count_for_candidate: int = 30,
) -> StrategyBacktestHtmlReportResult:
    if not metrics_path.exists():
        raise FileNotFoundError(f"strategy backtest metrics missing: {metrics_path}")
    metrics_payload = read_json_object(metrics_path)
    validation_payload = _read_optional_json(validation_path)
    benchmark_payload = _read_optional_json(benchmark_relative_path)
    stress_payload = _read_optional_json(stress_path)
    rolling_payload = _read_optional_json(rolling_stability_path)
    regime_payload = _read_optional_json(regime_split_path)
    data_availability_payload = _read_optional_json(data_availability_path)
    no_lookahead_payload = _read_optional_json(no_lookahead_path)
    comparison_payload = _read_optional_json(comparison_path)

    summary = _object(metrics_payload.get("summary"))
    aggregate = _object(summary.get("aggregate_metrics"))
    capital = _object(summary.get("capital"))
    trades = _trade_rows(metrics_payload)
    initial_capital = _numeric(capital.get("initial_capital_usd")) or 10000.0
    equity_curve = _equity_curve(trades, initial_capital_usd=initial_capital)
    total_return = _numeric(aggregate.get("total_return"))
    max_drawdown = _numeric(aggregate.get("max_drawdown"))
    trade_count = int(aggregate.get("trade_count") or len(trades))
    gates = _gate_statuses(
        validation_payload=validation_payload,
        benchmark_payload=benchmark_payload,
        stress_payload=stress_payload,
        data_availability_payload=data_availability_payload,
        no_lookahead_payload=no_lookahead_payload,
    )
    result_label = _result_label(
        trade_count=trade_count,
        total_return=total_return,
        max_drawdown=max_drawdown,
        gates=gates,
        min_trade_count_for_candidate=min_trade_count_for_candidate,
    )
    created_at = datetime.now(timezone.utc).isoformat()
    view_model: dict[str, Any] = {
        "schema_version": "strategy_backtest_html_report.v1",
        "created_at": created_at,
        "summary": {
            "strategy_id": metrics_payload.get("strategy_id"),
            "trade_count": trade_count,
            "total_return": total_return,
            "total_return_label": _return_label(total_return),
            "max_drawdown": max_drawdown,
            "max_drawdown_label": _return_label(max_drawdown),
            "win_rate": _numeric(_object(summary.get("executed_signal_summary")).get("win_rate")),
            "net_pnl_usd": _numeric(capital.get("net_pnl_usd")),
            "ending_equity_usd": _numeric(capital.get("ending_equity_usd")),
            "initial_capital_usd": initial_capital,
            "first_signal": trades[0].get("ts_signal") if trades else None,
            "last_signal": trades[-1].get("ts_signal") if trades else None,
        },
        "result_label": result_label,
        "gate_statuses": gates,
        "visual_data": {
            "trades": trades,
            "equity_curve": equity_curve,
            "periods": _period_summaries(trades),
            "benchmark_curve": _benchmark_curve(benchmark_payload),
            "stress_scenarios": _stress_scenarios(stress_payload),
            "rolling_stability_summary": _object(
                rolling_payload.get("summary") if rolling_payload else None
            ),
            "regime_split_summary": _object(
                regime_payload.get("summary") if regime_payload else None
            ),
            "comparison_diagnostics": _object(
                comparison_payload.get("comparison_diagnostics") if comparison_payload else None
            ),
        },
        "source_artifacts": {
            "metrics": _source_artifact(metrics_path),
            "pack_validation": _source_artifact(validation_path),
            "benchmark_relative": _source_artifact(benchmark_relative_path),
            "stress": _source_artifact(stress_path),
            "rolling_stability": _source_artifact(rolling_stability_path),
            "regime_split": _source_artifact(regime_split_path),
            "data_availability": _source_artifact(data_availability_path),
            "no_lookahead": _source_artifact(no_lookahead_path),
            "comparison": _source_artifact(comparison_path),
        },
    }
    html = _render_html(view_model)
    reports_dir.mkdir(parents=True, exist_ok=True)
    html_report_path = reports_dir / "strategy_backtest_html_report.html"
    html_report_path.write_text(html, encoding="utf-8")

    payload = with_backtest_paper_only_boundary(
        {
            **view_model,
            "html_report_path": html_report_path.as_posix(),
            "html_report_hash": sha256_file(html_report_path),
            "paper_observation_candidate_is_permission": False,
            "min_trade_count_for_candidate": min_trade_count_for_candidate,
        }
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "strategy_backtest_html_report.json"
    write_json_object(manifest_path, payload)
    return StrategyBacktestHtmlReportResult(
        html_report_path=html_report_path,
        manifest_path=manifest_path,
        payload=payload,
    )
