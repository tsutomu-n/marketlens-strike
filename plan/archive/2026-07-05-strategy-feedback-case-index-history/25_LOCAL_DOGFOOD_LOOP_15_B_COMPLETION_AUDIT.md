<!--
作成日: 2026-06-22_21:33 JST
更新日: 2026-06-22_21:33 JST
-->

# Local Dogfood Loop 15 B Completion Audit

## 結論

B の `ndx_open_gap_residual_v1` local dogfood slice は、現時点で実装可能な「楽観表示を潰す」範囲はかなり固まった。

確認した current artifact では、Runtime Observation、Input Feedback proposal / review、Case Lite、Case Index、Viewer が同じ停止境界を示している。`READY_FOR_HUMAN_REVIEW` が残る proposal はあるが、対応する review は `HOLD` で、Case Lite / Case Index も `HOLD` になっている。PnL 不足、stale quote age、manual update 未承認、paper/live 不許可も Viewer summary から確認できる。

この audit は B の local dogfood slice の完了確認であり、active goal 全体の完了ではない。A の trend runtime observation / learning event、C の Crypto Perp viewer / daily brief dogfood、paper evidence lane、manual contract update、credentialed/network work は別判断として残る。

## 1. 計画

対象:

- lane: `Local dogfood`
- candidate: B
- strategy_id: `ndx_open_gap_residual_v1`
- current viewer:
  - `data/local_dogfood/2026-06-22-ndx-open-gap/viewer/strategy_workbench_viewer_manifest.json`
  - `data/local_dogfood/2026-06-22-ndx-open-gap/viewer/strategy_workbench_viewer.html`
- docs:
  - `plan/2026-06-22-strategy-feedback-case-index/17_LOCAL_DOGFOOD_SELECTION_CATALOG.md`
  - this audit doc

完了条件:

- current viewer manifest を読み、8 artifact の status / summary が停止境界を示すことを確認する。
- 古い Loop 結果 docs の historical statement と current selection doc を分ける。
- 選定カタログの B 欄を Loop 14 後の current read に更新する。
- B local dogfood slice の完了 / 未完了 / 別前提を分ける。
- docs check と full check を通す。

やらないこと:

- manual contract update。
- paper order。
- live order。
- credentialed network。
- wallet、signing、exchange write。
- historical loop result docs の書き換え。

## 2. 追加調査と現実チェック

Current Viewer manifest:

```text
artifact_count=8
boundary_violation_count=0
```

Runtime Observation:

```text
status=INGESTED
paper_order_count=20
paper_fill_count=20
no_fill_count=0
blocked_count=0
filled_notional_usd_total=20000.0
max_observed_quote_age_ms=1048982067
max_observed_spread_bps=0.332474441027346
pnl_available=false
pnl_unavailable_reason=ledger rows do not include realized_pnl_usd, paper_pnl_usd, or pnl_usd
paper_execution_allowed=false
live_allowed=false
```

Input Feedback source contract なし:

```text
proposal status=NEEDS_SOURCE_CONTRACT_CONTEXT
review decision=HOLD
manual_contract_update_input_allowed=false
auto_applied=false
direct_contract_edit_allowed=false
paper_execution_allowed=false
live_allowed=false
```

Input Feedback source contract あり:

```text
proposal status=READY_FOR_HUMAN_REVIEW
review decision=HOLD
source_proposal_status=READY_FOR_HUMAN_REVIEW
manual_contract_update_input_allowed=false
auto_applied=false
direct_contract_edit_allowed=false
paper_execution_allowed=false
live_allowed=false
```

Case Lite:

```text
status=HOLD
latest_status=HOLD
first_open_action=Choose a human-approved manual contract update target before applying runtime-001 to any Strategy Input Contract.
first_blocked_reason=strategy_input_feedback_proposal:NEEDS_SOURCE_CONTRACT_CONTEXT
paper_execution_allowed=false
live_allowed=false
```

Case Index:

```text
status=HOLD
case_count=1
strategy_count=1
latest_status=HOLD
first_open_action=Choose a human-approved manual contract update target before applying runtime-001 to any Strategy Input Contract.
first_blocked_reason=strategy_input_feedback_proposal:NEEDS_SOURCE_CONTRACT_CONTEXT
paper_execution_allowed=false
live_allowed=false
```

Historical docs handling:

- `10_LOCAL_DOGFOOD_LOOP_01_PLAN_REVIEW_RESULTS.md` and `19_LOCAL_DOGFOOD_LOOP_09_NDX_INPUT_FEEDBACK_VIEWER_RESULTS.md` contain old `strategy_case_lite.v1 INGESTED` observations. These are historical loop snapshots, not current truth.
- Current read should come from `20` through `25`, code, tests, schema, CLI, and the regenerated viewer manifest.
- `17_LOCAL_DOGFOOD_SELECTION_CATALOG.md` is a selection/current-catalog doc, so it was updated with Loop 14 state.

## 3. 実装

変更した docs:

- `plan/2026-06-22-strategy-feedback-case-index/17_LOCAL_DOGFOOD_SELECTION_CATALOG.md`
  - B を Loop 14 後の current read に更新。
  - B は「まだ選ぶ候補」ではなく、いったん dogfood 済み slice として読むことを追記。
  - Case Lite / Case Index / Viewer の `HOLD`、PnL 不足、stale quote、manual update 未承認、不許可 flag を明記。
- `plan/2026-06-22-strategy-feedback-case-index/00_READ_ME_FIRST.md`
  - this audit doc を読む順に追加。
- `plan/2026-06-22-strategy-feedback-case-index/25_LOCAL_DOGFOOD_LOOP_15_B_COMPLETION_AUDIT.md`
  - B completion audit を追加。

コード変更:

- なし。

generated artifact 再生成:

- なし。Loop 14 の regenerated viewer manifest を audit source として使用。

## 完了判定

B local dogfood slice で完了と言えるもの:

1. Runtime Observation の quote age / PnL 不足が Viewer summary に出る。
2. Input Feedback proposal の first evidence が Viewer summary に出る。
3. Input Feedback review の `HOLD` が status badge と summary に出る。
4. `manual_contract_update_input_allowed=false`、`direct_contract_edit_allowed=false`、`auto_applied=false`、`paper_execution_allowed=false`、`live_allowed=false` が review summary に出る。
5. Case Lite / Case Index が `HOLD` を示す。
6. Case Lite / Case Index が first open action / first blocked reason を示す。
7. Boundary violation count は 0。
8. Schema / code / tests / docs は full check で検証する。

B local dogfood slice で未完了だが、今回の実装対象外のもの:

1. manual contract update。
   - 絶対前提: ユーザー承認済みの更新対象、更新方針、差分 review。
2. paper evidence threshold の充足。
   - 絶対前提: paper observation days / sessions の追加 evidence。
3. PnL evidence の補完。
   - 絶対前提: ledger rows に realized / paper / pnl field がある source artifact。
4. quote freshness の修復。
   - 絶対前提: fresh quote capture または freshness policy に合う source artifact。
5. credentialed/network work。
   - 絶対前提: explicit approval、credential handling、network permission、side-effect boundary。

## 残リスク

- B は local dogfood としては読める状態になったが、収益性、paper readiness、live readiness は証明していない。
- `READY_FOR_HUMAN_REVIEW` proposal は残るが、review が `HOLD` なので manual update input には進めない。
- historical Loop docs には当時の `INGESTED` snapshot が残る。current read は newer Loop docs と regenerated viewer manifest を優先する。
- generated `data/local_dogfood/...` は runtime/generated state であり、tracked source of truth ではない。tracked docs は再開索引である。

## 次の実務的な選択肢

1. A に戻り、trend の Runtime Observation / Learning Event を作る価値を判断する。
2. C に移り、Crypto Perp Viewer / Daily Brief の permission flag 表示を同じ観点で dogfood する。
3. B を paper evidence lane に進める。ただしこれは local dogfood ではなく、paper evidence / freshness / PnL 前提の別 work になる。
