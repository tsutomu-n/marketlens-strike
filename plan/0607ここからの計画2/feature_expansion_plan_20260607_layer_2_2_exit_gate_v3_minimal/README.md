<!--
作成日: 2026-06-07_21:35 JST
更新日: 2026-06-07_21:35 JST
-->

# Layer 2.2 Exit Gate Review Harness v3 Minimal

## 結論

この計画は、`marketlens-strike` に **Layer 2.2 Exit Gate Review Harness** を追加するための実装指示です。

v2からの主な修正は、LLMレビューを過剰設計にしないことです。

```text
採用する:
  deterministic precheck
  review pack generator
  manual LLM review import
  exit gate
  freeze manifest
  report

標準運用:
  1 LLM reviewで開始
  高リスク時のみ second adversarial review を要求

採用しない:
  in-repo LLM API call
  API key
  provider SDK
  2 LLM review の常時必須化
  feature panel
  residual calculation
  Strategy Lab export
  backtest
  paper/live接続
```

## 読む順番

```text
README.md
01_GOAL.md
02_SCOPE_AND_BOUNDARIES.md
03_CURRENT_REPO_CONTEXT.md
04_TASKS.md
05_ACCEPTANCE.md
06_TARGET_FILE_MAP.md
07_TEST_PLAN.md
08_RISK_AND_STOP_CONDITIONS.md
10_IMPLEMENTER_CHECKLIST.md
appendices/C_CODER_HANDOFF_PROMPT.md
```

## 最重要の境界

この計画は **2.2の出口審査だけ** を作ります。

```text
やる:
  2.2 artifact を検査し、2.3へ進めるかを決める

やらない:
  2.3 feature panel
  QQQデータ取得
  Open Gap Residual計算
  neutralization
  Strategy Lab export
  backtest
  paper candidate
  PaperIntentPreview
  external API
  credentials
  live order
```

## 最終完成状態

コーダーが完了した時点で、次が可能になります。

```bash
uv run sis research-layer22-review-pack \
  --root configs/research_layer_2_2/ndx \
  --out data/research/ndx/review

uv run sis research-layer22-review-import \
  --pack data/research/ndx/review/llm_review_input.json \
  --result data/research/ndx/review/llm_review_result.json

uv run sis research-layer22-exit-gate \
  --root configs/research_layer_2_2/ndx \
  --pack data/research/ndx/review/llm_review_input.json \
  --review data/research/ndx/review/normalized_review.json \
  --out data/research/ndx/review
```

結果として、以下が生成されます。

```text
data/research/ndx/review/llm_review_pack.md
data/research/ndx/review/llm_review_input.json
data/research/ndx/review/llm_review_prompt.md
data/research/ndx/review/normalized_review.json
data/research/ndx/review/layer_2_2_exit_decision.json
data/research/ndx/review/layer_2_2_freeze_manifest.json
data/reports/ndx_layer_2_2_exit_gate_report.md
```

## v3での判断

常時二段LLMレビューは重いので、標準では **1 LLM review** にします。

ただし、以下の場合は second adversarial review を要求します。

```text
- review_result.overall_decision が REVISE_REQUIRED / REJECT_SEED
- severity HIGH / BLOCKER がある
- required_human_decisions がある
- core_dag / temporal_availability / source_contract / counter_dags に変更が入った
- operator が --require-second-review を指定した
```
