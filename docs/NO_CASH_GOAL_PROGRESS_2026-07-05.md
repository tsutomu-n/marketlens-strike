<!--
作成日: 2026-07-05_13:13 JST
更新日: 2026-07-11_18:35 JST
-->

# No-Cash Goal Progress 2026-07-05

## 結論

お金を使わない段階の current goal に対する進捗は、単一の 65% ではなく次のように分けて読む。

| 観点 | 現実的な進捗 | 読み方 |
|---|---:|---|
| implementation / routing | 70% 前後 | CLI、schema、docs、artifact 生成経路、fail-closed routing はかなり揃っている。 |
| evidence quality | 50% 前後 | sample size、source coverage、books/trades/replay、PBO / rolling stability がまだ弱い。 |
| practical overall | 60-65% | 形はできているが、判断に足る証拠の厚みは未達。 |

この割合は metric ではなく、current artifact と current goal を照合した実務判断である。profit proof、actual cash readiness、tiny-live readiness、live readiness、wallet readiness、signing readiness、exchange-write readiness は対象外。

## 確認した正本

- [CURRENT_GOAL_AND_DIRECTION_2026-07-05.md](CURRENT_GOAL_AND_DIRECTION_2026-07-05.md)
- [CURRENT_STATE.md](CURRENT_STATE.md)
- [crypto_perp/BACKTEST_CANDIDATE_PACK_V1.md](crypto_perp/BACKTEST_CANDIDATE_PACK_V1.md)
- `uv run sis crypto-perp-backtest-candidate-pack --help`
- `uv run sis strategy-idea-candidates-authoring-bridge --help`
- `data/crypto_perp/backtest_candidate_pack/latest/decision.json`
- `data/crypto_perp/backtest_candidate_pack/latest/data_availability_ledger.json`
- `data/strategy_idea_candidates/c9-btcusdt-realdata-20260628T045945Z/authoring_bridge/strategy_idea_candidate_authoring_bridge_manifest.json`
- `data/strategy_idea_candidates/c9-btcusdt-realdata-20260628T045945Z/bitget_public_source/bitget_public_source_refresh_manifest.json`
- `data/strategy_idea_candidates/c9-btcusdt-realdata-20260628T045945Z/candidates/strategy_idea_candidate_set.json`
- `data/research/backtest_pack/strategy_backtest_pack_validation.json`

## Current Goal への対応

| goal item | 状態 | 根拠 | 残り |
|---|---|---|---|
| C9 bridge | 部分到達 | shortlisted 5 件のうち 3 件が `BRIDGED`、2 件が `BLOCKED_UNSUPPORTED_FAMILY_MAPPING`。candidate-scoped artifact と blocker は残っている。 | 対応 family の拡張より先に、blocked を stop result としてレビューし、bridged 3 件の証拠品質を厚くする。 |
| Bitget public source | 部分到達 | BTCUSDT / USDT-FUTURES / 5m / 200 rows の public source refresh artifact がある。credentials、exchange write、live order は使っていない。 | orderbook depth、measured slippage、websocket、deep backfill は未取得。 |
| ticker-aware / source availability | 部分到達 | Backtest Candidate Pack に data availability ledger がある。critical missing は 0、future signal source は 0。 | books、trades、replay が missing。cash ledger / live measurement は no-cash 段階では非目標だが、欠損として表示される。 |
| Backtest Candidate Pack | 到達済みだが判断未達 | 30 events / 14 tradesを生成し、decisionは`BACKTEST_REJECT`。guardはPBO sample条件でBLOCKED、no-lookahead failedは0。 | PBO専用証跡、position overlap、独立episode、selector benchmarkが未達。 |
| evidence quality | 未達寄り | 30 events / 14 trades / 10 winsだが、5 episodes、single-position負、30件中27件が同一UTC日。 | PBO計算、position accounting、期間/regime分散、books/trades/replayを増やす。 |
| live / actual cash boundary | 到達済み | artifacts は `permits_live_order=false`、`live_conversion_allowed=false`、wallet/signing/exchange write/live order は false。 | 境界は維持する。actual cash や tiny live へ進めない。 |

## 前回答からの補正

前回答の「65%前後」は、方向としては大きく外れていない。ただし、次の省略があった。

- implementation progress と evidence quality progress を分けていなかった。
- data availability の missing 50 rows を全部同じ重みで読んでいた。cash ledger / live measurement は no-cash 段階では非目標なので、実務上の弱点は books / trades / replay missing を中心に読む。
- C9 bridge の 2 件 blocked は失敗ではなく、C9 v0 mapping 対象外を fail-closed に止めた結果である。

したがって、今の答えは「実装・導線は 70% 前後、証拠品質は 50% 前後、総合は 60-65%」がより正確。

## 75-80% に上げる条件

お金を使わない範囲で次を満たすと、75-80% と言いやすくなる。

1. Backtest Candidate Pack の event / outcome 数を増やし、PBO と rolling stability が評価不能ではなくなる。
2. books / trades / replay の source missing を減らす。
3. C9 bridge の `BRIDGED` 候補について、candidate ごとの backtest pack validation、source range、cost assumptions、`NO_TRADE` 比較をまとめて読める。
4. Bitget public source を単発 BTCUSDT だけでなく、対象 ticker / timeframe / horizon に沿って再利用できる。
5. `NO_TRADE` が leader の場合に trade action へ手動で差し替えない運用を維持する。

## 進めてはいけないこと

- actual cash ledger を未接続のまま profit proof と呼ぶ。
- 30 event / 5 episode のlocal backtestを実利益証明と読む。
- `BRIDGED` を alpha proof、paper permission、live permission と読む。
- `BACKTEST_COLLECT_MORE_DATA` を candidate hold や live 近接と読む。
- missing books / trades / replay を zero-fill で埋めて通す。
- tiny-live、wallet、signing、exchange write へ進む。

## 再確認コマンド

```bash
uv run python scripts/check_current_docs.py
uv run python scripts/check_cli_catalog.py
uv run sis crypto-perp-backtest-candidate-pack --help
uv run sis strategy-idea-candidates-authoring-bridge --help
jq '{decision, reason_codes, event_count, outcome_count, selected_action_counts: .summary.selected_action_counts, no_lookahead: .summary.no_lookahead, boundary, non_goal_flags}' data/crypto_perp/backtest_candidate_pack/latest/decision.json
```
