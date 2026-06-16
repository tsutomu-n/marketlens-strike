<!--
作成日: 2026-06-16_18:25 JST
更新日: 2026-06-16_18:25 JST
-->

# Strategy Review

## 結論

`strategy-review-build` は、既存の Strategy Authoring / backtest artifact を読み、人間レビュー用の `review.md` と機械検証用の `review_manifest.json` を作る read-only builder です。

これは alpha、paper readiness、live readiness を証明しません。pack validation が `PASS` でも、収益性、paper 移行可否、live 実行可否は証明しません。

## Command

```bash
uv run sis strategy-review-build \
  --review-id ndx-smoke-001 \
  --out data/strategy_reviews \
  --pack-path data/research/backtest_pack/strategy_backtest_pack.json \
  --validation-path data/research/backtest_pack/strategy_backtest_pack_validation.json
```

出力:

- `data/strategy_reviews/{review_id}/review.md`
- `data/strategy_reviews/{review_id}/review_manifest.json`

既存 review directory がある場合、`--replace-existing` なしでは exit 2 で止まります。

## Status

`review_status` は、戦略が良いかどうかではなく、レビュー資料として読めるかどうかを表します。

| Status | 意味 |
|---|---|
| `READY_FOR_HUMAN_REVIEW` | 必須 artifact が読め、境界違反がない |
| `INCOMPLETE_ARTIFACTS` | 必須 artifact に欠損がある。既定の lenient mode では exit 0 |
| `INVALID_INPUT` | JSON、schema、path などが壊れていて信頼できない |
| `BLOCKED_BOUNDARY_VIOLATION` | live / wallet / signing / exchange write 系 field の混入を検出した |

`--strict` を付けると、欠損 artifact でも可能な限り出力を書いたうえで exit 2 になります。

## Manifest Contract

`review_manifest.json` は `strategy_review_manifest.v1` です。Pydantic model は `src/sis/strategy_review/manifest.py`、外部互換と artifact 検証用 JSON Schema は `schemas/strategy_review_manifest.v1.schema.json` にあります。

source artifact はコピーしません。manifest には repo-relative path と `sha256:<64 hex>` hash だけを記録します。欠損 artifact は `status=missing` とし、hash は省略します。

`evaluation_flags.pack_validation_pass_is_readiness_proof` は常に `false` です。
