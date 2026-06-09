<!--
作成日: 2026-06-09_16:13 JST
更新日: 2026-06-09_16:13 JST
-->

# Document Audit 2026-06-09 NDX/QQQ Venue Suitability Refresh

この監査は、コードを正本として NDX/QQQ family の paper-path fail-closed 境界を docs に反映した記録です。

## Code Truth

- `src/sis/venues/suitability.py` が venue suitability catalog の正本。
- current `VenueId` は `src/sis/venues/ids.py` の `trade_xyz` / `bitget_demo`。
- `bitget_futures` と `hyperliquid_perp` は catalog-only で、Strategy Lab artifact schema には入らない。
- NDX/QQQ family は research/backtest record として保持できる。
- NDX/QQQ family は current paper path では `PaperCandidatePack.selected_candidate_ids`、`PaperIntentPreview`、raw `paper-from-intents` JSON、legacy `paper-step` order generation で fail closed する。

## 更新したドキュメント

| Path | 更新内容 |
|---|---|
| `README.md` | Read First に本監査を追加し、NDX/QQQ venue-suitability hardening 後の verification snapshot へ更新 |
| `docs/CURRENT_STATE.md` | catalog-only venues、NDX/QQQ paper-path block、legacy `paper-step` metrics を追記 |
| `docs/CODE_STATUS.md` | Post-PR08 status に NDX/QQQ venue suitability paper-path gate を追加 |
| `docs/ARCHITECTURE_AND_PHASES.md` | `src/sis/venues/suitability` と Strategy Lab boundary を追記 |
| `docs/OPERATIONS_RUNBOOK.md` | Strategy Lab / legacy `paper-step` の stop condition を更新 |
| `docs/STRATEGY_RESEARCH_LAB_DOC_AUDIT_AND_SPEC_2026-05-30.md` | selected candidate、paper intent、raw JSON 再検証の実装境界を更新 |
| `docs/strategy_research_lab/01_SCHEMA_CONTRACTS_FOR_TRADING_STRATEGIES.md` | venue suitability、selected candidate guard、paper-intent guard を追加 |
| `docs/strategy_research_lab/04_PAPER_PROMOTION_AND_INTENT_SPEC.md` | promotion 前 validation と raw intent JSON 迂回防止を追加 |
| `docs/strategy_research_lab/05_OPERATOR_RUNBOOK.md` | candidate pack の selected/rejected 読み方を更新 |
| `docs/strategy_research_lab/07_VALIDATION_STOP_CONDITIONS_AND_TEST_MATRIX.md` | venue suitability と legacy `paper-step` の test matrix を追加 |
| `docs/strategy_research_lab/08_CURRENT_CAPABILITIES.md` | paper-only preview の可能範囲を venue-suitable 候補に限定 |
| `docs/strategy_research_lab/09_STRATEGY_AUTHOR_GUIDE.md` | promote 後も suitability block で intent が空になる場合を追記 |
| `plan/0609ここからの計画/01_ndx_qqq_venue_suitability_gate/` | 実装後 hardening を含む task / test / acceptance / handoff へ更新 |

## 古い内容があるが残すドキュメント

| Path | 扱い |
|---|---|
| `docs/backtest/BACKTEST_FIRST_VENUE_NEUTRAL_PIVOT_PLAN_2026-06-05.md` | 実装前後の pivot plan。現行 paper routing 可否の正本にはしない |
| `docs/DOCUMENT_AUDIT_2026-05-31.md` | 過去の docs audit。現在判断は本監査と current docs を優先 |
| `docs/DOCUMENT_AUDIT_2026-05-31_BACKTEST_UPDATE.md` | backtest 更新時点の履歴監査。NDX/QQQ venue suitability までは含まない |
| `docs/DOCUMENT_AUDIT_2026-06-09_NDX_2_3_2_4_REFRESH.md` | NDX Layer 2.3/2.4 local research gate の監査。paper-path suitability 監査とは別物 |
| `docs/archive/**` | historical context。current proof として読まない |
| `plan/archive/**` | historical migration contract。current proof として読まない |

## 作り直したほうがよいドキュメント

| Path | 理由 |
|---|---|
| `docs/trade_xyz_bot_beginner_guide.html` | 初心者向け HTML で現在も有用だが、current venue suitability / NDX/QQQ paper-path block を体系的に説明するには再生成または部分作り直しが必要 |
| `docs/strategy_research_lab/08_CURRENT_CAPABILITIES_EXPLAINED.html` | `08_CURRENT_CAPABILITIES.md` の companion HTML。Markdown 側を正として、次回ユーザー向け説明を更新する時に再生成する |

## 削除・アーカイブしてもよいドキュメント

- active current docs から今回ただちに削除すべきものはない。
- `docs/archive/**` と `plan/archive/**` はすでに archive 役割を持つため、追加移動は不要。
- 将来 `docs/trade_xyz_bot_beginner_guide.html` を再生成した場合、旧 HTML は `docs/archive/` へ移してよい。

## 完了条件

- current docs が NDX/QQQ family を paper/live ready と読ませない。
- `bitget_futures` / `hyperliquid_perp` を current `VenueId` と誤読させない。
- `data/research/signals.csv` を Strategy Lab 正本と誤読させない。
- `PaperIntentPreview` を live order と誤読させない。
- legacy `paper-step` が NDX/QQQ family を止めることを運用 docs から追える。
