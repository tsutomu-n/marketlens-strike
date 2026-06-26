<!--
作成日: 2026-06-26_18:52 JST
更新日: 2026-06-26_18:52 JST
-->

# Pass 387: Cost Matrix Metadata Helper Extraction

## 目的

`src/sis/reports/cost_matrix.py` から、base row と gTrade / Ostium metadata enrichment helper を独立モジュールへ切り出す。

この pass は、Venue Cost Matrix の quote aggregation / CSV 出力 / report rendering から、sidecar と registry による cost metadata 解決を分け、fee / holding cost 変換を直接テストできるようにする。

## 対象

- `src/sis/reports/cost_matrix.py`
- `src/sis/reports/cost_matrix_metadata.py`
- `tests/test_cost_matrix_metadata.py`

## 制約

- public CLI command 名・option は変えない。
- summary key 名、artifact key 名、CSV column 名、Markdown report text・順序は変えない。
- schema、auth、DB、CI、dependency、paper/live safety boundary は変えない。
- 既存 private helper 名は `cost_matrix.py` から引き続き参照できるよう alias を残す。
- Pass 377-386 の未コミット変更は保持し、上書きしない。

## 実装方針

1. RED: `tests/test_cost_matrix_metadata.py` を追加し、まだ存在しない `sis.reports.cost_matrix_metadata` の import で失敗させる。
2. GREEN: `BASE_ROWS`, base frame, sidecar selection, numeric coercion, gTrade fee conversion, gTrade holding cost, Ostium rollover conversion, metadata rows を新モジュールへ移す。
3. `cost_matrix.py` は新 helper を呼ぶだけにし、quote aggregation、CSV merge、report rendering は元ファイルに残す。
4. 既存 tests と CLI smoke で public behavior を保持する。

## 検証

- `CI=true timeout 120 uv run pytest -q tests/test_cost_matrix_metadata.py`
- `CI=true timeout 120 uv run pytest -q tests/test_cost_matrix_metadata.py tests/test_cost_matrix.py tests/test_cost_matrix_navigation.py`
- `CI=true timeout 120 uv run pytest -q tests/test_backtest_cost_matrix.py`
- `CI=true timeout 120 uv run pytest -q tests/test_cli_smoke.py -k 'cost_matrix'`
- `uv run ruff format src/sis/reports/cost_matrix.py src/sis/reports/cost_matrix_metadata.py tests/test_cost_matrix_metadata.py`
- `uv run ruff check src/sis/reports/cost_matrix.py src/sis/reports/cost_matrix_metadata.py tests/test_cost_matrix_metadata.py`
- `uv run ty check src --python-version 3.13 --output-format concise`
- `uv run sis --help`
- `git diff --check`
- `./scripts/check`

## リスクと対策

- CSV column/order regression: metadata helper returns same row dicts; existing `test_cost_matrix.py` keeps CSV behavior covered.
- gTrade fee/holding cost conversion regression: direct tests assert fee bps and holding bps conversions.
- Ostium rollover conversion regression: direct tests assert max(abs(long), abs(short)) 8hr percent conversion.

## ロールバック

この pass の追加ファイルと `cost_matrix.py` の helper alias/import 変更だけを戻せばよい。生成物、依存関係、外部状態は変更しない。
