<!--
作成日: 2026-05-25_19:45 JST
更新日: 2026-07-03_12:09 JST
-->

# Current State

この文書は `marketlens-strike` の現在地を短く読むための入口です。実装の正本は `src/`、`tests/`、`schemas/`、`configs/`、`scripts/`、CLI help、生成済み artifact です。

## 結論

- 現在の開発主軸は backtest-first / venue-neutral。Trade[XYZ] は実装済みの主要 venue だが、当面の注文口前提にはしない。
- 技術者向けではない利用者目線の説明は [APP_USER_GUIDE_NON_TECHNICAL_2026-06-20.md](APP_USER_GUIDE_NON_TECHNICAL_2026-06-20.md) を読む。
- アプリの全体像、できること、できないこと、専門用語の説明を一枚で読む場合は [APP_CURRENT_STATE_DETAILED_2026-06-20.md](APP_CURRENT_STATE_DETAILED_2026-06-20.md) を読む。
- 個人向け・利益目線で誤読しやすい点を見る場合は [AGENT_ASSESSMENT_INDIVIDUAL_TRADER_2026-06-20.md](AGENT_ASSESSMENT_INDIVIDUAL_TRADER_2026-06-20.md) と [AGENT_ASSESSMENT_PRACTICAL_DECISION_NOTE_2026-06-20.md](AGENT_ASSESSMENT_PRACTICAL_DECISION_NOTE_2026-06-20.md) を読む。どちらも正本ではなく判断補助です。
- いま使える主要 surface は Crypto Perp Truth-Cycle MVP artifact chain / Strategy Lab / Strategy Authoring / backtest pack / Strategy Review / NDX local research gates / read-only Trade[XYZ] / paper operations / operations audit。詳細は [IMPLEMENTED_SURFACES.md](IMPLEMENTED_SURFACES.md) を読む。
- AI / Codex が戦略作成と backtest を迷わず扱う入口は [AI_AGENT_STRATEGY_BACKTEST_GUIDE.md](AI_AGENT_STRATEGY_BACKTEST_GUIDE.md) を読む。
- 人間が戦略、YAML、backtest 結果、次の確認を専門用語少なめで読む入口は [STRATEGY_AND_BACKTEST_USER_GUIDE.md](STRATEGY_AND_BACKTEST_USER_GUIDE.md) を読む。
- プログラム構造ではなく、純粋に「何ができるか」と目的、背景、期待成果物を読む場合は [FEATURE_CAPABILITY_SUMMARY_2026-06-27.md](FEATURE_CAPABILITY_SUMMARY_2026-06-27.md) を読む。
- 戦略アイディアを発想する仕組みを非技術者向けに読む場合は [strategy_idea_candidates/NON_TECHNICAL_OVERVIEW_2026-06-28.md](strategy_idea_candidates/NON_TECHNICAL_OVERVIEW_2026-06-28.md) を読む。
- 入力データから戦略アイデア候補を作る新機能の現実的な調査、外部研究、Kaggle / Numerai からの制約、実装順を見る場合は [STRATEGY_IDEA_GENERATION_RESEARCH_2026-06-27.md](STRATEGY_IDEA_GENERATION_RESEARCH_2026-06-27.md) を読む。
- 戦略アイデア候補生成を実装する直前の現実的な境界、用語衝突、schema 必須項目、依存関係の修正判断を見る場合は [STRATEGY_IDEA_GENERATION_PRE_IMPLEMENTATION_AUDIT_2026-06-27.md](STRATEGY_IDEA_GENERATION_PRE_IMPLEMENTATION_AUDIT_2026-06-27.md) を読む。
- candidate generation pipeline の最終ゴールまでの checkpoint、順序、合格条件、停止条件を見る場合は [STRATEGY_IDEA_CANDIDATE_PIPELINE_CHECKPOINTS_2026-06-27.md](STRATEGY_IDEA_CANDIDATE_PIPELINE_CHECKPOINTS_2026-06-27.md) を読む。
- 実装済みの pre-intake candidate set contract、writer、blocked input-evidence artifact、shortlist export sidecar を見る場合は [strategy_idea_candidates/README.md](strategy_idea_candidates/README.md) を読む。
- Profit Core / Reality Check の次に直す1箇所を見る場合は `uv run sis profit-core-reality-check` を使う。これは既存 candidate / search ledger / C9 bridge / profit-readiness / risk / actual-cash artifact を読むだけで、missing artifact生成、actual-cash代用、demo/testnet、外部API、live permission は行わない。
- 戦略アイデア候補生成をより良くする依存関係の採否、追加順、optional extra 境界を見る場合は [STRATEGY_IDEA_GENERATION_DEPENDENCY_RESEARCH_2026-06-27.md](STRATEGY_IDEA_GENERATION_DEPENDENCY_RESEARCH_2026-06-27.md) を読む。
- backtest 結果を HTML / JS で見る入口は `uv run sis strategy-backtest-html-report`。生成先は `data/reports/strategy_backtest_html_report.html` と `data/research/backtest_html_report/strategy_backtest_html_report.json`。
- 専門用語を減らして「できること / できないこと」を読む場合は [REPO_CAPABILITIES_PLAIN_JA_2026-06-17.md](REPO_CAPABILITIES_PLAIN_JA_2026-06-17.md) を読む。
- 実務的な次方向と外部入力時の再確認は [NEXT_DIRECTION_CURRENT.md](NEXT_DIRECTION_CURRENT.md) を読む。
- Crypto Perp の日常運用は [runbooks/CRYPTO_PERP_TRUTH_CYCLE_RUNBOOK.md](runbooks/CRYPTO_PERP_TRUTH_CYCLE_RUNBOOK.md) を読む。利益判断用の追加層は [crypto_perp/PROFIT_READINESS_SURFACE_INVENTORY_2026-06-27.md](crypto_perp/PROFIT_READINESS_SURFACE_INVENTORY_2026-06-27.md) と [crypto_perp/PROFIT_READINESS_ACCEPTANCE_VOCABULARY.md](crypto_perp/PROFIT_READINESS_ACCEPTANCE_VOCABULARY.md) を読む。`crypto-perp-risk-taker-review` は existing local artifacts から human risk review 用の分類 artifact を作るだけで、live permission ではない。実装済み plan package は [../plan/archive/2026-06-22-crypto-perp-mvp-implemented/marketlens-strike-crypto-perp-mvp-final-plan-2026-06-20/00_READ_ME_FIRST.md](../plan/archive/2026-06-22-crypto-perp-mvp-implemented/marketlens-strike-crypto-perp-mvp-final-plan-2026-06-20/00_READ_ME_FIRST.md) に historical implementation contract として移動済みです。
- `READ_ONLY_GO`、Strategy Review の `READY_FOR_HUMAN_REVIEW`、backtest pack validation `PASS` は、paper execution permission、alpha proof、live readiness ではない。
- `data/` は runtime / generated state。fresh checkout では必要な artifact を再生成する。

## 現在できること

| 目的 | 読むもの |
|---|---|
| 技術者向けではない利用者目線で読む | [APP_USER_GUIDE_NON_TECHNICAL_2026-06-20.md](APP_USER_GUIDE_NON_TECHNICAL_2026-06-20.md) |
| アプリの全体像、できること、専門用語を詳しく知る | [APP_CURRENT_STATE_DETAILED_2026-06-20.md](APP_CURRENT_STATE_DETAILED_2026-06-20.md) |
| 個人トレーダー目線の現実的な評価を読む | [AGENT_ASSESSMENT_INDIVIDUAL_TRADER_2026-06-20.md](AGENT_ASSESSMENT_INDIVIDUAL_TRADER_2026-06-20.md) |
| 利益目線でPASSやSharpeの誤読を避ける | [AGENT_ASSESSMENT_PRACTICAL_DECISION_NOTE_2026-06-20.md](AGENT_ASSESSMENT_PRACTICAL_DECISION_NOTE_2026-06-20.md) |
| 実装済み surface を確認する | [IMPLEMENTED_SURFACES.md](IMPLEMENTED_SURFACES.md) |
| AI が戦略作成 / backtest を安全に操作する | [AI_AGENT_STRATEGY_BACKTEST_GUIDE.md](AI_AGENT_STRATEGY_BACKTEST_GUIDE.md) |
| 人間が戦略 / backtest 結果を理解する | [STRATEGY_AND_BACKTEST_USER_GUIDE.md](STRATEGY_AND_BACKTEST_USER_GUIDE.md) |
| 機能の目的、背景、期待成果物を読む | [FEATURE_CAPABILITY_SUMMARY_2026-06-27.md](FEATURE_CAPABILITY_SUMMARY_2026-06-27.md) |
| 戦略アイディア発想の仕組みを非技術者向けに読む | [strategy_idea_candidates/NON_TECHNICAL_OVERVIEW_2026-06-28.md](strategy_idea_candidates/NON_TECHNICAL_OVERVIEW_2026-06-28.md) |
| 戦略アイデア候補の自動生成を作るか判断する | [STRATEGY_IDEA_GENERATION_RESEARCH_2026-06-27.md](STRATEGY_IDEA_GENERATION_RESEARCH_2026-06-27.md) |
| 戦略アイデア候補生成の実装直前に、誤読・抜け・禁止事項を確認する | [STRATEGY_IDEA_GENERATION_PRE_IMPLEMENTATION_AUDIT_2026-06-27.md](STRATEGY_IDEA_GENERATION_PRE_IMPLEMENTATION_AUDIT_2026-06-27.md) |
| candidate generation pipeline の checkpoint を見る | [STRATEGY_IDEA_CANDIDATE_PIPELINE_CHECKPOINTS_2026-06-27.md](STRATEGY_IDEA_CANDIDATE_PIPELINE_CHECKPOINTS_2026-06-27.md) |
| 実装済み candidate set contract と export sidecar を見る | [strategy_idea_candidates/README.md](strategy_idea_candidates/README.md) |
| Profit Core / Reality Check の次blockerを読む | `uv run sis profit-core-reality-check` |
| 戦略アイデア候補生成に依存関係を足すか判断する | [STRATEGY_IDEA_GENERATION_DEPENDENCY_RESEARCH_2026-06-27.md](STRATEGY_IDEA_GENERATION_DEPENDENCY_RESEARCH_2026-06-27.md) |
| backtest 結果をHTMLで見る | `uv run sis strategy-backtest-html-report` |
| 技術詳細の capability catalog を見る | [REPO_CAPABILITIES_CURRENT_2026-06-16.md](REPO_CAPABILITIES_CURRENT_2026-06-16.md) |
| public CLI command catalog を見る | [REPO_CLI_CATALOG_CURRENT_2026-06-17.md](REPO_CLI_CATALOG_CURRENT_2026-06-17.md) |
| docs とディレクトリ構造の現在だけを読む | [CURRENT_DOCS_AND_STRUCTURE_TRIAGE_2026-06-27.md](CURRENT_DOCS_AND_STRUCTURE_TRIAGE_2026-06-27.md) |
| Strategy Lab / Strategy Authoring を使う | [strategy_research_lab/README.md](strategy_research_lab/README.md) |
| backtest pack / optional framework / robustness を見る | [backtest/README.md](backtest/README.md) |
| Strategy Review packet と operator record を使う | [strategy_review/README.md](strategy_review/README.md) |
| NDX local research gates を見る | [research/ndx/README.md](research/ndx/README.md) |
| Strategy Lifecycle / paper observation status を見る | [strategy_lifecycle/README.md](strategy_lifecycle/README.md) |
| venue capability boundary を見る | [venues/read_only_capability_probe.md](venues/read_only_capability_probe.md) |
| operator 手順を見る | [OPERATIONS_RUNBOOK.md](OPERATIONS_RUNBOOK.md) と [runbooks/README.md](runbooks/README.md) |
| Crypto Perp のeventからtournament reportまでを再生成する | [runbooks/CRYPTO_PERP_TRUTH_CYCLE_RUNBOOK.md](runbooks/CRYPTO_PERP_TRUTH_CYCLE_RUNBOOK.md) |
| Crypto Perp のsource availability / cost-adjusted estimate / risk-taker review / shadow preflightを読む | [crypto_perp/PROFIT_READINESS_SURFACE_INVENTORY_2026-06-27.md](crypto_perp/PROFIT_READINESS_SURFACE_INVENTORY_2026-06-27.md) |
| Crypto Perp Truth-Cycle MVP の実装履歴を読む | [../plan/archive/2026-06-22-crypto-perp-mvp-implemented/marketlens-strike-crypto-perp-mvp-final-plan-2026-06-20/07_TASK_CHAIN.yaml](../plan/archive/2026-06-22-crypto-perp-mvp-implemented/marketlens-strike-crypto-perp-mvp-final-plan-2026-06-20/07_TASK_CHAIN.yaml) |

## 境界

- `VenueId` は現行 schema では `trade_xyz` と `bitget_demo`。`bitget_futures` と `hyperliquid_perp` は catalog-only / disabled。
- `bitget_demo` は demo execution surface。production Bitget live readiness ではない。
- Trade[XYZ] read-only execution state collection は public user address と明示 opt-in がある時だけ外部 `/info` read を行う。wallet、signing、exchange write、live order は使わない。
- `PaperIntentPreview` は paper-only の仮注文意図。live order として扱わない。
- Strategy Review は existing artifact を読む human-review packet と operator decision record。paper execution や live trading を許可しない。
- NDX Layer 2.2-2.8 は local research / paper-observation gate。alpha、account readiness、wallet readiness、exchange-write readiness を証明しない。
- `micro_live` 系 code は存在するが、標準 operator CLI の live execution surface としては exposed していない。

## まだ証明していないこと

- production live order smoke。
- signing / wallet / exchange write integration。
- Bitget credentialed read-only network smoke。
- Bitget demo order lifecycle。
- live order preview / 注文候補生成の正式 command surface。
- Alpaca credentials ありの API connectivity smoke。
- Strategy Review や backtest validation からの paper / live permission。
- Crypto Perp Truth-Cycle MVP は M11 時点で Bitget public provider probe、immutable raw snapshot、probe audit、raw refresh、universe diff、ticker market snapshot、15m candle finality、gap / non-final bar quality guard、slow / fast / near-miss event detection、direction-neutral event artifact、event card rendering、candidate-only raw-first WS capture manifest、book checksum / sequence guard、atomic gzip JSONL segments、prospective decision ledger、matured outcome ledger、Tardis-style parser/book/VWAP golden fixture、OSS adoption notes、pybotters separate spike workspace、Freqtrade external sidecar boundary、Hummingbot Bitget connector notes、credential redaction、read-only account snapshot、non-writing order preview、deterministic clientOid、mock-only tiny live measurement gate、query-before-resubmit state logic、reduce-only close preview、flat reconciliation、actual cash ledger、direction-neutral execution replay、actual vs simulated fill bias calibration、REVERSAL_SHORT / CONTINUATION_LONG / NO_TRADE tournament、outcome before-cost proxy tournament rows preview、tournament gate decision、truth-cycle status、local-only next steps、stage checklist、fixture-only dogfood pack、Daily Brief first next-step / first stage blocker indexing、Workbench Viewer false-only permission summary、`crypto-perp-probe-audit` / `crypto-perp-raw-refresh` / `crypto-perp-decision-record` / `crypto-perp-outcome-record` / `crypto-perp-tournament-rows-preview` / `crypto-perp-tournament-report` / `crypto-perp-tournament-gate` / `crypto-perp-truth-cycle-status` / `crypto-perp-truth-cycle-dogfood-pack` CLI、Strategy Input Contract export、Strategy Workbench Viewer compact summary までです。Profit-readiness 追加層として `crypto-perp-source-availability`、`crypto-perp-replay-slice`、`crypto-perp-feature-pack`、`crypto-perp-edge-score`、`crypto-perp-tournament-rows-v2`、`crypto-perp-bias-guard`、`crypto-perp-risk-taker-review`、`crypto-perp-tiny-live-shadow` も local artifact として使えます。M09 の実ネットワーク測定は未実行です。
- Crypto Perp の tiny live measurement 実行。M09 の実ネットワーク実行は別の明示承認、isolated margin、withdrawal disabled API key、IP restriction、max notional 25 USD、flat reconciliation が揃うまで行わない。

## 外部入力待ち

- Trade[XYZ] execution state collection: `SIS_TRADE_XYZ_EXECUTION_STATE_USER_ADDRESS=<public-user-address>` と `SIS_TRADE_XYZ_EXECUTION_STATE_COLLECTOR_ENABLED=1` が必要。
- Bitget demo read-only network smoke: `BITGET_DEMO_API_KEY`、`BITGET_DEMO_API_SECRET`、`BITGET_DEMO_PASSPHRASE` が必要。
- normal paper observation: 新しい trading day を含む evidence が必要。同日 artifact の再実行だけでは normal observation の日数は増えない。

外部入力が来た時は [NEXT_DIRECTION_CURRENT.md](NEXT_DIRECTION_CURRENT.md) の `External Input Restart Checklist` を読む。

## Source Of Truth

優先順位:

1. `src/`, `tests/`, `configs/`, `schemas/`, `scripts/`
2. CLI help: `uv run sis --help`
3. generated runtime artifacts under `data/`
4. tracked docs under `docs/`
5. `plan/` historical planning records
6. `docs/archive/` and `plan/archive/`

archive 配下は historical context です。現行判断の正本にはしません。

## Recommended Read Order

1. [CURRENT_STATE.md](CURRENT_STATE.md)
2. [APP_USER_GUIDE_NON_TECHNICAL_2026-06-20.md](APP_USER_GUIDE_NON_TECHNICAL_2026-06-20.md)
3. [APP_CURRENT_STATE_DETAILED_2026-06-20.md](APP_CURRENT_STATE_DETAILED_2026-06-20.md)
4. [AGENT_ASSESSMENT_INDIVIDUAL_TRADER_2026-06-20.md](AGENT_ASSESSMENT_INDIVIDUAL_TRADER_2026-06-20.md)
5. [AGENT_ASSESSMENT_PRACTICAL_DECISION_NOTE_2026-06-20.md](AGENT_ASSESSMENT_PRACTICAL_DECISION_NOTE_2026-06-20.md)
6. [AI_AGENT_STRATEGY_BACKTEST_GUIDE.md](AI_AGENT_STRATEGY_BACKTEST_GUIDE.md)
7. [STRATEGY_AND_BACKTEST_USER_GUIDE.md](STRATEGY_AND_BACKTEST_USER_GUIDE.md)
8. [FEATURE_CAPABILITY_SUMMARY_2026-06-27.md](FEATURE_CAPABILITY_SUMMARY_2026-06-27.md)
9. [strategy_idea_candidates/NON_TECHNICAL_OVERVIEW_2026-06-28.md](strategy_idea_candidates/NON_TECHNICAL_OVERVIEW_2026-06-28.md)
10. [STRATEGY_IDEA_GENERATION_RESEARCH_2026-06-27.md](STRATEGY_IDEA_GENERATION_RESEARCH_2026-06-27.md)
11. [STRATEGY_IDEA_GENERATION_PRE_IMPLEMENTATION_AUDIT_2026-06-27.md](STRATEGY_IDEA_GENERATION_PRE_IMPLEMENTATION_AUDIT_2026-06-27.md)
12. [STRATEGY_IDEA_CANDIDATE_PIPELINE_CHECKPOINTS_2026-06-27.md](STRATEGY_IDEA_CANDIDATE_PIPELINE_CHECKPOINTS_2026-06-27.md)
13. [strategy_idea_candidates/README.md](strategy_idea_candidates/README.md)
14. [STRATEGY_IDEA_GENERATION_DEPENDENCY_RESEARCH_2026-06-27.md](STRATEGY_IDEA_GENERATION_DEPENDENCY_RESEARCH_2026-06-27.md)
15. [REPO_CAPABILITIES_PLAIN_JA_2026-06-17.md](REPO_CAPABILITIES_PLAIN_JA_2026-06-17.md)
16. [CODE_STATUS.md](CODE_STATUS.md)
17. [IMPLEMENTED_SURFACES.md](IMPLEMENTED_SURFACES.md)
18. [NEXT_DIRECTION_CURRENT.md](NEXT_DIRECTION_CURRENT.md)
19. [CURRENT_DOCS_AND_STRUCTURE_TRIAGE_2026-06-27.md](CURRENT_DOCS_AND_STRUCTURE_TRIAGE_2026-06-27.md)
20. [backtest/README.md](backtest/README.md)
21. [strategy_review/README.md](strategy_review/README.md)
22. [strategy_review/OPERATOR_REVIEW_PACKET_RECIPE.md](strategy_review/OPERATOR_REVIEW_PACKET_RECIPE.md)
23. [research/ndx/README.md](research/ndx/README.md)
24. [strategy_lifecycle/README.md](strategy_lifecycle/README.md)
25. [OPERATIONS_RUNBOOK.md](OPERATIONS_RUNBOOK.md)
26. [plan/README.md](../plan/README.md)

## Verification

固定の pass count はこの文書に置かない。作業時点で次を再実行する。

```bash
uv run python -V
uv run sis --help
uv run python scripts/check_cli_catalog.py
uv run python scripts/check_current_docs.py
./scripts/check
```

runtime artifact を更新する場合:

```bash
uv run sis phase-gate-review
uv run sis strategy-paper-observation-status
uv run sis refresh-operations-artifacts
```
