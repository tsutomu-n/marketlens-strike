# Strategy Authoring Completion Evidence Ledger

この文書は、active goal「生成しうるストラテジーについて考えうるすべてに対応させて。」に対する completion evidence ledger です。

結論: 現行 repo では、Strategy Authoring が対象にする paper-only の strategy generation / signal generation / fixed-horizon backtest / paper-preview / multi-strategy bundle comparison について、考えうる主要 archetype は `13_STRATEGY_ARCHETYPE_COVERAGE_MATRIX.md` に列挙され、コード・schema・test・docs・example で確認済みです。

## Scope

対象範囲は次です。

- `strategy_authoring_spec.v1` YAML からの declarative strategy authoring。
- Strategy Lab signal artifact generation。
- fixed-horizon paper backtest。
- paper-only scorecard / candidate / promotion / intent preview propagation。
- multi-leg / pair / hedge / basket paper signal expansion and group metrics。
- multi-strategy bundle comparison with fixed / equal / risk-parity allocation。
- JSON Schema guard for public authoring artifacts.

対象外は次です。

- live order submission。
- wallet signing。
- exchange write。
- broker-state live rebalance。
- live atomic multi-leg execution。
- live OCO / bracket order placement。
- full order book event replay / venue queue replay。
- profitability claim / live-ready claim。
- arbitrary user Python / formula execution。
- external model artifact loading / pickle execution。

These exclusions are explicitly recorded in `docs/strategy_research_lab/13_STRATEGY_ARCHETYPE_COVERAGE_MATRIX.md` under `Coverage Boundaries`.

## Coverage Matrix Evidence

Authoritative matrix:

- `docs/strategy_research_lab/13_STRATEGY_ARCHETYPE_COVERAGE_MATRIX.md`

Coverage rows marked supported:

- Trend following / moving average cross.
- Momentum / relative strength.
- Mean reversion.
- Breakout / channel / volatility breakout.
- Volatility filter / volatility targeting.
- Pair trade / spread / relative value.
- Hedge / basket / multi-leg strategy.
- Long / short fixed direction.
- Long / short row-driven direction.
- Cross-sectional top-bottom rotation.
- Group-aware rotation.
- Dollar-neutral / beta-neutral / group-neutral portfolio.
- Event-driven / calendar-window strategy.
- Regime-aware strategy.
- Quality / ensemble / composite factor.
- Flow / carry / funding / liquidity.
- Options / skew / volatility risk premium as feature-driven paper signal.
- On-chain / sentiment / fundamental event factor as feature-driven paper signal.
- Execution-aware strategy.
- Risk-throttled strategy.
- Position-state strategy.
- Reversal / close / reduce / add / rebalance lifecycle.
- Stop-loss / take-profit / trailing / partial exit.
- Bracket / OCO-like lifecycle, paper-only.
- Market / limit / stop-market order simulation, paper-only.
- Parameter sweep / optimizer.
- Multi-strategy bundle comparison.

Signal lifecycle rows marked supported:

- Entry long / short.
- Hold / no-trade.
- Explicit close.
- Reduce.
- Add.
- Rebalance.

Mechanical evidence check:

```bash
uv run python - <<'PY'
from pathlib import Path
import re
matrix = Path('docs/strategy_research_lab/13_STRATEGY_ARCHETYPE_COVERAGE_MATRIX.md').read_text()
tests = "\n".join(
    path.read_text()
    for path in Path('tests/strategy_authoring').glob('test_*.py')
)
missing=[]
for name in sorted(set(re.findall(r'`(test_[a-zA-Z0-9_]+)`', matrix))):
    if f'def {name}(' not in tests:
        missing.append(name)
print('missing_count', len(missing))
for name in missing:
    print(name)
PY
```

Observed result:

```text
missing_count 0
```

## Code Evidence

Primary implementation files:

- `src/sis/research/strategy_lab/authoring/`
- `src/sis/research/strategy_lab/specs.py`
- `src/sis/research/strategy_lab/signal_artifact.py`
- `src/sis/research/strategy_lab/signal_frame.py`
- `src/sis/research/strategy_lab/candidates.py`
- `src/sis/backtest/bridge.py`
- `src/sis/backtest/signals.py`

Important implemented surfaces:

- Declarative condition DSL with all / any / none and column-to-column comparisons.
- Strategy-local derived features for trend, mean-reversion, breakout, volatility, cross-asset, flow, carry, liquidity, options-vol, on-chain, sentiment, event, factor, execution constraints, quality, ensemble, capacity, drawdown, turnover, crowding, lag, EMA, RSI, rolling statistics, and group cross-sectional transforms.
- Entry / hold / close / reduce / add / rebalance signal rows.
- Long / short / side-column / long-entry / short-entry branching.
- Cross-sectional rotation and grouped rotation.
- Portfolio exposure controls including dollar-neutral, beta-neutral, group-neutral, target weight, inverse-vol, and volatility targeting.
- Position-state controls including markers, pyramiding, opposing-side constraints, and close-marker release.
- Risk throttle, data guard, temporal filters, event windows, regime overrides.
- Stop-loss, take-profit, trailing stop, partial exit, min/max holding period, reward-risk guard, stop/target width guard, exit priority.
- Paper bracket / OCO-like lifecycle with break-even and time stop.
- Paper market / limit / stop-market entry style, TIF, timeout, post-only, reduce-only, fill fraction, spread/depth/latency/queue/borrow/tax/turnover/capacity/crowding/fee gates.
- Multi-leg expansion with per-leg side, position weight, notional, exit, order, and execution overrides.
- Multi-leg group metrics including group return, win rate, drawdown, profit factor, leg imbalance, total notional, notional-weighted return, and exit reason counts.
- Compact `summary.executed_signal_summary` and `summary.strategy_scorecard`.
- Optimizer parameter sweep with fixed allowed paths and `selection_direction: auto`.
- Bundle comparison with fixed / equal / risk-parity allocation and member summary dotted metric selection.

## Schema Evidence

Public artifact schemas:

- `schemas/strategy_authoring_spec.v1.schema.json`
- `schemas/strategy_authoring_bundle.v1.schema.json`
- `schemas/strategy_authoring_backtest_result.v1.schema.json`
- `schemas/strategy_authoring_bundle_result.v1.schema.json`
- `schemas/strategy_signal.v1.schema.json`
- `schemas/trade_candidate.v1.schema.json`
- `schemas/paper_candidate_pack.v1.schema.json`
- `schemas/promotion_decision.v1.schema.json`
- `schemas/paper_intent_preview.v1.schema.json`
- `schemas/trial_record.v1.schema.json`

Schema guard test:

- `tests/test_strategy_lab_schemas.py`

Covered guards:

- Paper-only flags remain false / true as appropriate.
- `strategy_authoring_backtest_result.v1` fixes `summary.executed_signal_summary`, `summary.multi_leg_group_metrics`, and `summary.strategy_scorecard` public surfaces.
- `strategy_authoring_bundle_result.v1` fixes `portfolio.resolved_selection_direction` and bundle-level multi-leg notional metrics.

## User-Facing Examples

Examples available under `docs/strategy_research_lab/examples/`:

- `trend_pullback_authoring_spec.yaml`: simple trend / pullback authoring spec.
- `multi_strategy_authoring_bundle.yaml`: minimal multi-strategy bundle.
- `pair_hedge_notional_authoring_spec.yaml`: dynamic notional-aware pair / hedge spec.
- `pair_hedge_conservative_authoring_spec.yaml`: conservative pair / hedge variant.
- `notional_pair_hedge_bundle.yaml`: notional-weighted pair / hedge bundle comparison.

Example parse guard:

- `tests/strategy_authoring/test_contracts_validation.py::test_strategy_authoring_example_specs_and_bundles_parse`

This test loads all `*_authoring_spec.yaml` examples, all `*bundle.yaml` examples, and verifies bundle member references exist.

## Risk Term Audit

Command:

```bash
rg -n "TODO|FIXME|unsupported|not supported|not implemented|future|stub|pass #|raise NotImplementedError" src/sis/research/strategy_lab src/sis/backtest tests docs/strategy_research_lab
```

Observed categories:

- Intentional fail-closed validation, such as unsupported `exit_priority`, unsupported optimizer path, unsupported `selection_direction`, unsupported order columns.
- Explicit out-of-scope boundaries in `13_STRATEGY_ARCHETYPE_COVERAGE_MATRIX.md`.
- Historical / generic Strategy Lab docs mentioning future runner or older paper-intent context.
- No uncovered paper-only strategy archetype was identified by this audit.

## Verification Ledger

Final verification commands passed in the current worktree:

```bash
uv run pytest tests/strategy_authoring/test_contracts_validation.py::test_strategy_authoring_example_specs_and_bundles_parse -q
uv run pytest tests/strategy_authoring tests/test_strategy_lab_schemas.py -q
uv run python scripts/check_current_docs.py
git diff --check
./scripts/check
```

Observed results:

- `test_strategy_authoring_example_specs_and_bundles_parse`: `1 passed`
- `tests/strategy_authoring tests/test_strategy_lab_schemas.py`: `214 passed`
- `scripts/check_current_docs.py`: `checked 77 current docs: links, EOF, and legacy roots ok`; after adding the 2026-05-31 docs audit, current docs lint was `checked 78 current docs: links, EOF, and legacy roots ok`; after adding Trade[XYZ] pure backtest docs, current docs lint is `checked 81 current docs: links, EOF, and legacy roots ok`
- `git diff --check`: no output
- `./scripts/check`: ruff pass, ruff format pass, docs lint pass, pyrefly `0 errors`, pytest `650 passed`

## Completion Judgment

Within the declared paper-only Strategy Authoring scope, the objective is satisfied:

- Main generated strategy archetypes are listed and backed by code/test evidence.
- Entry, hold, close, reduce, add, rebalance, stop-loss, take-profit, trailing, partial exit, bracket, optimizer, bundle, and multi-leg notional-aware strategies are implemented and tested.
- Public artifacts have schema guards.
- High-functionality pair / hedge / notional workflows have copyable examples.
- Live execution and profitability claims are explicitly excluded rather than silently implied.

The remaining non-goals are not implementation gaps for this objective because they are outside the paper-only Strategy Authoring contract.
