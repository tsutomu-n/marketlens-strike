<!--
作成日: 2026-07-05_10:08 JST
更新日: 2026-07-11_19:42 JST
-->

# Crypto Perp Backtest Candidate Pack v1

## 結論

actual cash を扱わない短期の Crypto Perp 終着点は、`crypto-perp-backtest-candidate-pack` です。

これは利益証明ではなく、既存 local artifact から timestamp-safe な simulation backtest evidence pack を作り、候補を次の4択へ分類するための current surface です。

- `BACKTEST_REJECT`
- `BACKTEST_REVISE`
- `BACKTEST_COLLECT_MORE_DATA`
- `BACKTEST_CANDIDATE_HOLD`

`BACKTEST_PROMOTE_TO_LIVE` は存在しません。`BACKTEST_CANDIDATE_HOLD` でも、actual cash readiness、paper permission、tiny-live readiness、live readiness、wallet/signing、exchange write、live order permission は出ません。

次の段階は直接 Paper Observation ではなく、[NO_CASH_BACKTEST_GATE_V1.md](NO_CASH_BACKTEST_GATE_V1.md) の no-cash backtest gate です。stage order は `No-cash backtest evidence pack -> no-cash backtest gate -> human review for paper observation -> Paper Observation -> Actual Cash evidence` と読む。

現実評価は [EVIDENCE_QUALITY_REALITY_CHECK_2026-07-05.md](EVIDENCE_QUALITY_REALITY_CHECK_2026-07-05.md) も読む。

## 正本

- CLI: `uv run sis crypto-perp-backtest-candidate-pack`
- Builder: `src/sis/crypto_perp/backtest_candidate_pack.py`
- Models: `src/sis/crypto_perp/backtest_candidate_pack_models.py`
- Reports: `src/sis/crypto_perp/backtest_candidate_pack_reports.py`
- Profit diagnostics: `src/sis/crypto_perp/backtest_candidate_pack_profit.py`
- Raw artifact validation: `src/sis/crypto_perp/real_market_artifact_validation.py`
- Command wrapper: `src/sis/commands/crypto_perp_backtest_candidate_pack.py`
- Registration: `src/sis/commands/crypto_perp.py`
- Schema: `schemas/crypto_perp_backtest_candidate_pack.v1.schema.json`
- Tests: `tests/crypto_perp/test_backtest_candidate_pack.py`, `tests/crypto_perp/test_backtest_candidate_profit_hardening.py`
- Input integrity tests: `tests/crypto_perp/test_backtest_candidate_input_integrity.py`
- Cost reference: `configs/cost_models/crypto_perp_bitget_usdt_futures.yaml`
- Local output: `data/crypto_perp/backtest_candidate_pack/latest/`

## 生成する artifact

デフォルトでは `data/crypto_perp/backtest_candidate_pack/latest/` に次を出します。

- `signal_rows.jsonl`
- `data_availability_ledger.json`
- `execution_assumptions.json`
- `tournament_rows_v2.json`
- `bias_guard.json`
- `no_lookahead_report.json`
- `backtest_result.json`
- `stress_result.json`
- `regime_split_result.json`
- `rolling_stability_result.json`
- `decision.json`
- `decision.md`

## 実行

```bash
uv run sis crypto-perp-backtest-candidate-pack
```

主な option:

```bash
uv run sis crypto-perp-backtest-candidate-pack \
  --data-dir data/crypto_perp \
  --out data/crypto_perp/backtest_candidate_pack/latest \
  --notional-usd 100 \
  --min-events 10 \
  --min-events-for-stability 30 \
  --fold-count 0 \
  --fee-rate 0.0004 \
  --funding-rate 0.0001 \
  --slippage-bps 2
```

zero-cost simulationは禁止です。昇格runでは`fee_rate=0.0004`、`funding_rate=0.0001`、`slippage_bps=2`をproject floorとし、それ未満はexit code 2です。より高いcostの感応度runは許可します。現在のoperator labor costは`operator_time_minutes=0`、`operator_hourly_cost_usd=0`で、実務の監視・調査・レビュー工数を損益へ算入していません。

### Derived rowsの常時再計算とpack lineage

Candidate Packは既存`tournament_rows_v2.json`を一切再利用しません。選択したmatured `crypto_perp_outcome.v1`実ファイルから全action row、feature/edge、bias guardを毎run再計算します。既存derived rowsを入力として信用しないため、row内容の改ざんや都合のよいaction水増しをevent set/hash一致だけで通す経路がありません。

同一event IDに複数のmatured outcomeがある場合、duplicate event IDがある場合、event/outcome対応が一意でない場合はCLIがexit code 2で失敗します。曖昧なoutcomeを任意選択しません。

packは実際に計算した`tournament_rows_v2.json`と`bias_guard.json`を出力し、`decision.summary.pack_component_refs`へsignal、ledger、rows、guard、backtest、stress、rolling等のraw SHA-256とschema identityを記録します。後段はこのpack-local実体だけを使います。

fee、funding、slippageはproject既定値を昇格runの下限とします。既定未満はCLI exit code 2、高コスト感応度は許可します。notional、operator labor、fee、funding、slippage、stress multiplierはrows identityへ入り、感応度runごとに異なるrows SHAを持ちます。

### Raw market artifact integrity

全`market_window_v1`入力はproducer commandやmutable source-ref labelに関係なくraw public-candle検証へ通します。labelを書き換えて検証対象外へ逃がせません。JSONのID/hashが自己整合しているだけでも採用しません。Candidate Packは次をraw sourceから再構築して一致を要求します。

- event/outcome model identityとreturn/high/low/close等の算術
- public candle source refの実ファイルSHA-256、event feature、detector config、entry、settlement、outcome price window
- `selection_manifest.json`のevent set、outcome set、count、event/outcome pair、entry/settled/horizon window
- source availabilityのevent/cutoff/artifact identity、固定source status set、summary、`can_compute_*` derived flags
- ticker/funding status、metadata、source refs、event market featureをmanifest参照先のraw parquetから再構築した値
- ticker/fundingの`available`、row count、reason、metadata、refsをraw再計算statusと完全一致

同一eventのsource availabilityが複数ある場合もexit code 2です。matured horizonはeventごとに正確に1件で、candidate `max_holding_minutes`と一致しなければ拒否します。JSONを再sealしてIDだけ合わせた改ざん、raw fileだけ差し替えた古いSHA、manifestやticker/funding metadataの手書き変更を通しません。

非`market_window_v1` eventはraw provenanceを再構築できない限り`BACKTEST_COLLECT_MORE_DATA` / `EVENT_SOURCE_PROVENANCE_NOT_VERIFIABLE`です。fixture producerのeventは`DOGFOOD_FIXTURE_NOT_REAL_MARKET_EVIDENCE`も保持し、promotionしません。

`decision.json` は optional `evidence_grade_summary` を出します。既存 v1 artifact 互換のため required ではありません。ただし存在する場合は schema と Pydantic model が内部字段を検証します。`strongest_evidence_level` は `incomplete_local_artifact`、`recomputed_minimal_simulated_estimate`、`local_simulated_estimate` のいずれかです。

プロジェクト前提の taker fee は 0.04% です。`crypto-perp-backtest-candidate-pack`、`crypto-perp-tournament-rows-v2`、`build_cost_aware_tournament_rows`、`build_pre_actual_cash_evidence_pack`、`write_pre_actual_cash_evidence_pack` は normal project assumption を `src/sis/crypto_perp/cost_model.py` の共有定数から使います。`configs/cost_models/crypto_perp_bitget_usdt_futures.yaml` は同じ前提を文書化し、`0.0006` は explicit conservative / stress assumption としてのみ扱います。

## 現在の local result

現在のticker/funding-covered 30-event BTCUSDT packは次の分類です。

- decision: `BACKTEST_REJECT`
- reasons: `BIAS_GUARD_BLOCKED`、`BIAS_GUARD_FAILED_sample_sufficient_for_pbo`、`POSITION_OVERLAP_NOT_ACCOUNTED`、`INDEPENDENT_MARKET_EPISODE_SAMPLE_NOT_MET`、`SELECTOR_DOES_NOT_BEAT_BEST_STATIC_ACTION`
- event / outcome: `30 / 30`
- selected action: `CONTINUATION_LONG=12`、`REVERSAL_SHORT=2`、`NO_TRADE=16`
- executed simulated trades / wins: `14 / 10`
- after-cost / stress: `3.042366783076564551621614274 / 2.762366783076564551621614274 USD`
- peak concurrent positions: `6`
- market episodes / wins: `5 / 3`
- single-position total: `-0.4618201695034107750204885438 USD`
- always-long total: `5.816219911337534249441041925 USD`
- score/result correlation: `-0.2902937515082110915592253119`
- `REVERSAL_SHORT`: `2 trades / 0 wins / -0.4939911498820537167728313263 USD`
- PBO: `NOT_ESTIMABLE`、`fold_count=0`、`pbo_computed=false`
- bias guard: `BLOCKED`
- guard stop: `BIAS_GUARD_FAILED_sample_sufficient_for_pbo`
- warning: `BIAS_GUARD_WARNING_stress_cash_non_negative`

trade iid bootstrap total 95% intervalは`[+0.1069,+5.7882]`ですが、最大6同時positionの依存を無視します。5 episode bootstrap total 95% intervalは`[-1.9182,+9.2413]`で0を跨ぎ、single-position結果も負です。名目正値は仮説継続の材料であってprofit proofではありません。

cost sensitivityはslippage 2 bps / notional 100 USD=`+3.04237 USD`、slippage 50 bps=`-3.67763 USD`、notional 1000 USD=`+30.42367 USD`です。各rows SHAは異なり、cost identity変更が再計算へ反映されています。50 bpsで負になるため、実執行摩擦への耐性は未証明です。

default `fold_count=0`ではsample guardがBLOCKEDになります。foldを増やして`INPUT_THRESHOLD_MET`にしてもPBO計算済みではありません。Human Review Packetは専用PBO証跡を検査できるまで`pbo_evidence_verified=false`を維持するため、`COMPUTED_PASS`文字列だけでREADYへ進めません。

## Evidence grade summary

`decision.json` には `evidence_grade_summary` を出します。

これは decision を甘くするものではありません。証拠の強さを誤読しないための現実ラベルです。

| field | 読むこと |
|---|---|
| `overall_grade` | local simulation の証拠強度 |
| `strongest_evidence_level` | 現時点の最強証拠。actual cash ではない |
| `artifact_origin_counts` | existing と recomputed_minimal の混在 |
| `source_available_counts` | 使える source の種類と数 |
| `source_missing_counts` | books / trades / replay などの欠損 |
| `critical_missing_count` | critical source 欠損数 |
| `known_limits` | actual cash ではない、live readiness ではない等の限界 |

`overall_grade` は、少なくとも次のように読む。

- `insufficient_source_for_local_simulation`: critical source が欠けている。
- `local_simulation_with_recomputed_minimal_artifacts`: local simulation だが、recomputed minimal artifact を含む。
- `local_simulation_from_existing_artifacts`: local simulation であり、existing artifact 起点。ただし actual cash ではない。

## 読み方

| artifact | 読むこと | 読まないこと |
|---|---|---|
| `signal_rows.jsonl` | signal cutoff 時点で選ばれた action、entry allowed、UNKNOWN / NO_TRADE 理由 | outcome を見た後の裁量判断 |
| `data_availability_ledger.json` | source が signal cutoff 以前に利用可能だったか | unavailable source の zero-fill |
| `execution_assumptions.json` | fee、funding、slippage、holding、no-fill policy | 実約定条件や実現損益 |
| `tournament_rows_v2.json` | exact event set、outcome lineage、cost identity、全actionの反実仮想row | 選択方針そのものの利益証明 |
| `bias_guard.json` | current non-recursive policyで再計算したguard、PBO計算有無、warning | PBO未計算の代替証明 |
| `no_lookahead_report.json` | signal/source/feature の timestamp safety | alpha proof |
| `backtest_result.json` | cost-adjusted estimate の local simulation | actual cash profit |
| `stress_result.json` | stress estimate の local simulation | live readiness |
| `regime_split_result.json` | event family ごとの簡易 split | 十分な regime robustness |
| `rolling_stability_result.json` | sample size と cumulative stability | sample 十分性の自動証明 |
| `decision.json` | 4択decision、reason codes、profit robustness、`pack_component_refs` | live / tiny-live / paper permission |

## Pre Actual Cash との関係

2026-07-04 の `Pre Actual Cash Decision Gate` は historical context です。短期の current entry は、この Backtest Candidate Pack v1 です。

古い progress docs、pre-actual-cash gate doc、pre-actual-cash dogfood snapshots、完了済み implementation plans は `docs/archive/2026-07-05-docs-code-truth-cleanup/` へ移動済みです。

## 境界

この command は local artifact を読むだけです。

やらないこと:

- actual cash source 作成
- cash ledger 作成
- actual-cash rows 作成
- actual-cash report gate を通した profit proof
- tiny-live 実行
- live order
- wallet / signing
- exchange write
- ML/LLM trade decision
- `BACKTEST_PROMOTE_TO_LIVE`

## Verification

最小確認:

```bash
uv run pytest tests/crypto_perp/test_backtest_candidate_pack.py tests/crypto_perp/test_backtest_candidate_input_integrity.py
uv run sis crypto-perp-backtest-candidate-pack
jq '{decision, reason_codes, evidence_grade_summary, event_count, outcome_count, selected_action_counts: .summary.selected_action_counts, no_lookahead: .summary.no_lookahead, backtest: .summary.backtest, boundary, non_goal_flags}' data/crypto_perp/backtest_candidate_pack/latest/decision.json
```

広い確認:

```bash
uv run python scripts/check_current_docs.py
uv run python scripts/check_cli_catalog.py
./scripts/check
```

## Bias Guard / PBO Fail-Closed Contract

guardはpack-local rowsから現在のnon-recursive policyで毎回再計算します。`guard_status=BLOCKED`は`BACKTEST_REJECT`、guard missing / NOT_ESTIMABLE / unknownは`BACKTEST_COLLECT_MORE_DATA`です。error stop reasonはdecision summaryとreason codesへ、warningは`bias_guard_warning_codes`とknown gapへ残します。`stress_cash_non_negative`だけは全反実仮想action rowの診断warningで、選択方針のstress total、drawdown、最大損失、集中リスクは後段gateで引き続き拒否条件です。

PBOは別条件です。default `fold_count=0`は`NOT_ESTIMABLE`です。`INPUT_THRESHOLD_MET`とlegacy `ESTIMATED`も計算可能性の表示にすぎず、`pbo_computed=false`です。専用PBO計算証跡を検証するproducerがない現在は、`COMPUTED_PASS`というstatus文字列だけでもHOLDへ進めません。
