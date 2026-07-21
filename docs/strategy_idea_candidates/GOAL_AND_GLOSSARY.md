<!--
作成日: 2026-06-27_11:38 JST
更新日: 2026-07-02_20:51 JST
-->

# Strategy Idea Candidate Goal And Glossary

## 結論

現在の最終ゴールは、入力証跡つきの未検証 strategy idea candidate を生成し、探索全量と棄却理由を保存し、shortlist だけを既存 `strategy_idea.v1` draft と sidecar manifest に分けて次の gate へ渡せる candidate generation pipeline を作ることです。

ただし、最終ゴール全体が完了したわけではない。deterministic generator、split / leakage policy validation API、split materialization sidecar、selection-adjusted metrics local engine、Perp local cost estimate、operator review Markdown surface、richer review packet、Strategy Authoring preflight、fixture E2E、public CLI、Bitget USDT-FUTURES 用 `crypto-perp-risk-taker` profile、JSONL search ledger、manual AI packet/import、Perp estimate bridge、C9 v0 Prep Watchdeck authoring bridge、repo-native Bitget public source refresh は focused tests まで実装済みです。C9 v0 は対応 family に限る fail-closed bridge であり、汎用 Strategy Lab / backtest bridge と実測 Perp cost evaluator は未実装です。

## Fixed Vocabulary

| 用語 | 固定する意味 | 使ってはいけない意味 |
|---|---|---|
| Strategy Idea Candidate | `strategy_idea.v1` に export する前の未検証 strategy idea 候補 | trade candidate、paper candidate、注文候補、alpha proof |
| Strategy Idea Candidate Set | 1 回の候補生成 run の全候補 inventory と証跡 artifact | selected candidates だけの結果ファイル |
| candidate generation pipeline | input evidence から未検証候補を作り、探索全量、棄却理由、source/time/leakage/split 証跡、shortlist export を通す全体工程 | ML/LLM で良さそうな戦略を探すだけの処理 |
| deterministic generator | 入力、family、parameter grid、cap、seed なしの固定順序から同じ candidate set を再現する generator | 学習器、optimizer、LLM、外部 API、broad indicator catalog |
| Candidate Family | generator が使う候補テンプレートの小さな分類 | 戦略の有効性や market regime の証明 |
| parameter grid | family ごとの有限な parameter 組み合わせ定義 | 探索後に都合よく増やす自由記述 |
| candidate cap | 1 run で生成してよい candidate 数の上限 | 良い候補が出るまで続ける試行回数 |
| candidate inventory | `SHORTLISTED` と `REJECTED` を含む全 candidate 一覧 | shortlist だけの成功報告 |
| candidate decision | candidate-level の `SHORTLISTED` または `REJECTED` | paper / live 許可 |
| candidate status | 常に `UNVERIFIED_CANDIDATE` | ready、approved、tradable |
| rejection reason | `REJECTED` candidate を落とした理由 | 実装者向け debug note だけの任意情報 |
| duplicate rejection reason | 同一または近すぎる signal / parameter を落とした理由 | silent dedupe |
| input evidence | input contract validation refs と source path/hash/status/available-at/max observed timestamp | source path だけの参照 |
| PASS source evidence guard | `validation_status=PASS` でも source-level evidence の missing / invalid / hash mismatch / timestamp missing を候補生成前に拒否する guard | validation status 文字列だけを信用すること |
| source summary | candidate set に複製する source evidence の要約 | source file 本体の再保存 |
| search ledger summary | family count、candidate count、trial count、parameter grid hash、peek/rerank count の summary | JSONL / CSV の行単位 ledger |
| search ledger rows | C4 以降で実データ行が出てから追加する JSONL / CSV row output | C3 の必須 output |
| raw validation metrics | raw と明示して保存する未補正 metric | 発見、証明、採用理由 |
| selection-adjusted metrics | local engine による補正 metric disclosure。raw p-value がある場合だけ Benjamini-Hochberg FDR を `AVAILABLE` にし、入力不足は `NOT_ESTIMABLE` | raw metric の言い換え、alpha proof、profit proof |
| split policy | train / validation / sealed test の役割を保存する policy record | 完全な split engine の実装証明 |
| leakage policy | available-at、purge、embargo、sealed-test non-use の policy record | no-lookahead が実証済みという主張 |
| operator review surface | 人間が探索量、棄却数、selection policy、known gaps を読む surface | paper/live approval UI |
| sidecar manifest | `strategy_idea_candidate_export_manifest.v1`。candidate set path/hash と exported idea path/hash を持つ | `strategy_idea.v1` への metadata 押し込み |
| `crypto-perp-risk-taker` profile | Bitget USDT-FUTURES 前提で大量の未検証 Perp 仮説を作る高速実験 profile | live trading profile、wallet/signing profile、profit proof |
| Perp shortlist constraint | funding、fee、slippage、leverage、liquidation buffer、position loss limit、kill conditions が揃わない Perp candidate を shortlist しない guard | paper/live readiness |
| manual AI packet | candidate set と ledger summary を人間が任意AIへ渡すための local packet | repo が外部AI APIを呼ぶ処理 |
| AI import | manual AI response を検証し `source_kind=ai_generated` の未検証候補として取り込む処理 | AI候補の自動採用、AI scoreによる許可 |
| C9 v0 Prep Watchdeck authoring bridge | shortlist 済み Bitget `USDT-FUTURES` Perp candidate のうち対応 family だけを `/home/tn/projects/prep-watchdeck` の local read-only source から candidate-scoped Strategy Authoring spec / suite / bundle / standard backtest pack へ変換する fail-closed 経路。`BRIDGED` は technical bridge 成功だけを意味し、economic gate は `NOT_EVALUATED`。 | 全候補の backtest 成功保証、economic pass、実測 slippage evaluator、actual cash proof、paper/live 許可 |
| Strategy Lab / backtest full bridge | shortlisted candidate を `strategy_idea.v1` draft で止めず、Strategy Authoring spec と標準 backtest pack まで、candidate lineage と検証結果つきで機械的に接続する fail-closed の完成形 | 全候補の backtest 成功保証、`strategy-intake-validate` だけ、authoring preflight だけ、Perp estimate bridge、手順メモ、paper/live 許可 |

## Fixed Candidate Family IDs

C4 の初期 family ID は次に固定する。追加は C4 後の別 checkpoint で扱う。

| family_id | 目的 | 初期扱い |
|---|---|---|
| `trend_momentum` | trend / momentum follow-through 仮説を作る | C4 対象 |
| `volatility_regime` | volatility expansion / compression 仮説を作る | C4 対象 |
| `liquidity_spread` | liquidity / spread 条件を使う仮説を作る | C4 対象 |
| `cross_sectional_rank` | universe 内 ranking 仮説を作る | C4 対象 |
| `mean_reversion` | overextension / reversal 仮説を作る | C4 対象 |
| `regime_filter` | 他 family の filter 条件を作る | C4 では standalone candidate にしない |
| `perp_momentum_continuation` | Perp mark/index momentum continuation 仮説 | crypto-perp-risk-taker 対象 |
| `perp_reversal_after_liquidation_move` | liquidation move 後の reversal 仮説 | crypto-perp-risk-taker 対象 |
| `perp_funding_rate_carry_filter` | funding-rate carry/filter 仮説 | crypto-perp-risk-taker 対象 |
| `perp_basis_mark_index_spread` | mark-index spread / basis 仮説 | crypto-perp-risk-taker 対象 |
| `perp_volatility_breakout_compression` | volatility compression / breakout 仮説 | crypto-perp-risk-taker 対象 |
| `perp_liquidity_spread_filter` | liquidity / spread filter 仮説 | crypto-perp-risk-taker 対象 |
| `perp_open_interest_liquidation_pressure` | open-interest / liquidation-pressure placeholder 仮説 | crypto-perp-risk-taker 対象 |

## Final Goal

Strategy Idea Candidate Generation Pipeline の最終ゴール:

1. `strategy_input_contract_validation.v1` が `PASS` の input evidence だけを候補生成に使う。
2. 少数の fixed candidate family と finite parameter grid から `UNVERIFIED_CANDIDATE` を生成する。
3. `candidate_count_total`、`candidate_count_shortlisted`、`candidate_count_rejected`、`candidate_inventory`、`selection_policy`、`rejection_reason` を必ず保存する。
4. source path/hash/status、available-at、max observed timestamp、label window、prediction horizon、split policy、leakage policy、purge / embargo policy を candidate set に保存する。
5. raw metrics と selection-adjusted metrics status を分ける。engine が走っても必要入力がない場合は `NOT_ESTIMABLE` とする。
6. operator review surface で探索量、棄却数、selection policy、known gaps を人間が読めるようにする。
7. shortlist だけを strict `strategy_idea.v1` draft に export する。
8. candidate set path/hash と exported idea path/hash は `strategy_idea_candidate_export_manifest.v1` sidecar に置く。
9. 既存 `strategy-intake-validate`、Strategy Authoring、backtest、Strategy Review へ渡す。
10. alpha proof、profit proof、paper permission、live readiness、wallet/signing/exchange write permission を一切主張しない。

## Current Goal State

完了済み:

- C1: candidate set contract。
- C2: input evidence bridge。
- C3: canonical JSON / Markdown writer。
- C8: shortlist export と sidecar manifest。
- C4: deterministic generator Python API。fixed family、finite parameter grid、candidate cap、duplicate rejection、parameter grid hash を保存する。
- C5: split / leakage policy validation API と split materialization sidecar。time window ordering、sealed-test non-use、source available-at boundary、purge / embargo policy record を検査・保存する。
- C6: selection-adjusted metrics local engine。`raw_validation_metrics` と `selection_adjusted_metrics_status` を分け、BH FDR が可能な場合だけ `AVAILABLE`、入力不足は `NOT_ESTIMABLE` とし、raw metrics を proof と呼ばない。
- C10: operator review Markdown surface と richer review packet。探索量、棄却理由、selection policy、known gaps、policy validation、false boundary、人間 review template を読めるようにする。
- C11: fixture E2E。input evidence -> candidate set -> policy validation -> operator review -> shortlist export -> intake validation を通す。
- C12: public CLI。`strategy-idea-candidates-build`、`strategy-idea-candidates-ai-packet-build`、`strategy-idea-candidates-ai-import` を追加済み。
- C13: Bitget USDT-FUTURES Perp profile。`crypto-perp-risk-taker` family/grid、Perp risk metadata、shortlist constraint を追加済み。
- C14: JSONL search ledger。全 candidate row に source kind、parameter hash、decision、rejection reason、selection-adjusted metrics status、sealed-test non-use を保存済み。
- C15: manual AI packet/import。外部APIなしで packet を作り、manual AI response を検証して `ai_generated` candidate として取り込み済み。
- C16: Perp local cost estimate。funding / fee / slippage / liquidation buffer を local parameter estimate として保存済み。
- C17: Perp estimate bridge。shortlisted Perp candidate と `crypto_perp_outcome.v1` から candidate-scoped `crypto_perp_tournament_rows.v2` estimate を生成済み。
- C18: Strategy Authoring preflight。`strategy_idea.v1` export availability と authoring/backtest/paper/live readiness gap を保存済み。
- C9 v0: Prep Watchdeck authoring bridge。shortlisted Bitget `USDT-FUTURES` Perp candidate のうち `perp_momentum_continuation` と `perp_funding_rate_carry_filter` だけを candidate-scoped Strategy Authoring spec / suite / bundle / standard backtest pack へ変換し、変換不能・source 不足・pack 失敗は machine-readable blocker として保存済み。

未完了:

- C5 full statistical split engine。現状は validation と materialization sidecar まで。
- C9 full bridge generic mapping。現状は Prep Watchdeck authoring bridge v0 の対応 family に限定。
- Perp funding / fee / slippage / liquidation の実測 evaluator。現状は candidate metadata と local estimate boundary まで。

## C9 Strategy Lab / Backtest Full Bridge Definition

`Strategy Lab / backtest full bridge` とは、shortlist 済みの `Strategy Idea Candidate` を既存の Strategy Authoring / backtest chain へ接続する local-only / fail-closed の経路です。単なる readiness report ではありません。

現 repo の実装済み範囲は C9 v0 Prep Watchdeck bridge です。これは「変換可能な候補だけ candidate-scoped に `strategy_authoring_spec.v1` と標準 backtest pack へ進め、変換不能・データ不足・contract 不一致は machine-readable blocker として残す」ものです。全 Perp candidate を backtest 成功まで通す generic bridge ではありません。

### Required Inputs

full bridge は少なくとも次を入力として読む。

- `strategy_idea_candidate_set.v1`
- `strategy_idea_candidate_export_manifest.v1`
- exported `strategy_idea.v1`
- `strategy_input_contract_validation.v1` refs
- `search_ledger.jsonl`
- selection metrics / Perp cost estimates / split materialization / review packet / authoring preflight sidecars

### Required Outputs

full bridge が完了したと言えるには、候補ごとに次を出力する。

- `strategy_authoring_spec.v1`、または spec 化できない理由を持つ machine-readable rejection artifact
- `strategy_authoring_spec.v1` を生成した場合の Strategy Authoring validation result
- 標準 backtest pack、または backtest pack を作れない理由を持つ machine-readable blocker artifact
- 標準 backtest pack を生成した場合の backtest pack validation result
- candidate id、candidate set path/hash、exported idea path/hash、authoring spec path/hash、backtest pack path/hash、ledger path/hash をつなぐ bridge manifest
- Strategy Review / operator review へ渡せる source refs と known gaps

### Bridge Status Values

full bridge の候補別 status は、少なくとも次のように成功と blocker を分ける。C9 v0 の成功 status は `BRIDGED` です。blocker status は backtest 成功ではなく、明示的な停止結果です。

- `BRIDGED`: authoring spec 生成、candidate-scoped suite / bundle 生成、標準 backtest pack 生成、backtest pack validation が候補スコープで完了。これは technical bridge status であり、economic pass、profit proof、actual cash proof、paper/live 許可ではない。
- `BLOCKED_UNSUPPORTED_FAMILY_MAPPING`: candidate family / parameter set を既存 Strategy Authoring rule primitive に安全変換できない。
- `BLOCKED_UNSUPPORTED_SIGNAL_EXPRESSION`: free-text `signal_expression` しかなく、allowlist mapping で rule 化できない。
- `BLOCKED_MISSING_SOURCE_COLUMNS`: `prep-watchdeck` source から required columns を materialize できない。
- `BLOCKED_NO_SYMBOL_DATA`: candidate symbol の candle / quote history が無い。
- `BLOCKED_UNSUPPORTED_PRODUCT_TYPE`: candidate または source product type が C9 v0 対応外。
- `BLOCKED_UNSUPPORTED_SIDE_BIAS`: C9 v0 対応外の side bias。
- `BLOCKED_AUTHORING_VALIDATION`: `strategy_authoring_spec.v1` は生成したが Strategy Authoring validation が失敗。
- `BLOCKED_BACKTEST_PACK`: authoring / suite / bundle / pack generation または pack validation に失敗。

### Required Behavior

full bridge は次をすべて満たす必要がある。

1. `strategy_idea.v1` schema を探索 provenance 用に広げない。
2. candidate id と candidate set hash を Strategy Authoring / backtest 側の manifest まで失わない。
3. `strategy-intake-validate` を通った shortlist だけを対象にする。
4. feature columns、risk、execution assumptions、data requirements を `strategy_authoring_spec.v1` に変換するか、変換不能理由を明示して fail-closed にする。
5. Strategy Authoring validation を通す。
6. backtest pack を標準 engine で生成するか、必要データ不足・contract 不一致・unsupported signal の blocker を明示する。
7. backtest pack validation を通す。
8. search ledger、selection-adjusted metrics status、cost estimate status、split/leakage status を review source として残す。
9. estimate、raw metric、backtest result を alpha proof / profit proof / paper permission / live readiness と呼ばない。
10. wallet、signing、exchange write、live order、paper execution permission を一切有効化しない。

### Must Not Do

full bridge 実装では次を禁止する。

- `signal_expression` の自由文をコード、SQL、Polars expression、Python expression として実行または ad-hoc parse しない。変換は family / parameter_set / feature_columns_used / target_definition / timeframe / instruments の allowlist mapping だけで行う。
- Bitget USDT-FUTURES candidate を、既存 example の TradeXYZ / QQQ authoring spec、suite、bundle、baseline data へ暗黙変換しない。
- `strategy-backtest-pack` の default spec / suite / bundle を candidate proof として流用しない。候補別 spec、suite、bundle、out_dir、reports_dir を生成または指定する。
- `strategy-author-run` や backtest runner の global default output を読んで候補別結果として扱わない。artifact は candidate-scoped directory に隔離し、path/hash を bridge manifest に残す。
- authoring preflight、Perp estimate、既存 backtest pack の存在だけで `BRIDGED` にしない。
- backtest validation `PASS` を paper/live/wallet/signing/exchange-write 許可にしない。

### Current Repo Constraints

追加調査で確認した現行制約:

- `strategy_authoring_spec.v1` は `experiment.symbol_bindings`、`data.feature_panel_path`、`data.quote_data_path`、`data.cost_model_path`、`rules.entry`、`backtest` を要求する。
- Strategy Authoring validation は feature panel の存在、required columns、confirmation panels、`canonical_symbol` rows を確認する。
- 既存 example spec は `execution_venue: trade_xyz`、`execution_symbol: XYZ100`、`real_market_symbol: QQQ`、baseline feature / quote / cost files を前提にしている。
- 現行 `strategy-backtest-pack` command は default spec / suite / bundle を持ち、pack runner の多くの中間 artifact は `data/research/...` と `reports/...` に書かれる。
- `/home/tn/projects/prep-watchdeck` は Bitget `USDT-FUTURES` public market data の local source として使える。`var/snapshots/latest.json`、`var/snapshots/charts/latest/<SYMBOL>.json`、`data/candles_5m/date=*/candles.parquet`、`data/snapshots/date=*/*.parquet`、`data/scanner.duckdb` に Perp feature / quote / funding / open-interest proxy の材料がある。
- `prep-watchdeck/var/watchdeck.duckdb` には service DB として `instruments`、`ticker_latest`、`candles_1m` があるが、service writer が動作中は DuckDB lock で read-only 接続できない場合がある。この場合は published snapshot / chart JSON、または `data/scanner.duckdb` / parquet を入力源にする。
- したがって C9 v0 は、candidate-scoped generated spec / suite / bundle と isolated `data_dir` / `out_dir` / `reports_dir` を使うか、同等の隔離を行う Python API 経由で実装する。Perp data mapping は「未発見」ではなく、`prep-watchdeck` source adapter として明示実装する。

### Known Local Perp Data Source: prep-watchdeck-compatible root

`/home/tn/projects/prep-watchdeck` または `strategy-idea-candidates-bitget-source-refresh --out <run>/bitget_public_source` が作る `<run>/bitget_public_source/source_root` から C9 v0 に渡せる mapping は次の通り。repo-native refresh は `data/scanner.duckdb`、`data/candles_5m/date=*/candles.parquet`、`var/snapshots/latest.json` の互換 root を作る。

| C9 input | prep-watchdeck source | 使える列 / 値 | 境界 |
|---|---|---|---|
| feature panel | `var/snapshots/latest.json` rows、`data/snapshots/date=*/*.parquet`、`data/scanner.duckdb.tickers_snapshot`、`scanner_rows.row_json` | symbol、timestamp、last / analysis price、timeframe returns、turnover、volume ratio、24h range、74h price/volume features、funding bias、open interest state、data quality、coverage | latest snapshot は横断面の現在値。backtest 用履歴 panel には `data/scanner.duckdb` / parquet の時系列 materialization が必要。 |
| quote data | `var/snapshots/charts/latest/<SYMBOL>.json`、`data/candles_5m/date=*/candles.parquet`、`data/scanner.duckdb.candles_5m`、service DB `candles_1m` | OHLCV、quote volume、5m / 15m / 1h / 4h / 24h / 74h chart bars、1m candles when service DB is readable | `var/snapshots/charts/latest` は latest 128 bars 系。厚い履歴は parquet / DuckDB を優先する。 |
| cost estimate inputs | `var/snapshots/latest.json` rows、service DB `ticker_latest`、web `deal-check.ts` model | max leverage、funding bias / funding rate、bid / ask when service DB readable、mark / index price when service DB readable、24h quote volume、notional / fee / funding / slippage estimate formula | 板厚・実測 slippage は未実装。actual cash / measured execution cost evaluator ではなく、cost-estimate mapping として扱う。 |
| instrument constraints | `data/scanner.duckdb.contracts`、service DB `instruments` | product type、base / quote coin、symbol status、max leverage、min trade USDT / min trade num | Bitget `USDT-FUTURES` と active/valid symbol filtering を bridge 側で再検査する。 |

C9 v0 の blocker 条件は、「Perp 用 local source が無い」ではなく、次に変える。

- `prep-watchdeck` source path が指定されていない。
- 指定 source が存在しない、読めない、または required columns を満たさない。
- service DB が lock 中で、代替 snapshot / parquet / `data/scanner.duckdb` も指定されていない。
- candidate の symbol / timeframe / horizon に対して十分な quote history または feature history を materialize できない。
- cost mapping が実測 slippage / order book depth を要求しているが、`prep-watchdeck` には estimate input しかない。

### Practical V0 Scope

C9 v0 の実装済み範囲は次に限定する。

1. `strategy-idea-candidates-authoring-bridge` CLI と Python API。
2. 入力は candidate set、export manifest、search ledger、`prep-watchdeck` root とする。
3. allowlist mapping できる candidate だけ `strategy_authoring_spec.v1`、candidate-specific suite、candidate-specific bundle を生成する。
4. mapping できない candidate は `BLOCKED_UNSUPPORTED_FAMILY_MAPPING` で止める。
5. source rows / required columns が足りない candidate は `BLOCKED_NO_SYMBOL_DATA` または `BLOCKED_MISSING_SOURCE_COLUMNS` で止める。
6. backtest pack は候補別 out dir へ生成し、pack validation result を bridge manifest に保存する。
7. bridge manifest は candidate id、candidate set hash、export manifest hash、ledger hash、candidate-scoped artifacts、boundary false を持つ。

Perp 用 feature / quote / cost-estimate mapping は `prep-watchdeck` 互換 source root を local source として使う。ただし、候補の symbol / timeframe / horizon に必要な履歴が materialize できない場合や、実測 order-book slippage を要求する場合は blocker になります。blocker を返すことも C9 v0 の正しい完了動作に含める。

### Not Full Bridge

次は C9 v0 Prep Watchdeck bridge または full bridge ではない。

- `strategy_idea.v1` draft export だけ。
- `strategy-intake-validate` が通ることだけ。
- `authoring_preflight.json` が Strategy Authoring / backtest readiness gap を列挙すること。
- `strategy-idea-candidates-perp-estimate` が `crypto_perp_tournament_rows.v2` estimate を作ること。
- 手順書、Markdown review、operator memo だけ。
- 既存 backtest pack が別経路で存在するだけ。
- `strategy-backtest-pack` の default example spec / suite / bundle が通ること。
- paper observation、tiny live shadow、actual cash report、live readiness の許可。

### Completion Test

C9 v0 を完了扱いにする最小条件は、fixture で次が通ること。

1. candidate set build。
2. shortlist export。
3. `strategy-intake-validate`。
4. bridge manifest generation。
5. `strategy_authoring_spec.v1` generation or explicit machine-readable rejection。
6. `strategy_authoring_spec.v1` を生成した candidate の Strategy Authoring validation。
7. backtest pack generation or explicit machine-readable blocker。
8. backtest pack を生成した candidate の backtest pack validation。
9. source refs に candidate set / ledger / authoring / backtest hashes が残ること。
10. paper/live/wallet/signing/exchange-write boundary が false のまま維持されること。

追加で、次の negative tests を必須にする。

- unsupported family は explicit blocker になり、backtest pack を成功扱いしない。
- free-text `signal_expression` は実行・ad-hoc parse されない。
- Bitget USDT-FUTURES candidate は TradeXYZ / QQQ example data に暗黙変換されない。
- source rows / required columns が無い場合は `BLOCKED_NO_SYMBOL_DATA` または `BLOCKED_MISSING_SOURCE_COLUMNS` になる。
- default `strategy-backtest-pack` artifact を candidate proof として参照しない。
- `BRIDGED` でも paper/live/wallet/signing/exchange-write flags は false のまま。

## Next Goal

残っている正確なゴール:

- C9 v0 の実データ適用で、candidate ごとの blocker / pack result を review workflow に接続する。
- C9 の generic family mapping を増やす場合は、free-text `signal_expression` parsing ではなく family / parameter allowlist を拡張する。
- Perp funding / fee / slippage / liquidation の実測 evaluator を作る場合は、actual cash proof と estimate artifact を混ぜない。

検証:

- `uv run pytest tests/strategy_idea_candidates -q`
- `uv run pytest tests/backtest tests/strategy_authoring -q`
- `uv run sis strategy-idea-candidates-authoring-bridge --help`
- `uv run python scripts/check_current_docs.py`
- `uv run python scripts/check_cli_catalog.py`
- `git diff --check`

## Non-Goals

- 実 market data から alpha を証明すること。
- ML / LLM API / optimizer を導入すること。
- `strategy_idea.v1` schema を広げること。
- AI score、AI同意、複数AI一致を採用許可にすること。
- Bitget spot、spot margin、wallet、signing、exchange write、live order を扱うこと。
- paper / live / order preview / wallet / signing / exchange write を許可すること。

## Stop Conditions

- input validation が `PASS` ではない。
- source hash、available-at、max observed timestamp、label window、prediction horizon が candidate set に残せない。
- selected-only artifact になり、rejected inventory が消える。
- duplicate rejection が silent drop になる。
- raw metric を発見、証明、採用理由として扱う必要が出る。
- `strategy_idea.v1` に candidate set provenance を入れないと成立しない設計になる。
- 新依存や外部 API がないと C9 v0 を通せない。
