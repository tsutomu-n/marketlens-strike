# Phase Progression Criteria

## Purpose

この文書は、`marketlens-strike` における各 Phase の進行条件を正式に定義する。

ここでの進行条件は、単にコードが存在するかどうかではない。  
各 Phase は、**前 Phase の成果物が evidence 付きで再現可能に生成され、次 Phase の入力として使える状態になったか** で判定する。

## Core Rule

各 Phase を次へ進めるには、最低限次の 4 点が必要である。

1. 成果物が生成される
2. テストまたは検証が通る
3. Go/No-Go または phase report が出る
4. EvidenceCard / manifest / report により再現可能性が残る

逆に、次の状態では進めない。

- 手元では動いたが artifact がない
- 成果物はあるが schema validation や品質診断がない
- backtest 結果だけあり、入力データ品質が不明
- 実行条件が曖昧
- 失敗時の blocker が分類されていない

## Current Status

**2026-05-24 JST 時点の current repo は、運用上 Phase 1 として扱う。**

理由:

- repo には Phase 1 実装の多くがすでにある
- しかし live evidence quality gate はまだ閉じている
- 現在の Go/No-Go は `CONDITIONAL_GO_NEEDS_LIVE_WINDOW`

したがって、Phase 2 本実装はまだ正式着手扱いにしない。

## Phase 1 -> Phase 2

### Phase 1 Name

Venue Evidence Engine

### Objective

```txt
gTrade / Ostium が QQQ / SPY / XAU の 4h〜3d 研究に使える venue かを実測で判定する
```

### Phase 1 Completion Artifacts

```txt
data/raw/sidecar/gtrade/YYYY-MM-DD.jsonl
data/raw/sidecar/gtrade-pricing/YYYY-MM-DD.jsonl
data/raw/quotes/gtrade/YYYY-MM-DD.jsonl
data/raw/quotes/ostium/YYYY-MM-DD.jsonl
data/normalized/quotes.parquet
data/normalized/sis.duckdb
data/research/venue_cost_matrix.csv
data/research/go_no_go_report.md
data/evidence/evidence_card_*.json
logs/live_evidence/manifests/*.json
```

### Required To Enter Phase 2

```txt
- just check が通る
- CI が通る
- refresh_live_evidence が推奨 window で完走する
- gTrade QQQ / SPY / XAU の mark_price / index_price が取れる
- stale_rate が閾値以下
- tradable_rate が閾値以上
- missing_mark_price_rate / missing_index_price_rate が許容範囲内
- spread_p90_bps が許容範囲内
- validate-artifacts --strict が通る
- Go/No-Go が GO または CONDITIONAL_GO_NEEDS_SIGNAL_BACKTEST
```

### Must Not Enter Phase 2 If

```txt
- CONDITIONAL_GO_NEEDS_LIVE_WINDOW のまま
- NO_GO_STALE
- NO_GO_SESSION
- NO_GO_COST
- mark/index price が欠損する
- quote 取得はできるが診断値が悪い
```

### Operational Interpretation

```txt
Phase 1 完成:
  venue 研究基盤として使える

Phase 1 未完成:
  研究データを増やしても、実執行先としての信頼性が不明
```

## Phase 2 -> Phase 3

### Phase 2 Name

Research Layer

### Objective

```txt
QQQ / SPY / XAU のシグナル研究に必要な価格・マクロ・イベント・特徴量・初期 signal データを集める
```

### Phase 2 Completion Artifacts

```txt
data/research/market_panel.parquet
data/research/macro_panel.parquet
data/research/event_calendar.parquet
data/research/feature_panel.parquet
data/research/signals.csv
docs/RESEARCH_DATA_STRATEGY.md
```

### OSS Baseline

```txt
価格:
  yfinance primary
  yahooquery fallback

金利・マクロ:
  fredapi primary
  pandas-datareader fallback

イベント:
  CSV first
```

### Required To Enter Phase 3

```txt
- yfinance / yahooquery で QQQ / SPY / GLD / ^VIX / UUP / FX proxy が取れる
- fredapi / pandas-datareader で DGS10 / DGS2 / T10Y2Y / FEDFUNDS が取れる
- event_calendar.csv から event_calendar.parquet が生成される
- feature_panel.parquet が生成される
- signals.csv が再現可能に自動生成される
- 欠損率・時刻・timezone・future leak リスクを research_quality report で確認できる
- market_panel / macro_panel / event_calendar / feature_panel / signals の schema が固定される
```

### Must Not Enter Phase 3 If

```txt
- research price と venue execution price が混同されている
- FRED 系列の release date / vintage issue を無視している
- event_calendar の時刻が UTC / JST / ET で曖昧
- 欠損や重複を診断していない
- signals.csv が手作業依存で再現不能
```

### Operational Interpretation

```txt
Phase 2 完成:
  シグナルを作る材料が揃った

Phase 2 未完成:
  strategy を作っても、入力データの信頼性が不明
```

## Phase 3 -> Phase 4

### Phase 3 Name

Decision Engine

### Objective

```txt
Backtest / Paper / Live で同じ意思決定モデルを使う
```

### Phase 3 Completion Artifacts

```txt
src/sis/core/context.py
src/sis/core/decision.py
src/sis/core/strategy.py
src/sis/core/risk_gate.py
src/sis/core/execution_plan.py
data/evidence/decision_logs/*.jsonl
data/research/decision_summary.json
```

### Required Models

```txt
StrategyDecision
RiskDecision
ExecutionPlan
DecisionContext
```

### Required To Enter Phase 4

```txt
- StrategyDecision が定義されている
- RiskDecision が定義されている
- ExecutionPlan が定義されている
- DecisionContext が定義されている
- stale / spread / session / event / scalping / cost の risk gate が共通化されている
- backtest mode で Decision Engine を呼べる
- paper/live 用に同じ Decision Engine を使える設計になっている
- decision log artifact が共通 schema で出る
- blocked reason / selected action / risk decision が追える
- backtest report または companion summary で decision summary が出る
```

### Phase 3 Evidence Requirement

Phase 3 では、Evidence 要件を次のように切る。

必須:

- decision log artifact が出る
- decision log schema が固定される
- backtest 側で decision summary が出る
- `StrategyDecision` / `RiskDecision` / `ExecutionPlan` の trace が残る

まだ必須にしない:

- paper/live の長期永続運用ログ
- 監視通知
- daemon 運用前提の observability 一式

この線引きにより、Phase 3 の責務を「意思決定の共通化」に保ち、Phase 5/6 の運用責務を先食いしない。

### Must Not Enter Phase 4 If

```txt
- backtest 専用ロジックと paper/live 用ロジックが分離している
- signal_builder が直接発注判断まで持っている
- risk gate が複数箇所に分散している
- evidence に StrategyDecision / RiskDecision が残らない
```

### Operational Interpretation

```txt
Phase 3 完成:
  将来 paper/live に移植できる判断エンジンができた

Phase 3 未完成:
  backtest で勝っても、paper/live でロジック乖離が起きる
```

## Phase 4 -> Phase 5

### Phase 4 Name

Signal-driven Backtest

### Objective

```txt
4h / 1d / 3d のシグナルが、venue コスト込みで成立するか検証する
```

### Phase 4 Completion Artifacts

```txt
data/research/feature_panel.parquet
data/research/signals.csv
data/research/backtest_report.md
data/research/backtest_metrics.json
data/research/go_no_go_report.md
data/evidence/evidence_card_*.json
```

### Initial Strategy Scope

```txt
QQQ 4h / 1d:
  trend + VIX + DGS10 + event blackout + venue quality gate
```

### Required To Enter Phase 5

```txt
- feature_panel.parquet が生成される
- signals.csv が自動生成される
- 1m / 5m signal が生成されない
- event blackout 中は signal が出ない
- venue_quality_ok でないと signal が出ない
- signal-driven backtest が走る
- quote-to-quote fallback ではなく signals.csv が主入力になる
- cost_matrix のコストが backtest へ反映される
- trade_count が最低限ある
- avg_trade_return がコスト控除後で正
- max_drawdown が許容範囲
- halt_rejected / stale_rejected が過剰でない
```

### Must Not Enter Phase 5 If

```txt
- quote-to-quote fallback で良い結果が出ただけ
- signals.csv が手作業で再現性がない
- backtest がコスト抜き
- event blackout が未反映
- trade_count が極端に少ない
- 4h〜3d ではなく短期でしか成立しない
```

### Operational Interpretation

```txt
Phase 4 完成:
  paper trading へ進む戦略候補がある

Phase 4 未完成:
  実時間運用しても、検証済みの意思決定がない
```

## Phase 5 -> Phase 6

### Phase 5 Name

Paper Trading Engine

### Objective

```txt
実注文なしで、実時間の意思決定・状態管理・PnL を回す
```

### Phase 5 Completion Artifacts

```txt
src/sis/paper/broker.py
src/sis/paper/portfolio.py
src/sis/paper/fills.py
src/sis/paper/report.py
data/state/marketlens.sqlite
data/paper/orders.parquet
data/paper/positions.parquet
data/paper/fills.parquet
data/paper/daily_pnl.parquet
data/reports/daily_paper_report.md
```

### Required To Enter Phase 6

```txt
- paper mode で signal を受け取れる
- RiskGate を通過した signal だけ paper position になる
- entry / exit / close が仮想で記録される
- paper PnL が日次で出る
- blocked trade log が出る
- missed trade log が出る
- 再起動しても paper state を復元できる
- 30 日以上、手動介入なしで paper run できる
- paper result と backtest result の乖離を説明できる
```

### Must Not Enter Phase 6 If

```txt
- paper state がメモリだけ
- 再起動でポジションが消える
- blocked 理由が記録されない
- daily loss / exposure / event blackout が効かない
- paper と backtest の乖離を測っていない
```

### Operational Interpretation

```txt
Phase 5 完成:
  実時間で運用判断が回る

Phase 5 未完成:
  実注文を作っても、状態管理が危険
```

## Phase 6 -> Phase 7

### Phase 6 Name

Execution Adapter / Small Live Readiness

### Objective

```txt
実注文に必要な interface、安全装置、照合機構を作る
```

### Phase 6 Completion Artifacts

```txt
src/sis/execution/base.py
src/sis/execution/gtrade_adapter.py
src/sis/execution/ostium_adapter.py
src/sis/state/store.py
src/sis/state/reconciliation.py
src/sis/ops/kill_switch.py
src/sis/ops/healthcheck.py
src/sis/ops/daily_loss_limit.py
```

### Required To Enter Phase 7

```txt
- live adapter interface がある
- 実注文前に必ず RiskGate を通る
- position reconciliation がある
- balance reader がある
- order status / fill parser がある
- cancel / close logic がある
- kill switch がある
- daily loss limit がある
- max exposure limit がある
- API key / secret が安全に分離されている
- 小ロット・低レバの dry-run または testnet 相当が完了
```

### Must Not Enter Phase 7 If

```txt
- 実ポジションと内部状態を照合できない
- kill switch がない
- daily loss limit がない
- 注文失敗時の処理がない
- stale / spread / event blackout 中でも発注できてしまう
- 秘密鍵・API key 管理が曖昧
```

### Operational Interpretation

```txt
Phase 6 完成:
  小ロット実弾に入る準備ができた

Phase 6 未完成:
  実注文は危険
```

## Phase 7 Final Completion

### Phase 7 Name

Production Operation

### Objective

```txt
個人サーバー上で、低頻度・リスク制御済み・再現性のあるシステムトレードを継続運用する
```

### Phase 7 Completion Artifacts

```txt
daemon
scheduler
monitoring
alerts
state recovery
weekly review report
strategy lifecycle management
```

### Final Completion Conditions

```txt
- daemon として稼働する
- 再起動後に状態復元できる
- position reconciliation が定期実行される
- daily loss limit が効く
- kill switch が効く
- event blackout が自動反映される
- stale / spread / session 異常で自動停止する
- paper/live 比較 report が出る
- weekly strategy review が出る
- 小ロット実弾で 30〜60 日運用し、paper との乖離が許容範囲
- 期待値が維持されている
```

### Not Final Completion If

```txt
- たまに手で動かすだけ
- ログが残らない
- 再起動で状態が壊れる
- 異常時に止まらない
- live PnL と内部記録が合わない
```

## One-Page Summary Table

| 進む先 | 必要な完成 |
| --- | --- |
| Phase 2へ | Phase 1 live evidence が `GO` または `CONDITIONAL_GO_NEEDS_SIGNAL_BACKTEST` |
| Phase 3へ | market/macro/event/feature/signals が生成され、schema と品質診断がある |
| Phase 4へ | `StrategyDecision` / `RiskDecision` / `ExecutionPlan` が共通化され、decision evidence が残る |
| Phase 5へ | signal-driven backtest で、コスト控除後に候補戦略が残る |
| Phase 6へ | paper trading が 30 日以上安定し、state/PnL/block 理由が再現可能 |
| Phase 7へ | execution adapter、安全装置、照合、kill switch、小ロット検証が完了 |
| 最終完成 | daemon 化され、監視・復元・停止・週次評価まで回る |

## Immediate Next Branch

現在の次の分岐は、まず Phase 1 live evidence を確定することにある。

実行順:

```bash
just check
bash scripts/refresh_live_evidence.sh --duration-minutes 120 --metadata-interval-seconds 60 --dry-run
bash scripts/refresh_live_evidence.sh --duration-minutes 120 --metadata-interval-seconds 60 --force
uv run sis diagnose-quotes --venue gtrade --symbol QQQ
uv run sis diagnose-quotes --venue gtrade --symbol SPY
uv run sis diagnose-quotes --venue gtrade --symbol XAU
uv run sis check-go-no-go
uv run sis build-evidence-card
uv run sis validate-artifacts --strict
```

Phase 2 に進める条件:

```txt
GO
または
CONDITIONAL_GO_NEEDS_SIGNAL_BACKTEST
```

## Final Interpretation

各 Phase に進む条件は、簡単に言うと次のとおり。

```txt
Phase 2へ:
  venue が研究対象として成立した

Phase 3へ:
  研究データが信頼できる形で揃った

Phase 4へ:
  backtest/paper/live 共通の意思決定モデルができた

Phase 5へ:
  4h〜3d の戦略候補がコスト込みで残った

Phase 6へ:
  paper trading が実時間で安定した

Phase 7へ:
  実注文の安全装置と照合機構が完成した

最終完成:
  継続運用・監視・停止・復元・評価が自動で回る
```

