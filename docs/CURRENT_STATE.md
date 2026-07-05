<!--
作成日: 2026-05-25_19:45 JST
更新日: 2026-07-05_11:55 JST
-->

# Current State

## 結論

`marketlens-strike` の現在地は、backtest-first / venue-neutral の research and evidence workspace です。

現行の次方向は [CURRENT_GOAL_AND_DIRECTION_2026-07-05.md](CURRENT_GOAL_AND_DIRECTION_2026-07-05.md) に集約しました。docs の読み分けは [CURRENT_DOCS_INDEX_2026-07-05.md](CURRENT_DOCS_INDEX_2026-07-05.md) を使います。

## Source Of Truth

実装の正本は docs ではありません。優先順位は次です。

1. `src/`, `tests/`, `schemas/`, `configs/`, `scripts/`
2. CLI help: `uv run sis --help`
3. generated runtime artifacts under `data/`
4. tracked current docs under `docs/`
5. `plan/` historical planning records
6. `docs/archive/` and `plan/archive/`

archive と historical plan は、現在の status、readiness、許可判断の根拠にしません。

## いま使える主要 surface

| 領域 | 現在の入口 |
|---|---|
| 実装済み surface map | [IMPLEMENTED_SURFACES.md](IMPLEMENTED_SURFACES.md) |
| app overview | [APP_CURRENT_STATE_OVERVIEW_2026-07-05.md](APP_CURRENT_STATE_OVERVIEW_2026-07-05.md) |
| 用語 | [APP_TERMS_GLOSSARY_2026-07-05.md](APP_TERMS_GLOSSARY_2026-07-05.md) |
| artifact / code / schema reference | [CURRENT_ARTIFACT_SURFACE_REFERENCE_2026-07-05.md](CURRENT_ARTIFACT_SURFACE_REFERENCE_2026-07-05.md) |
| Crypto Perp no-actual-cash endpoint | [crypto_perp/BACKTEST_CANDIDATE_PACK_V1.md](crypto_perp/BACKTEST_CANDIDATE_PACK_V1.md) |
| Strategy Idea Candidate pipeline | [strategy_idea_candidates/README.md](strategy_idea_candidates/README.md) |
| Backtest | [backtest/README.md](backtest/README.md) |
| Strategy Review | [strategy_review/README.md](strategy_review/README.md) |
| Strategy Lab / Authoring | [strategy_research_lab/README.md](strategy_research_lab/README.md) |
| NDX local research gates | [research/ndx/README.md](research/ndx/README.md) |
| Runbooks | [runbooks/README.md](runbooks/README.md) |
| Venue boundary | [venues/read_only_capability_probe.md](venues/read_only_capability_probe.md) |

Backtest 結果を HTML / JS で見る入口は `uv run sis strategy-backtest-html-report`。生成先は `data/reports/strategy_backtest_html_report.html` と `data/research/backtest_html_report/strategy_backtest_html_report.json`。

## 現在の方向

- C9 bridge は shortlisted candidate を candidate-scoped Strategy Authoring / backtest pack へ fail-closed に接続する。
- Bitget public source refresh と ticker-aware source availability は local source quality を上げるために使う。
- `crypto-perp-backtest-candidate-pack` は actual cash なしの短期終着点として使う。
- `NO_TRADE`、missing source、sample insufficient、unsupported mapping は正式な停止結果として残す。
- Strategy Review、Workbench、NDX gates は判断材料であり、paper/live permission ではない。

## 境界

- `VenueId` は現行 schema では `trade_xyz` と `bitget_demo`。
- `bitget_futures` と `hyperliquid_perp` は catalog-only / disabled。
- `bitget_demo` は demo execution surface。production Bitget live readiness ではない。
- Trade[XYZ] は実装済みの read-only / historical venue context。default product axis ではない。
- Strategy Review は human-review packet と operator decision record。paper execution や live trading を許可しない。
- NDX Layer 2.2-2.8 は local research / paper-observation gate。alpha、account readiness、wallet readiness、exchange-write readiness を証明しない。
- `micro_live` 系 code は存在するが、標準 operator CLI の live execution surface としては exposed していない。
- `data/` は runtime / generated state。fresh checkout では必要な artifact を再生成する。

## まだ証明していないこと

- production live order smoke。
- signing / wallet / exchange write integration。
- Bitget credentialed read-only network smoke。
- Bitget demo order lifecycle。
- live order preview / 注文候補生成の正式 command surface。
- Alpaca credentials ありの API connectivity smoke。
- Strategy Review や backtest validation からの paper / live permission。
- Crypto Perp の actual cash profit。
- Crypto Perp の tiny live measurement 実行。

## 外部入力待ち

Trade[XYZ] execution state collection:

- `SIS_TRADE_XYZ_EXECUTION_STATE_USER_ADDRESS=<public-user-address>`
- `SIS_TRADE_XYZ_EXECUTION_STATE_COLLECTOR_ENABLED=1`

Bitget demo read-only network smoke:

- `BITGET_DEMO_API_KEY`
- `BITGET_DEMO_API_SECRET`
- `BITGET_DEMO_PASSPHRASE`

normal paper observation:

- 新しい trading day を含む evidence が必要。同日 artifact の再実行だけでは normal observation の日数は増えない。

外部入力が来た時は [NEXT_DIRECTION_CURRENT.md](NEXT_DIRECTION_CURRENT.md) の `External Input Restart Checklist` を読む。

## Verification

固定の pass count はこの文書に置かない。作業時点で次を再実行する。

```bash
uv run python -V
uv run sis --help
uv run python scripts/check_cli_catalog.py
uv run python scripts/check_current_docs.py
./scripts/check
```
