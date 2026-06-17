<!--
作成日: 2026-06-14_19:58 JST
更新日: 2026-06-18_02:04 JST
-->

# Backtest Non-Goals And Future Scope

## 結論

現在の backtest system completion scope では、ここに書く項目を実装しない。

ただし、これらは「不要」ではない。将来の作業候補として残す。現在のゴールへ混ぜると、data availability、schema、live safety、dependency policy、reproducibility の責務が一気に広がり、backtest system v0 の完成条件が曖昧になるため、明示的に外へ出す。

現行 scope の正本は `strategy_authoring_native` を標準 engine とし、採用済み optional extra は `vectorbt`, `bt`, `metrics`, `reports` に限る。ここで列挙する dependency や venue/data provider を、明示 task なしに `pyproject.toml` / `uv.lock` / CLI / schema / generated artifact へ混ぜない。

## Current Non-Goals

| Non-goal | 現在やらないこと | 将来やるなら最初に決めること |
|---|---|---|
| Bitget / Hyperliquid direct schema widening | `bitget_futures` / `hyperliquid_perp` を現行 backtest / paper artifact の正式 venue にしない。`VenueId`、schemas、paper preview、pack validation を広げない | venue id、account mode、instrument model、order constraint、fee/funding、rate limit、historical data availability、read-only/paper/live 境界 |
| Coinalyze collector | OI / funding / liquidation / long-short data collector を作らない。外部 API key、rate limit、retention、pagination を現行 backtest completion に入れない | data provider contract、raw recorder、retention limit、symbol mapping、`available_at`、source hash、data availability ledger |
| Live / wallet / signing / exchange write | live order、wallet secret、署名、取引所 write endpoint へ接続しない。backtest artifact から live readiness を主張しない | separate live/paper readiness gate、credential policy、kill switch、order intent contract、operator approval、audit log |
| NautilusTrader / HftBacktest / Tardis / PyBroker / Qlib / FinRL / skfolio / Riskfolio-Lib dependency adoption | これらを標準 dependency や optional extra に追加しない。runner 実装、CI 必須化、暗黙 data fetch をしない。HftBacktest / qstrader / skfolio / Riskfolio-Lib / PyBroker は reference-only contract artifact までは作る | isolated spike、license / terms review、Python 3.13 compatibility、local-input-only contract、source hash、failure mode、CI cost、Constraint Breaker decision |
| Replay-style simulation からの market impact claim | HftBacktest 的な market replay、OHLCV replay、quote replay の結果を、自分の注文が市場に与える影響まで再現した証拠として扱わない | calibrated impact model、order size vs liquidity、venue microstructure data、partial fill / cancel race validation、assumption ledger |
| Alpha claim | backtest / framework comparison / report / tear sheet だけで alpha を証明したと言わない | out-of-sample plan、negative control、trial ledger、data availability ledger、no-lookahead differential、paper observation criteria |
| Live readiness claim | pack validation、strategy scorecard、optional framework result、execution simulator v0 だけで live readiness を証明したと言わない | paper observation gate、risk limits、execution monitoring、venue-specific failure handling、credentialed read-only proof、explicit owner approval |

## Future Scope として残す理由

これらは将来価値がある。

- Bitget / Hyperliquid direct schema は、実 venue の execution-aware 検証に必要になる。
- Coinalyze は、OI、funding、liquidation、long-short 系の特徴量検証に必要になる可能性がある。
- Live / wallet / signing / exchange write は、paper observation を越える段階では避けられない。
- NautilusTrader や HftBacktest は、deterministic runtime、event-driven execution、latency、queue、partial fill の設計参考になる。
- PyBroker は、walk-forward、bootstrap、feature / model validation workflow の候補になる。
- Tardis は、historical market data provider または Nautilus integration の候補になる。
- Qlib / FinRL / skfolio / Riskfolio-Lib は、ML quant pipeline、RL environment、portfolio validation methodology の参考になる。

ただし、価値があることと、今の completion scope に入れることは別である。今はまず、local input、source hash、trial ledger、assumption ledger、no-lookahead guard、baseline / negative control、pack validation を完成させる。

## 将来 Reopen する条件

次の条件を満たすまで、この文書の項目を implementation task にしない。

1. 現行 backtest pack が、local artifact だけで再生成できる。
2. data availability ledger が、使える期間、粒度、欠損、source hash、`available_at` を記録している。
3. trial ledger が、成功した trial だけでなく失敗、skipped、parameter sweep、framework comparison を記録している。
4. assumption ledger が、`measured`, `configured`, `assumed`, `unknown` を分けている。
5. no-lookahead differential または同等の未来リーク検査が artifact 化されている。
6. baseline / negative control との比較で、複雑な戦略が単純手法に負けていないことを確認できる。
7. 新しい venue / provider / framework が、標準 engine を置き換えず、local input と source hash を持つ isolated surface として設計されている。
8. license、terms、credential、network、CI cost、Python 3.13 compatibility の確認結果が文書化されている。

## Future Task 化するときの対象ファイル

Bitget / Hyperliquid direct schema widening を再開する場合:

- `src/sis/venues/ids.py`
- `src/sis/venues/capabilities.py`
- `schemas/strategy_*.schema.json`
- `schemas/*paper*.schema.json`
- `src/sis/research/strategy_lab/`
- `src/sis/paper/`
- `tests/strategy_authoring/`
- `tests/test_*venue*`
- `docs/venues/`

Coinalyze collector を再開する場合:

- `src/sis/venues/` または専用 data provider module
- `src/sis/backtest/data_availability.py`
- `schemas/backtest_data_availability_ledger.v1.schema.json`
- `configs/`
- `tests/backtest/`
- `docs/backtest/`

Live / wallet / signing / exchange write を再開する場合:

- `src/sis/execution/`
- `src/sis/risk/`
- `src/sis/paper/`
- `src/sis/commands/execution*.py`
- `configs/env.example`
- `.env.example`
- `tests/test_*execution*`
- `docs/runbooks/` または `docs/venues/`

NautilusTrader / HftBacktest / Tardis / PyBroker / Qlib / FinRL / skfolio / Riskfolio-Lib を再評価する場合:

- `pyproject.toml`
- `uv.lock`
- `src/sis/backtest/`
- `src/sis/commands/strategy_authoring.py`
- `schemas/strategy_backtest_*.schema.json`
- `tests/strategy_authoring/`
- `tests/backtest/`
- `docs/archive/backtest/OPTIONAL_BACKTEST_FRAMEWORK_ADOPTION_REVIEW_2026-06-13.md`
- `docs/archive/backtest/CURRENT_BACKTEST_PLAN_AND_FRAMEWORK_ROLES_2026-06-14.md`
- `docs/backtest/OSS_BACKTEST_CAPABILITY_EXPANSION_IMPLEMENTATION_PLAN_2026-06-15.md`

## 完了条件を混ぜないための禁止事項

- `strategy-backtest-pack-validate` の PASS を、alpha proof と書かない。
- `strategy-backtest-framework-run` の成功を、framework 正式採用や live readiness と書かない。
- `strategy-backtest-microstructure-readiness` / `strategy-backtest-qstrader-contract` / `strategy-backtest-portfolio-validation-contract` / `strategy-backtest-pybroker-contract` の成功を、engine 実行可能や dependency 採用済みと書かない。
- `vectorbt`, `bt`, `empyrical-reloaded`, `quantstats` 以外の package を、owner approval と implementation plan なしに optional extra へ追加しない。
- `bitget_demo` を production Bitget futures として扱わない。
- `bitget_futures` / `hyperliquid_perp` を、schema-disabled のまま正式 venue として artifact に出さない。
- Coinalyze の external API 制約を確認せず、過去データがある前提で backtest 計画を書かない。
- HftBacktest / replay result を market impact の証明として扱わない。
- NautilusTrader や LEAN のような platform を、軽量 adapter と同じ粒度で入れない。
- PyBroker / Qlib / FinRL の外部 data fetch surface を、local reproducible backtest に暗黙混入させない。

## 実務上の読み方

現在の作業者は、この文書の項目を見つけたら次のように扱う。

```text
今のゴール:
  Backtest system completion within local, paper-only, no-live boundaries.

この文書の項目:
  future scope. 今のゴールへ混ぜない。

将来やる場合:
  separate plan, separate tests, separate acceptance, separate safety boundary.
```

この分離により、将来の venue / data / execution / platform work を捨てずに、現在の backtest completion を小さく完了できる。

## 通常レーンで実装済みの reference-only artifact

2026-06-15_21:08 JST 時点では、採用そのものではなく採用可否を判断するための artifact は実装済みである。

- `strategy-backtest-microstructure-readiness`: HftBacktest などの L2/L3/tick replay readiness。
- `strategy-backtest-qstrader-contract`: qstrader の local input contract。
- `strategy-backtest-portfolio-validation-contract`: skfolio / Riskfolio-Lib の portfolio validation contract。
- `strategy-backtest-pybroker-contract`: PyBroker の local DataFrame input contract。
- `strategy-backtest-constraint-breaker-decision`: 制約を破る価値を scorecard で判断する decision artifact。

これらは non-goal を解除しない。解除されるのは「採用前に何が足りないかを artifact で説明できること」だけである。
