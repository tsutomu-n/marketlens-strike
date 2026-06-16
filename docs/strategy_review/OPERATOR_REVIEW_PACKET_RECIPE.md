<!--
作成日: 2026-06-17_00:03 JST
更新日: 2026-06-17_00:03 JST
-->

# Operator Review Packet Recipe

## 結論

`strategy-review-build` の review packet は、人間が既存 artifact を読むための read-only packet です。`review.md` と `review_manifest.json` を作っても、alpha、paper readiness、live readiness、paper execution permission は証明しません。

この recipe は、operator が `review.md` を読む前に必要な artifact を揃え、complete / missing / invalid / blocked の挙動を同じ手順で確認するためのものです。

## 前提

実行前に CLI surface と現行 docs check を確認します。

```bash
uv run sis strategy-review-build --help
uv run python scripts/check_current_docs.py
```

`data/` は runtime output です。golden fixture や test 正本として扱いません。

## Build

通常の complete review:

```bash
uv run sis strategy-review-build \
  --review-id dogfood-complete-001 \
  --out data/strategy_reviews \
  --pack-path data/research/backtest_pack/strategy_backtest_pack.json \
  --validation-path data/research/backtest_pack/strategy_backtest_pack_validation.json \
  --lifecycle-review data/research/strategy_lifecycle/strategy_lifecycle_review.json \
  --replace-existing
```

欠損を lenient mode で読む:

```bash
uv run sis strategy-review-build \
  --review-id dogfood-missing-lenient-001 \
  --out data/strategy_reviews \
  --pack-path data/research/backtest_pack/not_found.json \
  --validation-path data/research/backtest_pack/not_found_validation.json \
  --replace-existing
```

欠損を strict mode で読む。出力は可能な限り書かれますが、終了コードは 2 です。

```bash
uv run sis strategy-review-build \
  --review-id dogfood-missing-strict-001 \
  --out data/strategy_reviews \
  --pack-path data/research/backtest_pack/not_found.json \
  --validation-path data/research/backtest_pack/not_found_validation.json \
  --strict \
  --replace-existing
```

## Review Order

operator は次の順で読みます。

1. `Summary`: `review_status`、`source_safety.status`、`strict` を確認する。
2. `Readiness Disclaimer`: readiness proof ではないことを確認する。
3. `Source Artifact Status`: 必須 artifact の `present` / `missing` / `invalid` / `blocked` を確認する。
4. `Backtest Pack / Validation Summary`: pack validation を readiness proof として読まない。
5. `Strategy Definition`: 戦略が何をするかを読む。
6. `Lifecycle Summary`: lifecycle decision を paper / live 許可として読まない。
7. `Safety Boundary`: builder と source の safety を分けて見る。
8. `Missing / Invalid / Blocked Details`: 先に解消する問題を確認する。
9. `Source Hash Table`: path、bytes、hash、schema version を再現性確認に使う。
10. `Next Human Review Checklist`: 次に作る operator review artifact の判断材料にする。

## Decision Boundary

この段階では `operator_review.yaml`、paper bridge、Strategy Case registry、UI は作りません。

paper observation 候補に進める場合でも、review packet から直接 `paper-from-intents` を呼びません。別の operator review artifact を作り、その後の paper bridge で既存 `paper-from-intents` revalidation を通します。

NDX / QQQ 系では既存 Layer 2.6 / 2.7 evidence と hash lineage を無視しません。Strategy Review の operator artifact は、既存 `ndx_operator_promotion_decision.v1` を置き換えません。

## Verification

最小確認:

```bash
uv run pytest -q tests/strategy_review
uv run python scripts/check_current_docs.py
git diff --check
```

広めの確認:

```bash
uv run pytest -q tests/strategy_review tests/backtest/test_artifact_summary_registry.py tests/strategy_authoring/test_cli_bundle.py
./scripts/check
```
