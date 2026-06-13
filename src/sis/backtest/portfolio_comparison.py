from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import importlib
import json
from pathlib import Path
from typing import Any

import polars as pl

from sis.backtest.frameworks import framework_adapter_status


@dataclass(frozen=True)
class BacktestPortfolioComparisonResult:
    comparison_path: Path
    report_path: Path
    payload: dict[str, Any]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _bt_candidate() -> dict[str, Any]:
    for candidate in framework_adapter_status():
        if candidate.get("framework_id") == "bt":
            return candidate
    return {
        "framework_id": "bt",
        "adapter_role": "portfolio_allocation_candidate",
        "status": "not_installed",
        "version": None,
    }


def _member_rows(bundle_payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw in bundle_payload.get("members") or []:
        if not isinstance(raw, dict):
            continue
        member_index = int(raw.get("member_index") or len(rows))
        strategy_id = str(raw.get("strategy_id") or f"member_{member_index}")
        column_id = f"{strategy_id}_{member_index}"
        rows.append(
            {
                "member_index": member_index,
                "strategy_id": strategy_id,
                "column_id": column_id,
                "effective_allocation_weight": float(raw.get("effective_allocation_weight") or 0.0),
            }
        )
    if not rows:
        raise ValueError("strategy authoring bundle result has no members.")
    total_weight = sum(row["effective_allocation_weight"] for row in rows)
    if total_weight <= 0:
        equal_weight = 1.0 / len(rows)
        for row in rows:
            row["effective_allocation_weight"] = equal_weight
    return rows


def _price_series(price_frame_path: Path) -> pl.DataFrame:
    frame = pl.read_parquet(price_frame_path)
    price_column = next(
        (
            column
            for column in ("mark_price", "mid_price", "exec_buy_price", "oracle_price")
            if column in frame.columns
        ),
        None,
    )
    if price_column is None or "ts_client" not in frame.columns:
        raise ValueError("price frame must include ts_client and a supported price column.")
    series = (
        frame.select(
            pl.col("ts_client").cast(pl.String).alias("ts"),
            pl.col(price_column).cast(pl.Float64).alias("price"),
        )
        .drop_nulls(["ts", "price"])
        .group_by("ts")
        .agg(pl.col("price").mean().alias("price"))
        .sort("ts")
    )
    if series.height < 2:
        raise ValueError("price frame must contain at least two priced timestamps.")
    return series


def _bt_data_frame(price_frame_path: Path, members: list[dict[str, Any]]) -> Any:
    series = _price_series(price_frame_path)
    data = {str(member["column_id"]): series["price"].to_list() for member in members}
    import pandas as pd

    index = pd.to_datetime(series["ts"].to_list(), utc=True).tz_convert(None)
    return pd.DataFrame(data, index=index)


def _scalar(value: Any) -> float | int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return value
    item = getattr(value, "item", None)
    if callable(item):
        try:
            return _scalar(item())
        except Exception:
            return None
    return None


def _stat(stats: Any, key: str, column: str) -> float | int | None:
    if isinstance(stats, dict):
        nested = stats.get(column)
        if isinstance(nested, dict):
            return _scalar(nested.get(key))
        return _scalar(stats.get(key))
    loc = getattr(stats, "loc", None)
    if loc is not None:
        try:
            return _scalar(loc[key, column])
        except Exception:
            return None
    return None


def _turnover_from_result(result: Any) -> float | None:
    get_security_weights = getattr(result, "get_security_weights", None)
    if not callable(get_security_weights):
        return None
    try:
        weights_frame: Any = get_security_weights()
        weights = weights_frame.fillna(0).diff().abs().sum()
        if isinstance(weights, dict):
            return float(sum(float(value) for value in weights.values()))
        total = weights.sum() if hasattr(weights, "sum") else weights
        scalar = _scalar(total)
        return float(scalar) if scalar is not None else None
    except Exception:
        return None


def _base_payload(
    *,
    candidate: dict[str, Any],
    bundle_path: Path,
    price_frame_path: Path,
    bundle_payload: dict[str, Any],
    allocation_rule_id: str,
    rebalance_cadence: str,
    run_status: str,
    reason_codes: list[str],
    engine_run: bool,
    runner_mode: str,
    portfolio_return: float | int | None = None,
    max_drawdown: float | int | None = None,
    turnover: float | int | None = None,
    rebalance_count: int = 0,
) -> dict[str, Any]:
    members = _member_rows(bundle_payload)
    return {
        "schema_version": "strategy_backtest_portfolio_comparison.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "framework_id": "bt",
        "adapter_role": str(candidate.get("adapter_role") or "portfolio_allocation_candidate"),
        "framework_version": candidate.get("version"),
        "runner_mode": runner_mode,
        "run_status": run_status,
        "reason_codes": reason_codes,
        "dependency_added": False,
        "engine_run": engine_run,
        "source_bundle_path": bundle_path.as_posix(),
        "source_bundle_hash": _sha256_file(bundle_path),
        "price_frame_path": price_frame_path.as_posix(),
        "price_frame_hash": _sha256_file(price_frame_path),
        "allocation_rule_id": allocation_rule_id,
        "rebalance_cadence": rebalance_cadence,
        "portfolio_return": portfolio_return,
        "max_drawdown": max_drawdown,
        "turnover": turnover,
        "rebalance_count": rebalance_count,
        "benchmark_return": None,
        "weight_drift": None,
        "allocation_trace": [
            {
                "column_id": str(member["column_id"]),
                "target_weight": float(member["effective_allocation_weight"]),
            }
            for member in members
        ],
        "members": members,
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "wallet_used": False,
        "exchange_write_used": False,
    }


def _run_bt_payload(
    *,
    candidate: dict[str, Any],
    bundle_path: Path,
    price_frame_path: Path,
    bundle_payload: dict[str, Any],
    allocation_rule_id: str,
    rebalance_cadence: str,
) -> dict[str, Any]:
    try:
        bt = importlib.import_module("bt")
        members = _member_rows(bundle_payload)
        data = _bt_data_frame(price_frame_path, members)
        weights = {
            str(member["column_id"]): float(member["effective_allocation_weight"])
            for member in members
        }
        strategy_name = "strategy_authoring_bt_portfolio"
        strategy = bt.Strategy(
            strategy_name,
            [
                bt.algos.RunAfterDate("1900-01-01"),
                bt.algos.SelectAll(),
                bt.algos.WeighSpecified(**weights),
                bt.algos.Rebalance(),
            ],
        )
        backtest = bt.Backtest(
            strategy,
            data,
            initial_capital=1_000_000.0,
            integer_positions=False,
            progress_bar=False,
        )
        result = bt.run(backtest, progress_bar=False)
        portfolio_return = _stat(result.stats, "total_return", strategy_name)
        max_drawdown = _stat(result.stats, "max_drawdown", strategy_name)
        turnover = _turnover_from_result(result)
    except Exception:
        return _base_payload(
            candidate=candidate,
            bundle_path=bundle_path,
            price_frame_path=price_frame_path,
            bundle_payload=bundle_payload,
            allocation_rule_id=allocation_rule_id,
            rebalance_cadence=rebalance_cadence,
            run_status="failed",
            reason_codes=["framework_run_failed"],
            engine_run=False,
            runner_mode="temporary_or_optional_import",
        )
    return _base_payload(
        candidate=candidate,
        bundle_path=bundle_path,
        price_frame_path=price_frame_path,
        bundle_payload=bundle_payload,
        allocation_rule_id=allocation_rule_id,
        rebalance_cadence=rebalance_cadence,
        run_status="completed",
        reason_codes=[],
        engine_run=True,
        runner_mode="temporary_or_optional_import",
        portfolio_return=portfolio_return,
        max_drawdown=max_drawdown,
        turnover=turnover,
        rebalance_count=1,
    )


def _write_report(path: Path, payload: dict[str, Any]) -> Path:
    lines = [
        "# Strategy Backtest Portfolio Comparison",
        "",
        f"- framework_id: {payload['framework_id']}",
        f"- framework_version: {payload['framework_version']}",
        f"- runner_mode: {payload['runner_mode']}",
        f"- run_status: {payload['run_status']}",
        f"- engine_run: {payload['engine_run']}",
        f"- source_bundle_path: `{payload['source_bundle_path']}`",
        f"- price_frame_path: `{payload['price_frame_path']}`",
        f"- allocation_rule_id: {payload['allocation_rule_id']}",
        f"- rebalance_cadence: {payload['rebalance_cadence']}",
        f"- portfolio_return: {payload['portfolio_return']}",
        f"- max_drawdown: {payload['max_drawdown']}",
        f"- turnover: {payload['turnover']}",
        f"- rebalance_count: {payload['rebalance_count']}",
        "- dependency_added: false",
        "- permits_live_order: false",
        "- wallet_used: false",
        "- exchange_write_used: false",
        "",
        "| Member | Strategy | Weight |",
        "|---:|---|---:|",
    ]
    for member in payload["members"]:
        lines.append(
            "| {member_index} | {strategy_id} | {weight} |".format(
                member_index=member["member_index"],
                strategy_id=member["strategy_id"],
                weight=member["effective_allocation_weight"],
            )
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def build_strategy_backtest_portfolio_comparison(
    *,
    bundle_path: Path,
    price_frame_path: Path,
    out_dir: Path,
    reports_dir: Path,
    allocation_rule_id: str = "fixed_weight",
    rebalance_cadence: str = "initial_only",
) -> BacktestPortfolioComparisonResult:
    if not bundle_path.exists():
        raise FileNotFoundError(f"strategy authoring bundle result missing: {bundle_path}")
    if not price_frame_path.exists():
        raise FileNotFoundError(f"price frame missing: {price_frame_path}")
    bundle_payload = _read_json(bundle_path)
    candidate = _bt_candidate()
    if candidate.get("status") != "installed":
        payload = _base_payload(
            candidate=candidate,
            bundle_path=bundle_path,
            price_frame_path=price_frame_path,
            bundle_payload=bundle_payload,
            allocation_rule_id=allocation_rule_id,
            rebalance_cadence=rebalance_cadence,
            run_status="skipped",
            reason_codes=["not_installed_in_current_env"],
            engine_run=False,
            runner_mode="not_installed_in_current_env",
            turnover=None,
        )
    else:
        payload = _run_bt_payload(
            candidate=candidate,
            bundle_path=bundle_path,
            price_frame_path=price_frame_path,
            bundle_payload=bundle_payload,
            allocation_rule_id=allocation_rule_id,
            rebalance_cadence=rebalance_cadence,
        )
    out_dir.mkdir(parents=True, exist_ok=True)
    comparison_path = out_dir / "strategy_backtest_portfolio_comparison.json"
    comparison_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    report_path = _write_report(
        reports_dir / "strategy_backtest_portfolio_comparison_report.md", payload
    )
    return BacktestPortfolioComparisonResult(
        comparison_path=comparison_path, report_path=report_path, payload=payload
    )
