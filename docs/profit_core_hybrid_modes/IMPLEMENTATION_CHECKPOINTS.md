<!--
作成日: 2026-06-29_22:07 JST
更新日: 2026-06-29_22:07 JST
-->

# Implementation Checkpoints

## 結論

最初に実装するのは 3 checkpoint だけ。

```text
CP1 candidate_protocol_manifest.v1
CP2 trial_multiplicity_account.v1
CP3 backtest_kill_gate.v1 thin
```

`risk_taker_sprint` の広い候補生成、external venue virtual execution、LLM adversarial review は後続。ここを急ぐと false positive と実行不能候補が増える。

## CP1 candidate protocol manifest

目的:

候補生成前に、探索空間、sealed holdout、除外規則、mode、venue制約を固定する。

候補ファイル:

- `schemas/candidate_protocol_manifest.v1.schema.json`
- `src/sis/edge_candidates/protocol.py`
- `src/sis/commands/edge_candidates.py`
- `tests/edge_candidates/test_protocol_manifest.py`

完了条件:

- `verification_throughput` と `risk_taker_sprint` を mode enum として持つ。
- `permits_actual_cash=false` と `permits_live_order=false` を固定する。
- sealed holdout definition が無い protocol を invalid にする。
- `risk_taker_sprint` には `mode_isolation=true` を要求する。

検証:

```bash
uv run pytest tests/edge_candidates/test_protocol_manifest.py -q
uv run python scripts/check_cli_catalog.py
uv run python scripts/check_current_docs.py
git diff --check
```

止める条件:

- protocol 作成時に source / venue / sealed holdout が曖昧。
- attack mode が actual cash 直行できる表現になる。

## CP2 trial multiplicity account

目的:

探索回数、family clustering、validation peek、rerank、未推定 status を保存する。

候補ファイル:

- `schemas/trial_multiplicity_account.v1.schema.json`
- `src/sis/edge_candidates/multiplicity.py`
- `tests/edge_candidates/test_multiplicity_account.py`

完了条件:

- `success_only_reporting=false` を必須にする。
- `sealed_test_used_for_selection=false` を必須にする。
- `PBO` / `DSR` / `White Reality Check` は入力不足時に `NOT_ESTIMABLE` を出す。
- `BH/FDR` は `raw_p_value_count > 0` の時だけ `AVAILABLE`。
- `effective_trial_count` と `correlation_cluster_count` を空欄にしない。推定不能なら理由を出す。

検証:

```bash
uv run pytest tests/edge_candidates/test_multiplicity_account.py -q
uv run pytest tests/strategy_idea_candidates/test_candidate_set_validation.py tests/strategy_idea_candidates/test_candidate_generator.py -q
git diff --check
```

止める条件:

- `AVAILABLE` を performance pass と誤読できる。
- family cluster を無視して BH/FDR を単独合格条件にする。

## CP3 backtest kill gate thin

目的:

候補を `KILL` / `INCONCLUSIVE_DATA` / `RESEARCH_ONLY` / `SHORTLIST_FOR_VIRTUAL` に分ける薄い gate を作る。

候補ファイル:

- `schemas/backtest_kill_gate.v1.schema.json`
- `src/sis/edge_candidates/backtest_kill_gate.py`
- `tests/edge_candidates/test_backtest_kill_gate.py`

完了条件:

- `NO_TRADE` 比較が無い candidate を `INCONCLUSIVE_DATA` に止める。
- family-specific event count policy を使う。
- `after_cost_edge_over_no_trade <= 0` は原則 `KILL`。
- source gap がある execution candidate は `INCONCLUSIVE_DATA` または `RESEARCH_ONLY`。
- output が live / paper / actual cash permission を持たない。

検証:

```bash
uv run pytest tests/edge_candidates/test_backtest_kill_gate.py -q
uv run pytest tests/crypto_perp/test_tournament_gate.py tests/crypto_perp/test_bias_guards.py -q
git diff --check
```

止める条件:

- `SHORTLIST_FOR_VIRTUAL` を trade permission と読める。
- rare dislocation を event_count だけで無条件 KILL にする。

## CP4 candidate-to-backtest bridge status split

目的:

C9 v0 bridge の `BRIDGED` を技術接続 status として分解し、経済的合格と混同しない。

候補 status:

```text
BRIDGED_TECHNICAL_ONLY
BLOCKED_UNSUPPORTED_FAMILY
BLOCKED_MISSING_SOURCE
BLOCKED_BACKTEST_PACK
BLOCKED_ECONOMIC_GATE
BLOCKED_MULTIPLICITY_ACCOUNT
```

止める条件:

- C9 bridge を Core 本体として固定してしまう。
- `BRIDGED_TECHNICAL_ONLY` を alpha proof に見せる。

## CP5 thin virtual execution gate

目的:

actual cash 前に order lifecycle と reconciliation を local/mock で検査する。PnL 判定はしない。

初期 scope:

- local lifecycle state machine。
- virtual fill ledger。
- duplicate order prevention。
- flat reconciliation。
- explicit false permissions。

後続:

- Bitget demo。
- Hyperliquid testnet / read-only。
- GRVT testnet。

外部 venue は同時実装しない。

## CP6 LLM adversarial evidence review

目的:

evidence packet の矛盾、欠落、overclaim を検出する。許可は出さない。

出力:

```text
ADVERSARIAL_FINDING
NEEDS_MORE_EVIDENCE
OVERCLAIM_FLAG
HUMAN_REVIEW_REQUIRED
NO_ADDITIONAL_BLOCKER_FOUND
```

hard blocker にできるのは machine-checkable な欠落だけ。

## CP7 risk-taker sprint mode

目的:

隔離された攻撃モードとして探索幅を広げる。

前提:

- CP1-CP3 が実装済み。
- sprint output が default mode 集計に混ざらない。
- sprint candidate が actual cash へ直行しない。

禁止:

- GA/ML 先行。
- external venue 同時対応。
- attack mode で actual cash boundary を緩める。

## 最初のPRでやらないこと

- GA / ML。
- LightGBM / XGBoost / Optuna / tsfresh 追加。
- Bitget demo 実行。
- Hyperliquid / GRVT 対応。
- LLM API 連携。
- Workbench UI 強化。
- live / tiny-live / actual cash 実行。
