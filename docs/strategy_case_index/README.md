<!--
作成日: 2026-06-22_18:55 JST
更新日: 2026-06-22_18:55 JST
-->

# Strategy Case Index

## 結論

Strategy Case Index は、複数の `strategy_case_lite.v1` を read-only に一覧化する local/offline artifact です。

これは DB registry ではありません。source case を上書きせず、merge policy、conflict resolution、timeline editor、検索 DB、server UI を実装しません。paper 実行、live 実行、wallet、signing、exchange write も許可しません。

## CLI

明示 case から index を作る:

```bash
uv run sis strategy-case-index-build \
  --case data/strategy_cases/ndx-breakout-001/strategy_case_lite.json \
  --case data/strategy_cases/ndx-breakout-002/strategy_case_lite.json \
  --out data/strategy_case_index \
  --index-id ndx-case-index
```

`data/` 配下を scan する:

```bash
uv run sis strategy-case-index-build \
  --data-dir data/strategy_cases \
  --out data/strategy_case_index \
  --replace-existing
```

`--case` と `--data-dir` は併用できます。同一 path / hash は deterministic に dedupe されます。

## Artifacts

- `strategy_case_index.v1`

index は次を含みます:

- case count
- strategy count
- case path / sha256
- latest status
- open actions
- blocked reasons
- per-strategy latest case
- source artifact hash

latest case は `updated_at`、次に path で deterministic に選びます。

## Scan Rules

- explicit `--case` は `strategy_case_lite.v1` 以外なら fail します。
- data-dir scan は `schema_version == "strategy_case_lite.v1"` の JSON だけを採用します。
- data-dir scan では viewer manifest、既存 index、任意 JSON、Markdown を採用しません。
- data-dir に case-lite が 0 件なら fail します。
- `strategy_case_lite.v1` を名乗る JSON が model validation に失敗した場合は fail します。

## Viewer

`strategy-workbench-viewer-build` は `strategy_case_index.v1` を static HTML の compact summary として表示できます。

表示対象:

- case count
- strategy count
- latest status
- latest case path
- open action
- blocked reason
- source hash

## 境界

- source case artifact を変更しない。
- DB に保存しない。
- paper / live execution permission ではない。
- wallet、signing、exchange write を使わない。
- full registry、merge policy、timeline editor は別計画。

## 検証

```bash
uv run pytest tests/strategy_case_index
uv run pytest tests/strategy_workbench_viewer
uv run sis strategy-case-index-build --help
uv run python scripts/check_current_docs.py
```
