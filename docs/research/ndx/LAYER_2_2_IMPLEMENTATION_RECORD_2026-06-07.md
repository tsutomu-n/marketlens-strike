<!--
作成日: 2026-06-07_20:09 JST
更新日: 2026-07-05_13:26 JST
-->

# Layer 2.2 Implementation Record

## 結論

この文書は Layer 2.2 の historical implementation record として固定する。Layer 2.3 以降の current status、現在の pass count、現在の artifact hash、paper / live readiness はここへ追記しない。

Layer 2.2 DAG Compiler foundation は `HYP-NDX-001` の local-only 研究 artifact 基盤として実装済みである。2026-06-08 時点では、DAG foundation に加えて Exit Gate Review Harness v3 Minimal も実装済みである。

2026-06-08 の追加作業は新規 Layer 2.2 実装ではなく、既存実装の受入監査と Exit Gate 意味論のハードニングである。対象計画は archived plan `plan/archive/2026-06-09-ndx-plan-routing/feature_expansion_plan_20260608_layer_2_2_acceptance_hardening_v1/` を履歴契約として読む。旧 v2/v5 ZIP は historical design background であり、新規実装指示ではない。

現在の実行結果を確認する場合は、`research-layer22-*` command を再実行し、`data/research/ndx/review/` 以下の git-ignored runtime artifact を読む。この文書中の固定値は snapshot であり、現在値の証明として使わない。

完成扱い:
- NDX / QQQ の research scope、seed、mechanism parts、variable inventory、causal roles、temporal availability を YAML と Pydantic contract で読める。
- `HYP-NDX-001` core DAG を validate / lint できる。
- forbidden edge、future-to-signal、outcome-to-treatment を拒否できる。
- counter DAG refs と counter DAG registry を必須 artifact として検証できる。
- JSON / Mermaid / counter DAG Markdown / data requirements / Markdown report を生成できる。
- review pack、manual review import、exit gate decision、approve-only freeze manifest を local-only で生成できる。

## 実装範囲

追加した主な領域:
- `configs/research_layer_2_2/ndx/`
- `docs/research/ndx/`
- `schemas/research_*.schema.json`
- `schemas/core_dag.v1.schema.json`
- `schemas/counter_dag.v1.schema.json`
- `schemas/llm_dag_review.v1.schema.json`
- `schemas/layer_2_2_human_resolutions.v1.schema.json`
- `schemas/layer_2_2_exit_decision.v1.schema.json`
- `schemas/layer_2_2_freeze_manifest.v1.schema.json`
- `src/sis/research/hypothesis/`
- `src/sis/research/dag/`
- `tests/research/`

変更した主な領域:
- `src/sis/commands/research.py`
- `scripts/check_current_docs.py`
- `tests/test_docs_current_truth.py`

## CLI

利用できる CLI:

```bash
uv run sis research-layer22-validate --root configs/research_layer_2_2/ndx
uv run sis research-layer22-export --root configs/research_layer_2_2/ndx --out data/research/ndx
uv run sis research-layer22-review-pack --root configs/research_layer_2_2/ndx --out data/research/ndx/review
uv run sis research-layer22-review-import --pack data/research/ndx/review/llm_review_input.json --result data/research/ndx/review/llm_review_result.json
uv run sis research-layer22-exit-gate --root configs/research_layer_2_2/ndx --pack data/research/ndx/review/llm_review_input.json --review data/research/ndx/review/normalized_review.json --out data/research/ndx/review
```

`research-layer22-validate` は core DAG 単体ではなく、同じ directory にある次の companion config も必須として検証する。

- `variable_inventory.yaml`
- `causal_roles.yaml`
- `temporal_availability.yaml`
- `counter_dags.yaml`

## 追加監査で修正した点

初回実装後の追加監査で、core DAG YAML だけが通る余地があることを検出した。Layer 2.2 は前段 contract 込みで成立するため、次を fail 条件にした。

- companion config 欠落
- DAG node が variable inventory にない
- DAG node が causal roles にない
- DAG node role と causal role assignment の不一致
- causal role が variable role candidates にない
- DAG node が temporal availability にない
- temporal availability と variable temporal class の不一致
- `counter_dag_refs` 欠落
- YAML duplicate key

Exit Gate の受入監査で、次の不変条件を code、schema、tests に固定した。

- `APPROVE_2_3` は `second_review_required=false` の時だけ成立する。
- `APPROVE_2_3` は `unresolved_human_decisions=[]` の時だけ成立する。
- `APPROVE_2_3` は `blocker_count=0` の時だけ成立する。
- `APPROVE_2_3` の時だけ freeze manifest を生成する。
- `REVISE_2_2` と `REJECT_SEED` では freeze manifest を生成せず、同じ output directory に古い freeze manifest があれば削除する。
- HIGH finding は、対応する human decision が解決済みの場合だけ `APPROVE_2_3` に進める。
- human decision がない HIGH finding、未解決 HIGH finding、BLOCKER は `REVISE_2_2` にする。

## 明示的にやっていないこと

今回の実装では次を行っていない。

- external API call
- Bitget network call
- Trade[XYZ] readiness 変更
- backtest engine 変更
- Strategy Lab export
- `strategy_signals.parquet` 生成
- PaperIntentPreview 生成
- paper/live order
- wallet / signing / exchange write

## 検証記録

この節は実装当時の snapshot である。現在の verification は固定の checked count や hash を読まず、下の command を再実行して確認する。

```bash
uv run sis research-layer22-validate --root configs/research_layer_2_2/ndx
uv run sis research-layer22-export --root configs/research_layer_2_2/ndx --out data/research/ndx
uv run sis research-layer22-review-pack --root configs/research_layer_2_2/ndx --out data/research/ndx/review
uv run sis research-layer22-review-import --pack data/research/ndx/review/llm_review_input.json --result data/research/ndx/review/llm_review_result.json
uv run sis research-layer22-exit-gate --root configs/research_layer_2_2/ndx --pack data/research/ndx/review/llm_review_input.json --review data/research/ndx/review/normalized_review.json --out data/research/ndx/review
uv run python scripts/check_current_docs.py
./scripts/check
```

2026-06-08 historical snapshot:

```text
HEAD: 4e6bd5f docs: update README.md and DOCS_LINT_POLICY with 2026-06-08 code truth refresh audit and remove obsolete cleanup plan documents
working tree: includes uncommitted Layer 2.2 acceptance-hardening docs/tests/code changes
uv run sis research-layer22-validate --root configs/research_layer_2_2/ndx
  status=pass
  dag_id=HYP-NDX-001
  node_count=9
  edge_count=8
  warning_count=0

uv run sis research-layer22-export --root configs/research_layer_2_2/ndx --out data/research/ndx
  status=pass
  core_dag_json=data/research/ndx/core_dag.json
  core_dag_mermaid=data/research/ndx/core_dag.mmd
  counter_dags_report=data/research/ndx/counter_dags.md
  data_requirements=data/research/ndx/data_requirements.yaml
  report=data/reports/ndx_core_dag_report.md

latest local exit decision artifact
  decision=APPROVE_2_3
  second_review_required=false
  unresolved_human_decision_count=0
  blocker_count=0
  pack_hash=sha256:7fc0d644d4a8d7432df29a8dfd6c878fc97342b5745febc26e6cd6206a01dd6a

uv run python scripts/check_current_docs.py
  passed at the then-current current-doc scope

./scripts/check
  passed at the then-current test scope
```

2026-06-09 repo-wide verification is archived in `docs/archive/2026-06-17-doc-routing/DOCUMENT_AUDIT_2026-06-09_NDX_2_3_2_4_REFRESH.md`. At that point, Layer 2.3/2.4 docs and code surfaces also exist, docs checker observed `101 current docs`, and the full local gate had a historical success count of 936; these are historical snapshot values, not current verification counts.

Generated artifacts under `data/` are runtime outputs and are gitignored. Do not copy new runtime hashes from those artifacts back into this historical record.

## 次の候補

Layer 2.3/2.4 は別scopeとして実装済み。現行入口は `docs/research/ndx/10_LAYER_2_3_NDX_PREFLIGHT.md` と `docs/research/ndx/11_LAYER_2_4_RESIDUAL_VALIDATION_GATE.md` を読む。

さらに次に進むなら別計画として扱う。

- larger-sample Layer 2.3 artifact generation
- Layer 2.4 `APPROVE_STRATEGY_LAB_EXPORT` を満たすだけの validation sample / era 確保
- Layer 2.5 Strategy Lab research-only export contract
- 実データ取得の利用規約、rate limit、保存方針

T5b Bitget credentialed read-only smoke と T6 demo order lifecycle は、この Layer 2.2 実装とは別タスクであり、credentials と明示許可がない限り進めない。
