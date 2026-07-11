<!--
作成日: 2026-07-11_16:01 JST
更新日: 2026-07-11_19:45 JST
-->

# Crypto Perp Profit Evidence Hardening Plan

## Checkpoint ID

`CP-PROFIT-HARDENING-20260711`

## 目的

現在の`READY_FOR_HUMAN_REVIEW_PLANNING`が、無視されたcost引数、旧guard、異なるrunのartifact、未知status、境界違反で偽陽性にならないようにする。同時に、選択action別損益とbreak-even costをreview evidenceへ出し、利益判断をaggregateの正値だけに依存させない。

## Hostile Audit Findings

- `--slippage-bps 2`と`50`、`--notional-usd 1000`で結果が完全一致した。tournament rows再利用がevent setしか見ていない。
- Candidate Packが再計算したPASS guardと使用rowsを保存せず、selection側の旧BLOCKED guardだけが残る。
- No-Cash Gateは未知candidate/PBO/rolling statusや必須source blockerがあってもHOLDへ進める。
- Human Review Packetはcandidate REJECT、mixed-run input、nested boundary violationでもREADYになり得る。
- 既存guard再利用は全check/status/threshold/fold整合を確認しない。
- 現行再生成は14 trades / 10 wins、nominal `+3.042366783076564551621614274 USD`、stress `+2.762366783076564551621614274 USD`。ただしpeak6、5 episodes中3勝、single-position `-0.4618201695034107750204885438 USD`、always-long `+5.816219911337534249441041925 USD`未達。
- 旧candle semanticsは5分bucket開始時刻でfull OHLCVを利用し、entry説明はnext-bar openなのにcurrent-bar closeを参照していた。可用時刻を`ts+5m`、entryをnext-bar openへ修正する。
- `ESTIMATED`は実PBO計算ではなかった。default `fold_count=0`は`NOT_ESTIMABLE`でguardをBLOCKEDにする。`COMPUTED_PASS`文字列だけでも不十分で、専用PBO証跡を検証するproduction経路はない。
- position overlapと資本拘束はaggregate損益に未反映。同一標本でshort laneを自動削除せず、action/episode/single-position economicsをreview evidenceとして露出する。
- nominal 30 eventsを独立標本とみなさない。trade iid bootstrap 95%は正でも、5-episode bootstrap 95%は0を跨ぐ。episode不足とselectorのalways-long未達をREJECT/KILL chainへ伝播する。
- source selectionはraw491からstrict window contractでeligible467、reject24。entry不一致2、full horizon非連続11、lookback非連続11を除外し、ticker eligibleは30ちょうどで余裕がない。
- Human Review Packetはstrict v2 12-input contractと個別schema検証を持ち、旧v1は`input_contract_version`なしの場合だけreader互換を維持する。
- Candidate Packは既存derived rowsを一切再利用せずmatured outcomesから常時再計算する。同一eventの複数outcome/duplicate event IDはexit 2。
- Kill CLIはgate/rowsを必須化し、rows modelとleader_actionを検査する。project floor未満のcostとinterval非整除設定もexit 2。
- event/outcome、selection manifest、source availabilityをraw candle/ticker/funding filesから再構築し、ID・算術・derived flags・execution windowのreseal改ざんを拒否する。
- trade単位のprofit concentrationが低く見えても、同時期のmarket episode単位で利益が1-2 episodeへ集中する経路を別検査する。
- candle timestamp/windowが正しくても、非有限・非正OHLC、open/closeを包含しないhigh/low、負volumeを通せる数値整合gapを閉じる。
- mutable producer/source-ref labels、fixture family偽装、自己申告ticker/funding available、自己申告episode totalsでprovenance/concentration検査を迂回できないようにする。

## 制約

- Paper Observation、paper order、actual cash、wallet、signing、exchange write、live executionを許可しない。
- order-book replayや新しい外部data collectionは本checkpointに含めない。
- runtime `data/`と`.ai-work/`をGit管理対象にしない。
- commit、push、merge、cherry-pickを行わない。
- 既存の`ai/human-review-packet-20260709-2200`を継続する。

## TestCommand

```bash
uv run pytest \
  tests/crypto_perp/test_tournament_rows.py \
  tests/crypto_perp/test_bias_guards.py \
  tests/crypto_perp/test_backtest_candidate_pack.py \
  tests/crypto_perp/test_backtest_candidate_input_integrity.py \
  tests/crypto_perp/test_backtest_candidate_profit_hardening.py \
  tests/crypto_perp/test_no_cash_backtest_gate.py \
  tests/crypto_perp/test_no_cash_backtest_sample.py \
  tests/crypto_perp/test_real_market_no_cash_sample.py \
  tests/crypto_perp/test_no_trade_kill_report.py \
  tests/crypto_perp/test_candidate_leaderboard.py \
  tests/crypto_perp/test_human_review_packet.py \
  tests/crypto_perp/test_human_review_packet_validation.py \
  tests/crypto_perp/test_real_market_candle_validation.py \
  tests/crypto_perp/test_profit_readiness_local_automation.py -q
```

## AllowedFiles

- `src/sis/crypto_perp/tournament_rows.py`
- `src/sis/crypto_perp/bias_guards.py`
- `src/sis/crypto_perp/backtest_candidate_pack.py`
- `src/sis/crypto_perp/backtest_candidate_pack_models.py`
- `src/sis/crypto_perp/backtest_candidate_pack_reports.py`
- `src/sis/crypto_perp/backtest_candidate_pack_profit.py`
- `src/sis/crypto_perp/no_cash_backtest_gate.py`
- `src/sis/crypto_perp/no_cash_backtest_sample.py`
- `src/sis/crypto_perp/real_market_no_cash_sample.py`
- `src/sis/crypto_perp/no_trade_kill_report.py`
- `src/sis/crypto_perp/candidate_leaderboard.py`
- `src/sis/crypto_perp/human_review_packet.py`
- `src/sis/crypto_perp/human_review_packet_validation.py`
- `src/sis/crypto_perp/real_market_candle_validation.py`
- `src/sis/crypto_perp/real_market_artifact_validation.py`
- `src/sis/crypto_perp/io.py`
- `src/sis/commands/crypto_perp_human_review_packet.py`
- `src/sis/commands/crypto_perp_no_trade_kill_report.py`
- `schemas/crypto_perp_bias_guard.v1.schema.json`
- `schemas/crypto_perp_backtest_data_availability_ledger.v1.schema.json`
- `schemas/crypto_perp_backtest_result.v1.schema.json`
- `schemas/crypto_perp_backtest_rolling_stability_result.v1.schema.json`
- `schemas/crypto_perp_backtest_signal_row.v1.schema.json`
- `schemas/crypto_perp_backtest_stress_result.v1.schema.json`
- `schemas/crypto_perp_real_market_no_cash_sample.v1.schema.json`
- `schemas/crypto_perp_human_review_packet.v1.schema.json`
- `schemas/crypto_perp_no_trade_kill_report.v1.schema.json`
- `tests/crypto_perp/test_tournament_rows.py`
- `tests/crypto_perp/test_bias_guards.py`
- `tests/crypto_perp/test_backtest_candidate_pack.py`
- `tests/crypto_perp/test_backtest_candidate_input_integrity.py`
- `tests/crypto_perp/test_backtest_candidate_profit_hardening.py`
- `tests/crypto_perp/test_no_cash_backtest_gate.py`
- `tests/crypto_perp/test_no_cash_backtest_sample.py`
- `tests/crypto_perp/test_real_market_no_cash_sample.py`
- `tests/crypto_perp/test_no_trade_kill_report.py`
- `tests/crypto_perp/test_candidate_leaderboard.py`
- `tests/crypto_perp/test_human_review_packet.py`
- `tests/crypto_perp/human_review_packet_fixtures.py`
- `tests/crypto_perp/test_human_review_packet_validation.py`
- `tests/crypto_perp/test_real_market_candle_validation.py`
- `tests/crypto_perp/test_profit_readiness_local_automation.py`
- `docs/CURRENT_DOCS_INDEX_2026-07-05.md`
- `docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md`
- `docs/crypto_perp/BACKTEST_CANDIDATE_PACK_V1.md`
- `docs/crypto_perp/CANDIDATE_LEADERBOARD_V1.md`
- `docs/crypto_perp/CURRENT_NO_CASH_HUMAN_REVIEW_EXPLAINER_2026-07-11.md`
- `docs/crypto_perp/EVIDENCE_QUALITY_REALITY_CHECK_2026-07-05.md`
- `docs/crypto_perp/HUMAN_REVIEW_FOR_PAPER_OBSERVATION_PLAN_2026-07-09.md`
- `docs/crypto_perp/HUMAN_REVIEW_PACKET_V1.md`
- `docs/crypto_perp/NO_CASH_BACKTEST_GATE_V1.md`
- `docs/crypto_perp/NO_TRADE_KILL_REPORT_V1.md`
- `docs/crypto_perp/NO_CASH_BACKTEST_GOAL_IMPLEMENTATION_PLAN_2026-07-08.md`
- `docs/crypto_perp/NEXT_NO_CASH_BACKTEST_TO_PAPER_PLAN_2026-07-06.md`
- `docs/crypto_perp/PROFIT_READINESS_ACCEPTANCE_VOCABULARY.md`
- `docs/crypto_perp/PROFIT_READINESS_SURFACE_INVENTORY_2026-06-27.md`
- `docs/runbooks/CRYPTO_PERP_TRUTH_CYCLE_RUNBOOK.md`
- `docs/final-summary.md`
- `docs/plans/CRYPTO_PERP_BIAS_GUARD_WARNING_SEMANTICS_2026-07-11.md`
- `docs/plans/CRYPTO_PERP_FAIL_CLOSED_DECISION_CHAIN_2026-07-11.md`
- `docs/plans/CRYPTO_PERP_NO_CASH_THIRD_PARTY_EXPLAINER_2026-07-11.md`
- this plan
- ignored `.ai-work/` records

## TASKS

- [x] TASK 1 RED: Existing derived rows、duplicate event/outcome、incompatible cost/window inputs must not enter an advancement run.
- [x] TASK 2 GREEN: Always recompute rows from unique matured outcomes; enforce cost floors/window integrity and persist pack-local rows/guard.
- [x] TASK 3 RED: Unknown candidate/PBO/rolling states and required-source blockers must never produce gate HOLD; missing selected action rows must not produce candidate HOLD.
- [x] TASK 4 GREEN: Convert gate HOLD to a positive whitelist with zero blockers and close candidate missing-row routing.
- [x] TASK 5 RED: Forged PASS guard, failed error check, threshold/fold mismatch, duplicate/missing action rows must not be accepted.
- [x] TASK 6 GREEN: Validate the full guard policy contract and exact per-event action set; do not trust an external guard, and recompute the current guard from the selected tournament rows.
- [x] TASK 7 RED: Candidate REJECT, mixed-run refs, mismatched gate/kill/leaderboard, and nested boundary flags must block Human Review Packet READY.
- [x] TASK 8 GREEN: Add strict v2 12-input schema/lineage validation, all-input boundary inspection, candidate HOLD requirement, and fail-closed lineage. Keep old v1 readable only through the conditional absence of `input_contract_version`.
- [x] TASK 9 RED/GREEN: Add action/episode/single-position performance, gross profit/loss, profit factor, break-even cost, independent-episode minimum, and best-static benchmark diagnostics. Propagate `INDEPENDENT_MARKET_EPISODE_SAMPLE_NOT_MET` and `SELECTOR_DOES_NOT_BEAT_BEST_STATIC_ACTION` without same-sample auto-optimization.
- [x] TASK 10 REFACTOR: Use one raw-byte SHA-256 helper for new source refs and update compatibility tests.
- [x] TASK 11 ARTIFACT: Regenerate the current chain under raw-source reconstruction and run sensitivity/concentration diagnostics. Current sample integrity passes; rows SHA values differ across cost cases; episode largest/top-2 concentration are approximately `0.716 / 0.997`. Upstream gate reject remains authoritative.
- [x] TASK 12 VERIFY: Focused count=249、targeted hostile count=44、full count=3134、runtime validator、diff/help/docs/catalog、hostile re-review all passed; 3 findings resolved with no new blockers.

## Final Authoritative Verification

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

## Current Runtime Truth

```text
event / trade / win            = 30 / 14 / 10
backtest / stress USD          = 3.042366783076564551621614274 / 2.762366783076564551621614274
peak positions                 = 6
market episodes / wins         = 5 / 3
single-position USD            = -0.4618201695034107750204885438
always-long USD                = 5.816219911337534249441041925
score/result correlation       = -0.2902937515082110915592253119
short sleeve                   = 2 losses / -0.4939911498820537167728313263
guard / PBO                    = BLOCKED / NOT_ESTIMABLE (fold_count=0)
candidate / gate               = BACKTEST_REJECT / NO_CASH_BACKTEST_REJECT
kill / leaderboard             = KILL_UPSTREAM_GATE_REJECTED / KILL
human review packet            = BLOCKED_BY_BIAS_GUARD
artifact lineage               = PASS
input contract                 = crypto_perp_human_review_packet_inputs.v2 / strict 12
position overlap accounted     = false
```

trade iid bootstrap total 95%=`[+0.1069,+5.7882]`に対し、5-episode bootstrap total 95%=`[-1.9182,+9.2413]`で0を跨ぐ。sampleは約35時間15分、30件中27件が2026-07-09 UTCへ集中する。

source selectionはraw491 / eligible467 / reject24（entry 2、full horizon 11、lookback 11）。ticker eligibleは30ちょうど。全paper/cash/wallet/signing/exchange/live flagはfalse。

## 完了条件

- 既存derived rowsを再利用せず、matured outcomesから常時再計算する。cost parameter変更で結果またはscaleとrows SHAが変わる。
- public event/outcome、selection manifest、source availabilityをraw sourceから再構築し、ID・算術・count/window・derived statusが一致する。
- OHLCは有限かつ正、high/lowはopen/closeを包含し、base/quote volumeは負でない。
- 全`market_window_v1`をproducer/ref labelに依存せずraw candle再構築へ通し、非market eventは検証可能provenanceがなければCOLLECTする。
- ticker/funding availableはraw再計算statusと完全一致し、dogfood fixtureはpromotion不能である。
- Kill episode totalsはexecution windowsとbacktest resultsから再計算し、reported totalsと完全一致する場合だけ採用する。
- episode totals missing/invalidはCOLLECT、largest `>0.60`またはtop-2 `>0.80`はREVISEとなり、上流rejectを上書きしない。
- pack内に実際に使用したrows/guardが保存され、decisionから追跡できる。
- gate HOLDは既知の肯定条件とblocker 0の場合だけ。
- mixed-run、candidate非HOLD、nested boundaryでpacket READYにならない。
- action別損益とbreak-even costがreview packetで見える。
- 現artifactの判定は修正後の実結果に従い、READYを前提に固定しない。
- 全安全flagがfalseで、focused/full verificationが成功する。

## 失敗条件

- existing derived rowsが入力として再利用される、またはduplicate event/outcomeが任意選択される。
- 再計算guardがsummaryにしか存在しない。
- blockerまたは未知statusがあるのにHOLDになる。
- 異なるrunのartifact混在でREADYになる。
- 同じ14 tradesへの後知恵でshort laneを自動削除する。

## 移行

既存derived tournament rowsは内容やidentityにかかわらず再利用せず、matured outcomesから再計算する。Human Review Packetは出力schema v1を維持するが、新規生成物は`input_contract_version=crypto_perp_human_review_packet_inputs.v2`を出し、固定12入力をschemaで強制する。このfieldがない旧v1だけは従来required fieldでread-compatibleとし、新規v2と同じlineage強度とは扱わない。runtime latestは全段を順番に再生成する。

## ロールバック

本checkpointの差分だけを手動で戻し、直前のartifact再生成コマンドを再実行する。破壊的git操作は使わない。
