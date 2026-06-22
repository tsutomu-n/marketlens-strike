<!--
作成日: 2026-06-22_22:22 JST
更新日: 2026-06-22_22:25 JST
-->

# Local Dogfood Loop 19 Crypto Perp Daily Brief Viewer Summary Results

## 結論

C: Crypto Perp truth-cycle viewer-only の Local dogfood を実施した。

修正前は `strategy_daily_brief.v1` の JSON には follow-up count、first item の category / status / action / reason が入っていたが、Workbench Viewer manifest では `boundary_violation_count` と `pending_human_review_count` 程度しか見えなかった。これでは、`MISSING_PROBE_AUDIT` で止まっている理由と次に確認すべき command が Viewer で見落とされやすい。

修正後は、Daily Brief の count と first brief item の category / severity / status / schema / action / reason / path が Viewer compact summary に出る。

これは read-only な表示改善であり、credentialed network、probe audit 実行、paper order、live order、wallet、signing、exchange write、tiny live measurement の許可ではない。

## 1. 計画

対象:

- lane: `Local dogfood`
- selection: `C`
- scope: Crypto Perp truth-cycle viewer-only
- primary viewer:
  - `data/crypto_perp/truth_cycle_dogfood_check/reports/strategy_workbench_viewer/strategy_workbench_viewer_manifest.json`
  - `data/crypto_perp/truth_cycle_dogfood_check/reports/strategy_workbench_viewer/strategy_workbench_viewer.html`

完了条件:

- `strategy_daily_brief.v1` の現物構造を確認する。
- Viewer compact summary に、Daily Brief の count と first item を追加する。
- focused RED / GREEN を残す。
- Crypto Perp dogfood check Viewer を再生成し、現物 manifest に summary が出ることを確認する。
- docs を更新し、focused tests と docs check を通す。

やらないこと:

- network。
- credential。
- probe audit 実行。
- paper order。
- live order。
- wallet、signing、exchange write。
- tiny live measurement。

## 2. 追加調査と現実チェック

修正前の Viewer 現物:

```text
strategy_daily_brief.v1:
- summary.boundary_violation_count=0
- summary.pending_human_review_count=0
```

Daily Brief JSON には次が存在していた。

```text
summary:
- scanned_json_count=3
- total_item_count=1
- broken_artifact_count=0
- pending_human_review_count=0
- crypto_perp_gate_follow_up_count=0
- crypto_perp_truth_cycle_follow_up_count=1
- normal_paper_gap_count=0
- drift_review_needed_count=0
- learning_request_pending_count=0
- boundary_violation_count=0

first item:
- category=crypto_perp_truth_cycle_follow_up
- severity=warning
- status=MISSING_PROBE_AUDIT
- schema_version=crypto_perp_truth_cycle_status.v1
- action=uv run sis crypto-perp-probe-audit --probe <provider_probe.json> --out <probe-audit-dir>
- reason=crypto perp truth-cycle follow-up: uv run sis crypto-perp-probe-audit --probe <provider_probe.json> --out <probe-audit-dir>
- path=data/crypto_perp/truth_cycle_dogfood_check/truth_cycle_status/truth_cycle_status.json
```

判断:

- Daily Brief は「今日見るべき follow-up」を読むための artifact なので、first item の action / reason が Viewer に出る価値は高い。
- `action` は next command の表示であり、実行許可ではない。
- `<provider_probe.json>` は placeholder であり secret や credential ではない。
- `live_allowed=false` と `paper_execution_allowed=false` は引き続き compact summary に残す。

## 3. 実装

変更した code:

- `src/sis/strategy_workbench_viewer/service.py`
  - compact summary key に次を追加。
    - `scanned_json_count`
    - `total_item_count`
    - `broken_artifact_count`
    - `crypto_perp_gate_follow_up_count`
    - `crypto_perp_truth_cycle_follow_up_count`
    - `normal_paper_gap_count`
    - `drift_review_needed_count`
    - `learning_request_pending_count`
    - `first_brief_item_category`
    - `first_brief_item_severity`
    - `first_brief_item_status`
    - `first_brief_item_schema_version`
    - `first_brief_item_action`
    - `first_brief_item_reason`
    - `first_brief_item_path`
  - `strategy_daily_brief.v1` の `items` から first item を抽出する処理を追加。

変更した tests:

- `tests/strategy_workbench_viewer/test_strategy_workbench_viewer.py`
  - `test_strategy_workbench_viewer_summarizes_strategy_daily_brief_follow_up` を追加。

更新した docs:

- `docs/strategy_workbench_viewer/README.md`
  - Daily Brief count / first brief item summary を明記。
- `plan/2026-06-22-strategy-feedback-case-index/29_LOCAL_DOGFOOD_ALL_CURRENT_SELECTION_INVENTORY.md`
  - C の補足として Loop 19 の結果を追記。

再生成した local artifact:

- `data/crypto_perp/truth_cycle_dogfood_check/reports/strategy_workbench_viewer/strategy_workbench_viewer.html`
- `data/crypto_perp/truth_cycle_dogfood_check/reports/strategy_workbench_viewer/strategy_workbench_viewer_manifest.json`

再生成コマンド:

```bash
uv run sis strategy-workbench-viewer-build \
  --artifact data/crypto_perp/truth_cycle_dogfood_check/truth_cycle_status/truth_cycle_status.json \
  --artifact data/crypto_perp/truth_cycle_dogfood_check/truth_cycle_status/truth_cycle_status.md \
  --artifact data/crypto_perp/truth_cycle_dogfood_check/reports/strategy_daily_brief/strategy_daily_brief.json \
  --artifact data/crypto_perp/truth_cycle_dogfood_check/reports/strategy_daily_brief/strategy_daily_brief.md \
  --out data/crypto_perp/truth_cycle_dogfood_check/reports/strategy_workbench_viewer \
  --viewer-id crypto-perp-truth-cycle-dogfood-viewer \
  --replace-existing
```

再生成結果:

```text
status=pass
artifact_count=4
boundary_violation_count=0
```

## 4. 修正後の現物確認

Viewer manifest:

```text
strategy_daily_brief.v1:
- scanned_json_count=3
- total_item_count=1
- broken_artifact_count=0
- crypto_perp_truth_cycle_follow_up_count=1
- first_brief_item_category=crypto_perp_truth_cycle_follow_up
- first_brief_item_severity=warning
- first_brief_item_status=MISSING_PROBE_AUDIT
- first_brief_item_schema_version=crypto_perp_truth_cycle_status.v1
- first_brief_item_action=uv run sis crypto-perp-probe-audit --probe <provider_probe.json> --out <probe-audit-dir>
- first_brief_item_reason=crypto perp truth-cycle follow-up: uv run sis crypto-perp-probe-audit --probe <provider_probe.json> --out <probe-audit-dir>
- first_brief_item_path=data/crypto_perp/truth_cycle_dogfood_check/truth_cycle_status/truth_cycle_status.json
- live_allowed=false
- paper_execution_allowed=false
```

## 5. 検証

RED:

```text
uv run pytest tests/strategy_workbench_viewer/test_strategy_workbench_viewer.py::test_strategy_workbench_viewer_summarizes_strategy_daily_brief_follow_up -q
-> failed: KeyError: 'scanned_json_count'
```

GREEN / focused verification:

```text
uv run pytest tests/strategy_workbench_viewer/test_strategy_workbench_viewer.py::test_strategy_workbench_viewer_summarizes_strategy_daily_brief_follow_up -q
-> 1 passed

uv run pytest tests/strategy_workbench_viewer -q
-> 15 passed

uv run ruff format --check src/sis/strategy_workbench_viewer/service.py tests/strategy_workbench_viewer/test_strategy_workbench_viewer.py
-> 2 files already formatted

uv run ruff check src/sis/strategy_workbench_viewer/service.py tests/strategy_workbench_viewer/test_strategy_workbench_viewer.py
-> All checks passed
```

Full check:

```text
./scripts/check
-> 1529 passed in 69.02s
```

## 6. 残リスク

- C は permission 表示の dogfood であり、Strategy Input Feedback / Case Index 中心の主対象ではない。
- `MISSING_PROBE_AUDIT` の next command は表示されるが、実行はしていない。
- 実 probe audit、network、credential、tiny live measurement には別の明示承認と前提条件が必要。
- Viewer は source artifact を読みやすくするだけで、truth-cycle status を進めない。
