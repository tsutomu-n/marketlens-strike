<!--
作成日: 2026-07-05_19:24 JST
更新日: 2026-07-06_12:22 JST
-->

# Crypto Perp Follow-up Remediation 2026-07-05

## 結論

前回の evidence quality 補強後に残っていた backtest candidate pack 側の remediation は完了済みです。issue #22 では、残った Crypto Perp cost model default の surface 間統一を扱います。

完了済み項目は次です。

1. `build_crypto_perp_backtest_candidate_pack` の Python API default fee を `0.0004` に合わせる。
2. `evidence_grade_summary.strongest_evidence_level` を source 不足時に `simulated_estimate` と呼ばない。
3. `docs/crypto_perp/BACKTEST_CANDIDATE_PACK_V1.md` の option 例を `--fee-rate 0.0004` に合わせる。
4. `configs/cost_models/crypto_perp_bitget_usdt_futures.yaml` を、CLI default と builder default の差分が残っている場合に合わせて更新する。
5. `CURRENT_DOCS_INDEX_2026-07-05.md` に、この現実評価docへの導線を追加する。

## 理由

### 1. v1 schema 互換性

`evidence_grade_summary` は新規生成 artifact には出す。ただし既存の `crypto_perp_backtest_candidate_pack.v1` artifact を読むだけで壊さないため、schema では optional とする。

この互換性修正は実施済み。

### 2. fee default

プロジェクト前提は taker fee `0.0004` です。

CLI default と Python API builder default は `0.0004` に修正済み。issue #22 では `tournament_rows.py`、`pre_actual_cash.py`、`crypto-perp-tournament-rows-v2` も normal project assumption に揃える。

### 3. strongest evidence label

critical source が不足している場合、`strongest_evidence_level` を `simulated_estimate` と呼ぶと強く見えすぎる。

推奨:

- critical source 不足、または simulated trade 0 件: `incomplete_local_artifact`
- recomputed minimal artifact を含む: `recomputed_minimal_simulated_estimate`
- existing artifact 起点の local simulation: `local_simulated_estimate`

## 完了条件

```bash
uv run pytest tests/crypto_perp/test_backtest_candidate_pack.py
uv run python scripts/check_current_docs.py
uv run python scripts/check_cli_catalog.py
./scripts/check
```

`jq` で次を確認する。

```bash
jq '{decision, reason_codes, evidence_grade_summary}' data/crypto_perp/backtest_candidate_pack/latest/decision.json
```
