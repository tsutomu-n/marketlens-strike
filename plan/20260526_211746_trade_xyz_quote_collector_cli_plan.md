# Trade[XYZ] Quote Collector CLI Plan

Timestamp: 2026-05-26 21:17:46 JST

## 結論

`trade_xyz` quote collector の public CLI 化は、`src/sis/cli.py` のリファクタリング後に行う。
ただし、実装の方向性は先に固定してよい。

現時点での第一候補は:

```bash
uv run sis collect-trade-xyz-quotes
```

であり、既存の `log-quotes --venue ...` を拡張しない。

## この文書の目的

この文書は、`src/sis/cli.py` のリファクタリング後に読み直し、
追加調査なしで CLI 化に着手できるようにするための implementation memo である。

## 2026-05-26 時点の確認済み事実

### CLI 構造

- `src/sis/cli.py` は完全な一枚岩ではなく、すでに一部 command を module registration に寄せている。
- 現在の登録箇所:
  - `register_probe_commands(app)` at `src/sis/cli.py`
  - `register_quote_commands(app, _recommended_read_order)` at `src/sis/cli.py`
  - `register_research_commands(app, _recommended_read_order)` at `src/sis/cli.py`
- したがって、`trade_xyz` quote collector の CLI 化は、`src/sis/cli.py` 本体に直書きするより、
  `src/sis/commands/quotes.py` 側へ寄せるのが自然。

### 既存の probe surface

- `src/sis/commands/probe.py` に `probe trade-xyz` がある。
- この command は次を生成する:
  - `data/registry/trade_xyz_instrument_registry.json`
  - `data/reports/trade_xyz_universe_report.md`
  - `data/reports/trade_xyz_universe_summary.json`
- registry 生成には:
  - `configs/instrument_registry.seed.json`
  - live `TradeXyzClient().all_mids()`
  - live `TradeXyzClient().meta()`
  を使うか、fixture path (`--all-mids-path`, `--meta-path`) を使う。

### 既存の quote surface

- `src/sis/commands/quotes.py` の `log-quotes` は legacy `gtrade` sidecar replay 専用。
- `trade_xyz` を与えると、明示的に
  `"Only gtrade sidecar ingestion is available in the initial scaffold."`
  で exit code 2 になる。
- `normalize-quotes` は `data/raw/quotes/*/*.jsonl` を走査して、
  `data/normalized/quotes.parquet` と `data/normalized/sis.duckdb` を作る。

### collector 実装の既存 surface

- `src/sis/venues/trade_xyz/collector.py`
  - `collect_trade_xyz_quotes(...)`
  - `collect_and_normalize_trade_xyz_quotes(...)`
- 既存 collector の動作:
  - `InstrumentSpec.active` が true のものだけ処理
  - `coin` が無ければ `xyz:<canonical_symbol>` を使う
  - `all_mids()` と `l2_book()` を使って quote を作る
  - API error 時は例外で command 全体を落とさず、
    `{"levels": [[], []], "error": "BLOCK_API_ERROR"}` を payload として fail-closed quote を書く
  - `all_mids` に coin が無い場合も `is_tradable=False` / `BLOCK_API_ERROR` へ落とす
  - JSONL append は `append_jsonl()` により親ディレクトリを自動作成する

### quote shape の既存挙動

- `src/sis/venues/trade_xyz/normalizer.py` の `quote_from_l2_book(...)` が `QuoteLog` を作る。
- 埋まる主要 field:
  - `venue=trade_xyz`
  - `dex=xyz`
  - `coin`
  - `asset_id`
  - `real_market_symbol`
  - `recv_ts_ms`
  - `source_ts_ms`
  - `best_bid`, `best_ask`, `bid_price`, `ask_price`, `mid_price`
  - `spread_bps`
  - `depth_10bps_usd`, `depth_25bps_usd`
  - `block_reasons`
  - `raw_payload_sha256`
  - `raw_payload`
- 片側板欠落時は `BLOCK_NO_BID` / `BLOCK_NO_ASK` で `is_tradable=False` になる。

### 既存 test truth

- `tests/test_trade_xyz_collector.py`
  - raw JSONL が書かれる
  - `raw_payload_sha256` が入る
  - `normalize_quotes(...)` が `trade_xyz` raw quotes を受け付ける
- `tests/test_trade_xyz_normalizer.py`
  - best bid/ask, mid, spread, depth, block reason の既存期待値がある
- `tests/test_cli_smoke.py`
  - CLI command は `recommended_read_order_1=docs/CURRENT_STATE.md` を stdout に出すパターンが標準

## なぜ `log-quotes` 拡張ではなく別 command か

`log-quotes` を流用しない理由は明確である。

1. `log-quotes` は現在 `archive/legacy_sidecars/gtrade` replay の責務を持つ
2. `trade_xyz` は sidecar replay ではなく live API collection
3. option shape が異なる
4. help text を自然に保ちにくい
5. exit behavior と artifact 意味づけが異なる

したがって、`log-quotes --venue trade_xyz` を許可するより、
別 command のほうが docs と tests の drift が少ない。

## command contract

### command 名

第一候補:

```bash
uv run sis collect-trade-xyz-quotes
```

代替候補:

- `collect-trade-xyz`
- `trade-xyz-collect-quotes`

ただし、既存 command naming (`build-cost-matrix`, `paper-operations-cycle`, `execution-snapshot`) に揃えるなら、
`collect-trade-xyz-quotes` が最も説明的で、既存 `log-quotes` とも混同しにくい。

### 配置

第一候補:

- `src/sis/commands/quotes.py` に追加

代替:

- リファクタ後に `src/sis/commands/trade_xyz.py` のような専用 module が導入されていれば、そちらでも可

判断ルール:

- `normalize-quotes` と並ぶ quote ingestion surface である以上、専用 module が無い限り `quotes.py` を優先する
- `src/sis/cli.py` 本体への直書きは避ける

## option contract

### 必須 option

- なし

### 追加する option

`--registry-path`

- default: `data/registry/trade_xyz_instrument_registry.json`
- 型: `Path`
- 理由:
  - `probe trade-xyz` 後の標準 artifact をそのまま使える
  - fixture registry で smoke test を組みやすい

`--normalize/--no-normalize`

- default: `--normalize`
- 理由:
  - 既存 `collect_and_normalize_trade_xyz_quotes(...)` がある
  - operator から見て、quote collection 後に normalize される方が自然
  - ただし test や debugging では raw JSONL だけ見たいケースがある

`--date`

- default: なし
- 型: `str | None`
- 形式: `YYYY-MM-DD`
- 理由:
  - 現在の collector は `now` から UTC date を決めるため、
    replay-like な deterministic run に日付固定 option があると便利
- 実装判断:
  - リファクタ後に command 追加時、必要性が低ければ後回しでもよい
  - 先に入れるなら UTC midnight 固定で `datetime(..., tzinfo=timezone.utc)` を生成する

### 追加しない option

- `--venue`
- `--replace`
- `--all-mids-path`
- `--meta-path`
- micro live / paper / tracking / real market に関する option

理由:

- これは registry build command ではなく quote collection command だから
- registry の生成責務は `probe trade-xyz` に残すべきだから
- option を増やしすぎると `probe` と責務が重なるから

## 入出力 contract

### 入力

- registry JSON:
  - default `data/registry/trade_xyz_instrument_registry.json`
  - shape は `write_trade_xyz_registry(...)` が出す `InstrumentSpec[]`

### registry 読込

第一候補:

- `src/sis/venues/trade_xyz/registry.py` に
  `load_trade_xyz_registry(path: Path) -> list[InstrumentSpec]`
  を追加する

理由:

- 現在あるのは seed 用 `load_trade_xyz_seed(...)` だけ
- seed と built registry は意味が違う
- CLI 側で ad hoc に JSON を `InstrumentSpec.model_validate` するより、
  registry module に寄せた方が再利用しやすい

### 出力

raw:

- `data/raw/quotes/trade_xyz/<YYYY-MM-DD>.jsonl`

normalized (`--normalize` default 時):

- `data/normalized/quotes.parquet`
- `data/normalized/sis.duckdb`

stdout:

- `quote_count=<n>`
- `raw_quotes_path=<path>`
- normalize 実行時は `normalized_quotes_path=<path>`
- normalize 実行時は `duckdb_path=<path>`
- `recommended_read_order_*`

この stdout shape にすると、既存 CLI smoke pattern と揃えやすい。

## 処理フロー

第一候補フロー:

1. `get_settings()` で `data_dir` を得る
2. `registry_path` を決定
3. registry JSON を読む
4. `venue == trade_xyz` かつ `active == true` の `InstrumentSpec` のみ抽出
5. active instruments が 0 件なら exit code 2
6. `collect_trade_xyz_quotes(...)` を呼ぶ
7. `--normalize` が true なら `normalize_quotes(...)` を呼ぶ
8. artifact path と `recommended_read_order_*` を出力

### active filter の扱い

ここで使うのは `active` のみでよい。

`api_orderable` まで必須にしない理由:

- PR-04 の quote collector は order path ではなく read-only collection
- unresolved / paper-only でも、tracking 用 quote は集める価値がある
- 現在の `build_trade_xyz_registry(...)` でも active と orderable は分けている

### venue filter の扱い

registry file が他 venue を含み得る形になっても壊れないように、
`instrument.venue == Venue.TRADE_XYZ` を明示 filter する。

## エラー方針

### exit code 2 にするケース

- registry file が存在しない
- registry file が空、または JSON array でない
- `trade_xyz` active instruments が 0 件
- `--date` を導入する場合に形式不正

### fail-closed で継続するケース

- `all_mids()` / `l2_book()` の symbol 単位 API 失敗
- book 片側欠落
- `all_mids` に coin が無い

理由:

- 既存 collector 実装が symbol 単位失敗を quote row に落として継続する設計だから
- CLI はその既存挙動を変えない方が安全

### command 全体を失敗にしない方針

- 1 symbol でも quote row が書けたなら command 自体は exit 0 でよい
- 完全に 0 row の時だけ non-zero を検討する

ただし既存 collector は `count == len(active instruments)` を返し、API error row でも count は増えるため、
command exit は基本 0 になる想定でよい。

## テスト計画

### 新規 test file

第一候補:

- `tests/test_trade_xyz_quote_cli.py`

代替:

- 既存スタイルに合わせて `tests/test_cli_smoke.py` に追加

判断:

- 単純 smoke だけなら `tests/test_cli_smoke.py`
- fixture-heavy になるなら `tests/test_trade_xyz_quote_cli.py`
- repo の現状では `tests/test_cli_smoke.py` が CLI entrypoint 回帰の主置き場なので、まずはそこへ追加するのが自然

### 必須 test cases

1. happy path
   - fixture registry を置く
   - fake `TradeXyzClient` か monkeypatch で `all_mids` / `l2_book` を差し込む
   - `collect-trade-xyz-quotes` 実行
   - exit 0
   - `quote_count=...` を出す
   - `data/raw/quotes/trade_xyz/<date>.jsonl` ができる
   - `data/normalized/quotes.parquet` と `data/normalized/sis.duckdb` ができる
   - `recommended_read_order_1=docs/CURRENT_STATE.md` が出る

2. `--no-normalize`
   - raw JSONL はできる
   - normalized artifacts は作られない

3. registry missing
   - exit 2
   - 説明的な error message

4. registry exists but active `trade_xyz` instruments が 0
   - exit 2

5. mixed registry
   - `trade_xyz` 以外の venue row を含めても `trade_xyz` active row だけ collect する

6. API error fallback
   - `l2_book` 例外時も command exit 0
   - JSONL row が書かれ、`is_tradable=false` または `block_reasons` が残る

### 既存 test で壊してはいけないもの

- `tests/test_trade_xyz_collector.py`
- `tests/test_trade_xyz_normalizer.py`
- `tests/test_docs_current_truth.py`
- `tests/test_cli_smoke.py::test_normalize_and_build_cost_matrix_cli`

### 実行コマンド

最小:

```bash
uv run pytest tests/test_trade_xyz_collector.py tests/test_trade_xyz_normalizer.py tests/test_cli_smoke.py -q
```

全体:

```bash
./scripts/check
```

## docs 更新対象

CLI 化したら更新する:

- `README.md`
- `docs/OPERATIONS_RUNBOOK.md`
- `docs/CURRENT_STATE.md`

必要に応じて更新する:

- `src/sis/reports/implementation_status.py`
  - `docs/CODE_STATUS.md` は generated doc なので、ここを source of truth とする

### docs に書くべき文言

- `probe trade-xyz` は registry / universe report の生成 command
- `collect-trade-xyz-quotes` は quote collection command
- `normalize-quotes` は raw quote root 全体の normalize command
- `log-quotes --venue gtrade` は legacy replay path

## 実装順

1. リファクタ後の CLI module 配置を確認
2. `quotes.py` に command を追加するか、専用 module に切るか決める
3. registry load helper を追加
4. command 実装
5. CLI smoke test 追加
6. docs 更新
7. `./scripts/check`

## 完了条件

- `uv run sis collect-trade-xyz-quotes` が operator-facing public CLI として使える
- default で raw + normalized artifacts を作れる
- docs に unsupported command が残らない
- `trade_xyz` collector が code/test surface だけでなく CLI surface に昇格したと説明できる
- `./scripts/check` が通る
