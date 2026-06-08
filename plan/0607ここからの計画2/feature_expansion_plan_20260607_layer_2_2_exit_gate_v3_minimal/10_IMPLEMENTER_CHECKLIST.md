<!--
作成日: 2026-06-07_21:35 JST
更新日: 2026-06-07_21:35 JST
-->

# 10_IMPLEMENTER_CHECKLIST

## 実装前

- [ ] `configs/research_layer_2_2/ndx/` が存在する
- [ ] `uv run sis research-layer22-validate --root configs/research_layer_2_2/ndx` が通る
- [ ] `uv run sis research-layer22-export --root configs/research_layer_2_2/ndx --out data/research/ndx` が通る
- [ ] 外部API不要であることを確認
- [ ] no-touch pathを確認

## EG-1 Schema

- [ ] `schemas/llm_dag_review.v1.schema.json` 作成
- [ ] `schemas/layer_2_2_human_resolutions.v1.schema.json` 作成
- [ ] `schemas/layer_2_2_exit_decision.v1.schema.json` 作成
- [ ] `schemas/layer_2_2_freeze_manifest.v1.schema.json` 作成
- [ ] `src/sis/research/dag/review_contracts.py` 作成
- [ ] schema tests追加

## EG-2 Review Pack

- [ ] `review_pack.py` 作成
- [ ] deterministic precheck実装
- [ ] evidence_catalog生成
- [ ] pack_hash生成
- [ ] `llm_review_pack.md` 出力
- [ ] `llm_review_input.json` 出力
- [ ] `llm_review_prompt.md` 出力
- [ ] pack tests追加

## EG-3 Import

- [ ] `review_import.py` 作成
- [ ] Pydantic validation
- [ ] pack_hash検証
- [ ] evidence_refs検証
- [ ] severity_counts検証
- [ ] normalized JSON出力
- [ ] import tests追加

## EG-4 Exit Gate

- [ ] `exit_gate.py` 作成
- [ ] decision rules実装
- [ ] second review trigger実装
- [ ] freeze manifest出力
- [ ] report出力
- [ ] exit gate tests追加

## EG-5 CLI

- [ ] `research-layer22-review-pack`
- [ ] `research-layer22-review-import`
- [ ] `research-layer22-exit-gate`
- [ ] CLI tests追加
- [ ] exit code確認

## EG-6 Docs

- [ ] `docs/research/ndx/09_LLM_REVIEW_GATE.md`
- [ ] 東京時間metadata header
- [ ] `scripts/check_current_docs.py` が通る

## 最終確認

- [ ] `uv run pytest -q tests/research`
- [ ] `uv run python scripts/check_current_docs.py`
- [ ] `./scripts/check`
- [ ] `pyproject.toml` を変更していない
- [ ] `uv.lock` を変更していない
- [ ] paper/live/order pathを触っていない
- [ ] external APIを呼んでいない
