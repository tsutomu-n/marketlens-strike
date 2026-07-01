#!/usr/bin/env python3
"""
Romano-Wolf Stepwise Multiple Testing Procedure for Trading Strategy Backtests
Implements FWER control (asymptotically) for multiple candidate strategies vs benchmark.

Context: Backtest Kill Gate enhancement in candidate generation / multiplicity accounting pipeline.
Use after computing periodic returns for shortlisted candidates, before Virtual Execution Gate or Risk-Taker Review.

References:
- Romano, J. P., & Wolf, M. (2005). Stepwise Multiple Testing as Formalized Data Snooping. Econometrica.
- Practical stepdown adjusted p-value construction following common implementations (e.g. Stata rwolf, recent adaptations).

Risks & Limitations (must read before use in production):
- Default is now stationary bootstrap (geometric blocks). Still, mean_block_length choice affects dependence capture. Too small → behaves like iid (under-controls FWER for autocorrelated returns). Too large → low variability, power loss. Daily financial data: start with 10-30 or estimate from ACF significant lags.
- Test statistic choice matters: "t_stat" recommended for raw edge; risk-adjusted (Sharpe etc.) needs studentized bootstrap (future extension).
- Assumes subset pivotality for strong FWER control.
- Computational cost: O(B * T * m). Stationary is slightly slower than iid due to block generation.
- Does NOT replace economic gates (after_cost_edge, stress, concentration, NO_TRADE). Combine them.
- In repo: Add "KILLED_BY_ROMANO_WOLF" to rejection_account / trial_multiplicity_account.
- LLM Adversarial Evidence Review can audit RW output for contradictions/overclaim when candidate volume is high.

Integration suggestion for your Backtest Kill Gate:
After sealed holdout / PBO / FDR pass, before or parallel to Virtual Execution:
  rw_result = romano_wolf_stepwise(periodic_returns_df, strategy_cols, benchmark_col="benchmark_or_zero", ...)
  Then filter candidates where rejected == True, or add kill_reason to ledger.
  This kills strategies that do not show statistically significant edge after accounting for the multiplicity of all candidates tested.

Next improvement ideas (if you want):
- Add block bootstrap (stationary bootstrap with geometric block length).
- Support for precomputed test_stats (e.g. from your selection-adjusted metrics).
- Studentized version (more robust).
- Parallel bootstrap with joblib or multiprocessing.
"""

import polars as pl
import numpy as np
from typing import List, Dict, Optional
import warnings


def _compute_test_stats(excess: np.ndarray, method: str = "t_stat") -> np.ndarray:
    """Compute test statistics for excess returns (T x m array)."""
    if method == "t_stat":
        n = excess.shape[0]
        means = np.nanmean(excess, axis=0)
        stds = np.nanstd(excess, axis=0, ddof=1)
        # Avoid division by zero
        se = stds / np.sqrt(n)
        se = np.where(se == 0, np.nan, se)
        return means / se
    elif method == "mean_excess":
        return np.nanmean(excess, axis=0)
    else:
        raise ValueError(f"Unknown test_stat method: {method}. Use 't_stat' or 'mean_excess'.")


def _stationary_bootstrap_indices(
    T: int, mean_block_length: float, rng: np.random.Generator
) -> np.ndarray:
    """
    Generate T indices using stationary bootstrap (Politis & Romano 1994).
    Blocks have random length ~ Geometric(p=1/mean_block_length), starting points uniform,
    with circular wrapping to preserve stationarity.
    """
    if mean_block_length <= 1:
        mean_block_length = max(mean_block_length, 1.0)
    p = 1.0 / mean_block_length
    indices: list[int] = []
    while len(indices) < T:
        # Block length L >= 1
        L = int(rng.geometric(p))
        start = int(rng.integers(0, T))
        block = [(start + i) % T for i in range(L)]
        indices.extend(block)
    return np.asarray(indices[:T], dtype=np.int64)


def romano_wolf_stepwise(
    returns: pl.DataFrame,
    strategy_cols: List[str],
    benchmark_col: str = "benchmark",
    n_bootstrap: int = 2000,
    alpha: float = 0.05,
    random_state: Optional[int] = 42,
    test_stat: str = "t_stat",
    min_periods: int = 30,
    bootstrap_method: str = "stationary",
    mean_block_length: float = 20.0,
) -> Dict:
    """
    Romano-Wolf stepwise procedure for FWER control in multiple strategy testing.
    Now supports stationary bootstrap (default) for time-series dependence.

    Parameters
    ----------
    returns : pl.DataFrame
        Must contain benchmark_col and all strategy_cols as numeric return columns (period returns, e.g. daily).
    strategy_cols : list of str
        Column names of candidate strategies.
    benchmark_col : str
        Column name for benchmark returns (e.g. risk-free, zero, or market). Excess = strategy - benchmark.
    n_bootstrap : int
        Number of bootstrap replications. 1000-5000 typical.
    alpha : float
        FWER level (e.g. 0.05 or 0.10 for more power in screening).
    random_state : int or None
        Seed for reproducibility.
    test_stat : {"t_stat", "mean_excess"}
        "t_stat" recommended for mean edge detection.
    min_periods : int
        Minimum observations required per strategy.
    bootstrap_method : {"stationary", "iid"}
        "stationary" (default): Politis & Romano stationary bootstrap with geometric block lengths.
        "iid": simple with-replacement row resampling (faster but ignores serial correlation).
    mean_block_length : float
        Mean block length for stationary bootstrap (p = 1/mean_block_length).
        Daily returns: 10-30 typical. Too small ≈ iid, too large reduces variability.
        Data-driven choice (e.g. via significant ACF lag) recommended for production.

    Returns
    -------
    dict with keys:
        decisions : pl.DataFrame
            strategy, obs_stat, adj_pval (Romano-Wolf adjusted), rejected (bool), kill_reason
        killed_strategies : list[str]
        n_rejected : int
        n_tested : int
        summary : str
        params : dict
    """
    rng = np.random.default_rng(random_state)

    if benchmark_col not in returns.columns:
        raise ValueError(f"benchmark_col '{benchmark_col}' not in DataFrame")

    missing = [c for c in strategy_cols if c not in returns.columns]
    if missing:
        raise ValueError(f"strategy_cols not found: {missing}")

    # Extract arrays (handle potential nulls)
    bench_arr = returns[benchmark_col].cast(pl.Float64).to_numpy()
    strat_arr = returns.select([pl.col(c).cast(pl.Float64) for c in strategy_cols]).to_numpy()

    # Filter strategies with enough data
    valid_mask = np.array(
        [np.sum(~np.isnan(strat_arr[:, i])) >= min_periods for i in range(len(strategy_cols))]
    )
    if not np.any(valid_mask):
        warnings.warn("No strategies have sufficient observations.")
        return {
            "decisions": pl.DataFrame(
                {
                    "strategy": strategy_cols,
                    "obs_stat": np.nan,
                    "adj_pval": 1.0,
                    "rejected": False,
                    "kill_reason": "INSUFFICIENT_DATA",
                }
            ),
            "killed_strategies": strategy_cols,
            "n_rejected": 0,
            "n_tested": len(strategy_cols),
            "summary": "All strategies killed due to insufficient data.",
            "params": {"n_bootstrap": n_bootstrap, "alpha": alpha, "test_stat": test_stat},
        }

    valid_strats = [s for s, v in zip(strategy_cols, valid_mask) if v]
    if len(valid_strats) < len(strategy_cols):
        warnings.warn(
            f"{len(strategy_cols) - len(valid_strats)} strategies dropped due to < {min_periods} observations."
        )

    strat_arr = strat_arr[:, valid_mask]
    excess = strat_arr - bench_arr[:, np.newaxis]
    T, m = excess.shape

    if m == 0:
        return {"error": "no valid strategies after filtering"}

    # Observed test statistics
    obs_stats = _compute_test_stats(excess, method=test_stat)

    # Bootstrap generation
    boot_stats = np.empty((n_bootstrap, m))
    if bootstrap_method == "iid":
        for b in range(n_bootstrap):
            idx = rng.choice(T, size=T, replace=True)
            boot_excess = excess[idx]
            boot_stats[b] = _compute_test_stats(boot_excess, method=test_stat)
    elif bootstrap_method == "stationary":
        for b in range(n_bootstrap):
            idx = _stationary_bootstrap_indices(T, mean_block_length, rng)
            boot_excess = excess[idx]
            boot_stats[b] = _compute_test_stats(boot_excess, method=test_stat)
    else:
        raise ValueError(f"bootstrap_method must be 'stationary' or 'iid', got {bootstrap_method}")

    # Romano-Wolf stepdown adjusted p-values (monotonic)
    # Order hypotheses by observed statistic descending (largest/most significant first)
    order = np.argsort(obs_stats)[::-1]
    sorted_obs = obs_stats[order]

    adj_p_sorted = np.ones(m)
    for k in range(m):
        # Max bootstrap statistic among the k most significant (by observed ranking)
        cols_k = order[: k + 1]
        if k == 0:
            max_boot = np.nanmax(boot_stats, axis=1)
        else:
            max_boot = np.nanmax(boot_stats[:, cols_k], axis=1)
        # Raw p for this step: fraction of bootstrap where max >= observed k-th
        raw_p = np.nanmean(max_boot >= sorted_obs[k])
        # Enforce monotonicity (stepdown property)
        adj_p_sorted[k] = max(adj_p_sorted[k - 1], raw_p) if k > 0 else raw_p

    # Map adjusted p-values back to original column order
    adj_p = np.empty(m)
    adj_p[order] = adj_p_sorted

    # Decisions
    rejected = adj_p < alpha

    # Build output DataFrame (only valid strategies; others marked separately if needed)
    kill_reasons = []
    for r, p in zip(rejected, adj_p):
        if r:
            kill_reasons.append(None)  # survived
        else:
            kill_reasons.append("KILLED_BY_ROMANO_WOLF")

    result_df = pl.DataFrame(
        {
            "strategy": valid_strats,
            "obs_stat": obs_stats,
            "adj_pval": adj_p,
            "rejected": rejected,
            "kill_reason": kill_reasons,
        }
    )

    killed = [s for s, r in zip(valid_strats, rejected) if not r]
    n_rej = int(np.sum(rejected))

    summary = (
        f"Romano-Wolf stepwise FWER control (alpha={alpha}, B={n_bootstrap}, stat={test_stat}): "
        f"{n_rej}/{m} strategies rejected (significant edge after multiplicity correction). "
        f"{len(killed)} killed by RW. "
        "Use in combination with economic gates (after_cost, stress, concentration, NO_TRADE)."
    )

    return {
        "decisions": result_df.sort("obs_stat", descending=True),
        "killed_strategies": killed,
        "n_rejected": n_rej,
        "n_tested": m,
        "summary": summary,
        "params": {
            "n_bootstrap": n_bootstrap,
            "alpha": alpha,
            "test_stat": test_stat,
            "random_state": random_state,
            "min_periods": min_periods,
        },
    }


# --------------------------- Example & Quick Test ---------------------------
if __name__ == "__main__":
    print("=== Romano-Wolf Stepwise Example (synthetic data) ===")
    np.random.seed(42)
    T = 750  # ~3 years daily
    n_strat = 30

    # Benchmark ~ 0.0005 daily drift, 1% vol
    bench = np.random.normal(0.0005, 0.01, T)

    # Strategies: first 8 have true edge (+0.001 daily), rest pure noise around benchmark
    strats = np.random.normal(0.0005, 0.01, (T, n_strat))
    strats[:, :8] = strats[:, :8] + 0.001  # true edge group

    df = pl.DataFrame(
        {"benchmark": bench} | {f"candidate_{i:02d}": strats[:, i] for i in range(n_strat)}
    )

    res = romano_wolf_stepwise(
        df,
        strategy_cols=[f"candidate_{i:02d}" for i in range(n_strat)],
        benchmark_col="benchmark",
        n_bootstrap=1000,
        alpha=0.05,
        test_stat="t_stat",
        random_state=42,
    )

    print(res["summary"])
    print("\nTop 10 by obs_stat (should see the true edge ones rejected/survive more):")
    print(res["decisions"].head(10))
    print(f"\nKilled by RW: {len(res['killed_strategies'])} strategies")
    print("Example killed:", res["killed_strategies"][:5] if res["killed_strategies"] else "None")

    print("\n=== Integration note for your repo ===")
    print("In Backtest Kill Gate (after sealed_holdout / PBO / FDR):")
    print(
        "  rw = romano_wolf_stepwise(periodic_returns_ledger_df, candidate_list, benchmark_col=..., n_bootstrap=2000, alpha=0.10)"
    )
    print(
        "  Then update trial_multiplicity_account and rejection_account with rw['killed_strategies'] and 'KILLED_BY_ROMANO_WOLF'"
    )
    print("  Pass only rw['decisions'].filter(pl.col('rejected')) to Virtual Execution Gate.")
    print(
        "This kills non-significant (after multiplicity) candidates early, reducing verification backlog and lucky winner risk."
    )
