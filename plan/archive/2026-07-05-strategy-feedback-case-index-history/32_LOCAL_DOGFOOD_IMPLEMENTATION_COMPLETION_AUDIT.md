<!--
作成日: 2026-06-22_22:32 JST
更新日: 2026-06-22_22:37 JST
-->

# Local Dogfood Implementation Completion Audit

## 結論

このフォルダーの active plan で実装可能だった範囲は、2026-06-22_22:37 JST 時点で実装・dogfood・検証済み。

対象は次の範囲に限る。

1. Strategy Input Feedback proposal / review。
2. Strategy Case Lite Index。
3. Strategy Case Lite の additional artifact input。
4. Static Workbench Viewer の summary 改善。
5. `1=Local dogfood`、`2=unknown`、`3=Codex推奨`、`4/5=未決` というユーザー回答に基づく、現存 artifact の網羅 inventory と推奨順位付け。
6. 選択候補 A/B/C のうち、B は既存 dogfood 完了、A と C は追加 dogfood と Viewer summary 改善まで完了。

この完了は、paper readiness、live readiness、account readiness、wallet readiness、signing readiness、exchange-write readiness、profit proof、production readiness を意味しない。

## 1. 監査対象

### 1.1 実装契約

正として読んだ計画:

- [01_IMPLEMENTATION_CONTRACT.md](01_IMPLEMENTATION_CONTRACT.md)
- [02_TASKS.md](02_TASKS.md)
- [04_TEST_AND_ACCEPTANCE.md](04_TEST_AND_ACCEPTANCE.md)
- [06_DEFERRED_WORK_AND_ENTRY_CRITERIA.md](06_DEFERRED_WORK_AND_ENTRY_CRITERIA.md)
- [07_IMPLEMENTABLE_REMAINING_RISK_DETAIL.md](07_IMPLEMENTABLE_REMAINING_RISK_DETAIL.md)
- [08_USER_INPUTS_AND_PROVISION_GUIDE.md](08_USER_INPUTS_AND_PROVISION_GUIDE.md)
- [29_LOCAL_DOGFOOD_ALL_CURRENT_SELECTION_INVENTORY.md](29_LOCAL_DOGFOOD_ALL_CURRENT_SELECTION_INVENTORY.md)

コード側で確認した正本:

- `src/sis/strategy_input_feedback/`
- `src/sis/strategy_case_index/`
- `src/sis/strategy_case_lite/`
- `src/sis/strategy_workbench_viewer/`
- `schemas/strategy_input_contract_update_proposal.v1.schema.json`
- `schemas/strategy_input_contract_update_review.v1.schema.json`
- `schemas/strategy_case_index.v1.schema.json`
- `schemas/strategy_case_lite.v1.schema.json`
- `schemas/strategy_workbench_viewer.v1.schema.json`
- `tests/strategy_input_feedback/`
- `tests/strategy_case_index/`
- `tests/strategy_case_lite/`
- `tests/strategy_workbench_viewer/`
- `uv run sis --help`
- `./scripts/check`

### 1.2 ユーザー回答の扱い

| 番号 | ユーザー回答 | この監査での扱い |
|---:|---|---|
| 1 | `Local dogfood` | 外部 API、credential、paper order、live order、wallet、signing、exchange write を使わない。手元の artifact だけで試す。 |
| 2 | `unknown` | strategy / venue / case は最初に固定しない。現存 artifact を列挙してから選ぶ。 |
| 3 | `Codex推奨` | 現物の有無、status、危険な誤読、外部前提を見て推奨順位を付ける。 |
| 4 | 未決 | network、paper order、live order、wallet、signing、exchange write は許可されていないものとして扱う。 |
| 5 | 未決 | secret、account raw data、statement raw data、注文 ID、残高全文は扱わない。 |

この回答に対する成果物は [29_LOCAL_DOGFOOD_ALL_CURRENT_SELECTION_INVENTORY.md](29_LOCAL_DOGFOOD_ALL_CURRENT_SELECTION_INVENTORY.md)。この文書は、Local dogfood で選べる現存 artifact を網羅し、A/B/C/D/E/F/G に分類した。

## 2. 実装完了判定

### 2.1 T0: 実装前確認

判定: 完了。

確認済み:

- `HANDOFF.md` は restart artifact として読んだが、期待 HEAD `551bb28` は現行 HEAD と合っていなかった。
- 現行 HEAD は `de5d812`。
- `git status --short --branch` は `## main...origin/main` で、作業差分はこの実装・docs 由来。
- CLI surface は `uv run sis --help` で確認した。

補足:

- `HANDOFF.md` は古いので、今後の restart 混乱を避けるには最後に更新が必要。

### 2.2 T1/T2: Strategy Input Feedback

判定: 完了。

実装済み:

- `strategy_input_contract_update_proposal.v1`
- `strategy_input_contract_update_review.v1`
- `strategy-input-feedback-proposal-build`
- `strategy-input-feedback-proposal-review`
- source artifact の path / hash / schema version 記録。
- Runtime Observation / Learning Event からの proposal 生成。
- source contract なし proposal を `NEEDS_SOURCE_CONTRACT_CONTEXT` として止める境界。
- source contract あり proposal を human review 用 artifact として止める境界。
- review decision、approved_change_ids、required_actions の整合検査。
- direct apply、auto patch、paper/live permission を許可しない boundary。

Local dogfood:

- B: `ndx_open_gap_residual_v1` で source contract なし / あり proposal と review を作成済み。
- source contract なしは `NEEDS_SOURCE_CONTRACT_CONTEXT`。
- source contract ありは `READY_FOR_HUMAN_REVIEW` だが、review は `HOLD`。

残るもの:

- manual contract update は未実装。これは D3 の entry criteria 待ち。
- A: `trend_pullback_user_v1` には Runtime Observation / Learning Event がないため、Input Feedback proposal は作っていない。これは正しい未着手。

### 2.3 T3/T4: Strategy Case Lite Index

判定: 完了。

実装済み:

- `strategy_case_index.v1`
- `strategy-case-index-build`
- explicit `--case` 複数指定。
- `--data-dir` scan。
- `strategy_case_lite.v1` だけを採用する scan。
- duplicate path / hash の deterministic dedupe。
- case count / strategy count / latest case / open actions / blocked reasons / source hash。
- index は read-only derived artifact。DB registry ではない。

Local dogfood:

- B: `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_case_index/ndx-open-gap-local-dogfood-index.json`
- A: `data/local_dogfood/2026-06-22-trend-pullback/strategy_case_index/trend-pullback-local-dogfood-index.json`

残るもの:

- full registry、DB、merge workflow、conflict resolution は未実装。これは D4 の entry criteria 待ち。

### 2.4 T4A: Strategy Case Lite additional artifact input

判定: 完了。

実装済み:

- `strategy-case-lite-update --artifact`
- known schema を typed timeline artifact として扱う処理。
- unknown schema を generic に落とす処理。
- backtest result / pack / pack validation / suite / comparison / review manifest / input validation を Case Lite に入れる経路。
- `status` top-level key を timeline status 候補として読む処理。
- boundary は paper / live / wallet / signing / exchange write を許可しない。

Local dogfood:

- A: `trend_pullback_user_v1` の backtest-only artifact を Case Lite / Case Index / Viewer へ通した。
- A の Case Lite は `READY_FOR_HUMAN_REVIEW`。これは review 用の状態であり、paper/live readiness ではない。

### 2.5 T5: Static Workbench Viewer

判定: 完了。

実装済み:

- `strategy_case_index.v1` summary。
- `strategy_case_lite.v1` summary の latest status / open action / blocked reason / artifact count / timeline count / first source artifact。
- `strategy_input_contract_update_proposal.v1` summary。
- `strategy_input_contract_update_review.v1` summary。
- `strategy_runtime_observation_manifest.v1` summary。
- `strategy_authoring_backtest_result.v1` summary。
- `strategy_backtest_pack.v1` summary。
- `strategy_backtest_pack_validation.v1` summary。
- `strategy_backtest_suite_result.v1` summary。
- `strategy_backtest_comparison.v1` summary。
- `strategy_daily_brief.v1` summary。
- permission 系 true flag は boundary violation として扱い、許可表示として扱わない。
- manifest shape は変えていない。`strategy_workbench_viewer.v1` の `summary: dict[str, Any]` の範囲内。

追加 refactor:

- `src/sis/strategy_workbench_viewer/service.py` の summary 抽出ロジックを `src/sis/strategy_workbench_viewer/summary.py` に分割した。
- 分割後の行数:
  - `src/sis/strategy_workbench_viewer/service.py`: 172 lines
  - `src/sis/strategy_workbench_viewer/summary.py`: 728 lines
- これで「新規または大きく編集する Python file は 800 行以下」の制約を source file 側で満たした。

Local dogfood:

- B: `ndx_open_gap_residual_v1` Viewer dogfood は Loop 08-15 で完了。
- A: `trend_pullback_user_v1` Viewer dogfood は Loop 16-18 で追加実施。
- C: Crypto Perp truth-cycle viewer-only は Loop 19 で追加実施。

残るもの:

- Svelte UI、server UI、DB、auth、interactive timeline editor は未実装。これは D5 の entry criteria 待ち。

### 2.6 T6/T7: docs / CLI catalog / final verification

判定: 完了。

確認済み:

- current docs check 通過。
- CLI catalog check 通過。
- full check 通過。
- plan docs に Local dogfood inventory、追加 dogfood 結果、残リスクを記録済み。

## 3. 生成・更新済み Local Dogfood Artifact

### 3.1 A: `trend_pullback_user_v1`

Primary artifacts:

- `data/local_dogfood/2026-06-22-trend-pullback/strategy_inputs/trend_pullback_user_v1_input_contract.yaml`
- `data/local_dogfood/2026-06-22-trend-pullback/strategy_inputs/validation/strategy_input_contract_validation.json`
- `data/local_dogfood/2026-06-22-trend-pullback/strategy_cases/trend_pullback_user_v1/strategy_case_lite.json`
- `data/local_dogfood/2026-06-22-trend-pullback/strategy_case_index/trend-pullback-local-dogfood-index.json`
- `data/local_dogfood/2026-06-22-trend-pullback/viewer/strategy_workbench_viewer_manifest.json`
- `data/local_dogfood/2026-06-22-trend-pullback/viewer/strategy_workbench_viewer.html`

Viewer summary で確認できる主な値:

- `artifact_count=9`
- `boundary_violation_count=0`
- Case Lite summary:
  - `artifact_count=7`
  - `timeline_count=7`
  - `latest_status=READY_FOR_HUMAN_REVIEW`
  - `first_source_artifact_type=strategy_input_contract_validation`
  - `first_source_artifact_path=data/local_dogfood/2026-06-22-trend-pullback/strategy_inputs/validation/strategy_input_contract_validation.json`

### 3.2 B: `ndx_open_gap_residual_v1`

Primary artifacts:

- `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_runtime_observation/strategy_runtime_observation_manifest.json`
- `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback/ndx_open_gap_residual_v1/ndx_open_gap_residual_v1-input-feedback-e7447e63.json`
- `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback_with_contract/ndx_open_gap_residual_v1/ndx_open_gap_residual_v1-input-feedback-f3cb881ae7447e63.json`
- `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_cases/ndx_open_gap_residual_v1/strategy_case_lite.json`
- `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_case_index/ndx-open-gap-local-dogfood-index.json`
- `data/local_dogfood/2026-06-22-ndx-open-gap/viewer/strategy_workbench_viewer_manifest.json`
- `data/local_dogfood/2026-06-22-ndx-open-gap/viewer/strategy_workbench_viewer.html`

重要な読み:

- Runtime Observation は `INGESTED`。
- PnL は `pnl_available=false`。
- max observed quote age は `1048982067 ms`。
- proposal review は `HOLD`。
- Case Lite status は `HOLD`。
- これは manual update や paper/live readiness ではない。

### 3.3 C: Crypto Perp truth-cycle viewer-only

Primary artifacts:

- `data/crypto_perp/truth_cycle_dogfood_check/truth_cycle_status/truth_cycle_status.json`
- `data/crypto_perp/truth_cycle_dogfood_check/reports/strategy_daily_brief/strategy_daily_brief.json`
- `data/crypto_perp/truth_cycle_dogfood_check/reports/strategy_workbench_viewer/strategy_workbench_viewer_manifest.json`
- `data/crypto_perp/truth_cycle_dogfood_check/reports/strategy_workbench_viewer/strategy_workbench_viewer.html`

Viewer summary で確認できる主な値:

- `artifact_count=4`
- `boundary_violation_count=0`
- Daily Brief summary:
  - `scanned_json_count=3`
  - `total_item_count=1`
  - `crypto_perp_truth_cycle_follow_up_count=1`
  - `first_brief_item_status=MISSING_PROBE_AUDIT`
  - `first_brief_item_action=uv run sis crypto-perp-probe-audit --probe <provider_probe.json> --out <probe-audit-dir>`

重要な読み:

- `MISSING_PROBE_AUDIT` は次に必要な確認を示すだけ。
- probe audit、network、credential、tiny live measurement は実行していない。
- Viewer は truth-cycle status を進めない。

## 4. 検証結果

### 4.1 近接検証

分割後の Viewer 検証:

```text
uv run ruff format src/sis/strategy_workbench_viewer/service.py src/sis/strategy_workbench_viewer/summary.py
-> 1 file reformatted, 1 file left unchanged

uv run ruff check src/sis/strategy_workbench_viewer/service.py src/sis/strategy_workbench_viewer/summary.py
-> All checks passed!

uv run pytest tests/strategy_workbench_viewer -q
-> 15 passed in 1.23s
```

CLI surface 確認:

```text
uv run sis --help
-> strategy-input-feedback-proposal-build
-> strategy-input-feedback-proposal-review
-> strategy-case-lite-update
-> strategy-case-index-build
-> strategy-daily-brief
-> strategy-workbench-viewer-build
```

### 4.2 全体検証

```text
./scripts/check
-> Python 3.13.7
-> ruff check: All checks passed
-> ruff format --check: 800 files already formatted
-> current docs: checked 186 current docs ... ok
-> CLI catalog: checked 208 public CLI commands against Typer registration
-> Pyrefly: 0 errors
-> ty: All checks passed
-> pytest: 1529 passed in 69.49s
```

## 5. まだ着手しないもの

次は「実装不能」ではない。ただし、この plan の完了だけでは entry criteria を満たしていない。

| ID | 領域 | 状態 | 絶対前提条件 |
|---|---|---|---|
| D1 | Paper Bridge Validation | 未着手 | 対象 strategy 固定、Strategy Input Contract / Idea / Authoring YAML / backtest / review / Stage Decision / Paper Smoke Plan の一式、paper permission 誤読防止方針 |
| D2 | Normal Paper Observation Continuation | 未着手 | 新しい trading day を含む paper evidence、normal threshold gap の再確認、session / artifact dir / reports dir の固定 |
| D3 | Strategy Input Contract Direct Apply | 未着手 | proposal/review の複数 dogfood、approved/rejected/hold sample、backup、rollback、diff format、人間承認 step |
| D4 | Strategy Case Full Registry | 未着手 | Case Lite Index で足りない具体的な運用痛み、storage判断、merge policy、conflict resolution、migration方針 |
| D5 | Svelte UI / Server UI | 未着手 | Static Viewer で解けない workflow 3件以上、source of truth 方針、auth / file access / artifact write 方針、E2E fixture |
| D6 | Bitget Read-only Probe | 未着手 | 別 plan、demo/production分離、read-only or demo credential、redaction test、normal CI no-network、timeout/rate-limit/stop condition |
| D7 | Hyperliquid Read-only Probe | 未着手 | public/address/credentialed のどれを扱うかの固定、no-write boundary、network opt-in 方針 |
| D8-D13 | preview/order/live/secret系 | 未着手 | D6/D7、explicit approval、secret管理、account boundary、write禁止または tiny-live の明示承認 |
| D14-D15 | optimizer / profit claim | 未着手 | 評価設計、no-auto-apply、paper/normal evidence、accounting evidence |
| D19-D21 | freshness / ops / accounting | 未着手 | data freshness policy、operations drill、cash/fee/funding/statement reconciliation |

## 6. 残リスク

### 6.1 Test file size

`tests/strategy_workbench_viewer/test_strategy_workbench_viewer.py` は 1264 行ある。

現行の機械 gate は `src/sis/research/strategy_lab/authoring` だけを 800 行制約で検査しており、この test file は gate 対象ではない。ただし、Viewer summary の対応 schema が増えてきたため、将来は summary type ごとに test file を分ける余地がある。

この監査では、実装制約上の source file 違反だった `src/sis/strategy_workbench_viewer/service.py` を 172 行へ分割し、`summary.py` も 728 行に収めた。

### 6.2 Local dogfood artifact は gitignored

`data/local_dogfood/` と `data/crypto_perp/` 配下の生成 artifact は runtime/generated state として gitignored の可能性が高い。

したがって、再現に必要なコマンドと結果は plan docs に残しているが、commit 差分としては見えない。future coder は artifact が手元にない場合、各 loop doc の再生成コマンドから作り直す。

### 6.3 `HANDOFF.md` restart risk

`.ai_memory/HANDOFF.md` は作業開始時点では古い HEAD `551bb28` を期待していた。今回の実装・docs・検証後に更新し、現行 HEAD `de5d812` 上の dirty worktree と completion audit から再開する契約へ直した。

この監査後の扱い:

1. 次回 restart では `.ai_memory/HANDOFF.md` を読んだうえで、code / tests / schemas / CLI help / plan `32` を正として再確認する。
2. 最新 full check は `1529 passed in 69.49s`。
3. 次 action を「final review / commit preparation」にする。

## 7. 完了条件への最終照合

| 完了条件 | 判定 | 根拠 |
|---|---|---|
| 新規 CLI が `uv run sis --help` に出る | pass | help に対象 command が表示される |
| 新規 schema が fixture と pytest で確認される | pass | full pytest 通過 |
| Runtime Observation / Learning Event fixture から proposal artifact を生成できる | pass | Strategy Input Feedback tests と B dogfood |
| source contract なし proposal が apply-ready と誤読されない | pass | `NEEDS_SOURCE_CONTRACT_CONTEXT` と review `HOLD` |
| proposal review artifact が decision を持ち direct apply を許可しない | pass | model/service/tests と dogfood |
| 複数 Case Lite から Case Index を生成できる | pass | Strategy Case Index tests と A/B dogfood |
| Viewer が Case Index / Case Lite / backtest / Daily Brief を表示できる | pass | Loop 16-19 と tests |
| current docs と CLI catalog が通る | pass | `./scripts/check` 内で通過 |
| 800 行制約への実務対応 | pass | `service.py=172`, `summary.py=728` |
| `./scripts/check` が通る | pass | `1529 passed in 69.49s` |
| live / wallet / signing / exchange write を実施していない | pass | 全 loop は local/offline artifact workflow。外部副作用なし |

## 8. 最終判定

実装可能だった active plan の範囲は完了。

ただし、次へ進めるにはユーザーが未決の 4/5 を決めるか、D1-D21 の各 entry criteria を個別に満たす必要がある。特に paper evidence、credentialed probe、secret、network、tiny-live、accounting は、この完了を根拠に自動で進めてはいけない。
