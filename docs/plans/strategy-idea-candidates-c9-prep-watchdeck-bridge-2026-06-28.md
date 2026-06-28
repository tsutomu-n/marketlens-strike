<!--
作成日: 2026-06-28_10:32 JST
更新日: 2026-06-28_10:32 JST
-->

# C9 Prep Watchdeck Bridge Implementation

## 結論

C9 v0 は、shortlist 済み Bitget `USDT-FUTURES` Perp candidate を `/home/tn/projects/prep-watchdeck` の local read-only data から candidate-scoped Strategy Authoring / backtest pack artifact に変換する。

利益証明、actual cash proof、paper/live 許可、private API、wallet、signing、exchange write は範囲外です。

## 実装対象

- `strategy-idea-candidates-authoring-bridge` CLI。
- `src/sis/strategy_idea_candidates/prep_watchdeck_source.py`
- `src/sis/strategy_idea_candidates/authoring_bridge.py`
- `schemas/strategy_idea_candidate_authoring_bridge.v1.schema.json`
- `tests/strategy_idea_candidates/test_authoring_bridge.py`

## 入力

- `--candidate-set`: `strategy_idea_candidate_set.v1`
- `--export-manifest`: `strategy_idea_candidate_export_manifest.v1`
- `--ledger`: `search_ledger.jsonl`
- `--prep-watchdeck-root`: local `prep-watchdeck` root
- `--out`: candidate-scoped output root

## Source Mapping

優先 source は `prep-watchdeck/data/scanner.duckdb` と `data/candles_5m/date=*/candles.parquet`。`var/snapshots/latest.json` は source metadata / quality 補助に使う。`var/watchdeck.duckdb` は read-only 接続できる場合だけ ticker bid/ask / instrument metadata の補助に使い、lock されていても fallback があれば失敗扱いにしない。

## 対応 Family

- `perp_momentum_continuation`
- `perp_funding_rate_carry_filter`

その他 family は `BLOCKED_UNSUPPORTED_FAMILY_MAPPING` で止める。symbol rows、funding rate、product type、side bias、pack 実行で不足があれば machine-readable blocker を出す。

## 出力

各 candidate は `--out/<candidate_id>/` に隔離する。

- `prep_watchdeck_source_manifest.json`
- `feature_panel.parquet`
- `quotes.parquet`
- `venue_cost_matrix.csv`
- `strategy_authoring_spec.yaml`
- `strategy_backtest_suite.yaml`
- `strategy_authoring_bundle.yaml`
- `backtest_pack/strategy_backtest_pack.json`
- `backtest_pack/strategy_backtest_pack_validation.json`
- `bridge_blocker.json` when blocked

Top-level には `strategy_idea_candidate_authoring_bridge_manifest.json` を出す。

## 境界

`quotes.parquet` は existing backtest bridge 互換の列を含むが、bid/ask が source に無い場合は `spread_bps_estimate` から推定し、source manifest に記録する。`venue_cost_matrix.csv` は `ESTIMATE_ONLY` であり、actual cash report や tournament actual proof へ昇格しない。

既存 pack runner の venue / risk-gate 制約に合わせ、Strategy Authoring execution venue は paper-only 互換 surface として `trade_xyz` を使う。Bitget 由来は source manifest と bridge manifest に残す。

## 検証

```bash
uv run pytest tests/strategy_idea_candidates/test_authoring_bridge.py -q
uv run sis strategy-idea-candidates-authoring-bridge --help
uv run python scripts/check_cli_catalog.py
uv run python scripts/check_current_docs.py
git diff --check
```
