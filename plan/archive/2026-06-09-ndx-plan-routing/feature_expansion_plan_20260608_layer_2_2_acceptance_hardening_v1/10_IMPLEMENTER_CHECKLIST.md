<!--
作成日: 2026-06-08_19:23 JST
更新日: 2026-06-08_19:23 JST
-->

# 10_IMPLEMENTER_CHECKLIST

## 実装前

```text
[ ] このZIPは新規2.2実装計画ではなく、既存2.2受入監査計画だと理解した
[ ] v2/v5 ZIPはhistorical design backgroundだと理解した
[ ] AGENTS.mdのsource-of-truth順位を読んだ
[ ] docs/research/ndx/README.mdと09_LLM_REVIEW_GATE.mdを読んだ
[ ] feature panel / residual / Strategy Lab export は今回やらないと理解した
```

## 現状確認

```text
[ ] uv run sis --help で research-layer22-* commandを確認
[ ] research-layer22-validateがpass
[ ] research-layer22-exportがpass
[ ] research-layer22-review-packがpass
[ ] tests/researchがpass
```

## Exit Gate監査

```text
[ ] exit_gate.pyのrun_exit_gateを読んだ
[ ] _decision_valueを読んだ
[ ] _second_review_requiredを読んだ
[ ] freeze_manifest生成条件を読んだ
[ ] APPROVE_2_3 + second_review_required=true が起きないよう確認/修正した
[ ] REVISE_2_2 / REJECT_SEED でfreeze_manifestが出ないよう確認した
```

## テスト

```text
[ ] HIGH unresolved case追加
[ ] HIGH resolved case追加
[ ] BLOCKER case確認
[ ] REJECT_SEED case確認
[ ] APPROVE_2_3 invariant確認
[ ] tests/research/test_layer22_exit_gate.py pass
[ ] tests/research pass
[ ] scripts/check_current_docs.py pass
[ ] ./scripts/check pass
```

## 完了

```text
[ ] layer_2_2_exit_decision.jsonの意味論が明確
[ ] freeze_manifestがAPPROVE時だけ出る
[ ] 2.3へ進む条件が明文化済み
[ ] no-touch領域を触っていない
[ ] dependency追加なし
[ ] external APIなし
```
