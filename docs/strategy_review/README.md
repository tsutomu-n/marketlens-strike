<!--
作成日: 2026-06-16_18:25 JST
更新日: 2026-06-17_09:01 JST
-->

# Strategy Review

## 結論

`strategy-review-build` は、既存の Strategy Authoring / backtest artifact を読み、人間レビュー用の `review.md` と機械検証用の `review_manifest.json` を作る read-only builder です。`strategy-review-record` は、その packet を読んだ人間判断を `operator_review.yaml` として hash 付きで保存し、後から同じ `review.md` / `review_manifest.json` に対する判断だったか再検証します。

これは alpha、paper readiness、live readiness を証明しません。pack validation が `PASS` でも、収益性、paper 移行可否、live 実行可否は証明しません。

## Build Command

```bash
uv run sis strategy-review-build \
  --review-id ndx-smoke-001 \
  --out data/strategy_reviews \
  --pack-path data/research/backtest_pack/strategy_backtest_pack.json \
  --validation-path data/research/backtest_pack/strategy_backtest_pack_validation.json \
  --lifecycle-review data/research/strategy_lifecycle/strategy_lifecycle_review.json
```

出力:

- `data/strategy_reviews/{review_id}/review.md`
- `data/strategy_reviews/{review_id}/review_manifest.json`

既存 review directory がある場合、`--replace-existing` なしでは exit 2 で止まります。`--replace-existing` を付けても directory は削除せず、`review.md` と `review_manifest.json` だけを同一 directory の一時ファイルから atomic replace します。

`--authoring-spec` は任意です。未指定の場合は pack JSON の `spec_path` から Strategy Authoring YAML を導出し、導出できない場合は `戦略定義` section を `not_configured` として出します。

`--lifecycle-review` は任意の Strategy Lifecycle review JSON です。既定値は `data/research/strategy_lifecycle/strategy_lifecycle_review.json` です。欠損は optional missing として扱い、壊れた JSON や schema version mismatch は `INVALID_INPUT` にします。

## Record Command

`operator_review.yaml` を作る通常手順:

```bash
uv run sis strategy-review-record \
  --review-dir data/strategy_reviews/ndx-smoke-001 \
  --decision REVIEWED_FOR_CONTEXT \
  --reviewer operator-name \
  --rationale "review.md を読み、現時点では文脈確認として記録する"
```

必要な修正がある場合:

```bash
uv run sis strategy-review-record \
  --review-dir data/strategy_reviews/ndx-smoke-001 \
  --decision NEEDS_FIX \
  --reviewer operator-name \
  --rationale "lifecycle review の根拠を追加確認する" \
  --required-action "strategy_lifecycle_review.json の source hash を確認する"
```

保存済み判断を現在の `review.md` / `review_manifest.json` と照合する:

```bash
uv run sis strategy-review-record \
  --review-dir data/strategy_reviews/ndx-smoke-001 \
  --validate-existing
```

成功時は `status=pass`、失敗時は `status=fail` と `error=...` を出します。既存 `operator_review.yaml` は `--replace-existing` なしでは上書きしません。`--validate-existing` は保存済みの path と hash が現在の review directory と一致することを確認します。

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

runtime validation は Pydantic model で行います。tracked JSON Schema は runtime では読み込まず、tests で Pydantic model と固定 schema の整合を確認します。

`producer` は固定値です。`tool=sis`、`command=strategy-review-build`、`schema_version=strategy_review_manifest.v1` を記録します。

source artifact はコピーしません。manifest には repo-relative POSIX path、`sha256:<64 hex>` hash、`bytes`、検出できた top-level `schema_version` を記録します。欠損 artifact は `status=missing` とし、hash と bytes は省略します。壊れた artifact は `status=invalid`、live / wallet / signing / exchange write 系 field が混入した artifact は `status=blocked` とし、`error` に短い理由を記録します。

artifact path は repo-relative POSIX path だけを許可します。empty、absolute、backslash、`..`、hidden path segment、URL scheme、repo 外 path、`.env` / `.env.local` / `.envrc` / `id_rsa` / `id_ed25519` / `credentials` / `credential` / `secrets` / `secret` segment は拒否します。

`builder_safety` は builder 自身が live order、wallet、signing、exchange write を使わないことを固定します。`source_safety` は入力 artifact から読めた境界状態で、`PASS` / `UNKNOWN` / `BLOCKED` のいずれかです。`UNKNOWN` は必須 artifact の欠損などで境界を確認できない状態、`BLOCKED` は入力に live / wallet / signing / exchange write 系 flag が混入した状態です。

`evaluation_flags.pack_validation_pass_is_readiness_proof` は常に `false` です。

`authoring_spec` と `lifecycle_review` は `required=false` の optional artifact です。optional artifact の欠損は `review_status` を変えませんが、invalid input と boundary violation は全体の `review_status` に反映します。

`review.md` は、Summary、Readiness Disclaimer、Source Artifact Status、Backtest Pack / Validation Summary、Strategy Definition、Lifecycle Summary、Safety Boundary、Missing / Invalid / Blocked Details、Source Hash Table、Next Human Review Checklist の順で出力します。Lifecycle Summary の decision は paper / live 実行許可ではない、と section 近くに固定文を出します。

## Operator Review Contract

`operator_review.yaml` は `operator_strategy_review.v1` です。Pydantic model と runtime service は `src/sis/strategy_review/operator_review.py`、外部互換と artifact 検証用 JSON Schema は `schemas/operator_strategy_review.v1.schema.json` にあります。

`operator_review.yaml` は Strategy Review 専用の人間判断記録です。paper order、paper intent、paper bridge、live 実行、NDX promotion とは接続しません。`live_allowed=false` と `paper_execution_allowed=false` は固定です。

decision は `REJECT`、`NEEDS_FIX`、`REVIEWED_FOR_CONTEXT`、`PAPER_OBSERVATION_CANDIDATE` のいずれかです。`NEEDS_FIX` は `--required-action` が 1 件以上必要です。`PAPER_OBSERVATION_CANDIDATE` は validation candidate だけを意味し、paper 実行許可ではありません。この decision は `review_status=READY_FOR_HUMAN_REVIEW`、`source_safety_status=PASS`、`pack_validation_status=PASS`、`lifecycle_review_status=present`、各 count が 0 の時だけ保存できます。

## Operator Recipe

copy-paste 用の実行手順、読む順番、paper / NDX gate との境界は [OPERATOR_REVIEW_PACKET_RECIPE.md](OPERATOR_REVIEW_PACKET_RECIPE.md) を見ます。
