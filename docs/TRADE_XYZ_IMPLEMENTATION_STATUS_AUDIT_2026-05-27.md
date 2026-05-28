# Trade[XYZ] 実装状況棚卸し 2026-05-27

## 0. 結論

この文書は、`/home/tn/projects/marketlens-strike/資料` に入っている 2 つの ZIP 指示書を基準に、現在の `marketlens-strike` repo がどこまで実装済みか、どこが一部実装か、どこが未実装かを、現 repo のコード、テスト、設定、生成 artifact から確認した棚卸しである。

結論から言うと、資料パックが求めている `Trade[XYZ] fresh read-only evidence chain` は、運用上の主目的である PR9a から PR12 までについてはほぼ実装済みで、現 artifact でも `READ_ONLY_GO` まで到達している。`uv run sis --help`、`collect-trade-xyz-quotes --dry-run`、`validate-artifacts --strict`、`phase-gate-review`、関連テスト 31 件はこの棚卸し時点で通った。PR12 の 60 分 read-only smoke artifact も存在し、`observed_window_seconds=3673.995702`、`raw_row_count=310`、5 銘柄 x 62 rows、`strict_validation_issue_count=0`、`phase_gate_decision=READ_ONLY_GO`、`next_actions=[]` が確認できる。

ただし、資料の要求を「完全な本番 Bot readiness」や「micro live 実行 ready」と読むなら、未実装または意図的に未公開の領域が残っている。代表的には、wallet/signing、production live trading、public micro live CLI、本番交換所 write API、Bot の注文候補生成、fee_mode の銘柄別確定、PR13 以降の live canary 運用導線が未完了である。現 repo は read-only/paper までを通す証拠収集基盤としては使えるが、実資金の自動発注を開始する状態ではない。

また、PR9a-PR12 の内側にも「資料の理想形とは完全一致しないが、現 tests と artifact 上は許容されている」一部実装がある。たとえば、`quality_blocks()` の depth gate は `min_side_depth_10bps_usd` ではなく合算 `depth_10bps_usd` を受け取っており、資料が強調する「execution gate は side-specific depth を見る」という厳密要求とは少しずれている。`build_trade_xyz_registry()` は `perpDexs` から `perp_dex_index` を解決するが、解決できない場合に `meta` payload の legacy-looking fields へ fallback する。これは fail-closed の補助としては理解できるが、「meta だけに頼らない」という資料の指示に対しては、一部実装と見るのが安全である。`fee_model.trade_xyz.yaml` には observed/growth/standard の考え方があるが、現 registry artifact の各銘柄 `fee_mode` は `unknown` のままであり、quote diagnostics でも `fee_mode_unknown_rate=1.0` である。これは read-only/paper の範囲では警告で済むが、micro live 候補にはブロック要因である。

この文書の判定は、提案や希望ではなく、確認できた現 repo の実体に基づく。既存 docs は `DONE` と書いているが、ここでは `DONE` をさらに分解し、実行入口、コード実装、テスト、artifact、運用境界の 5 つを分けて評価する。

## 1. 確認対象

確認対象の workspace は次である。

```text
/home/tn/projects/marketlens-strike
```

確認した資料パックは次の 2 つである。

```text
/home/tn/projects/marketlens-strike/資料/marketlens_from_current_repo_pr9_pr12_pack.zip
/home/tn/projects/marketlens-strike/資料/marketlens_indie_coder_addendum (1).zip
```

前者は PR9a から PR12 までを current repo に対して実装するための正本に近いパックで、後者は個人開発者向けに作業単位を細かく分けた追加指示書である。両者のゴールは同じで、Bot 本体、wallet、signing、production live trading、public micro live CLI を作ることではない。まず `Trade[XYZ] fresh read-only evidence chain` を完成させ、実ネットワークの read-only evidence を収集し、strict validation と diagnostics と phase gate まで通すことである。

資料上の大きな実装順は次である。

```text
PR9a: CLI / import recovery
PR9b: Trade[XYZ] HIP-3 mapping and contexts
PR9c: collect-trade-xyz-quotes fresh window CLI
PR10: validation / diagnostics strict対応
PR11: operations artifact chain cutover
PR12: fresh read-only smoke
PR12.5 optional: 0xArchive backfill
PR13 deferred: micro live public CLI
```

追加 ZIP の task 名では次のように対応する。

```text
TASK_01_CLI_IMPORT_RECOVERY
TASK_02_TRADE_XYZ_HIP3_MAPPING
TASK_03_META_AND_ASSET_CONTEXTS
TASK_04_L2_NORMALIZER_AND_DEPTH
TASK_05_COLLECT_CLI_WINDOW
TASK_06_VALIDATION_AND_DIAGNOSTICS
TASK_07_OPERATIONS_CUTOVER
TASK_08_FRESH_READ_ONLY_SMOKE
```

資料の最終ゴールとして何度も出てくるコマンド列は次である。

```bash
uv run sis --help
uv run sis probe trade-xyz
uv run sis collect-trade-xyz-quotes \
  --symbols SP500,XYZ100,NVDA,AAPL,MSFT \
  --duration-minutes 60 \
  --interval-seconds 60 \
  --normalize \
  --write-summary \
  --write-report
uv run sis diagnose-quotes --venue trade_xyz
uv run sis validate-artifacts --strict
uv run sis refresh-operations-artifacts
uv run sis phase-gate-review
```

現 repo では、この read-only chain は artifact 上もコマンド上も到達済みである。ただし、後述するように、execution lineage 系の一部 generated summary は `degraded` を残している。これは Trade[XYZ] read-only PR12 の gate と、実 live execution readiness を同じものとして読まないために重要である。

## 2. 判定基準

この棚卸しでは、単純な `DONE` / `TODO` ではなく、次の 5 段階で評価した。

```text
実装済み:
  コード入口があり、資料の主要求を満たし、対応テストまたは現 artifact で確認できるもの。

一部実装:
  コード入口または artifact はあるが、資料の厳密な要件の一部が弱いもの。
  または read-only/paper では使えるが micro live / production へ進めるには不足するもの。

未実装:
  コード入口、public CLI、実運用 artifact がないもの。
  または資料で明示的に deferred / non-goal とされているもの。

意図的に未公開:
  code/test surface はあるが、operator 向け public CLI としては出していないもの。
  micro live safety canary が代表例。

履歴/legacy:
  active path ではなく archive や historical docs としてだけ残すもの。
```

今回の確認では、資料パック上の PR9a-PR12 は大半が「実装済み」である。ただし、`fee_mode`、side-specific depth を gate に使う厳密性、phase gate output schema の一部、real-market tracking report の厚み、micro live surface の公開有無は「一部実装」または「未実装」に分類する。

ここでの「実装済み」は production live trading ready を意味しない。`README.md` と `docs/CURRENT_STATE.md` も同じ境界を明記しており、現行の主軸は `Trade[XYZ] / real_market / tracking / paper / micro_live safety` へ移っているが、実 live order integration はまだ opt-in safety surface 止まりで、public CLI surface には micro live 実行コマンドを出していない。

## 3. 今回の read-only 確認で実行したコマンド

この文書作成前に、次の確認を実施した。

```bash
git status --short --branch
```

結果は次で、作業前の repo は clean だった。

```text
## main...origin/main
```

資料ディレクトリは ZIP 2 件だけだった。

```text
/home/tn/projects/marketlens-strike/資料/marketlens_from_current_repo_pr9_pr12_pack.zip
/home/tn/projects/marketlens-strike/資料/marketlens_indie_coder_addendum (1).zip
```

実行確認として次を実施した。

```bash
uv run sis --help
uv run sis collect-trade-xyz-quotes --dry-run --max-symbols 3
uv run sis validate-artifacts --strict
uv run sis phase-gate-review
uv run pytest -q \
  tests/test_trade_xyz_registry.py \
  tests/test_trade_xyz_collector.py \
  tests/test_trade_xyz_normalizer.py \
  tests/test_validate_artifacts_trade_xyz.py \
  tests/test_quote_diagnostics.py \
  tests/test_phase_gate_review.py \
  tests/test_real_vs_venue_tracking.py \
  tests/test_micro_live_canary.py \
  tests/test_bot_preview.py
```

確認結果は次である。

```text
uv run sis --help: pass
uv run sis collect-trade-xyz-quotes --dry-run --max-symbols 3: pass
uv run sis validate-artifacts --strict: checked_files=11, issues=0
uv run sis phase-gate-review: pass, decision=READ_ONLY_GO
targeted pytest: 31 passed in 0.54s
```

`collect-trade-xyz-quotes --dry-run --max-symbols 3` の出力は次だった。

```text
dry_run=true
symbol_count=3
symbols=SP500,XYZ100,NVDA
```

`validate-artifacts --strict` の出力では、Trade[XYZ] registry、raw quote JSONL、summary、normalized parquet、quote schema を含む validation が `issues=0` で通った。

`phase-gate-review` は `data/reports/phase_gate_review.md` と `data/ops/phase_gate_review_summary.json` を書くコマンドである。今回の確認でも同コマンドを実行したが、git status は clean のままだった。これは generated artifact が git 管理外であるか、同じ内容で再生成されたためである。

## 4. 現 artifact の要約

現 artifact の重要値は次である。

```text
data/ops/phase_gate_review_summary.json:
  phase_gate_decision: READ_ONLY_GO
  phase2_entry_allowed: true
  strict_validation_issue_count: 0
  next_actions: []
  read_only_collector_gate_passed: true
  latest_trade_xyz_registry_path: data/registry/trade_xyz_instrument_registry.json
  latest_trade_xyz_quote_path: data/raw/quotes/trade_xyz/2026-05-27.jsonl
  latest_trade_xyz_summary_path: data/ops/trade_xyz_quote_collection_summary.json
  individual_stock_decision: paper_only
  index_only_decision: not_required
```

PR12 smoke summary は次である。

```text
data/ops/pr12_fresh_read_only_smoke_summary.json:
  started_at: 2026-05-27T02:23:16.768478+00:00
  ended_at: 2026-05-27T03:28:59.563619+00:00
  raw_quote_started_at: 2026-05-27T02:23:16.768478+00:00
  raw_quote_ended_at: 2026-05-27T03:24:30.764180+00:00
  observed_window_seconds: 3673.995702
  raw_row_count: 310
  per_symbol_raw_row_count:
    AAPL: 62
    MSFT: 62
    NVDA: 62
    SP500: 62
    XYZ100: 62
  final_decision: READ_ONLY_GO
  individual_stock_decision: paper_only
  index_only_decision: not_required
  next_action: none
```

quote collection summary は次である。

```text
venue: trade_xyz
duration_minutes: 60
interval_seconds: 60
requested_symbols: SP500, XYZ100, NVDA, AAPL, MSFT
collected_symbols: SP500, XYZ100, NVDA, AAPL, MSFT
row_count: 310
api_error_count: 0
```

各 symbol の要約は次である。

```text
SP500:
  row_count: 62
  tradable_rate: 1.0
  missing_mark_rate: 0.0
  missing_oracle_rate: 0.0
  missing_funding_rate: 0.0
  missing_open_interest_rate: 0.0
  spread_bps_p50: 0.13283123127837348
  spread_bps_p90: 0.1328594678983144
  bid_depth_10bps_usd_p50: 1602087.2393999998
  ask_depth_10bps_usd_p50: 1611556.5298
  funding_present_rate: 1.0

XYZ100:
  row_count: 62
  tradable_rate: 1.0
  missing_mark_rate: 0.0
  missing_oracle_rate: 0.0
  missing_funding_rate: 0.0
  missing_open_interest_rate: 0.0
  spread_bps_p50: 0.3324523346465201
  spread_bps_p90: 0.33256289595769795
  bid_depth_10bps_usd_p50: 2161294.1496
  ask_depth_10bps_usd_p50: 2134720.0499
  funding_present_rate: 1.0

NVDA:
  row_count: 62
  tradable_rate: 1.0
  missing_mark_rate: 0.0
  missing_oracle_rate: 0.0
  missing_funding_rate: 0.0
  missing_open_interest_rate: 0.0
  spread_bps_p50: 0.46692970373267834
  spread_bps_p90: 0.9340556697170657
  bid_depth_10bps_usd_p50: 217666.36204
  ask_depth_10bps_usd_p50: 130936.27276000002
  funding_present_rate: 1.0

AAPL:
  row_count: 62
  tradable_rate: 1.0
  missing_mark_rate: 0.0
  missing_oracle_rate: 0.0
  missing_funding_rate: 0.0
  missing_open_interest_rate: 0.0
  spread_bps_p50: 3.8940809968848824
  spread_bps_p90: 5.187731016147624
  bid_depth_10bps_usd_p50: 67139.37676999999
  ask_depth_10bps_usd_p50: 87566.99713000002
  funding_present_rate: 1.0

MSFT:
  row_count: 62
  tradable_rate: 1.0
  missing_mark_rate: 0.0
  missing_oracle_rate: 0.0
  missing_funding_rate: 0.0
  missing_open_interest_rate: 0.0
  spread_bps_p50: 2.8975708697542992
  spread_bps_p90: 3.862401931200197
  bid_depth_10bps_usd_p50: 86031.39455
  ask_depth_10bps_usd_p50: 92696.00938000002
  funding_present_rate: 1.0
```

quote diagnostics summary では、5 symbols、310 rows、missing mark/oracle/funding/OI はすべて 0.0、l2_only_rate も 0.0 である。一方で `fee_mode_unknown_rate` は全銘柄 1.0 である。これは資料上の「fee 0.04% 固定禁止」「fee_mode unknown は micro live candidate NG」という条件に照らすと、read-only chain としては合格、micro live readiness としては未完了という判定になる。

## 5. 総合ステータス表

| 領域 | 判定 | 根拠 | 注意点 |
|---|---|---|---|
| PR9a CLI/import recovery | 実装済み | `uv run sis --help` pass、CLI command registration 存在 | `src/sis/cli.py` は多くの command writer を import しており、完全な lazy import ではない |
| PR9b HIP-3 asset mapping | 実装済み寄り / 一部実装 | `resolve_asset_id()` 公式式、`perpDexs` 解決、registry artifact asset_id 解決済み | `perpDexs` 失敗時に meta fallback が残る |
| PR9b metaAndAssetCtxs enrichment | 実装済み | `TradeXyzClient.meta_and_asset_ctxs()`、collector/normalizer で mark/oracle/funding/OI 反映 | ctx が空の場合 `BLOCK_META_CTX_MISSING` は明示されず、ctx あり欠損時のみ個別 block |
| PR9c fresh window CLI | 実装済み | duration/interval/symbols/max/dry-run/summary/report/normalize がある | iteration は `int(duration*60/interval)` の floor。端数 duration は厳密な wall-clock 終端ではない |
| PR10 strict validation | 実装済み | `validate-artifacts --strict` が checked_files=11/issues=0 | strict required は Python 側で non-null check。schema 自体は base required が緩い |
| PR10 diagnostics | 実装済み | `diagnose-quotes --venue trade_xyz`、summary に missing rates / fee unknown / block reason | diagnostics report の quick navigation に `data/docs/live_evidence_reports/latest.md` のような存在しない可能性のある path が混じる |
| PR11 operations cutover | 実装済み寄り / 一部実装 | phase gate が Trade[XYZ] artifact を見て `READ_ONLY_GO` | execution lineage 側は degraded、phase gate markdown の fallback next actions に旧 QQQ/SPY/XAU 文言が残る |
| PR12 fresh read-only smoke | 実装済み | `observed_window_seconds=3673.995702`、`raw_row_count=310`、exit_codes 全 0 | `research_quality_report_exists=false` が summary に残る |
| bot-preview v1 | 実装済み | read-only HOLD preview code と CLI がある | 注文候補生成は未実装で、明示的に `BOT_ORDER_LOGIC_NOT_IMPLEMENTED` |
| micro live safety code | 一部実装 / 意図的に未公開 | adapter/policy/canary code と tests はある | `configs/micro_live_policy.yaml` は `enabled: false`、public micro live CLI はない |
| wallet/signing/production live trading | 未実装 | 資料でも non-goal / PR13 deferred | 実装してはいけない範囲として維持されている |
| legacy gTrade/Ostium active path | 履歴/legacy | ZIP archive のみ tracked、active source は削除 | `sidecars/` と `data/raw/sidecar/` の空 dir はあるが tracked file は archive zip のみ |

## 6. PR9a: CLI / import recovery

### 6.1 判定

PR9a は実装済みである。

資料の PR9a は、`uv run sis --help` と `uv run python -m sis.cli --help` が落ちない状態、missing reports modules の復元、`__init__.py` の eager import 削減、archive adapter を public import surface から外すこと、CLI smoke test を求めている。

今回の確認で `uv run sis --help` は pass した。出力上も `collect-trade-xyz-quotes`、`phase-gate-review`、`refresh-operations-artifacts`、`paper-operations-cycle`、`bot-preview` などの command が見えている。`bot-preview` は説明文として `Build a read-only HOLD preview; no wallet, signing, or exchange writes.` を持ち、現行の read-only boundary が CLI 上にも出ている。

`src/sis/reports/summary_normalizers.py`、`src/sis/reports/phase_gate_review.py`、`src/sis/reports/remediation_evaluator.py` は現 repo に存在する。`src/sis/reports/__init__.py`、`src/sis/ops/__init__.py`、`src/sis/execution/__init__.py` も存在し、少なくとも archive adapter を public import して root CLI を落とす状態ではない。

### 6.2 コード根拠

`src/sis/cli.py` は root Typer app を作り、各 `register_*_commands()` を呼ぶ構成である。command 実装は `src/sis/commands/` 配下に分割されている。これは `docs/CURRENT_STATE.md` の「root CLI split」と一致する。

ただし、PR9a の資料には「`__init__.py` は極力空」「command 内部で必要になった時だけ local import」という理想形が書かれている。現 `src/sis/cli.py` は `register_*` 関数だけでなく、多数の report writer や manifest appender を top-level import している。今回 `uv run sis --help` が通るので PR9a の運用目的は達成しているが、設計上の完全 lazy import ではない。したがって、CLI 起動性は「実装済み」、import surface の軽量化は「完全ではないが現状問題なし」という評価になる。

### 6.3 テスト根拠

対象テスト群の中で `tests/test_cli_smoke.py` が存在し、今回の targeted pytest には入れていないが、既存 docs は full gate で 280 passed と記録している。今回の直接実行では CLI help の pass を確認した。資料の PR9a acceptance に含まれる `python -m compileall -q src tests` と `uv run python -m sis.cli --help` は今回実行していないため、この文書では「今回確認済み」と「既存 docs 記録」を分ける。

今回確認済み:

```text
uv run sis --help: pass
```

既存 docs 記録:

```text
./scripts/check: pass
uv run pytest -q: 280 passed
```

## 7. PR9b: Trade[XYZ] HIP-3 mapping and contexts

### 7.1 判定

PR9b は実装済み寄りだが、一部注意点がある。

実装済みの根拠は、`src/sis/venues/trade_xyz/client.py` に `perp_dexs()`、`meta()`、`meta_and_asset_ctxs()`、`all_mids()`、`l2_book()` が存在すること、`src/sis/venues/trade_xyz/registry.py` に HIP-3 asset id 公式式が実装されていること、現 registry artifact で主要銘柄の `asset_id` が解決済みであること、quote collector が `metaAndAssetCtxs` から mark/oracle/funding/OI を取り込んでいることである。

一部実装と見る理由は、`build_trade_xyz_registry()` が `perpDexs` で解決できない場合に `_extract_perp_dex_index(meta)` へ fallback するためである。資料は「`perp_dex_index` を `meta` payload から推測するだけでは不十分」「`perpDexs` と `meta(dex="xyz")` から確定」と書いている。現実装は `perpDexs` を最初に使うため主要求は満たすが、fallback があるため「meta だけに頼らない」という厳密ポリシーの監査では注意が必要である。

### 7.2 client endpoint

`TradeXyzClient` は次を持つ。

```text
post_info(payload)
all_mids(dex=None)
meta(dex=None)
perp_dexs()
meta_and_asset_ctxs(dex=None)
all_perp_metas()
l2_book(coin)
candle_snapshot(coin, interval, start_ms, end_ms)
```

`meta_and_asset_ctxs()` は `{"type": "metaAndAssetCtxs", "dex": dex or self.config.dex}` を `/info` に POST し、返り値が `[meta, ctxs]` shape であることを検証する。`all_mids()` と `meta()` も `dex` を渡せる。`l2_book()` は `{"type": "l2Book", "coin": coin}` を使う。

資料の endpoint 要求に対して、read-only 収集に必要な主要 endpoint は実装済みである。`perpsAtOpenInterestCap(dex="xyz")` は資料 Appendix に候補として出ているが、PR9a-PR12 の必須 chain では現 repo の中心ではない。

### 7.3 asset id 公式式

`src/sis/venues/trade_xyz/registry.py` には次の式がある。

```python
def resolve_asset_id(perp_dex_index: int, index_in_meta: int) -> int:
    return 100000 + perp_dex_index * 10000 + index_in_meta
```

これは資料の式と一致する。現 registry artifact の主要値は次である。

| symbol | coin | perp_dex_index | index_in_meta | asset_id | active | api_orderable | fee_mode |
|---|---|---:|---:|---:|---|---|---|
| SP500 | xyz:SP500 | 1 | 52 | 110052 | true | true | unknown |
| XYZ100 | xyz:XYZ100 | 1 | 0 | 110000 | true | true | unknown |
| NVDA | xyz:NVDA | 1 | 2 | 110002 | true | true | unknown |
| AAPL | xyz:AAPL | 1 | 9 | 110009 | true | true | unknown |
| MSFT | xyz:MSFT | 1 | 10 | 110010 | true | true | unknown |
| AMZN | xyz:AMZN | 1 | 13 | 110013 | true | true | unknown |
| GOOGL | xyz:GOOGL | 1 | 12 | 110012 | true | true | unknown |
| META | xyz:META | 1 | 8 | 110008 | true | true | unknown |
| TSLA | xyz:TSLA | 1 | 1 | 110001 | true | true | unknown |
| AMD | xyz:AMD | 1 | 14 | 110014 | true | true | unknown |
| EWJ | xyz:EWJ | 1 | 48 | 110048 | true | true | unknown |

主要 5 銘柄に加え、AMZN/GOOGL/META/TSLA/AMD/EWJ も解決されている。`EXCLUDED_ACTIVE_SYMBOLS` には `MSTR`, `COIN`, `CRCL`, `XAU`, `WTI`, `JPY`, `BTC` が入っており、seed にあっても active/orderable から外す設計である。

### 7.4 allMids prefix 差の吸収

`mid_candidates()` は次の candidate set を返す。

```text
SYMBOL
COIN
COIN without XYZ:
XYZ:SYMBOL
xyz:SYMBOL
```

現 implementation では大文字小文字が混じるが、registry 側では `set(mids.keys())` と `_normalize_mid_keys()` を併用しているため、`xyz:NVDA` と `NVDA` の差で全 block になるリスクは下がっている。テストにも allMids prefix 差の fixture がある。

### 7.5 fee_mode

ここは一部実装である。

`configs/fee_model.trade_xyz.yaml` は存在し、`mode: observed` と growth/standard fallback を持ち、「old 0.04% assumption を hardcode しない」「instrument ごとに fee_mode を決める」と明記している。これは資料の「fee 0.04% 固定禁止」と整合する。

一方、現 `data/registry/trade_xyz_instrument_registry.json` の全銘柄 `fee_mode` は `unknown` であり、quote diagnostics の `fee_mode_unknown_rate` は 5 銘柄すべて 1.0 である。したがって、read-only evidence chain は通るが、micro live candidate としてはまだ fee mode が未確定である。これは PR13 以降に進む前の明確な残作業である。

## 8. TASK_03 / metaAndAssetCtxs enrichment

### 8.1 判定

`metaAndAssetCtxs` による mark/oracle/funding/OI enrichment は実装済みである。

`collect_trade_xyz_quotes()` は、`created_client.meta_and_asset_ctxs()` を呼び、`_ctx_by_symbol()` で meta universe と ctx list を symbol に対応させる。その ctx を `quote_from_l2_book()` に渡し、`quote_from_l2_book()` 側で次を抽出する。

```text
mark_price
oracle_price
index_price
funding_rate
open_interest_usd
premium
prev_day_price
day_notional_volume
```

現 PR12 quote collection summary では 5 銘柄すべて `missing_mark_rate=0.0`、`missing_oracle_rate=0.0`、`missing_funding_rate=0.0`、`missing_open_interest_rate=0.0` である。quote diagnostics でも `l2_only_rate=0.0` である。したがって、「L2 mid だけで strict pass している」状態ではない。

### 8.2 注意点

資料では `BLOCK_META_CTX_MISSING` も block reason として挙げている。現 `quote_from_l2_book()` は `ctx = asset_ctx or {}` とし、ctx が存在するのに個別値が欠ける場合は `BLOCK_MARK_PRICE_MISSING`、`BLOCK_ORACLE_PRICE_MISSING`、`BLOCK_FUNDING_MISSING`、`BLOCK_OPEN_INTEREST_MISSING` を付ける。一方、ctx 自体が空の場合に `BLOCK_META_CTX_MISSING` を常に付けるわけではない。strict validation は mark/oracle/funding/OI の non-null を要求するため、ctx 欠損は最終的には strict failure になるが、block reason として `BLOCK_META_CTX_MISSING` を出す資料要求には完全一致していない。

これは実運用上の failure reason 分解としては改善余地がある。たとえば `meta_and_asset_ctxs()` が API error で空 fallback になった場合、raw quote に「ctx layer が欠けた」という意味が直接残らず、後段で mark/oracle/funding/OI missing として見える。この差分は今すぐ read-only GO を壊すものではないが、障害解析性では一部実装である。

## 9. TASK_04 / L2 normalizer と depth

### 9.1 判定

side-specific depth の記録は実装済みだが、quality gate の使用は一部実装である。

`BookMetrics` は次の fields を持つ。

```text
best_bid
best_ask
mid_price
spread_bps
depth_10bps_usd
depth_25bps_usd
bid_depth_10bps_usd
ask_depth_10bps_usd
bid_depth_25bps_usd
ask_depth_25bps_usd
block_reasons
```

`compute_book_metrics()` は bids と asks を別々に集計し、`bid_depth_10bps_usd`、`ask_depth_10bps_usd`、`bid_depth_25bps_usd`、`ask_depth_25bps_usd` を計算する。`QuoteLog` にはさらに `min_side_depth_10bps_usd` が入り、tracking 側では `quote.min_side_depth_10bps_usd <= 0` の場合に `BLOCK_SIDE_DEPTH_TOO_THIN` を付ける。

つまり、raw quote と normalized schema の観点では side-specific depth は実装済みである。現 summary も bid/ask depth p50 を別々に持っている。

### 9.2 一部実装ポイント

資料が強く禁止しているのは「bid/ask depth を合算して execution depth に使う」ことである。現 `normalizer.py` は side-specific fields を作る一方で、`quality_blocks()` には `metrics.depth_10bps_usd` を渡している。`metrics.depth_10bps_usd` は `bid_depth_10 + ask_depth_10` の合算である。

```text
quality_blocks(
  spread_bps=metrics.spread_bps,
  depth_10bps_usd=metrics.depth_10bps_usd,
  ...
)
```

`quality_blocks()` は `depth_10bps_usd < min_depth_10bps_usd` なら `BLOCK_DEPTH_TOO_THIN` を付ける。したがって、collector の quote quality gate はまだ合算 depth で thin 判定をしている。一方で tracking gate は `min_side_depth_10bps_usd` を見る条件を持つ。つまり、collector quality と tracking quality で depth の厳密性が揃っていない。

これはこの棚卸しで最も重要な「一部実装」項目のひとつである。PR12 artifact は十分な depth があるため問題化していないが、片側だけ薄い book を過大評価しないという資料の要求を満たすには、`quality_blocks()` の interface を `min_side_depth_10bps_usd` または bid/ask depth に変更するのが筋である。

## 10. PR9c: collect-trade-xyz-quotes fresh window CLI

### 10.1 判定

PR9c は実装済みである。

`src/sis/commands/quotes.py` の `collect-trade-xyz-quotes` command は次の options を持つ。

```text
--registry-path
--normalize / --no-normalize
--symbols
--max-symbols
--duration-minutes
--interval-seconds
--replace / --append
--dry-run
--write-summary / --no-write-summary
--write-report / --no-write-report
--output-dir
```

資料の option 要求は満たしている。`--dry-run` は registry を読み、対象 symbol を解決して、API/書き込みを行わずに symbol count と symbols を出す。今回の確認でも `symbol_count=3`、`symbols=SP500,XYZ100,NVDA` が出た。

### 10.2 window collector

`collect_trade_xyz_quote_window()` は `duration_minutes` と `interval_seconds` を検証し、`iterations = max(1, int((duration_minutes * 60) / interval_seconds))` で loop 回数を決める。各 iteration で `all_mids()`、`meta_and_asset_ctxs()`、`l2_book()` を使い、raw JSONL へ quote を append し、必要なら normalized parquet と DuckDB を生成する。

現 PR12 artifact では 60 分 x 60 秒の指定で、5 symbols x 62 rows が取れている。通常 `60分 / 60秒` なら 60 iterations x 5 = 300 rows になりそうだが、artifact は 62 rows/symbol である。これは実際の PR12 smoke で replace/re-run や wall-clock loop の影響があった可能性がある。重要なのは `observed_window_seconds >= 3600` と raw rows が 310 あることであり、phase gate はこの条件を見て `next_actions=[]` にしている。

### 10.3 一部実装ポイント

`collect_trade_xyz_quote_window()` の loop 回数は floor である。`duration_minutes=2`、`interval_seconds=90` のような端数指定では 1 iteration になる。資料が求める「fresh evidence window」としては、実際の PR12 では 60/60 なので問題ないが、汎用 window collector としては duration の終端まで while-loop する実装の方が資料の疑似コードに近い。

また、`api_error_count` は `rows_written == before` の時だけ increment される。symbol 単位で `l2_book` が失敗しても、payload は `{"levels": [[], []], "error": "BLOCK_API_ERROR"}` として quote 化され、他 symbol が書けている限り `api_error_count` に出ない可能性がある。raw quote の block reason で見る設計と解釈できるが、summary の API error count としては弱い。この点も完全な運用診断としては一部実装である。

## 11. PR10: strict validation と diagnostics

### 11.1 判定

PR10 は実装済みである。

`validate-artifacts --strict` は今回の実行で `checked_files=11`、`issues=0` だった。`src/sis/validation/artifacts.py` は `strict=True` かつ Trade[XYZ] registry/raw/summary が存在する場合に `trade_strict` として動き、legacy gTrade/Ostium registry を必須にしない。raw quote JSONL は `quote_log_v2.schema.json` で validation され、さらに Trade[XYZ] row に対して Python 側で required non-null fields を検査する。

Trade[XYZ] strict row の non-null required は次である。

```text
venue
canonical_symbol
coin
asset_id
recv_ts_ms
best_bid
best_ask
mid_price
spread_bps
bid_depth_10bps_usd
ask_depth_10bps_usd
mark_price
oracle_price
funding_rate
open_interest_usd
block_reasons
venue_quality_score
```

資料の required とほぼ一致する。`fee_mode` は schema にあるが、Python strict non-null required には入っていない。資料の strict required fields には `fee_mode` も入っていたため、ここは一部実装と見てもよい。ただし `fee_mode_unknown_rate` は diagnostics で出るため、完全に見落とされているわけではない。

### 11.2 schema と strict の関係

`schemas/quote_log_v2.schema.json` 自体の `required` は base fields に留まる。Trade[XYZ] strict fields を schema required に直接入れるのではなく、`validate_artifacts()` の `_validate_trade_xyz_strict_row()` が non-null check を追加する設計である。

これは実装としては成立しているが、schema 単体を外部 validator へ渡した場合は strict required を再現できない。資料の `quote_log_v2 strict required fields` を schema contract として配布したいなら、schema 側にも `if venue == trade_xyz then required` を入れるか、別 strict schema を作る方が明確である。現 repo 内の CLI validation としては実装済み、schema artifact 単体としては一部実装である。

### 11.3 diagnostics

`src/sis/reports/quote_diagnostics.py` は次を計算する。

```text
rows
market_open_rows
tradable_rate
stale_rate
missing_mark_price_rate
missing_index_price_rate
missing_oracle_price_rate
missing_funding_rate
missing_open_interest_rate
missing_spread_rate
l2_only_rate
fee_mode_unknown_rate
block_reason_distribution
stale_missing_oracle_ts_rate
stale_old_oracle_ts_rate
market_status_unknown_rate
market_closed_rate
oracle_age_p50_ms
oracle_age_p90_ms
spread_p50_bps
spread_p90_bps
```

現 `data/ops/quote_diagnostics_summary.json` では 5 銘柄全て missing rates が 0.0、stale_rate が 0.0、tradable_rate が 1.0 である。ただし `fee_mode_unknown_rate=1.0` が全銘柄に出ている。これは diagnostics が機能している証拠であり、同時に fee mode 未確定を示す証拠でもある。

## 12. PR11: operations artifact chain cutover

### 12.1 判定

PR11 は read-only phase gate については実装済みである。ただし execution lineage / production execution readiness まで含めるなら一部実装である。

`phase-gate-review` は Trade[XYZ] artifact が存在する場合、diagnostics symbols を `SP500`, `XYZ100`, `NVDA`, `AAPL`, `MSFT` にし、strict validation と diagnostics を見て判定する。5 symbols 全て mark/oracle/funding/OI 欠損がなければ `READ_ONLY_GO`、指数 2 銘柄だけ healthy なら `CONDITIONAL_INDEX_ONLY`、それ以外なら `NO_GO` にする。

現 summary では `phase_gate_decision=READ_ONLY_GO`、`individual_stock_decision=paper_only`、`index_only_decision=not_required`、`phase2_entry_allowed=true` である。legacy gTrade/Ostium artifact は strict 必須ではない。

### 12.2 phase gate の注意点

`data/ops/phase_gate_review_summary.json` では、Trade[XYZ] read-only gate は通っているが、execution snapshot 系には degraded が残る。

```text
execution_overall_status: degraded
execution_venue_count: 0
execution_diagnostics_status: degraded
execution_balance_gap_detected: true
execution_fills_gap_detected: true
execution_drift_overview_status: degraded
execution_comparison_all_registries_present: false
```

これをどう読むかが重要である。Trade[XYZ] read-only PR12 の判定は `READ_ONLY_GO` であり、PR12 の資料ゴールは達成している。一方で、execution lineage の degraded は、実注文・残高・fills・state comparison といった live execution readiness がまだ閉じていないことを示す。つまり、phase gate は read-only/paper continuation を許しているが、production live trading を許しているわけではない。

また、phase gate report の Markdown には `Next Actions` として fallback 的に次が出る。

```text
recollect live evidence during the recommended window
rerun diagnose-quotes for QQQ / SPY / XAU
rerun validate-artifacts --strict
rerun check-go-no-go and build-evidence-card
```

一方、summary JSON の `next_actions` は `[]` である。この差は、Markdown writer が `next_actions` 空の場合に汎用 fallback を表示しているためで、current PR12 closeout の正本は summary JSON の `next_actions=[]` と見るべきである。Markdown の QQQ/SPY/XAU は legacy 文脈が残っているため、将来の docs cleanup 候補である。

### 12.3 market session と underlying session

資料は `venue_market_status` と `underlying_session` の分離を求めている。現 repo には複数層でこの考え方が入っている。

`src/sis/real_market/calendar.py` は XNYS の `regular`、`premarket`、`afterhours`、`closed` を返す。`src/sis/market_calendar.py` は `SP500`, `XYZ100`, `NVDA`, `AAPL`, `MSFT`, `AMZN`, `GOOGL`, `META`, `TSLA`, `AMD`, `EWJ` を XNYS 系に割り当て、推奨収集 window を計算する。

`src/sis/tracking/real_vs_venue.py` は `feature.market_session != "regular"` のとき `BLOCK_UNDERLYING_SESSION_CLOSED` を付ける。micro live policy でも `underlying_session_regular=False` のとき `BLOCK_UNDERLYING_NOT_REGULAR_SESSION` を付ける。

ただし、QuoteLog 自体は `market_status=OPEN if not block_reasons else UNKNOWN`、`session_type=UNKNOWN` として作られており、quote layer だけで underlying session が入るわけではない。underlying session gate は tracking / micro live layer の責務になっている。これは設計として成立するが、資料が求める `venue_market_status` / `underlying_session` fields を raw quote strict contract にまで求めるなら一部実装である。

## 13. PR12: fresh read-only smoke

### 13.1 判定

PR12 は実装済みである。

PR12 の資料は、実ネットワークで 60 分 window を取り、strict validation、diagnostics、paper operations cycle、operations artifact refresh、phase gate review まで通すことを求めている。現 `data/ops/pr12_fresh_read_only_smoke_summary.json` には、そのコマンド列と exit code が保存されている。

commands_run は次である。

```text
uv run sis --help
uv run sis probe trade-xyz
uv run sis collect-trade-xyz-quotes --symbols SP500,XYZ100,NVDA,AAPL,MSFT --duration-minutes 60 --interval-seconds 60 --normalize --replace --write-summary --write-report
uv run sis ingest-research-data
uv run sis build-event-calendar
uv run sis build-feature-panel
uv run sis build-signals
uv run sis check-research-quality
uv run sis diagnose-quotes --venue trade_xyz
uv run sis validate-artifacts --strict
uv run sis paper-operations-cycle
uv run sis refresh-operations-artifacts
uv run sis phase-gate-review
```

exit_codes はすべて 0 である。

### 13.2 生成 artifact

PR12 summary の `artifacts_created` には次がある。

```text
data/registry/trade_xyz_instrument_registry.json
data/raw/quotes/trade_xyz/2026-05-27.jsonl
data/normalized/quotes.parquet
data/normalized/sis.duckdb
data/ops/trade_xyz_quote_collection_summary.json
data/reports/trade_xyz_quote_collection_report.md
data/ops/quote_diagnostics_summary.json
data/ops/phase_gate_review_summary.json
data/reports/phase_gate_review.md
data/reports/real_market_to_trade_xyz_tracking_report.md
```

資料が求めていた `data/ops/pr12_fresh_read_only_smoke_summary.json` と `data/reports/pr12_fresh_read_only_smoke_report.md` も存在する。

### 13.3 注意点

PR12 summary には `research_quality_report_exists=false` が残る。commands_run では `check-research-quality` が exit 0 なので、PR12 の主 chain は通っているが、research quality report artifact の存在確認は false である。これは read-only quote chain の失敗ではないが、研究データ品質 report を PR12 closeout に含めたいなら未完了項目として扱う。

`data/reports/real_market_to_trade_xyz_tracking_report.md` は存在するが、内容は NVDA 1 sample の `decision=keep` 程度でかなり薄い。PR11 の資料が求める「real market features exist」「tracking records exist」「oracle divergence を gate に使う」という観点では、コードはあるが artifact は厚くない。phase gate は quote diagnostics と strict validation を中心に `READ_ONLY_GO` を出しているため、full tracking evidence としては一部実装と見る余地がある。

## 14. Bot preview v1

### 14.1 判定

Bot preview v1 は実装済みである。ただし、注文候補生成は未実装であり、これは意図的な境界である。

`src/sis/bot/preview.py` は `build_bot_preview()` を持ち、`data/ops/phase_gate_review_summary.json`、`data/ops/trade_xyz_quote_collection_summary.json`、latest raw quote path を読み、read-only artifact が揃っているかを見る。出力は常に `decision: HOLD` であり、`live_order_submitted=false`、`wallet_used=false`、`exchange_write_used=false` を明記する。

`reason_codes` には、read-only artifact が揃っていても `BOT_ORDER_LOGIC_NOT_IMPLEMENTED` が必ず追加される。つまり Bot preview v1 は「artifact が揃っていることを読めるが、まだ order candidate を作らない」ための HOLD preview である。

`src/sis/commands/bot.py` は `bot-preview` command を public CLI に登録している。help text は `Build a read-only HOLD preview; no wallet, signing, or exchange writes.` である。

### 14.2 現 artifact

今回の確認では `data/bot/bot_decision.json` と `data/reports/bot_orders_preview.md` は存在しなかった。README には bot-preview が出力すると書かれているが、現 worktree の data artifact としては未生成である。これは `uv run sis bot-preview` を実行すれば生成される類の runtime artifact であり、コード未実装ではない。

ただし、現 artifact の有無を基準に「いま repo checkout 直後に見られるか」と問うなら、bot preview output は未生成である。この文書ではコード surface は実装済み、現 artifact は未生成と分ける。

## 15. micro live safety surface

### 15.1 判定

micro live safety surface は一部実装であり、public operator CLI としては意図的に未公開である。

コードは次を持つ。

```text
src/sis/execution/live_order_policy.py
src/sis/execution/trade_xyz_adapter.py
src/sis/execution/micro_live_canary.py
tests/test_trade_xyz_live_order_policy.py
tests/test_trade_xyz_adapter_safety.py
tests/test_micro_live_canary.py
```

`live_order_policy.py` は `MicroLivePolicy` と `MicroLiveGateInput` を定義し、次の block reason を実装している。

```text
BLOCK_MICRO_LIVE_DISABLED
BLOCK_CONFIRM_FLAG_REQUIRED
BLOCK_KILL_SWITCH_ACTIVE
BLOCK_SCHEDULE_CANCEL_REQUIRED
BLOCK_ORDER_TYPE_PROHIBITED
BLOCK_NOTIONAL_TOO_HIGH
BLOCK_LEVERAGE_TOO_HIGH
BLOCK_MAX_OPEN_POSITIONS
BLOCK_DAILY_LOSS_LIMIT
BLOCK_SYMBOL_NOT_ALLOWED
BLOCK_UNDERLYING_NOT_REGULAR_SESSION
BLOCK_TRACKING_DISALLOWS_TRADE
BLOCK_LOW_SOURCE_CONFIDENCE
BLOCK_LOW_VENUE_QUALITY
BLOCK_EVENT_WINDOW
```

`configs/micro_live_policy.yaml` は `enabled: false` であり、allowed symbols は `SP500`, `XYZ100`, `NVDA`, `AAPL`, `MSFT`、max notional は 50、max leverage は 2、market order 禁止、schedule cancel required、reduce-only close required である。

`micro_live_canary.py` は schedule cancel を先に置き、policy gate を通したうえで limit order を出し、order status by cloid を読み、open/working/resting なら cancelByCloid、filled なら reduce-only close を出す流れを持つ。tests は fake exchange で schedule cancel before order、filled position close、schedule cancel failure block、notional too high block を確認している。

### 15.2 未実装 / 未公開ポイント

資料上、PR13 は deferred であり、今回実装しない範囲である。現 repo もその境界を守っている。

未実装または未公開のものは次である。

```text
public micro live operator CLI
wallet secret loading
signing integration
real exchange write credential path
production live order smoke
manual live canary runbook with actual account preflight
fee_mode known condition connected to micro live promotion
agent wallet address and account query address separation in production config
cloid 0x + 32 hex chars enforcement as public input gate
```

一部注意として、`TradeXyzSafetyAdapter` は Protocol に対して `schedule_cancel`、`place_limit_order`、`cancel_by_cloid` などを呼べる形を持つが、これは実 exchange client ではなく adapter abstraction である。tests は fake exchange であり、本番 API に対する write smoke ではない。したがって、micro live safety code があることを live trading ready と解釈してはいけない。

## 16. legacy gTrade / Ostium

### 16.1 判定

legacy gTrade/Ostium は active path から外れており、履歴/legacy として扱う。

tracked file として確認できた archive は次である。

```text
archive/gtrade_ostium_legacy_archive_20260527_013818.zip
```

`git ls-files` で gTrade/Ostium 関連として active に見えるものは、上記 ZIP と `docs/archive/` 配下の historical docs 程度である。`sidecars/` と `data/raw/sidecar/` の directory は存在するが、tracked file はない。これは README と docs の「legacy source, sidecar, raw data, registry, 専用テストは ZIP 化済みで active file tree から削除」という説明と一致する。

ただし、`src/sis/reports/live_evidence_report.py` や `src/sis/reports/go_no_go.py` などには、historical compatibility や archived flow のための gTrade/Ostium path 名がまだ出てくる。これは active collector として使うという意味ではない。今後の docs では、Trade[XYZ] current path と legacy reports の文脈を混ぜないことが重要である。

## 17. 実装済みの詳細一覧

この章では、現在の repo で「実装済み」と見てよいものを列挙する。

### 17.1 CLI 起動と command registration

実装済み:

```text
uv run sis --help
collect-trade-xyz-quotes
normalize-quotes
probe trade-xyz
diagnose-quotes
validate-artifacts
refresh-operations-artifacts
phase-gate-review
paper-operations-cycle
bot-preview
execution read-only/report commands
```

`uv run sis --help` の command list に `collect-trade-xyz-quotes` と `bot-preview` が見える。これは public CLI surface として使える状態である。

### 17.2 Trade[XYZ] registry

実装済み:

```text
seed registry loading
allMids reading
meta(dex="xyz") reading
perpDexs reading
universe index extraction
HIP-3 asset id formula
excluded active symbols
api_orderable fail-closed
registry JSON writing
universe report writing
```

現 artifact では 11 symbols が `asset_id` 解決済みである。

### 17.3 quote collection

実装済み:

```text
allMids fetch
metaAndAssetCtxs fetch
l2Book fetch
mark/oracle/funding/open interest enrichment
raw JSONL append
duration / interval window collection
symbol filter
max symbols
dry-run
replace / append
summary JSON
markdown report
normalize to parquet / DuckDB
```

PR12 artifact では 5 symbols x 62 rows、310 rows、api_error_count=0 である。

### 17.4 diagnostics / validation

実装済み:

```text
quote_log_v2 schema
Trade[XYZ] strict non-null validation
summary schema validation
normalized parquet existence check
legacy gTrade/Ostium strict requirement removal
per-symbol diagnostics
missing mark/oracle/funding/OI rates
l2_only_rate
fee_mode_unknown_rate
block reason distribution
spread quantiles
oracle age quantiles
```

現 validation は `checked_files=11`、`issues=0` である。

### 17.5 phase gate

実装済み:

```text
Trade[XYZ] artifact detection
read-only collector gate
strict validation integration
diagnostics integration
READ_ONLY_GO / CONDITIONAL_INDEX_ONLY / NO_GO decision
PR12 summary window check
next_actions clear when PR12 complete
phase2_entry_allowed boolean
Markdown and JSON report output
```

現 summary は `READ_ONLY_GO` と `phase2_entry_allowed=true` である。

### 17.6 paper / execution read-only surfaces

実装済み:

```text
paper operations cycle command
paper reports
execution snapshot reports
execution venue comparison reports
execution venue diagnostics reports
state comparison / drift reports
operations dashboard / audit bundle reports
```

ただし、これらの一部は現 artifact 上 degraded であり、live execution readiness としては未完了である。

### 17.7 bot-preview v1

実装済み:

```text
read-only HOLD decision
phase gate summary reading
quote summary reading
raw quote window existence check
no wallet / no signing / no exchange writes flags
BOT_ORDER_LOGIC_NOT_IMPLEMENTED reason
fail-on-not-ready option
```

現 artifact は未生成だが、CLI と code は存在する。

## 18. 一部実装の詳細一覧

この章は、将来 PR13 や Bot preview v2 へ進む前に見落とすと危ない「一部実装」をまとめる。

### 18.1 depth gate が合算 depth をまだ使う

side-specific depth fields は存在するが、collector quality gate は `depth_10bps_usd` の合算を渡している。資料は「bid/ask depth を合算して execution depth にするな」と明示している。tracking layer は `min_side_depth_10bps_usd` を見るが、collector の `is_tradable` 判定では合算 depth の影響が残る。

影響:

```text
片側だけ厚く片側が薄い orderbook を collector level で tradable と判定する可能性がある。
tracking layer で later block される場合はあるが、raw quote の is_tradable と venue_quality_score が過大評価になる可能性がある。
```

推奨:

```text
quality_blocks() の引数を min_side_depth_10bps_usd に変える。
または bid_depth_10bps_usd / ask_depth_10bps_usd を渡し、片側が threshold 未満なら BLOCK_SIDE_DEPTH_TOO_THIN を付ける。
tests/test_trade_xyz_normalizer.py に bid-heavy / ask-thin fixture を追加する。
```

### 18.2 perpDexs fallback

`perpDexs` が primary だが、失敗時に `meta` から `perp_dex_index` を拾う fallback がある。

影響:

```text
live API shape が変わった時、meta field の意味を誤読して asset_id を出す可能性がある。
ただし、現 live artifact では perp_dex_index=1、asset_id は整合している。
```

推奨:

```text
fallback を残すなら notes に fallback_source を残す。
strict registry validation で perp_dex_index_source == "perpDexs" を要求する。
fallback を使った場合 api_orderable=false にする選択も検討する。
```

### 18.3 fee_mode unknown

全 registry row の `fee_mode` が `unknown` である。quote diagnostics も `fee_mode_unknown_rate=1.0` を示す。

影響:

```text
read-only保存: OK
paper: 警告付きなら OK
micro live candidate: NG
strategy expected value: 手数料過小評価のリスク
```

推奨:

```text
Trade[XYZ] fee tier / growth vs standard を instrument ごとに決める。
registry builder で fee_mode を埋める。
unknown の場合は phase gate の micro_live_status を BLOCKED にする。
paper report には unknown fee の警告を明示する。
```

### 18.4 strict schema が単体では緩い

`quote_log_v2.schema.json` の `required` は base fields だけで、Trade[XYZ] strict required は Python validator が追加する。

影響:

```text
CLI validation では問題ない。
外部ツールや別言語で schema だけを見ると strict required が再現されない。
```

推奨:

```text
schemas/quote_log_v2.trade_xyz.strict.schema.json を追加する。
または JSON Schema の if/then で venue=trade_xyz の時の required を表現する。
```

### 18.5 `BLOCK_META_CTX_MISSING` の明示性

ctx が空の場合に `BLOCK_META_CTX_MISSING` が常に出るわけではない。ctx ありで個別値 missing の場合は block reason が出る。

影響:

```text
API failure と symbol-level missing の区別が raw quote だけでは弱い。
```

推奨:

```text
metaAndAssetCtxs が取れなかった場合は quote 全体に BLOCK_META_CTX_MISSING を付ける。
ctx index が存在しない場合も BLOCK_META_CTX_MISSING を付ける。
```

### 18.6 PR12 tracking report が薄い

`data/reports/real_market_to_trade_xyz_tracking_report.md` は NVDA 1 sample だけである。PR12 summary の main decision には足りているが、real-market tracking evidence としては薄い。

影響:

```text
個別株 paper_only と言うには quote diagnostics は十分でも、real market divergence の継続評価は薄い。
```

推奨:

```text
5 symbols 全部の tracking records を PR12 report に入れる。
mark_real_diff_bps / oracle_real_diff_bps / underlying_session / trade_allowed を symbol ごとに出す。
```

### 18.7 phase gate Markdown の next action fallback

summary JSON は `next_actions=[]` だが、Markdown report は fallback next actions として QQQ/SPY/XAU を含む古い文言を出す。

影響:

```text
人間が Markdown だけ読むと、PR12 完了後も旧 legacy collection をすべきと誤読する可能性がある。
```

推奨:

```text
Trade[XYZ] artifact がある時は fallback next actions を Trade[XYZ] 用に変える。
summary JSON の next_actions を Markdown の正本にする。
```

### 18.8 bot-preview artifact が現 checkout にはない

`bot-preview` の code/CLI はあるが、`data/bot/bot_decision.json` と `data/reports/bot_orders_preview.md` は現時点で見つからなかった。

影響:

```text
bot-preview の結果を見たい場合は `uv run sis bot-preview` を実行する必要がある。
```

推奨:

```text
docs で「出力する」ではなく「実行すると出力する」と書く。
handoff で bot-preview artifact の有無を current truth として明記する。
```

## 19. 未実装または意図的に未実装の詳細一覧

### 19.1 wallet / signing

未実装であり、資料でも non-goal である。現 repo の public command surface に wallet secret loading や signing workflow は見当たらない。これは正しい未実装である。

### 19.2 production live trading

未実装である。`TradeXyzSafetyAdapter` と `MicroLiveCanary` はあるが、fake exchange tests で検証される safety surface であり、本番 exchange write integration ではない。

### 19.3 public micro live CLI

未公開である。`uv run sis --help` に `micro-live` や `trade-xyz-micro-live-canary` の public command は出ていない。これは資料の PR13 deferred と一致する。

### 19.4 order candidate generation

未実装である。`bot-preview` は必ず `BOT_ORDER_LOGIC_NOT_IMPLEMENTED` を reason に入れ、order candidates を出さない。Bot Preview v2 の task ledger に進むまで実装しない境界である。

### 19.5 0xArchive backfill

PR12.5 optional であり、現 repo の active path には見当たらない。API key がなければ skip という資料方針なので、未実装でも PR12 完了を妨げない。

### 19.6 Lighter 実装

未実装であり、資料でも non-goal である。`Venue.LIGHTER` enum はあるが、今回の Trade[XYZ] chain とは別物である。

### 19.7 commodity / metal / oil / FX / pure crypto support

今回範囲外である。legacy XAU/WTI/JPY/BTC などは excluded active symbols に入っており、Trade[XYZ] current chain の対象ではない。

## 20. artifact を読む時の注意

### 20.1 `data/` は git 管理外

README と docs は `data/` を generated runtime artifacts として扱っている。したがって、artifact は current checkout に存在しても git の正本ではない。再開時は、必要に応じて次で再生成する。

```bash
uv run sis implementation-status --write
uv run sis refresh-operations-artifacts
uv run sis phase-gate-review
uv run sis bot-preview
```

PR12 quote artifact を更新するなら、次を使う。

```bash
uv run sis probe trade-xyz
uv run sis collect-trade-xyz-quotes \
  --symbols SP500,XYZ100,NVDA,AAPL,MSFT \
  --duration-minutes 60 \
  --interval-seconds 60 \
  --normalize \
  --replace \
  --write-summary \
  --write-report
uv run sis diagnose-quotes --venue trade_xyz
uv run sis validate-artifacts --strict
uv run sis phase-gate-review
```

### 20.2 summary JSON と Markdown が食い違う時

この repo では、人間向け Markdown report と machine-readable summary JSON の両方がある。closeout 判定では JSON を優先するのが安全である。今回の代表例は `phase_gate_review` の `next_actions` である。

```text
data/ops/phase_gate_review_summary.json:
  next_actions: []

data/reports/phase_gate_review.md:
  fallback next actions に legacy 文言が残る
```

PR12 完了判定では summary JSON の `next_actions=[]`、PR12 summary の `next_action=none` を優先して読む。

### 20.3 `READ_ONLY_GO` と live trading ready は別物

`READ_ONLY_GO` は read-only/paper continuation の gate である。production live trading ready ではない。現 summary でも execution lineage は degraded で、micro live policy は disabled で、fee mode は unknown である。この 3 点だけでも live trading へ進めない理由として十分である。

## 21. 資料要求との差分

資料パックの要求に対する現状を、より直接的に対応表にする。

| 資料要求 | 現状 | 判定 |
|---|---|---|
| `uv run sis --help` が通る | 通る | 実装済み |
| missing reports modules 復元 | modules 存在 | 実装済み |
| `__init__.py` eager import 削減 | root CLI は分割済みだが top-level import は多い | 一部実装 |
| archive adapter を public surface から外す | legacy active source は archive zip のみ | 実装済み |
| `perpDexs` endpoint | あり | 実装済み |
| `meta(dex="xyz")` endpoint | あり | 実装済み |
| `metaAndAssetCtxs(dex="xyz")` endpoint | あり | 実装済み |
| asset id 公式式 | あり | 実装済み |
| `perp_dex_index` を `perpDexs` から解決 | primary は perpDexs | 実装済み寄り |
| meta 推測だけに頼らない | fallback あり | 一部実装 |
| mark/oracle/funding/OI を QuoteLog へ入れる | 入る、artifact missing 0 | 実装済み |
| allMids prefix 差吸収 | candidate set あり | 実装済み |
| side-specific depth | fields あり | 実装済み |
| side-specific depth を gate に使う | tracking は使うが collector quality は合算 | 一部実装 |
| window collector | あり | 実装済み |
| dry-run | あり、確認済み | 実装済み |
| summary/report | あり | 実装済み |
| normalize | あり、parquet/duckdb artifact あり | 実装済み |
| strict validation Trade[XYZ] | あり、issues 0 | 実装済み |
| strict validation が legacy を必須にしない | trade_strict では外す | 実装済み |
| diagnostics Trade[XYZ] | あり | 実装済み |
| fee 0.04% 固定禁止 | config 上は固定禁止 | 実装済み |
| fee_mode known | 現 artifact は unknown | 未完了 |
| operations cutover | phase gate は Trade[XYZ] を見る | 実装済み |
| underlying session gate | tracking/micro policy にあり | 実装済み寄り |
| raw quote に underlying_session | なし、session_type UNKNOWN | 一部実装 |
| PR12 60分 smoke | artifact あり | 実装済み |
| PR12 final decision | READ_ONLY_GO | 実装済み |
| 個別株 vs 指数のみ判定 | individual_stock_decision=paper_only | 実装済み |
| PR12.5 0xArchive backfill | 見当たらない | optional 未実装 |
| PR13 public micro live CLI | なし | deferred 未実装 |
| wallet/signing | なし | non-goal 未実装 |

## 22. 次に実装するなら優先度が高いもの

この文書は実装計画ではなく棚卸しだが、現状から次に進む場合の優先順位は明確である。

### 22.1 最優先: depth gate の厳密化

資料要求とのズレが最も実装に近いのは depth gate である。修正範囲は狭い。

候補:

```text
src/sis/venues/trade_xyz/quality.py
src/sis/venues/trade_xyz/normalizer.py
tests/test_trade_xyz_normalizer.py
```

期待:

```text
quality_blocks() が min_side_depth_10bps_usd を見る。
片側だけ薄い fixture で BLOCK_SIDE_DEPTH_TOO_THIN が出る。
quote.is_tradable が合算 depth で過大評価されない。
```

### 22.2 次点: fee_mode 確定

read-only ではなく paper/live 評価へ進むには `fee_mode unknown` を潰す必要がある。

候補:

```text
configs/fee_model.trade_xyz.yaml
configs/instrument_registry.seed.json
src/sis/venues/trade_xyz/registry.py
src/sis/reports/quote_diagnostics.py
phase gate micro_live_status
```

期待:

```text
registry artifact に growth / standard / observed が入る。
fee_mode_unknown_rate が 0 に近づく。
unknown の場合は micro live status が明示的に BLOCKED になる。
```

### 22.3 PR12 report の tracking 厚み

PR12 report は quote collection と strict validation については十分だが、real-market tracking report は薄い。個別株を paper_only と言うなら、5 symbols 全部の tracking evidence を出す方が良い。

候補:

```text
src/sis/tracking/reports.py
src/sis/reports/phase_gate_review.py
data/reports/real_market_to_trade_xyz_tracking_report.md
```

期待:

```text
SP500 / XYZ100 / NVDA / AAPL / MSFT の tracking rows
mark_real_diff_bps
oracle_real_diff_bps
underlying_session
trade_allowed
block_reasons
```

### 22.4 phase gate report の文言 cleanup

summary JSON が正しい一方で Markdown fallback に legacy 文言が残る。運用者が混乱しやすいので docs/report writer cleanup として低リスクに直せる。

候補:

```text
src/sis/reports/phase_gate_review.py
tests/test_phase_gate_review.py
```

期待:

```text
Trade[XYZ] artifact がある場合の fallback next actions は Trade[XYZ] 用になる。
summary JSON と Markdown の意味が一致する。
```

### 22.5 bot-preview v2 は別タスク

bot-preview v1 は HOLD only である。注文候補生成や BUY/SELL/HOLD rules は未実装で、現在の HANDOFF でも明示的な task number 指示が必要な後続作業として扱われている。これを勝手に進めるべきではない。

## 23. この repo を今どう使えるか

今使えるもの:

```text
Trade[XYZ] registry refresh
Trade[XYZ] quote read-only collection
Trade[XYZ] quote diagnostics
strict artifact validation
phase gate review
paper operations cycle
read-only bot preview command
operations reports
micro live safety code tests
```

今使えるが注意が必要なもの:

```text
paper / execution reports:
  generated summaries はあるが execution lineage は degraded を残す。

bot-preview:
  CLI はあるが output artifact は実行時生成。
  order candidates は出ない。

micro live safety:
  code/test surface はあるが policy disabled。
  public operator CLI はない。
```

今使えないもの:

```text
production live trading
wallet/signing
public micro live canary
order candidate generation
fee-mode-resolved micro live promotion
0xArchive backfill
Lighter implementation
commodity/FX/pure crypto current active path
```

## 24. 完了判定

資料の PR9a-PR12 についての完了判定は次である。

```text
PR9a: 実装済み
PR9b: 実装済み寄り。一部 fallback/fee_mode 注意
PR9c: 実装済み
PR10: 実装済み。一部 schema 単体 strictness 注意
PR11: read-only gate は実装済み。execution/live readiness は一部実装
PR12: 実装済み
PR12.5: optional 未実装
PR13: deferred 未実装
```

`Trade[XYZ] fresh read-only evidence chain` という資料パックの主ゴールに対しては、現 repo は完了済みと見てよい。根拠は、PR12 artifact の `observed_window_seconds >= 3600`、`raw_row_count=310`、`strict_validation_issue_count=0`、`phase_gate_decision=READ_ONLY_GO`、`next_actions=[]` である。

一方で、Bot や実資金運用の readiness に対しては未完了である。根拠は、`fee_mode_unknown_rate=1.0`、`configs/micro_live_policy.yaml` の `enabled: false`、public micro live CLI 不在、wallet/signing 不在、bot-preview が `BOT_ORDER_LOGIC_NOT_IMPLEMENTED` を必ず出す設計、execution lineage の degraded である。

したがって、現時点の正しい言い方は次である。

```text
Trade[XYZ] read-only PR12 は完了。
read-only/paper 継続判断は可能。
個別株は paper_only として扱う。
production live trading は未完了。
micro live は code/test surface のみで、operator public CLI は未公開。
Bot の注文候補生成は未実装。
```

## 25. 再確認コマンド

この文書を後で再検証するなら、まず destructive でない次の read-only / generated artifact 確認を行う。

```bash
git status --short --branch
uv run sis --help
uv run sis collect-trade-xyz-quotes --dry-run --max-symbols 3
uv run sis validate-artifacts --strict
uv run sis phase-gate-review
uv run pytest -q \
  tests/test_trade_xyz_registry.py \
  tests/test_trade_xyz_collector.py \
  tests/test_trade_xyz_normalizer.py \
  tests/test_validate_artifacts_trade_xyz.py \
  tests/test_quote_diagnostics.py \
  tests/test_phase_gate_review.py \
  tests/test_real_vs_venue_tracking.py \
  tests/test_micro_live_canary.py \
  tests/test_bot_preview.py
```

本当に PR12 freshness を再取得するなら、60 分かかる次を実行する。

```bash
uv run sis probe trade-xyz
uv run sis collect-trade-xyz-quotes \
  --symbols SP500,XYZ100,NVDA,AAPL,MSFT \
  --duration-minutes 60 \
  --interval-seconds 60 \
  --normalize \
  --replace \
  --write-summary \
  --write-report
uv run sis diagnose-quotes --venue trade_xyz
uv run sis validate-artifacts --strict
uv run sis paper-operations-cycle
uv run sis refresh-operations-artifacts
uv run sis phase-gate-review
```

Bot preview artifact を作るだけなら次でよい。

```bash
uv run sis bot-preview
```

ただし、これで出るのは read-only HOLD preview であり、注文候補や live order ではない。

## 26. 最終メモ

この repo は、資料パックの主旨である「Bot を作る前に、Trade[XYZ] が read-only evidence として信頼できるか確認する」段階については、かなり進んでいる。むしろ今の危険は、`READ_ONLY_GO` を「実資金 ready」と読み替えることにある。

現状の正しい境界は、次の 3 行に集約できる。

```text
証拠収集: できる。
paper/read-only 判断: できる。
実資金自動売買: まだできない。
```

この境界を守る限り、現 repo の PR9a-PR12 実装は有効である。次に進むなら、まず depth gate の side-specific 化、fee_mode 解決、phase gate report の legacy 文言 cleanup、tracking evidence の厚み追加を片付けるのが安全である。その後に初めて Bot Preview v2、注文候補、manual micro live canary、wallet/signing といった PR13 以降の話に進むべきである。

## 27. 追補: 抜け漏れ・誤謬リスクの修正

この章は、初稿を見直して追加した修正点である。初稿の大筋は維持できるが、より code truth に寄せるために、次の補足を正本として扱う。

### 27.1 Python runtime は 3.13

現 repo の runtime は Python 3.13 である。

根拠:

```text
pyproject.toml:
  requires-python = ">=3.13,<3.14"
  [tool.ruff] target-version = "py313"
  [tool.pyrefly] python-version = "3.13"

scripts/check:
  uv sync --dev --locked
  uv run python -V
  uv run ruff check .
  uv run ruff format --check .
  uv run pyrefly check
  uv run pytest -q
```

過去 memory や別作業の文脈には Python 3.14 へ寄せた記録が混じり得るが、この checkout の code truth は 3.13 である。したがって、この repo の verification 表記で 3.14 と書くのは誤りである。

### 27.2 bot-preview artifact は「実行すると生成」であり、常時存在ではない

初稿では、`bot-preview` の code/CLI と current artifact の有無を分けて書いた。この点は正しい。ただし、既存 `README.md`、`docs/CURRENT_STATE.md`、`docs/CODE_STATUS.md`、`.ai_memory/HANDOFF.md` には「bot-preview が `data/bot/bot_decision.json` と `data/reports/bot_orders_preview.md` を出力する」という記述があり、人によっては「現 checkout に必ず存在する」と読める。

現時点の code truth は次である。

```text
src/sis/bot/preview.py:
  decision_path = data_dir / "bot/bot_decision.json"
  report_path = data_dir / "reports/bot_orders_preview.md"

src/sis/commands/bot.py:
  uv run sis bot-preview
```

つまり、`uv run sis bot-preview` を実行すれば生成される。現 checkout にあるかは runtime artifact 状態次第であり、git 管理の current docs と同じ意味の正本ではない。この区別を docs に入れないと、artifact が無いことを実装未完了と誤読するリスクがある。

### 27.3 `.ai_memory/HANDOFF.md` は restart 正本だが、artifact existence は再確認する

`.ai_memory/HANDOFF.md` は再開時の正本として有用である。ただし、そこに書かれた generated artifact の存在は時間と操作で変わる。`data/` は git 管理外なので、handoff の `data/bot/bot_decision.json` や `data/reports/bot_orders_preview.md` は「その時点で生成した/生成できる」情報として読み、再開時には次で確認する。

```bash
find data/bot data/reports -maxdepth 1 -type f \
  \( -name 'bot_decision.json' -o -name 'bot_orders_preview.md' \) \
  -printf '%p\n'
```

今回の確認では、この 2 ファイルは見つからなかった。これは code 未実装ではなく、runtime artifact 未生成である。

### 27.4 `phase-gate-review` は read-only gate と execution degraded を同時に出す

初稿では `READ_ONLY_GO` と execution degraded の併存を説明したが、より強く書く必要がある。現 `phase-gate-review` の読み方は次である。

```text
Trade[XYZ] read-only PR12:
  READ_ONLY_GO
  strict_validation_issue_count=0
  read_only_collector_gate_passed=true
  next_actions=[]

execution / live readiness:
  execution_overall_status=degraded
  execution_venue_count=0
  execution_diagnostics_status=degraded
  execution_balance_gap_detected=true
  execution_fills_gap_detected=true
  execution_drift_overview_status=degraded
```

この 2 つは矛盾しない。read-only quote collection と live execution account/fill/order observation は別の readiness surface である。`READ_ONLY_GO` を live trading ready と読むのが最大の誤謬リスクである。

### 27.5 `phase_gate_review_summary.json` の nullable fields は未実装とは限らない

現 summary には次のような null がある。

```text
trade_xyz_phase_gate_decision: null
paper_status: null
micro_live_status: null
reason_codes: null
```

これらは、現実装が `phase_gate_decision`, `individual_stock_decision`, `index_only_decision`, `venue_decisions`, `blockers`, `next_actions` を主として使っているために残る schema/summary 上の余白である。`micro_live_status=null` は、少なくとも public micro live readiness が評価・解放されていないことを示すが、PR12 read-only 判定の失敗ではない。今後の Better としては、null を残すより `micro_live_status=BLOCKED_NOT_PUBLIC` のように明示する方が誤読が減る。

### 27.6 research quality artifact の扱い

PR12 summary には `research_quality_report_exists=false` がある。一方で `check-research-quality` の exit code は 0 である。これは PR12 quote chain の失敗ではないが、「research quality report artifact まで含めて完了」と言う場合は未確認/不足として扱うべきである。

現時点の正しい表現:

```text
PR12 command chain は exit 0。
Trade[XYZ] quote / validation / diagnostics / phase gate は完了。
research_quality_report artifact の存在は PR12 summary 上 false なので、研究品質レポートの成果物まで完備とは言わない。
```

### 27.7 `sidecars/` と `data/raw/sidecar/` の空 directory

初稿で「`sidecars/` と `data/raw/sidecar/` の空 dir はある」と書いた。これは現 filesystem truth では正しい。ただし git truth と混ぜると誤読がある。`git ls-files` 上、legacy gTrade/Ostium の active tracked file は `archive/gtrade_ostium_legacy_archive_20260527_013818.zip` と historical docs 程度である。空 directory は git では tracking されない。したがって、repo の active implementation tree として legacy sidecar が残っているとは見ない。

### 27.8 docs/live_evidence_reports は source docs ではない

`docs/live_evidence_reports/README.md` だけは current guide として残す価値がある。一方で、過去の generated report は `docs/archive/2026-05-26-live-evidence-history/` へ移されている。`docs/live_evidence_reports/` に将来 generated report が戻ってきた場合、source doc として扱わず、archive するか git 管理外にすべきである。

### 27.9 `plan/20260526_211746_trade_xyz_quote_collector_cli_plan.md` は二重性がある

この plan は PR9a-PR12 の consumed plan である一方、後半に Bot Preview v1 以降の A-G task ledger を持つ。したがって、単純に「古いから archive」とすると、現 handoff が参照する次タスク ledger まで失う。

正しい扱い:

```text
PR9a-PR12 plan 部分: historical / consumed
A-G task ledger 部分: current restart reference
```

Better にするなら、この 1 ファイルを分割する。

```text
plan/archive/20260526_trade_xyz_quote_collector_cli_consumed_plan.md
plan/bot_preview_next_task_ledger.md
```

分割するまでは `plan/20260526_211746_trade_xyz_quote_collector_cli_plan.md` を削除・移動しない方が安全である。

## 28. ドキュメント棚卸し

この章は、コードを正としたときに、どの docs を更新できるか、どれが古いか、どれを作り直した方がよいか、どれを削除・アーカイブ候補にできるかをまとめる。

### 28.1 現行入口として維持する docs

| path | 判定 | 理由 | 注意 |
|---|---|---|---|
| `README.md` | 維持・小更新候補 | repo の最短入口。current command と境界がまとまっている | bot-preview output は「実行すると生成」と書くとより正確 |
| `docs/CURRENT_STATE.md` | 維持・小更新候補 | current truth の短い入口 | artifact は生成物なので値が古くなる可能性を明記済み |
| `docs/CODE_STATUS.md` | 維持・小更新候補 | PR-00〜PR-12 の code status table として有用 | `DONE` を live trading ready と誤読しない注意が必要 |
| `docs/OPERATIONS_RUNBOOK.md` | 維持・小更新候補 | current command runbook として有用 | legacy `run_live_evidence.py` non-dry-run stop をさらに目立たせるとよい |
| `docs/ARCHITECTURE_AND_PHASES.md` | 維持・小更新候補 | code surface と phase boundary の整理として有用 | `Phase 6 code surface` と public CLI 不在をより強調してよい |
| `docs/trade_xyz_bot_beginner_guide.html` | 維持・更新候補 | 非エンジニア向け説明として有用 | HTML なのでコード変更時の同期が難しい。生成元がないなら作り直し候補 |
| `docs/TRADE_XYZ_IMPLEMENTATION_STATUS_AUDIT_2026-05-27.md` | 維持 | PR9a-PR12 実装棚卸しの詳細版 | generated artifact の数値は再検証日を明記して読む |
| `.ai_memory/HANDOFF.md` | 維持 | restart 正本 | artifact existence は再確認が必要 |

### 28.2 更新できるドキュメント

更新できる、かつ current docs として残す価値が高いものは次である。

```text
README.md
docs/CURRENT_STATE.md
docs/CODE_STATUS.md
docs/OPERATIONS_RUNBOOK.md
docs/ARCHITECTURE_AND_PHASES.md
docs/trade_xyz_bot_beginner_guide.html
docs/DOCUMENT_AUDIT_2026-05-27.md
docs/TRADE_XYZ_IMPLEMENTATION_STATUS_AUDIT_2026-05-27.md
docs/live_evidence_reports/README.md
.ai_memory/HANDOFF.md
```

更新方針:

```text
README.md:
  bot-preview outputs は runtime generated と明記する。
  280 passed は「latest recorded」か「再実行済み」を分ける。

docs/CURRENT_STATE.md:
  fee_mode unknown と execution degraded を read-only GO とは別 surface として追記する。

docs/CODE_STATUS.md:
  PR9a-PR12 DONE の下に「一部実装 caveat」欄を追加する。
  depth gate / fee_mode / public micro live CLI を分ける。

docs/OPERATIONS_RUNBOOK.md:
  generated artifact の再生成 command と、PR12 freshness 再取得 command を分ける。
  `uv run sis bot-preview` は output を生成するだけで order candidate を出さないと明記する。

docs/ARCHITECTURE_AND_PHASES.md:
  Phase 6 は code/test surface、Phase 7 は未完了という境界をより強くする。

docs/trade_xyz_bot_beginner_guide.html:
  `bot_decision.json` / `bot_orders_preview.md` は `uv run sis bot-preview` 実行後にできると書く。

docs/live_evidence_reports/README.md:
  current source doc は README だけ、report files は generated artifact であることを維持する。

.ai_memory/HANDOFF.md:
  `data/bot/...` の存在は再開時確認にする。
```

### 28.3 古い内容があるドキュメント

古い内容を含むが、historical banner があるため即削除ではないものは次である。

| path | 古い理由 | 現在の扱い |
|---|---|---|
| `docs/DOCUMENT_AUDIT_2026-05-26.md` | PR12 前の snapshot | superseded。archive 移動候補 |
| `docs/READ_ONLY_COLLECTOR_IMPLEMENTATION_PLAN.md` | legacy gTrade/Ostium collector plan | historical / legacy。current CLI 正本ではない |
| `docs/LIVE_EVIDENCE_READ_ONLY_COLLECTORS.md` | legacy gTrade/Ostium collector operations | historical / legacy。archive restore 前提なら有用 |
| `docs/READ_ONLY_COLLECTOR_RISK_REVIEW.md` | legacy collector risk review | historical / legacy。Trade[XYZ] PR12 risk ではない |
| `plan/20260526_211746_trade_xyz_quote_collector_cli_plan.md` | 前半は consumed plan | 後半 A-G ledger は current 参照なので要分割 |
| `plan/README.md` | plan 全体は historical と説明済み | 維持可 |
| `plan/archive/*` | migration contract の履歴 | archive として維持 |
| `docs/archive/**` | historical generated / handoff docs | current requirement として読まない |

古い docs を読む時のルール:

```text
1. 冒頭 banner を見る。
2. current command として実行しない。
3. code truth と衝突したら code truth を優先する。
4. legacy restore を明示的にやる場合だけ参照する。
```

### 28.4 作り直したほうがいいドキュメント

作り直し優先度が高いのは次である。

#### 28.4.1 `plan/20260526_211746_trade_xyz_quote_collector_cli_plan.md`

理由:

```text
前半: PR9a-PR12 の historical consumed plan
後半: Bot Preview v1 以降の current task ledger
```

1 ファイルに二つの性質が混在している。再開時に A-G ledger を読むには有用だが、PR9a-PR12 plan としては古い。

推奨:

```text
plan/archive/20260526_trade_xyz_quote_collector_cli_consumed_plan.md
plan/bot_preview_next_task_ledger.md
```

この分割をするまでは、削除・archive 移動しない。

#### 28.4.2 legacy read-only collector docs 3 本

対象:

```text
docs/READ_ONLY_COLLECTOR_IMPLEMENTATION_PLAN.md
docs/LIVE_EVIDENCE_READ_ONLY_COLLECTORS.md
docs/READ_ONLY_COLLECTOR_RISK_REVIEW.md
```

理由:

```text
すでに historical / legacy banner はあるが、active docs 直下にあるため、current Trade[XYZ] path と誤読されやすい。
```

推奨:

```text
docs/archive/legacy_read_only_collectors/
  README.md
  IMPLEMENTATION_PLAN.md
  RISK_REVIEW.md
  OPERATIONS_NOTES.md
```

または active docs に残すなら 3 本を 1 本の「legacy archive restore runbook」に再構成する。

#### 28.4.3 `docs/trade_xyz_bot_beginner_guide.html`

理由:

```text
HTML 単体で更新されており、生成元が見当たらない。
コードや status が変わった時に同期漏れが起きやすい。
```

推奨:

```text
docs/trade_xyz_bot_beginner_guide.md を source にする。
HTML は生成 artifact として扱う。
```

ただし、現時点の内容は大筋で current boundary と合っているので、即削除ではない。

#### 28.4.4 `docs/DOCUMENT_AUDIT_2026-05-27.md`

この文書は今回更新した。今後は短い docs index として残し、詳細棚卸しは `docs/TRADE_XYZ_IMPLEMENTATION_STATUS_AUDIT_2026-05-27.md` に寄せるのがよい。さらに厳密にするなら、各 docs の owner / source of truth / regeneration command を表にする。

### 28.5 削除・アーカイブしてもよいドキュメント

即削除ではなく、archive 移動または banner 維持が安全な候補は次である。

| path | 推奨 | 理由 |
|---|---|---|
| `docs/DOCUMENT_AUDIT_2026-05-26.md` | archive 移動候補 | superseded snapshot |
| `docs/READ_ONLY_COLLECTOR_IMPLEMENTATION_PLAN.md` | archive 移動候補 | current Trade[XYZ] path ではない |
| `docs/LIVE_EVIDENCE_READ_ONLY_COLLECTORS.md` | archive 移動候補 | current public CLI ではない legacy command を含む |
| `docs/READ_ONLY_COLLECTOR_RISK_REVIEW.md` | archive 移動候補 | Trade[XYZ] PR12 risk review ではない |
| `docs/live_evidence_reports/live_evidence_report_*` | archive / generated 扱い | source docs ではない |
| `docs/live_evidence_reports/live_evidence_followup_*` | archive / generated 扱い | source docs ではない |

削除しない方がよいもの:

```text
docs/archive/**
plan/archive/**
archive/gtrade_ostium_legacy_archive_*.zip
```

理由は、migration の監査証跡として価値があるためである。current docs から参照しない、または historical と明記することで十分である。

### 28.6 docs を更新する時の優先順位

次の順で直すのがよい。

```text
1. README.md の bot-preview artifact 表現を runtime generated に直す。
2. docs/CURRENT_STATE.md に fee_mode unknown / execution degraded / bot-preview artifact runtime generated を追記する。
3. docs/CODE_STATUS.md の PR9a-PR12 DONE 表に caveat column を足す。
4. docs/OPERATIONS_RUNBOOK.md の bot-preview と live evidence non-dry-run 境界をさらに強調する。
5. plan/20260526... を consumed PR9a-PR12 plan と active A-G ledger に分割する。
6. legacy read-only collector docs 3 本を archive restore runbook へ統合する。
```

この順序なら、current user がまず読む docs から誤読リスクを下げられる。

## 29. Better にするための具体的な修正案

この章はコード変更案ではなく、docs と implementation hygiene の改善案である。

### 29.1 docs source of truth table を追加する

`docs/CURRENT_STATE.md` か `docs/DOCUMENT_AUDIT_2026-05-27.md` に、次の列を持つ表を置くとよい。

```text
path
role
source of truth
regeneration command
staleness risk
owner surface
```

例:

```text
data/reports/phase_gate_review.md:
  role: generated human report
  source of truth: data/ops/phase_gate_review_summary.json + code
  regeneration command: uv run sis phase-gate-review
  staleness risk: high

docs/CURRENT_STATE.md:
  role: tracked current entrypoint
  source of truth: code/tests/artifacts
  regeneration command: none, manual update
  staleness risk: medium
```

### 29.2 generated artifact と source docs を path で分ける

現状でも `data/` は generated として扱われているが、`docs/live_evidence_reports/` は generated report の置き場名を含んでいるため混乱しやすい。README だけを残す方針はよい。今後 generated docs を tracked に戻す場合は、必ず `docs/archive/` へ入れる。

### 29.3 phase gate summary に explicit statuses を入れる

`paper_status`, `micro_live_status`, `reason_codes` が null だと、未実装なのか未評価なのかが読みにくい。

Better:

```text
paper_status: PAPER_ONLY_ALLOWED or NOT_EVALUATED
micro_live_status: BLOCKED_NOT_PUBLIC
reason_codes: []
```

この変更は code/schema/test 変更を伴うため、この docs audit では実装しない。

### 29.4 docs から「実装済み」と「artifact 生成済み」を分ける

今後の docs では次の語を使い分ける。

```text
code implemented:
  code と tests がある。

artifact generated:
  data/ 配下に現時点で出力がある。

live verified:
  実ネットワーク・実時間・外部副作用なしで確認した。

production ready:
  wallet/signing/exchange write/secrets/ops runbook まで完了。
```

現状の `bot-preview` は code implemented だが、今回の checkout では artifact generated ではなかった。PR12 は code implemented かつ artifact generated かつ live verified である。production ready ではない。

### 29.5 docs lint を追加するなら

将来追加するなら、次のような軽量 check が有効である。

```text
docs 内に `Python 3.14` が出たら警告。
current docs 内に `gTrade` / `Ostium` が出る場合、legacy / archive 文脈か確認。
`bot_decision.json` を「存在する」と断定する表現を検出し、「生成する」に直す。
`READ_ONLY_GO` と `live trading ready` が近接していないか確認。
```

ただし、docs/archive は対象外にする。archive を current lint で直すと歴史文書の意味が壊れる。
