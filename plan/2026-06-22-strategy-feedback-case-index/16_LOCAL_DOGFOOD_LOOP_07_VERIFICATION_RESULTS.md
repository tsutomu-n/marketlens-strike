<!--
作成日: 2026-06-22_20:28 JST
更新日: 2026-06-22_20:31 JST
-->

# Local Dogfood Loop 07 Verification Results

## 結論

Loop 07 では、Loop 03-06 の code / schema / docs / plan / generated artifact 変更を検証した。

確認済み:

- focused tests は通った。
- current docs check は通った。
- CLI catalog check は通った。
- `TASK_CHAIN.yaml` は YAML として parse できた。
- `git diff --check` は通った。
- `strategy-case-lite-update --help` に `--artifact` が表示される。
- full `./scripts/check` は、この文書追加後にも再実行して通った。
- 最終 full pytest は `1521 passed in 68.81s`。

## 1. 計画

目的:

1. Case Lite `--artifact` 実装と plan docs 更新後に、狭いテストと full check を通す。
2. 実行した検証コマンドと結果を tracked plan doc に残す。
3. live / wallet / signing / exchange write に触れていないことを確認する。

## 2. 現実チェック

検証前に分かった注意点:

- `python` コマンドはこの shell で存在しなかった。
- repo 標準は `uv run python` なので、YAML parse は `uv run python` で実行し直した。

失敗した非標準コマンド:

```text
python - <<'PY'
...
PY
```

結果:

```text
zsh:1: command not found: python
```

修正:

```bash
uv run python - <<'PY'
from pathlib import Path
import yaml
p=Path('plan/2026-06-22-strategy-feedback-case-index/TASK_CHAIN.yaml')
yaml.safe_load(p.read_text())
print('yaml=ok')
PY
```

結果:

```text
yaml=ok
```

## 3. 実行した検証

### 3.1 Focused tests

実行:

```bash
uv run pytest tests/strategy_case_lite tests/strategy_input_feedback tests/strategy_case_index tests/strategy_workbench_viewer -q
```

結果:

```text
46 passed in 1.98s
```

### 3.2 Current docs

実行:

```bash
uv run python scripts/check_current_docs.py
```

結果:

```text
checked 169 current docs: metadata, links, EOF, legacy roots, HTML sources, semantic drift, and plan routing ok
```

### 3.3 CLI catalog

実行:

```bash
uv run python scripts/check_cli_catalog.py
```

結果:

```text
checked 208 public CLI commands against Typer registration
```

### 3.4 YAML parse

実行:

```bash
uv run python - <<'PY'
from pathlib import Path
import yaml
p=Path('plan/2026-06-22-strategy-feedback-case-index/TASK_CHAIN.yaml')
yaml.safe_load(p.read_text())
print('yaml=ok')
PY
```

結果:

```text
yaml=ok
```

### 3.5 Diff whitespace

実行:

```bash
git diff --check
```

結果:

```text
pass
```

### 3.6 CLI help

実行:

```bash
uv run sis strategy-case-lite-update --help | rg -n -- "--artifact|Additional JSON"
```

結果:

```text
37:│    --artifact                                    FILE  Additional JSON       │
```

### 3.7 Full check

実行:

```bash
./scripts/check
```

結果:

```text
Python 3.13.7
All checks passed!
799 files already formatted
checked 169 current docs: metadata, links, EOF, legacy roots, HTML sources, semantic drift, and plan routing ok
checked 208 public CLI commands against Typer registration
INFO 0 errors (169 warnings not shown)
All checks passed!
1521 passed in 69.22s (0:01:09)
```

## 4. 生成済み sample artifacts

NDX local dogfood:

- `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_runtime_observation/strategy_runtime_observation_manifest.json`
- `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_inputs/validation/strategy_input_contract_validation.json`
- `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback_with_contract/ndx_open_gap_residual_v1/ndx_open_gap_residual_v1-input-feedback-f3cb881ae7447e63.json`
- `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback_with_contract/ndx_open_gap_residual_v1/ndx_open_gap_residual_v1-input-feedback-f3cb881ae7447e63-review-20b18c2a.json`
- `data/local_dogfood/2026-06-22-ndx-open-gap/viewer/strategy_workbench_viewer.html`

Trend Pullback local dogfood:

- `data/local_dogfood/2026-06-22-trend-pullback/strategy_inputs/trend_pullback_user_v1_input_contract.yaml`
- `data/local_dogfood/2026-06-22-trend-pullback/strategy_inputs/validation/strategy_input_contract_validation.json`
- `data/local_dogfood/2026-06-22-trend-pullback/strategy_cases/trend_pullback_user_v1/strategy_case_lite.json`
- `data/local_dogfood/2026-06-22-trend-pullback/strategy_case_index/trend-pullback-local-dogfood-index.json`
- `data/local_dogfood/2026-06-22-trend-pullback/viewer/strategy_workbench_viewer.html`

## 5. 境界確認

実施していないこと:

- credentialed network
- paper order
- live order
- wallet
- signing
- exchange write
- DB persistence
- production venue schema widening

確認した境界:

- Trend Case Index: `paper_execution_allowed=false`、`live_allowed=false`、`db_persistence_allowed=false`
- Trend Viewer: `boundary_violation_count=0`
- NDX contract review: `manual_contract_update_input_allowed=false`

## 6. 最終再検証

この文書追加後に再実行した。

実行:

```bash
uv run python scripts/check_current_docs.py
git diff --check
./scripts/check
```

結果:

```text
checked 170 current docs: metadata, links, EOF, legacy roots, HTML sources, semantic drift, and plan routing ok
git diff --check: pass
Python 3.13.7
All checks passed!
799 files already formatted
checked 170 current docs: metadata, links, EOF, legacy roots, HTML sources, semantic drift, and plan routing ok
checked 208 public CLI commands against Typer registration
INFO 0 errors (169 warnings not shown)
All checks passed!
1521 passed in 68.81s (0:01:08)
```

## 7. 残った現実的な課題

1. `trend_pullback_user_v1` の runtime observation はまだない。
   - 影響: drift review、learning event、Input Feedback proposal はまだ作れない。

2. `ndx_open_gap_residual_v1` の manual contract update はまだ承認されていない。
   - 影響: proposal は `READY_FOR_HUMAN_REVIEW` だが review は `HOLD`。

3. Generated `data/local_dogfood/...` は runtime/generated state であり、tracked plan docs が再開用の索引になる。

## 8. 次ループ案

### 推奨: Loop 08 は completion audit

理由:

- Loop 03-07 で local/offline 実装と dogfood はかなり進んだ。
- ただし active goal 全体を完了扱いにできるかは、実装済み要件と残課題を requirement-by-requirement で監査する必要がある。

実行候補:

1. active plan の明示要件を列挙する。
2. code / tests / schemas / CLI help / docs / generated artifacts の証拠を対応付ける。
3. 完了、未完了、外部前提、承認待ちを分ける。
4. 完了と言える範囲だけを明示し、goal complete 判定を行う。
