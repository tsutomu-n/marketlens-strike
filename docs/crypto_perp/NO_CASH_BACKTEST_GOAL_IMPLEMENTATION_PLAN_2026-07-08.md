<!--
作成日: 2026-07-08_20:10 JST
更新日: 2026-07-08_20:10 JST
-->

# No-Cash Backtest Goal Implementation Plan 2026-07-08

## 結論

この計画のゴールは、リアルマネーを使う前、かつヴァーチャルフォワードテストまたは Paper Observation を始める前に、Crypto Perp の real-market no-cash backtest が実務判断材料として成立する状態に到達することです。

現在は、backtest machinery と gate machinery はかなり揃っています。しかし、real-market run はまだ ticker-covered trade action evaluation の入口前です。現実的な進捗は 60-65% と読む。

Paper Observation へ進める計画ではありません。Paper Observation の前に、real-market no-cash gate が source / sample / metric の重大 blocker なしで成立することを確認する。

## ゴール定義

便宜上の完了状態は次です。

```text
real-market public/local source
  -> timestamp-safe event/outcome set
  -> backtest candidate pack
  -> no-cash backtest gate
  -> NO_CASH_BACKTEST_HOLD
  -> human review for Paper Observation の計画を作れる状態
```

このゴールは次を含まない。

- Paper Observation 開始
- paper order permission
- actual cash readiness
- cash ledger
- wallet / signing
- exchange write
- live order
- profit proof
- production order readiness

## 現在地

PR #33 時点の現実的な状態:

```text
gate_decision=NO_CASH_BACKTEST_COLLECT_MORE_DATA
event_count=30
outcome_count=30
executed_trade_count=0
unknown_count=30
critical_missing_count=30
pbo_status=ESTIMATED
rolling_stability_status=complete
paper_permission_granted=false
```

核心 blocker:

```text
CRITICAL_SIGNAL_SOURCE_MISSING_TICKER
HISTORICAL_TICKER_SOURCE_NOT_AVAILABLE
TICKER_SOURCE_STALE
```

現時点では、PBO と rolling stability が評価可能でも、trade action evaluation には入れていない。`executed_trade_count=0` と `unknown_count=30` を重く見る。

## 進捗評価

| 段階 | 進捗 | 読み方 |
|---|---:|---|
| backtest / gate machinery | 85-90% | CLI、schema、artifact、gate は機能している |
| fixture-only dogfood | 90%+ | fixture では HOLD 可能。ただし実市場証拠ではない |
| real-market candle/funding run | 65-70% | 30 event/outcome、funding、PBO、rolling は前進 |
| ticker-covered trade evaluation | 20-30% | ticker blocker のため `UNKNOWN` が残る |
| 実務的な no-cash backtest readiness | 60-65% | まだ Paper 前の判断材料としては未完成 |

進捗の実務表現:

```text
current: 60-65%
PR #33 merge + forward ticker collection operational: 65-70%
ticker-covered 30 events + executed_trade_count > 0 + gate HOLD: 80-85%
human review packet for Paper Observation: 90%前後
```

## 基本方針

1. blocker を消すために source を捏造しない。
2. current ticker snapshot を過去 event cutoff に流用しない。
3. market / mark / index candles を bid/ask ticker coverage として使わない。
4. `NO_TRADE` が leader の時に trade action へ差し替えない。
5. fixture-only HOLD を real-market evidence と呼ばない。
6. gate HOLD を Paper Observation permission と呼ばない。
7. 一度に広く実装しない。one blocker class -> one issue -> one PR。

## Checkpoints

### CP0: PR #33 を安全に完了する

目的:

- forward-only ticker snapshot append flow を main に入れる。
- ただし、これを Paper readiness と読ませない。

対象:

- PR #33 `Add forward ticker snapshot append flow`
- issue #29

完了条件:

- CI が success。
- draft を解除。
- squash merge。
- issue #29 は open のまま維持。
- docs / PR body に `NO_CASH_BACKTEST_COLLECT_MORE_DATA` と ticker blocker が残ることを明記。

検証:

```bash
gh pr checks 33
gh pr ready 33
gh pr merge 33 --squash --delete-branch
```

失敗条件:

- PR #33 が Paper Observation readiness のように読める。
- current ticker snapshot を古い cutoff に使っている。
- candle OHLC を bid/ask ticker coverage として扱っている。

### CP1: ticker snapshot collection を運用可能にする

目的:

- future event 用の timestamp-safe ticker rows を蓄積する。
- `ts_received_ms <= information_cutoff_at` を満たす ticker rows を作る。

対象ファイル候補:

- `src/sis/strategy_idea_candidates/bitget_public_source.py`
- `src/sis/crypto_perp/ticker_source.py`
- `src/sis/crypto_perp/real_market_no_cash_sample.py`
- `src/sis/commands/crypto_perp_real_market_no_cash_sample.py`
- `tests/strategy_idea_candidates/test_bitget_public_source.py`
- `tests/crypto_perp/test_real_market_no_cash_sample.py`
- `docs/crypto_perp/REAL_MARKET_NO_CASH_SAMPLE_V1.md`

実装タスク:

1. public ticker snapshot append が idempotent に動くことを保証する。
2. append key は少なくとも `exchange`, `symbol_canonical`, `ts_received_ms`, `source_channel` を含める。
3. `bid_px` / `ask_px` がない行は ticker coverage として clear しない。
4. `funding_rate` は funding coverage として独立評価し、ticker missing と連動させない。
5. ticker manifest に coverage window、row count、warnings、snapshot-only limitation を出す。
6. `--require-ticker-coverage` は outcome 前選別であることを manifest に明記する。

完了条件:

- `strategy-idea-candidates-bitget-source-refresh --append-existing` を複数回実行しても重複が壊れない。
- `ticker_rows` の timestamp range が manifest に出る。
- `crypto-perp-real-market-no-cash-sample --require-ticker-coverage` が、coverage不足時に `TICKER_COVERED_EVENT_COUNT_BELOW_TARGET` で止まる。
- current snapshot は古い event cutoff を clear しない。

検証:

```bash
SIS_ALLOW_PUBLIC_NETWORK=1 uv run sis strategy-idea-candidates-bitget-source-refresh \
  --symbol BTCUSDT \
  --product-type USDT-FUTURES \
  --granularity 5m \
  --limit 200 \
  --out data/strategy_idea_candidates/btc-perp/bitget_public_source \
  --append-existing
uv run sis crypto-perp-real-market-no-cash-sample \
  --source-root data/strategy_idea_candidates/btc-perp/bitget_public_source/source_root \
  --require-ticker-coverage \
  --out data/crypto_perp/real_market_no_cash/ticker_required
uv run pytest tests/strategy_idea_candidates/test_bitget_public_source.py tests/crypto_perp/test_real_market_no_cash_sample.py -q
```

### CP2: ticker-covered 30 event/outcome を作る

目的:

- real-market event/outcome set を、ticker coverage ありで 30 件以上作る。

前提:

- forward collection には時間が必要。
- 現在の single snapshot だけでは過去 cutoff を満たせない。
- 30 covered event 到達まで待つことは正常な stop condition であり、失敗ではない。

実装タスク:

1. `--require-ticker-coverage` の selector が outcome 生成前に coverage を確認する。
2. selected event の `information_cutoff_at` と selected ticker row の `ts_received_ms` / staleness を manifest に残す。
3. coverage不足時は何件足りないかを出す。
4. covered events だけを選ぶときも、outcome を見てから有利な event を選ばない。
5. losing event を落とさない。選択基準は source/timestamp coverage のみ。

完了条件:

- `ticker_covered_event_count >= 30`。
- `event_count=30`、`outcome_count=30`。
- `ticker_available_count=30`。
- `funding_available_count=30` または precise funding blocker。
- `DOGFOOD_FIXTURE_NOT_REAL_MARKET_EVIDENCE` がない。

検証:

```bash
uv run sis crypto-perp-real-market-no-cash-sample \
  --source-root data/strategy_idea_candidates/btc-perp/bitget_public_source/source_root \
  --require-ticker-coverage \
  --out data/crypto_perp/real_market_no_cash/ticker_required
jq '{summary, known_gaps, source_refs}' data/crypto_perp/real_market_no_cash/ticker_required/manifest.json
```

### CP3: ticker-covered pack で backtest candidate pack を再生成する

目的:

- source critical blocker なしで backtest pack を作る。
- `UNKNOWN` を source不足由来ではなくす。

対象:

- `crypto-perp-backtest-candidate-pack`
- `data/crypto_perp/real_market_no_cash/ticker_required`

完了条件:

- `decision.json` が生成される。
- `evidence_grade_summary` が fixture marker なし。
- `critical_missing_count=0`。
- `future_signal_source_count=0`。
- `unknown_count=0` または source欠損以外の理由として machine-readable に説明される。
- `executed_trade_count > 0`。できれば gate threshold の `min_simulated_trades >= 10` を満たす。

検証:

```bash
uv run sis crypto-perp-backtest-candidate-pack \
  --data-dir data/crypto_perp/real_market_no_cash/ticker_required \
  --out data/crypto_perp/real_market_no_cash/backtest_candidate_pack/latest
jq '{decision, reason_codes, event_count, outcome_count, evidence_grade_summary, summary, non_goal_flags}' \
  data/crypto_perp/real_market_no_cash/backtest_candidate_pack/latest/decision.json
```

### CP4: no-cash gate を通す

目的:

- no-cash backtest goal の完了判定を行う。

完了条件:

`NO_CASH_BACKTEST_HOLD` を目指す。ただし HOLD でも Paper permission ではない。

Gate HOLD の最低条件:

- `gate_decision=NO_CASH_BACKTEST_HOLD`
- `blocker_count=0`
- `event_count >= 30`
- `outcome_count >= 30`
- `critical_missing_count=0`
- `unknown_count=0`
- `executed_trade_count >= 10`
- `pbo_status=ESTIMATED` かつ failed ではない
- `rolling_stability_status=complete`
- stress result が positive
- `NO_TRADE` が同一 event set の leader ではない
- `permits_paper_order=false`
- `permits_live_order=false`
- `actual_cash_used=false`

検証:

```bash
uv run sis crypto-perp-no-cash-backtest-gate \
  --decision data/crypto_perp/real_market_no_cash/backtest_candidate_pack/latest/decision.json \
  --data-availability data/crypto_perp/real_market_no_cash/backtest_candidate_pack/latest/data_availability_ledger.json \
  --backtest data/crypto_perp/real_market_no_cash/backtest_candidate_pack/latest/backtest_result.json \
  --stress data/crypto_perp/real_market_no_cash/backtest_candidate_pack/latest/stress_result.json \
  --rolling-stability data/crypto_perp/real_market_no_cash/backtest_candidate_pack/latest/rolling_stability_result.json \
  --out data/crypto_perp/real_market_no_cash/no_cash_backtest_gate/latest
jq '{gate_decision, reason_codes, blocker_count: (.blockers | length), blockers, known_gaps, summary, permits_paper_order, permits_live_order, actual_cash_used}' \
  data/crypto_perp/real_market_no_cash/no_cash_backtest_gate/latest/no_cash_backtest_gate.json
```

### CP5: HOLD しない場合は blocker class を一つだけ issue 化する

目的:

- 広くやらず、残った blocker を一つずつ潰す。

分岐:

| next blocker | 次 issue |
|---|---|
| ticker coverage / staleness | ticker source collection / interval / retention |
| funding coverage | funding history / availability policy |
| books / trades / replay | real source coverage 調査または collector |
| simulated trade count | signal/action rule review。NO_TRADE 差し替えは禁止 |
| `NO_TRADE` leader | candidate reject / revise。手動で trade 化しない |
| stress <= 0 | cost/slippage/stress耐性の不足として reject/revise |
| drawdown / concentration | risk profile / candidate revise |

ルール:

```text
one blocker class -> one issue -> one PR
```

### CP6: HOLD した場合は human review packet 計画へ進む

目的:

- Paper Observation を始めるのではなく、human review for Paper Observation を計画する。

次計画名:

```text
Plan human review for Crypto Perp Paper Observation candidate
```

対象:

- no-cash gate artifact
- backtest candidate pack artifacts
- source availability ledger
- known gaps
- cost model assumptions
- risk limits
- `NO_TRADE` comparison
- PBO / rolling stability / stress result

完了条件:

- human review packet artifact を作る計画がある。
- explicit human decision が必要と明記される。
- paper order permission はまだ出ない。
- actual cash / wallet / signing / exchange write はまだ対象外。

## 対象ファイル一覧

Codex が主に触る可能性があるファイル:

```text
src/sis/strategy_idea_candidates/bitget_public_source.py
src/sis/crypto_perp/ticker_source.py
src/sis/crypto_perp/funding_source.py
src/sis/crypto_perp/source_availability.py
src/sis/crypto_perp/real_market_no_cash_sample.py
src/sis/crypto_perp/backtest_candidate_pack.py
src/sis/crypto_perp/no_cash_backtest_gate.py
src/sis/commands/crypto_perp_real_market_no_cash_sample.py
src/sis/commands/strategy_idea_candidates.py
tests/strategy_idea_candidates/test_bitget_public_source.py
tests/crypto_perp/test_source_availability.py
tests/crypto_perp/test_real_market_no_cash_sample.py
tests/crypto_perp/test_backtest_candidate_pack.py
tests/crypto_perp/test_no_cash_backtest_gate.py
docs/crypto_perp/REAL_MARKET_NO_CASH_SAMPLE_V1.md
docs/crypto_perp/NO_CASH_BACKTEST_GATE_V1.md
docs/crypto_perp/BACKTEST_CANDIDATE_PACK_V1.md
docs/runbooks/CRYPTO_PERP_TRUTH_CYCLE_RUNBOOK.md
docs/CURRENT_DOCS_INDEX_2026-07-05.md
docs/final-summary.md
```

## Test policy

Minimum focused tests per implementation PR:

```bash
uv run pytest tests/strategy_idea_candidates/test_bitget_public_source.py \
  tests/crypto_perp/test_source_availability.py \
  tests/crypto_perp/test_real_market_no_cash_sample.py \
  tests/crypto_perp/test_backtest_candidate_pack.py \
  tests/crypto_perp/test_no_cash_backtest_gate.py -q
```

Docs / catalog checks:

```bash
uv run python scripts/check_current_docs.py
uv run python scripts/check_cli_catalog.py
git diff --check
```

Full check:

```bash
./scripts/check
```

Runtime dogfood check:

```bash
SIS_ALLOW_PUBLIC_NETWORK=1 uv run sis strategy-idea-candidates-bitget-source-refresh \
  --symbol BTCUSDT \
  --product-type USDT-FUTURES \
  --granularity 5m \
  --limit 200 \
  --out data/strategy_idea_candidates/btc-perp/bitget_public_source \
  --append-existing
uv run sis crypto-perp-real-market-no-cash-sample \
  --source-root data/strategy_idea_candidates/btc-perp/bitget_public_source/source_root \
  --require-ticker-coverage \
  --out data/crypto_perp/real_market_no_cash/ticker_required
uv run sis crypto-perp-backtest-candidate-pack \
  --data-dir data/crypto_perp/real_market_no_cash/ticker_required \
  --out data/crypto_perp/real_market_no_cash/backtest_candidate_pack/latest
uv run sis crypto-perp-no-cash-backtest-gate \
  --decision data/crypto_perp/real_market_no_cash/backtest_candidate_pack/latest/decision.json \
  --data-availability data/crypto_perp/real_market_no_cash/backtest_candidate_pack/latest/data_availability_ledger.json \
  --backtest data/crypto_perp/real_market_no_cash/backtest_candidate_pack/latest/backtest_result.json \
  --stress data/crypto_perp/real_market_no_cash/backtest_candidate_pack/latest/stress_result.json \
  --rolling-stability data/crypto_perp/real_market_no_cash/backtest_candidate_pack/latest/rolling_stability_result.json \
  --out data/crypto_perp/real_market_no_cash/no_cash_backtest_gate/latest
```

## Full completion conditions

この計画全体の完了条件:

- PR #33 または同等の forward ticker snapshot collection が main に入っている。
- timestamp-safe ticker-covered event/outcome が 30 件以上ある。
- funding coverage が timestamp-safe に 30 件ある、または precise funding blocker がある。
- real-market no-cash sample に fixture marker がない。
- `crypto-perp-backtest-candidate-pack` が real-market ticker-covered sample で成功する。
- `crypto-perp-no-cash-backtest-gate` が成功する。
- `gate_decision=NO_CASH_BACKTEST_HOLD`。
- gate artifact が paper / live / actual cash permission を出さない。
- docs が `NO_CASH_BACKTEST_HOLD` を human review eligible とだけ説明している。
- `./scripts/check` が通る。

## Stop conditions

次の場合は止める。

- ticker-covered 30 events が集まらない。
- public/local source で native bid/ask ticker coverage が得られない。
- source timestamp が event cutoff より後。
- funding が欠損しているのに 0 埋めが必要になる。
- `NO_TRADE` を外さないと trade count が増えない。
- stress result が負。
- gate が HOLD しない。
- Paper Observation permission が必要になる。
- actual cash / wallet / signing / exchange write が必要になる。

## Codex final report format

Codex は各 checkpoint 実装後に次で報告する。

```text
状態: 完了 / 未完了
結果:
いま使えるか:
反映タイミング:
変更点:
検証:
Gate結果:
残blocker class:
残リスク:
次にやること:
```
