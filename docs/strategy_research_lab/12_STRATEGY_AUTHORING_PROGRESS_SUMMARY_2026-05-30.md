# Strategy Authoring Progress Summary 2026-05-30

この文書は、2026-05-30 時点で進めた Strategy Authoring 周りの調査・実装・ドキュメント更新を、コードを正として整理したものです。

正本は次です。

- `src/sis/research/strategy_lab/authoring.py`
- `src/sis/backtest/bridge.py`
- `src/sis/backtest/signals.py`
- `src/sis/research/strategy_lab/signal_artifact.py`
- `src/sis/research/strategy_lab/signal_frame.py`
- `src/sis/research/strategy_lab/specs.py`
- `src/sis/research/strategy_lab/candidates.py`
- `schemas/strategy_authoring_spec.v1.schema.json`
- `schemas/strategy_signal.v1.schema.json`
- `schemas/trade_candidate.v1.schema.json`
- `tests/test_strategy_authoring.py`

## 結論

ユーザーが YAML で売買ロジックを作るための機能は、paper-only の Strategy Lab flow として実装済みです。

作れる範囲は、entry、long / short、hold、close、reduce、add、rebalance、損切、利確、部分利確、stop/target width guard、reward/risk gate with row threshold、トレーリングストップ、activation threshold、row-level minimum / maximum holding period、row-level slippage / partial-fill / min-fill / spread gate、bracket / OCO 的 lifecycle、row-level partial-profit break-even、row-level bracket time stop、fixed-or-row-level entry type / offset / time-in-force / timeout / post-only と reduce-only paper order constraint、position sizing、portfolio exposure、turnover budget、data guard presets / row thresholds、risk throttle profiles / row thresholds / cooldown、multi-timeframe confirmation、event window、cross-sectional rotation、multi-leg / pair trade with fixed-or-row-level leg-specific exits, order, and execution overrides、parameter sweep、bundle comparison、paper backtest、paper-preview です。

今回の追加で、`rules.order.entry_type_column` / `limit_offset_bps_column` / `stop_offset_bps_column` により、venue、symbol、signal ごとに market / limit / stop-market と offset を変えられるようになりました。固定の `entry_type` / `limit_offset_bps` / `stop_offset_bps` は fallback として残ります。

## 追加・整理した主要機能

| 領域 | 追加・整理した内容 | 代表 surface |
| --- | --- | --- |
| Signal lifecycle | entry だけでなく hold / close / reduce / add / rebalance と小さい drift の band skip を明確化。 | `rules.entry`, `rules.hold`, `rules.close`, `rules.reduce`, `rules.add`, `rules.rebalance` |
| Long / short | fixed side、column side、auto side、long / short 条件分岐を整理。 | `rules.side`, `rules.side_column`, `rules.long_entry`, `rules.short_entry` |
| Exit / risk | stop loss、take profit、stop/target width guard、reward/risk gate with row threshold、partial take profit、trailing stop with optional activation、minimum hold、maximum hold、row-level holding period、exit priority、bracket、row-level bracket break-even/time stop、row-level partial-profit break-even を整理。 | `rules.exit.*`, `rules.bracket.*` |
| Order simulation | 固定または row ごとの market / limit / stop-market、row-level offset、GTC / GTD / IOC / FOK、row-level timeout、row-level post-only limit、reduce-only の paper constraint を整理。 | `rules.order.*` |
| Portfolio constraints | total / long / short / net / symbol / group / group-net exposure cap、row-level exposure cap、timestamp turnover budget、固定または row 由来の allocation target を整理。 | `rules.portfolio.*` |
| Risk throttle / data guard | conservative / strict profile、固定または row-level の drawdown、daily loss、loss streak threshold、risk throttle cooldown、fixed or row-level freshness、source / venue quality、staleness、regime transition で新規 paper signal を止める。 | `rules.risk_throttle.*`, `rules.data_guard.*` |
| Position state | 同一 symbol の仮想 open signal 数と open weight を制限。 | `rules.position.*` |
| Cross-sectional | top / bottom n、fraction tail、group rotation、min candidates、score threshold を整理。 | `rules.cross_sectional.*` |
| Multi-leg | anchor signal から複数 leg の paper signal を展開し、leg ごとに固定または row-level の stop/take/trailing/partial exit 幅、order style、execution quality を変えられる。同じ anchor から出た leg 群は `multi_leg_group_id` で追跡でき、backtest summary で group 合算も確認できる。 | `rules.multi_leg.*` |
| Derived features | trend、mean reversion、breakout、pair、benchmark active risk、Kelly / VaR / expected shortfall、percentile-rank / skew / kurtosis、microstructure、capacity、quality 系 feature を YAML で生成。 | `rules.derived_features` |
| Execution quality | slippage with row cost、partial fill with row fill、min-fill gate with row threshold、spread、depth、latency、queue、borrow、tax、turnover、capacity、crowding、fee edge を paper-only に整理。 | `rules.execution.*` |
| Model score | paper-only 線形 score と train-model adapter を整理。 | `rules.score.model_score`, `strategy-author-train-model` |
| Temporal / event | 曜日、時間帯、cooldown、symbol 日次上限、event allow/block window を整理。 | `rules.temporal.*`, `rules.event_windows.*` |
| Optimizer / bundle | parameter sweep と multi-spec bundle comparison を整理。 | `optimizer.parameter_sweep`, `strategy_authoring_bundle.v1` |

## Execution quality の現状

| Gate | できること | Block reason |
| --- | --- | --- |
| Spread | entry quote の spread が固定または row ごとの上限を超える trade を除外。 | `microstructure_spread_too_wide` |
| Depth | depth 欠損、固定または row ごとの必要額不足を除外し、depth participation で paper exposure を縮小。 | `microstructure_depth_missing`, `microstructure_depth_too_low` |
| Latency | snapshot latency が欠損、または固定 / row ごとの上限超過なら除外。 | `microstructure_latency_missing`, `microstructure_latency_too_high` |
| Queue position | snapshot queue score が欠損、または固定 / row ごとの閾値未満なら除外。 | `microstructure_queue_position_missing`, `microstructure_queue_position_too_low` |
| Short borrow | short signal だけ borrow availability / borrow cost を評価。 | `short_borrow_availability_missing`, `short_borrow_availability_too_low`, `short_borrow_cost_missing`, `short_borrow_cost_too_high` |
| Tax drag | tax drag が欠損、または固定 / row ごとの上限超過なら除外。 | `tax_drag_missing`, `tax_drag_too_high` |
| Turnover pressure | turnover pressure が欠損、または固定 / row ごとの上限超過なら除外。 | `turnover_pressure_missing`, `turnover_pressure_too_high` |
| Capacity usage | capacity usage が欠損、または固定 / row ごとの上限超過なら除外。 | `capacity_usage_missing`, `capacity_usage_too_high` |
| Correlation crowding | correlation crowding が欠損、または固定 / row ごとの上限超過なら除外。 | `correlation_crowding_missing`, `correlation_crowding_too_high` |
| Fee edge | maker/taker fee edge が欠損、または固定 / row ごとの閾値未満なら除外。 | `fee_edge_missing`, `fee_edge_too_low` |

## 実装で同期した artifact surface

今回の機能は、単に YAML model へ足しただけではなく、次まで同期しています。

- authoring spec validation
- required feature column detection
- signal row generation
- `StrategySignalRecord`
- canonical signal artifact schema
- `ResearchSignal` loader
- backtest bridge entry gate
- paper preview candidate field propagation
- JSON Schema guard
- targeted tests
- current docs

## 使える CLI

```bash
uv run sis strategy-author-init --out docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml
uv run sis strategy-author-validate --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml
uv run sis strategy-author-explain --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml
uv run sis strategy-author-run --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml --through backtest
uv run sis strategy-author-run --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml --through paper-preview
uv run sis strategy-author-bundle-run --bundle docs/strategy_research_lab/examples/multi_strategy_authoring_bundle.yaml
```

## Paper-only boundary

できることは、研究用 signal artifact、fixed-horizon backtest、candidate pack、promotion decision、paper intent preview までです。

できないことは次です。

- live order submission
- wallet signing
- exchange write API
- broker / exchange の実 position を読む portfolio rebalance
- live multi-leg order
- live OCO / bracket order
- broker queue priority を再現する order book event replay
- `PromotionDecision` から live trading へ進む自動導線
- Strategy Lab artifact だけを根拠にした profitability / paper-ready / live-ready claim

## ドキュメント整理

現時点の読み分けは次です。

1. [09_STRATEGY_AUTHOR_GUIDE.md](09_STRATEGY_AUTHOR_GUIDE.md): YAML を書くユーザー向けの実務ガイド。
2. [11_STRATEGY_AUTHORING_CURRENT_SUMMARY.md](11_STRATEGY_AUTHORING_CURRENT_SUMMARY.md): 何が作れるかの一覧。
3. [10_STRATEGY_AUTHORING_IMPLEMENTATION_SPEC.md](10_STRATEGY_AUTHORING_IMPLEMENTATION_SPEC.md): 実装・validation・schema 契約。
4. [08_CURRENT_CAPABILITIES.md](08_CURRENT_CAPABILITIES.md): Strategy Research Lab 全体で今できること。
5. この文書: 今回までの進捗、追加領域、paper-only 境界の整理。

## 検証済み

2026-05-31 の最終確認値です。

- `uv run pytest tests/test_strategy_authoring.py tests/test_strategy_lab_schemas.py -q`: `204 passed`
- `uv run python scripts/check_current_docs.py`: `checked 78 current docs: links, EOF, and legacy roots ok`
- `./scripts/check`: pass, pytest `586 passed`, pyrefly `0 errors`

## 残る範囲

残る範囲は、Strategy Authoring の paper research 能力ではなく、live execution や venue realism 側です。

- full order book event replay
- broker / exchange queue priority の再現
- live portfolio optimizer / rebalance execution
- live order submission
- wallet signing
- exchange write API
- production risk control と監視

これらは Strategy Lab の paper-only 境界外です。実装する場合は、別の live-readiness 設計と安全 gate が必要です。
