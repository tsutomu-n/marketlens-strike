<!--
作成日: 2026-06-27_11:32 JST
更新日: 2026-07-11_19:45 JST
-->

# Final Summary

## 結論

Crypto Perp no-cash判定チェーンの偽READY経路は閉じました。現在の実artifactは、guard `BLOCKED`、candidate/gate REJECT、kill/leaderboard KILL、Human Review Packet `BLOCKED_BY_BIAS_GUARD`です。artifact lineageは`PASS`、next actionは`FIX_REVIEW_PACKET_BLOCKERS`です。

利益仮説は捨てる段階ではありません。14 trades / 10 wins、名目`+3.042366783076564551621614274 USD`は追跡価値があります。しかし5 episode bootstrapは0を跨ぎ、single-position近似は負、selectorはalways-long未達、50 bps slippageで損益は負です。現実的な判断は「攻める候補は残すが、Paperへは進めない」です。

## Goal / Branch / Status

- goal: Crypto Perp判定チェーンをfail-closed化し、薄い利益証拠をREADYへ誤昇格させない。
- 作業ref: `ai/human-review-packet-20260709-2200`
- merge status: hold
- commit / push / merge / cherry-pick: 未実施
- runtime `data/`、`.tmp/`、`.ai-work/`: Git差分対象外
- Paper、actual cash、wallet、signing、exchange write、live order: 対象外、全flag false

## Current Artifact Chain

```text
bias_guard_status=BLOCKED
bias_guard_stop_reason=BIAS_GUARD_FAILED_sample_sufficient_for_pbo
bias_guard_warning=BIAS_GUARD_WARNING_stress_cash_non_negative
fold_count=0
pbo_status=NOT_ESTIMABLE
pbo_computed=false
pbo_evidence_verified=false
candidate_decision=BACKTEST_REJECT
candidate_reasons=BIAS_GUARD_BLOCKED,
                  BIAS_GUARD_FAILED_sample_sufficient_for_pbo,
                  POSITION_OVERLAP_NOT_ACCOUNTED,
                  INDEPENDENT_MARKET_EPISODE_SAMPLE_NOT_MET,
                  SELECTOR_DOES_NOT_BEAT_BEST_STATIC_ACTION
gate_decision=NO_CASH_BACKTEST_REJECT
kill_decision=KILL_UPSTREAM_GATE_REJECTED
leaderboard_next_action=KILL
packet_decision=BLOCKED_BY_BIAS_GUARD
next_action=FIX_REVIEW_PACKET_BLOCKERS
artifact_lineage_status=PASS
input_contract_version=crypto_perp_human_review_packet_inputs.v2
review_input_count=12
```

安全flag:

```text
paper_permission_granted=false
permits_paper_order=false
permits_live_order=false
actual_cash_used=false
profit_proven=false
wallet_used=false
signing_used=false
exchange_write_used=false
live_order_submitted=false
```

## Profit Evidence

| Metric | Value | 現実的な読み方 |
|---|---:|---|
| events / trades / wins | 30 / 14 / 10 | trade数は独立標本数ではない |
| backtest total | 3.042366783076564551621614274 USD | overlap込みlocal estimate |
| stress total | 2.762366783076564551621614274 USD | actual fillではない |
| peak concurrent positions | 6 | 資本拘束未反映 |
| episodes / wins | 5 / 3 | minimum 10未達 |
| single-position total | -0.4618201695034107750204885438 USD | 重複を除く近似は負 |
| always-long total | 5.816219911337534249441041925 USD | selectorの追加価値未証明 |
| score/result correlation | -0.2902937515082110915592253119 | ranking signalを支持しない |
| short sleeve | 2 losses / -0.4939911498820537167728313263 USD | short edge未証明 |
| naive iid t | 2.0179 | overlap依存を無視 |
| one-sided sign p | 0.0898 | 通常の5%水準を満たさない |
| trade iid bootstrap total 95% | +0.1069 to +5.7882 USD | 独立仮定で見栄えが良い |
| episode bootstrap total 95% | -1.9182 to +9.2413 USD | 0を跨ぎ不確実 |
| episode largest / top-2 positive concentration | about 0.716 / 0.997 | 0.60 / 0.80閾値を超える |

trade-levelの見た目改善とepisode-levelの不確実性を分離して読みます。前者は仮説の継続理由、後者は昇格を止める理由です。

## Data Selection Reality

- symbol: BTCUSDTのみ
- cutoff span: 約35時間15分
- date concentration: 2026-07-07 UTCが3件、2026-07-09 UTCが27件
- raw / eligible / rejected windows: `491 / 467 / 24`
- reject内訳: entry不一致2、full horizon非連続11、lookback非連続11
- ticker-covered eligible: 30ちょうど、headroom 0
- entry: cutoff+5分の最初の完全bar open
- holding: 連続60分full horizon
- candle rows: unique strict-increasing timestamp、`available_at >= ts + interval`、連続lookback必須
- OHLC: finite and positive; high/low contains open/close; base/quote volume is non-negative
- invalid settings: interval非整除のlookback/horizonはexit code 2
- outcome integrity: duplicate event ID / 同一eventの複数matured outcomeはexit code 2

books、trades、replayは欠損しています。candle local simulationはqueue、partial fill、latency、動的spreadを再現しません。

## Cost Sensitivity

| Case | Backtest total |
|---|---:|
| slippage 2 bps / notional 100 USD | +3.04237 USD |
| slippage 50 bps / notional 100 USD | -3.67763 USD |
| slippage 2 bps / notional 1000 USD | +30.42367 USD |

各caseの`tournament_rows_v2.json` SHA-256はすべて異なります。既存derived rowsは再利用せず、毎回matured outcomesから計算します。fee/funding/slippageはproject既定を下限とし、高コスト感応度だけを許可します。ただし50 bpsで負になるため、実摩擦への耐性は弱いままです。operator labor costも0です。

## Implemented Changes

- 既存derived tournament rowsを再利用せず、matured outcomesから常時再計算
- pack-local rows/guardとcomponent raw SHA refsを保存
- current non-recursive guardを毎回再計算し、外部guardを信用しない
- candidate/gateでguard BLOCKED、missing、unknownをfail-closed処理
- gateをpositive whitelist化し、kill/leaderboard/packetへ停止理由を伝播
- Kill Reportの`--gate` / `--tournament-rows`を必須化し、pack-local rowsとleader_actionを検証
- Human Review Packetをstrict v2固定12入力、個別schema、event/outcome/window、nested boundary検査へ強化
- `COMPUTED_PASS`文字列だけではPBO通過させず、専用証跡未実装中は`pbo_evidence_verified=false`
- candle validationをnext complete bar、連続lookback、連続full horizon、available_at contractへ強化
- candle OHLCの有限性・正値・包絡関係と非負volumeを検証
- duplicate event/multiple outcome、interval非整除、project cost floor未満をexit code 2で拒否
- public event/outcome、selection manifest、source availabilityをraw candle/ticker/funding filesから再構築して検証
- duplicate source availability、derived flag/summary改変、horizon count/holding不一致を拒否
- 全market_windowをmutable labelに依存せずraw検証し、非marketの未検証provenanceとdogfood fixtureをCOLLECT
- ticker/funding availableをraw再計算statusと完全照合
- Kill Reportで必須gate/rowsとleader_action整合を検査し、不明leaderはCOLLECT
- Kill Reportでmarket episode profit concentrationを別検査し、missing/invalidはCOLLECT、高集中はREVISE
- Kill Reportでexecution windows+backtest resultsからepisode totalsを再計算し、reported totals不一致をCOLLECT
- action/episode/single-position、static benchmark、cost sensitivityを利益判断へ露出

主要入口:

- [Backtest Candidate Pack](crypto_perp/BACKTEST_CANDIDATE_PACK_V1.md)
- [No-Cash Gate](crypto_perp/NO_CASH_BACKTEST_GATE_V1.md)
- [Human Review Packet](crypto_perp/HUMAN_REVIEW_PACKET_V1.md)
- [Current Explainer](crypto_perp/CURRENT_NO_CASH_HUMAN_REVIEW_EXPLAINER_2026-07-11.md)
- [Truth-Cycle Runbook](runbooks/CRYPTO_PERP_TRUTH_CYCLE_RUNBOOK.md)
- [Profit Evidence Hardening Plan](plans/CRYPTO_PERP_PROFIT_EVIDENCE_HARDENING_2026-07-11.md)

## Public Contract / Migration

- `crypto-perp-no-trade-kill-report --gate PATH --tournament-rows PATH`は両方必須です。旧呼び出しにはgateとpack-local rows pathを追加します。
- Human Review Packetの出力schema名はreader互換のためv1を維持します。
- 新規packetは`input_contract_version=crypto_perp_human_review_packet_inputs.v2`を出し、固定12入力を強制します。
- `input_contract_version`を持たない旧v1だけは従来required fieldでread-compatibleです。旧v1を新規v2と同じlineage強度とは扱いません。
- runtime latestはcandidate packからpacketまで同一runで順番に再生成します。

破壊的なDB/schema migration、依存追加、外部送信はありません。`pyproject.toml` / lockfileの変更もありません。

## Verification

```text
focused contract list    = PASS; count=249; elapsed=11.80s
targeted hostile review  = PASS; count=44; elapsed=2.56s
hostile findings         = 3 resolved; no new blockers
./scripts/check          = PASS
Python                   = 3.13.12
Ruff lint                = PASS
Ruff format check        = 1681 files already formatted
current docs             = 160 PASS
CLI catalog              = 241 PASS
Pyrefly                  = 0 errors (175 warnings not shown)
ty                       = PASS
Pytest                   = PASS; count=3134; elapsed=97.74s
git diff --check         = PASS
sis --help               = PASS
runtime validator        = PASS
artifact lineage         = PASS
safety flags             = all false
runtime chain            = unchanged BLOCKED / REJECT / KILL
```

hostile re-reviewの3 findingsはすべて解消し、新規blockerはありません。

## Rollback

本checkpointの関連差分だけを手動で戻し、runbookの順序でruntime latestを再生成します。`git reset --hard`などの破壊的操作は使いません。旧artifactへ戻す場合も、v2 packetと混在させず別runとして扱います。

## Residual Risk

- 30 events / 5 episodesの小標本
- 同一symbol、約35時間、27/30が同一UTC日
- ticker eligibleが30ちょうどで余裕なし
- books/trades/replay欠損
- position overlap、資本拘束、position limit未反映
- episode bootstrapが0を跨ぐ
- positive episode利益の約71.6%が最大1 episode、約99.7%が上位2 episodesへ集中
- selectorがalways-longを下回る
- short sleeve 2/2 loss
- 50 bps slippageで負
- operator labor未計上
- production PBO計算・専用証跡producer未実装
- local simulationと実約定条件の差
- raw SHAと再構築はlocal artifact改変を検出するが、取引所側データの完全性・配信欠落・上流真正性を独立証明しない

## Merge Conditions

authoritative full verification、runtime validator、hostile re-reviewは完了し、3 findingsは解消済みです。merge holdは維持し、明示的な人間レビュー、cleanなcommit対象確認、merge判断を別途行います。自動commit、push、merge、cherry-pickは行いません。
