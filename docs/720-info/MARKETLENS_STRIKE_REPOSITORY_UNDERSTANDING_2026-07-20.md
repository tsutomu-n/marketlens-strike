<!--
作成日: 2026-07-20_19:33 JST
更新日: 2026-07-20_19:40 JST
-->

# MarketLens Strike Repository Understanding 2026-07-20

## 0. 文書の目的

この文書は、`marketlens-strike`を新しく担当する開発者が、repoの目的、実装構造、データフロー、安全境界、現在のGit状態、利用可能なsurface、未証明事項、検証状態、再開時の注意を一つの文書から理解できるようにするための調査報告である。

調査日時は`2026-07-20_19:33 JST`。調査対象は主に次の二つである。

- local checkout: `/home/tn/projects/marketlens-strike`, branch `main`, HEAD `590c5855e0e4347f13ce07c9adccf28910624d8a`
- local remote-tracking ref: `origin/main`, HEAD `427de2b62ebb21a613793aee92b1d49bbe69e09c`

外部networkの再取得は行っていない。`origin/main`は調査時点でlocal repositoryが保持していたremote-tracking refである。

## 1. 最重要結論

### 1.1 Repoの本質

`marketlens-strike`はproduction自動売買アプリではない。Python 3.13のCLIを入口に、戦略仮説、市場データ、backtest、review、paper observation、operations evidenceを再現可能なartifactとして生成・検証するresearch and evidence workspaceである。

主目的は「注文を出すこと」ではなく、次をfail-closedに確認することである。

- 入力データの出所、期間、時刻、欠損、利用可能時点
- 仮説やcandidateのidentityとlineage
- backtestの前提、費用、no-lookahead、sample不足、頑健性
- `NO_TRADE`を含む比較と停止判断
- human reviewのためのpacketとdecision record
- paper-onlyまたはread-only段階の運用証跡
- live、wallet、signing、exchange writeへ誤って昇格しないpermission boundary

### 1.2 現在の主軸

repo-local guideとcurrent docs上の既定軸はbacktest-first / venue-neutralである。Crypto Perpは現在もっとも厚い実装・artifact chainを持つ具体的な検証対象だが、core全体をBitgetまたは単一venue専用にする設計ではない。

Trade[XYZ]は実装済みのhistorical/read-only venue contextとして残るが、default product axisでも主要な次アクションでもない。

### 1.3 現在の最大注意点

local `main`と`origin/main`は分岐している。

```text
local main 590c585
  590c585 Fix typo in Seed Foundry Core plan section heading
  64ac82c Add execution replay design and portfolio capacity spike plan
  80d20ba Add graphify knowledge graph integration and ignore hypothesis state

origin/main 427de2b
  427de2b Implement Seed Foundry A1 technical walking product (#48)
  c8c950d docs: organize Seed Foundry Core v1 plans by chunk (#45)
```

調査時点の表示は`main...origin/main [ahead 3, behind 2]`である。

local checkoutにはgraphifyと大規模な計画文書がある。一方、`origin/main`にはSeed Foundry A1の実コード、schema、fixture、test、CLIがある。local checkoutの`src/sis/`だけを見て「A1は未実装」と判断するのも、HANDOFFだけを見て「local mainにもA1がある」と判断するのも誤りである。

## 2. 調査方法と証拠の優先順位

### 2.1 使用した証拠

- `AGENTS.md`
- `.ai_memory/HANDOFF.md`
- A1 worktree側の`.ai_memory/HANDOFF.md`
- `git status`, `git log`, `git diff`, `git ls-tree`, `git show`
- `src/sis/`
- `tests/`
- `schemas/`
- `configs/`
- `pyproject.toml`, `.python-version`, `uv.lock`
- `.github/workflows/ci.yml`, `scripts/check`, current-doc checker, CLI catalog checker
- `uv run sis --help`
- `data/`配下の主要artifact
- `graphify-out/graph.json`, `graphify-out/GRAPH_REPORT.md`, `graphify query`
- current docsとSeed Foundry A1-A8の計画文書

### 2.2 事実認定の規則

優先順位は次のとおりとした。

1. current checkoutまたは明示したGit refのcode/test/schema/config
2. 実際のCLI helpとchecker結果
3. path、hash、timestampを確認したruntime artifact
4. current docs
5. HANDOFFとplan
6. graphifyの推論関係

graphifyは関連領域の発見に使った。推論edgeは実装事実として採用せず、該当codeまたはartifactで裏付けられた内容だけを結論へ使用した。

## 3. Repo規模と技術基盤

### 3.1 調査時点の規模

| 対象 | 値 | 数え方 |
|---|---:|---|
| `src/sis` Python files | 931 | `find ... -name '*.py'` |
| `src/sis` Python LOC | 144,744 | `wc -l`合計 |
| `tests` Python files | 741 | supportを含むPython files |
| `tests` Python LOC | 114,649 | `wc -l`合計 |
| top-level schema files | 176 | `schemas/`直下 |
| config files | 26 | `configs/`配下 |
| public CLI commands | 241 | CLI catalog checker |
| local runtime `data/` | 約2.1 GiB | `du -sh data` |

### 3.2 Runtime

- Python requirement: `>=3.13,<3.14`
- 調査時実体: Python `3.13.12`
- package manager / runner: `uv`
- CLI entry point: `sis = sis.cli:main`
- CLI framework: Typer
- validation/model: Pydantic, JSON Schema
- table/data: Polars, PyArrow, DuckDB
- network: HTTPX, WebSockets
- market/macro source helpers: yfinance, yahooquery, fredapi, pandas-datareader
- retry: Tenacity
- logging: Loguru

### 3.3 Optional backtest/report packages

`vectorbt`, `bt`, `empyrical-reloaded`, `quantstats`はoptional extrasである。core installの必須dependencyではない。外部framework surfaceはadapter、contract、smoke、differential用途であり、単一frameworkをrepo全体の正本engineにはしていない。

### 3.4 CIとlocal gate

CIはUbuntu上で次を行う。

1. checkout
2. uv setupとPython setup
3. Bun setup
4. `bun install --frozen-lockfile`
5. `./scripts/check`

`./scripts/check`の順序は次のとおり。

1. `uv sync --dev --locked`
2. Python version
3. Ruff lint
4. Ruff format check
5. current-doc checker
6. CLI catalog checker
7. Pyrefly
8. ty
9. Pytest

current-doc checkerで停止すると、その実行では後段のtype checkとtestへ到達しない。

## 4. 全体アーキテクチャ

### 4.1 概念フロー

```text
External or local source
  ↓
Raw snapshot / normalized table / source manifest
  ↓
Availability, identity, timestamp and lineage validation
  ↓
Seed / Idea / Candidate / Strategy Input
  ↓
Strategy Authoring and candidate-scoped backtest artifacts
  ↓
No-lookahead, cost, stress, regime, rolling and bias checks
  ↓
Kill / revise / collect-more-data / hold decision
  ↓
Human review packet and operator decision record
  ↓
Paper-only observation and drift evidence
  ↓
Separate approval boundary
```

どの矢印も無条件ではない。missing source、unsupported mapping、invalid schema、time leakage、sample不足、費用後の劣後、`NO_TRADE`優位は正常なstop resultである。

### 4.2 Artifact-first設計

domain間の接続は、内部関数を直接連鎖させるより、versioned JSON、JSONL、Parquet、CSV、Markdown、manifest、hash参照で行う傾向が強い。

利点:

- 再実行と監査が可能
- sourceと判断結果を分離できる
- human reviewを挟める
- downstreamがupstreamのpermissionを勝手に拡大しにくい
- fixtureでcontract testを書きやすい

代償:

- artifact種類とCLI数が多い
- docs、schema、CLI catalog、testの同期コストが高い
- 古いruntime artifactをcurrent proofと誤認しやすい
- path、hash、schema version、timestampの整合検証が不可欠

### 4.3 共通の横断関心

graphifyとcode inspectionから、次が複数domainを横断する中心であると分かった。

- UTC-aware timestamp validationとUTC Z serialization
- stable hashとartifact identity
- source referenceとcomponent hash
- boundary flag
- `created_at`, `available_at`, `information_cutoff_at`, receive timestamp
- JSON artifact writerとhuman-readable Markdown renderer
- known gap、reason code、blocker、next action

時刻は単なる表示属性ではない。未来情報混入、source freshness、event/outcome maturity、paper observation day、replay snapshot selectionを支える契約である。

## 5. Sourceとstorage

### 5.1 主なsource系統

- local fixture
- yfinance / Yahoo系のread-only market data
- FRED等のmacro data
- Bitget public REST
- Bitget public WebSocket関連コード・branch
- Trade[XYZ] public/historical/read-only collection
- operator-provided CSV / JSON / YAML
- manual LLM review JSON

外部network利用を必要とするcommandは、通常のlocal artifact処理と分離される。例としてBitget public source refreshは`SIS_ALLOW_PUBLIC_NETWORK=1`の明示opt-inを要求する設計である。

### 5.2 主な形式

| 形式 | 主用途 |
|---|---|
| JSON | manifest、decision、summary、schema-bound artifact |
| JSONL | ledger、signals、append-only record |
| Parquet | candles、features、quotes、orders、fills、大量row |
| CSV | interchange、event calendar、small table |
| YAML | strategy spec、operator input、config |
| Markdown | human review、runbook、decision explanation |
| HTML | backtest report、workbench viewer |
| DuckDB / SQLite | query index、normalized store、state store |

Seed Foundry計画ではimmutable fragmentやParquetをportable truthとし、DuckDBを再構築可能indexへ限定する方針が明記されている。

### 5.3 Runtime directory

`data/`, `logs/`, `.tmp/`はgenerated/runtime stateである。fresh checkoutに存在する保証はない。`data/`の存在、件数、decisionをcurrent proofへ使う時は、生成日時、入力path/hash、schema versionを確認する必要がある。

## 6. Public CLI

### 6.1 構成

`src/sis/cli.py`がroot Typer appを構成し、実commandは`src/sis/commands/`のregister関数へ分割されている。調査時点のlocal checkoutではCLI catalog checkerが241 public commandsとTyper registrationの一致を確認した。

### 6.2 主なcommand family

- research data ingest / feature panel / quality
- Strategy Authoring
- strategy backtest suite / compare / stress / stability / pack
- Strategy Input / Intake / Feedback
- Strategy Review / AI Review / Workbench
- Strategy Stage / Paper Smoke / Runtime Observation / Drift / Learning
- Strategy Idea Candidates / C9 bridge
- Crypto Perp truth-cycle family
- NDX research DAG / Layer 2.2 gates
- Trade[XYZ] collection / normalization / historical archive
- execution read-only status / demo smoke / estimate
- paper operations
- operations / audit / remediation / readiness

### 6.3 CLIの意味

commandが存在することは、その経路がproduction-readyであることを意味しない。commandは次のいずれかである場合がある。

- fixture/local artifact builder
- read-only network probe
- preview
- schema validator
- report generator
- human-review helper
- paper-state operator
- blocked/disabled adapter surface

command名だけでwrite capabilityやreadinessを判断せず、help、adapter、boundary field、testを確認する。

## 7. Strategy Idea Seed Foundry

### 7.1 Domainの位置

SeedはCandidateより前にある未検証仮説資産である。既存`strategy_idea_candidates`はshortlist/reject責務を持つため、Seedを同じdomainへ押し込まず、`src/sis/strategy_idea_seeds/`として独立させる設計が採用された。

### 7.2 A1-A8

全体計画は8段階である。

1. A1 Technical Walking Product
2. A2 Identity / Archive / Storage Foundation
3. A3 ML Data Truth
4. A4 ML Discovery Lane
5. A5 LLM Seed Lane
6. A6 Mutation / Counterfactual / Cross-lane
7. A7 Unified Archive / Review Product
8. A8 Operational Release

最終文書状態は`SEED_FOUNDRY_CORE_V1_OPERATIONAL`。これはA1完了と同義ではない。

### 7.3 A1実装済み範囲

`origin/main`の`427de2b`にはA1が統合済みである。

主な追加surface:

- Common Seed Envelope
- Technical Payload
- Source Probe
- mechanism/operator catalog
- deterministic generator
- AttemptとSeedの分離
- artifact writer
- Markdown renderer
- public CLI
- 5本のJSON Schema
- source fixture
- focused tests

初期mechanismはFunding CrowdingとVolatility Compression / Releaseに限定される。

### 7.4 A1の重要境界

- Seed statusは`UNVERIFIED_SEED`
- `DATA_REQUIRED`は有効なSeed outcome
- invalid type/unit/minimum contractはAttempt-only
- exact duplicate attemptもledgerへ残す
- budget超過は`PRUNED_BUDGET`とcursorで残す
- titleをidentityへ混ぜない
- Candidate、Backtest、Paper、Live artifactを生成しない
- profit、勝率、Sharpe、supportをSeed最低条件にしない

Boundaryは次のようなflagをfalseへ固定する。

- `backtest_evaluated`
- `execution_evaluated`
- `cost_evaluated`
- `profit_claimed`
- `auto_shortlisted`
- `permits_candidate_export`
- `permits_paper_candidate`
- `paper_execution_allowed`
- `live_allowed`
- `wallet_used`
- `signing_used`
- `exchange_write_used`

### 7.5 現在のcheckout上の注意

local `main` HEADにはA1 codeがない。A1について変更・検証する時は、まず`origin/main`との分岐を安全に解消するか、A1 worktree / current branchを明示しなければならない。

A1 worktree HANDOFFは「A1完了、A2を始めない」としている。新しい明示指示なしにA2へ進めない。

## 8. Strategy Idea CandidatesとC9 bridge

### 8.1 Candidateの責務

CandidateはSeedと違い、定義済みfamily、parameter、source mapping、shortlist/rejectを持つ評価対象である。candidate-set contract、search ledger、export manifest、AI review packet/import、perp estimateなどがある。

### 8.2 C9 bridge

C9 bridgeはshortlisted candidateをcandidate-scoped Strategy Authoring spec、suite、bundle、standard backtest packへ接続するfail-closed bridgeである。

`BRIDGED`の意味:

- 対応familyだった
- source mappingが解決できた
- downstream artifactが生成・検証できた

`BRIDGED`ではない意味:

- alpha proof
- profit proof
- paper permission
- live permission

unsupported familyやsource不足は`BLOCKED_*`として停止させる。

### 8.3 既存artifact

current docsが参照する2026-06-28のBTCUSDT runでは、5 candidate中3件がbridged、2件がunsupported family mappingでblockedと記録されている。この値はhistorical runtime snapshotであり、再実行なしにcurrent codeの固定結果とはみなさない。

## 9. Strategy Lab / Authoring

### 9.1 役割

Strategy Labはvenue-neutralな研究、戦略記述、feature、signal、backtest artifact生成の中心である。

主なsurface:

- strategy spec initialization / validation / explanation
- single run / bundle run
- backtest suite
- comparison
- data availability
- baseline comparison
- no-lookahead diff
- execution simulation
- assumption ledger
- trial ledger
- portfolio comparison
- stress
- regime split
- rolling stability
- benchmark relative
- HTML/report extension
- standard backtest packとvalidation
- optional framework adapter/contract/smoke

### 9.2 設計上の意味

Strategy Authoringは既に豊富なstrategy expressionを持つ。新しい探索系を作る時は、別DSLを増やす前に既存contractを再利用できるか確認する必要がある。

Backtest artifactがPASSしてもpaper/liveへ自動変換しない。reportは判断材料でありpermissionではない。

## 10. Backtest

### 10.1 主な評価

- return/performance metrics
- cost assumption
- execution simulation
- baseline comparison
- portfolio comparison
- regime split
- rolling stability
- stress
- no-lookahead
- data availability
- trial ledger
- adapter differential / framework smoke

### 10.2 現実的な限界

repoの既存文書とartifactは次の弱点を認めている。

- small sample
- independent episode不足
- 同一日への集中
- books/trades/replay不足
- PBOが評価不能または十分でない場合がある
- selector benchmark不足
- actual cashがない

Backtestの良好な結果をprofit proofへ読み替えない。

## 11. Strategy Reviewとlifecycle

### 11.1 Review

Strategy Reviewは既存artifactからhuman-review packetを作り、operator decision recordを保存する。欠損artifactをstrictまたはlenient policyで扱えるが、review result自体はpaper/live executionを許可しない。

### 11.2 AI Review

Strategy AI Reviewはsafe summary packet、AI note、structured findingを扱う。AI outputはhuman-review supportであり、auto-apply、contract edit、paper/live permissionではない。

### 11.3 Lifecycle artifact

- Strategy Input Contract / Intake
- Feedback proposal / review
- Stage policy / decision
- Paper Smoke Plan
- Runtime Observation ingest
- Paper vs Backtest Drift Review
- Learning ledger
- Revision request / review
- Authoring update handoff
- Case Lite / Case Index
- Daily Brief
- Model Loop run record
- Micro Live Plan
- Next Scale Plan
- Live Observation ingest
- Scale Decision
- Workbench Viewer

多くはfirst sliceのlocal artifact surfaceである。名前に`live`が含まれても、live order executionを意味しないものがある。

## 12. Crypto Perp

### 12.1 Repo内での位置

Crypto Perpは、sourceからno-cash decisionまでの縦のartifact chainが最も具体的に揃ったdomainである。Bitget public dataを利用する部分はあるが、core contractはartifact中心で、live writeから切り離されている。

### 12.2 主な構成

- Bitget public HTTP client / normalizer / raw store
- public provider probe / audit
- account snapshot / credential scope attestation
- order preview
- candle quality
- event detection
- outcome construction
- source availability
- replay slice
- feature pack
- edge score
- tournament rows / report / gate
- bias guard
- candidate leaderboard
- no-trade kill report
- no-cash backtest candidate pack
- human review packetとlineage validation
- truth-cycle status
- profit-readiness inventory / plan / run
- cash ledger / actual-cash rows / report gate
- tiny-live review packet / shadow / readiness / measurement helper
- execution replay、capture、portfolio capacityに関するbranchまたはlocal plan

### 12.3 No-cash chain

概略は次のとおり。

```text
public/local candle and ticker source
  → event and outcome
  → source availability
  → feature and edge score
  → action rows including NO_TRADE
  → bias guard and robustness
  → backtest candidate decision
  → no-trade kill / no-cash gate
  → human review
```

### 12.4 Decision vocabulary

Backtest Candidate Packは概ね次の4択を使う。

- `BACKTEST_REJECT`
- `BACKTEST_REVISE`
- `BACKTEST_COLLECT_MORE_DATA`
- `BACKTEST_CANDIDATE_HOLD`

`BACKTEST_PROMOTE_TO_LIVE`はない。`BACKTEST_CANDIDATE_HOLD`もactual cash、paper、tiny-live、live permissionを意味しない。

### 12.5 NO_TRADE

`NO_TRADE`は欠損や失敗の代替値ではなく、比較対象となる正式actionである。費用、funding、slippage、operator timeを考慮した結果、trade actionが`NO_TRADE`を上回らなければtradeへ差し替えない。

### 12.6 Actual cash境界

estimate、preview、simulated return、paper resultを`actual_cash`と呼ばない。actual-cash report gateはcash ledgerまたは対応するmeasurement artifactを要求する。入力がなければblockedになることが正しい。

### 12.7 調査時点のartifact snapshot

`data/crypto_perp/backtest_candidate_pack/latest/decision.json`:

- mtime: `2026-07-06_20:33 JST`付近
- decision: `BACKTEST_CANDIDATE_HOLD`
- outcome count: 30
- reason: local simulation candidate remains / actual cash, paper, tiny live are out of scope
- `permits_live_order=false`
- `live_conversion_allowed=false`

これは7月6日のruntime snapshotであり、現在のmarket edgeやprofitを証明しない。

### 12.8 Portfolio Capacity / Execution Replay

local `main`には`plan/0716計画/Execution-Replay導入設計.md`がある。目的はevent単位の独立損益から、共通資本、同時position、cash reuse、portfolio capacity、execution replayを扱う推定へ進めること。

計画上の段階:

- Candidate Pack Reader
- shared-cash portfolio capacity reference path
- VectorBT differential
- market capture
- native depth execution replay
- 必要な場合だけNautilusTrader sidecar

一方、`origin/ai/crypto-perp-portfolio-replay-20260716-2204`にはcapture、book handling、receive timestamp、portfolio capacity、execution replay関連commitが見えるが、`origin/main`ではない。未統合branchの存在をcurrent production surfaceとして数えない。

## 13. NDX research gates

### 13.1 役割

NDX Layer 2.2以降は、local DAG foundation、feature/residual artifact、manual LLM review、exit gate、paper-observation reviewを扱う。

主なcommand:

- `research-layer22-validate`
- `research-layer22-export`
- `research-layer22-review-pack`
- `research-layer22-review-import`
- `research-layer22-exit-gate`

### 13.2 Permission境界

NDXのPASSやpromotionは、local researchまたはpaper-observation段階の判断である。

調査したartifact例:

- `paper_observation_gate_decision.json`: `APPROVE_PAPER_OBSERVATION_REVIEW`
- `operator_promotion_decision.json`: `promote_to_paper_observation`
- `permits_live_order=false`
- `live_conversion_allowed=false`

paper observationへ進む判断とlive tradingは別のpermissionである。

## 14. Trade[XYZ]とvenue境界

### 14.1 現在の扱い

Trade[XYZ]関連にはcollection、quote normalization、coverage、reference data、funding、historical archive、readiness、execution state comparisonなど多くの実装がある。

しかしrepo-local guideでは、Trade[XYZ]をdefault product axisから外し、historical/read-only venue contextとして扱う。ユーザーが明示しない限り、新しいTrade[XYZ]前提、collector、order path、readiness claimを追加しない。

### 14.2 Venue schema

current docsでは`VenueId`は`trade_xyz`と`bitget_demo`を許可し、`bitget_futures`と`hyperliquid_perp`はcatalog-only / disabledとされる。schema変更時はcurrent codeを再確認する。

### 14.3 Execution command

CLIにはorder status、estimate、balance、fill status、cancel、close、reconcileなどの名前がある。adapterはpaper/demo/read-only/blocked surfaceを含むため、command名だけでproduction exchange writeと判断しない。

repo全体としてstandard operator pathのproduction live、wallet、signing、exchange write readinessは証明されていない。

## 15. Paper operations

`src/sis/paper/`とpaper-related commandsはlocal paper positions、orders、fills、intent preview、report、observation ledger、cycle、drift比較を扱う。

paper artifactはexecution realityの一段階だが、actual cashではない。paperとbacktestの乖離を観測し、同一日rerunで観測日数を水増ししない設計を採る。

normal paper observationには新しいtrading dayを含むevidenceが必要である。

## 16. Operations / audit / remediation

### 16.1 役割

operations領域は機能実装の代替ではなく、状態、欠損、readiness、履歴、監査をartifactとして集約する。

主なsurface:

- healthcheck
- daemon manifest / dry run / run
- monitoring status
- kill switch
- lifecycle and comparison report
- operations dashboard / bundle / timeline / audit pack
- audit dashboard / bundle / history
- current-state index
- readiness snapshot
- remediation planner / execution plan / session / evidence / scoreboard / evaluator
- phase-gate review

### 16.2 `READ_ONLY_GO`

`data/ops/phase_gate_review_summary.json`の調査snapshot:

- mtime: `2026-06-17_21:39 JST`付近
- decision: `READ_ONLY_GO`
- strict validation: pass
- execution overall: degraded
- reason: Trade[XYZ] execution-state user address missing
- phase2 entry allowed: true

この`READ_ONLY_GO`はread-only/paper gateであり、wallet、signing、exchange write、production liveの許可ではない。

## 17. Safety / permission model

### 17.1 基本原則

repoの重要な設計は、良い評価結果よりもfalse permissionを防ぐことである。

```text
Artifact exists
  ≠ Valid artifact
Valid artifact
  ≠ Sufficient evidence
Sufficient backtest evidence
  ≠ Profit proof
Human review ready
  ≠ Paper permission
Paper observation approved
  ≠ Live permission
Demo configured
  ≠ Production readiness
```

### 17.2 代表的なfalse boundary

- `permits_live_order=false`
- `live_conversion_allowed=false`
- `wallet_used=false`
- `signing_used=false`
- `exchange_write_used=false`
- `profit_claimed=false`
- `paper_execution_allowed=false`

Pydantic model、JSON Schema、artifactの複数層でfalseを固定するsurfaceがある。

### 17.3 正常な停止結果

- missing source
- invalid source
- snapshot-only sourceをhistoricalとして使えない
- unsupported family mapping
- sample insufficient
- PBO / rolling stability not estimable
- time leakage risk
- `NO_TRADE` leader
- actual cash artifact missing
- credentials missing
- external network opt-in missing
- operator approval missing

これらをzero-fill、mock、手動上書きでpassへ変えない。

## 18. Runtime artifactから確認したこと

### 18.1 Data volume

local `data/`は約2.1 GiB。research、NDX、paper、ops、Crypto Perp、Trade[XYZ]、strategy review、reportsなど多数のartifactを含む。

### 18.2 Backtest pack

`data/research/backtest_pack/strategy_backtest_pack_validation.json`:

- mtime: `2026-06-17_19:36 JST`付近
- decision: `PASS`
- `live_conversion_allowed=false`
- `permits_live_order=false`

### 18.3 NDX

paper observation系decisionはreview/paper observationを許可しているが、live orderはfalse。

### 18.4 Artifact freshness risk

調査した主要artifactの多くは6月17日または7月6日生成である。codeは7月16日まで変化している。artifactのschema compatibilityや再現性をcurrent codeで再検証せず、古い値を現況として固定しない。

## 19. 検証結果

### 19.1 成功

- `uv run python -V`: Python 3.13.12
- `uv run python scripts/check_cli_catalog.py`: 241 public CLI commandsとTyper registrationが一致
- `git diff --check`: 調査開始時点のtracked diffにwhitespace errorなし
- Pytest全体のうち3132 testがpass
- `origin/main`にA1 merge commit `427de2b`が存在
- A1 dedicated worktree HANDOFFはA1完了、A2未着手を記録

### 19.2 失敗

Pytest結果:

```text
2 failed, 3132 passed
```

失敗test:

- `tests/test_docs_current_truth.py::test_plan_routing_keeps_historical_docs_archived`
- `tests/test_docs_current_truth.py::test_current_docs_checker_passes`

直接原因:

- `plan/0716計画/Execution-Replay導入設計.md`
- `plan/0716計画/Seed-Foundry-Core-716.md`

上記2本がcurrent root planまたはarchive routingの許可された配置外にある。

これはdomain behavior testの失敗ではないが、authoritative full gateがgreenでないことに変わりはない。現checkoutを「全test成功」と報告してはいけない。

### 19.3 Test cleanup warning

全Pytest実行後、`/tmp/pytest-of-tn/`配下の一部test fixture cleanupでpermission / directory-not-empty warningが出た。最終fail countには含まれていないが、再発する場合はtest isolationまたはpermission操作を調査する価値がある。

## 20. Git / worktree / HANDOFF

### 20.1 Local checkout

- branch: `main`
- HEAD: `590c5855e0e4347f13ce07c9adccf28910624d8a`
- tracked worktree: 調査開始時clean
- upstream relation: ahead 3 / behind 2

### 20.2 origin/main

- ref: `427de2b62ebb21a613793aee92b1d49bbe69e09c`
- PR #48のSeed Foundry A1を含む

### 20.3 A1 worktree

- path: `/home/tn/projects/marketlens-strike/.worktrees/marketlens-strike-a1-20260716-1654`
- branch: `ai/seed-foundry-a1-technical-walking-product-20260716-1654`
- implementation commit: `3684ef512730f20c8a2ee00b1c7ce2a660c0b48a`
- merge result: `427de2b62ebb21a613793aee92b1d49bbe69e09c`
- HANDOFF status: A1 complete, await fresh direction, do not start A2

### 20.4 Handoffの古さ

root HANDOFFはA1 worktreeへ誘導するが、A1 merge後のlocal main divergence全体を解決する指示ではない。再開artifactとして重要だが、Git refとcurrent codeの再確認を省略しない。

### 20.5 統合時の禁止事項

- local `main`を無条件にresetしない
- `origin/main`を雑にmergeして大規模delete/addを受け入れない
- graphify generated files、計画文書、A1 codeの差を個別に確認する
- 未統合remote branchをcurrent main扱いしない
- A2をA1の続きとして自動開始しない

## 21. Graphifyから得た構造理解

### 21.1 Snapshot

- graph artifact mtime: 2026-07-16 23:23-23:24 JST
- nodes: 1,129
- edges: 3,668
- 対象: local checkout側
- Seed Foundry A1はlocal checkoutにないためgraphにも含まれない

### 21.2 主なcommunity

graph reportではCrypto Perp周辺が次のcommunityへ分かれていた。

- market bar / event data
- Bitget HTTP client
- account state
- candidate pack
- profit robustness
- order book recording
- human review pack
- artifact validation
- no-trade kill gate
- no-cash gate
- depth execution replay
- tournament gates
- time/readiness
- outcomes
- cash ledger
- truth-cycle status
- ticker coverage
- universe
- fill calibration
- tiny-live shadow
- workbench bridge

### 21.3 読み取れる設計

Crypto Perpは単一moduleではなく、時刻とartifact identityを共有する多数の小さなdomain componentからなる。特に`ensure_utc_aware`、UTC serialization、producer/boundary modelが横断的に現れる。

### 21.4 限界

graphには多数のinferred edgeがある。centralityやcommunityは探索順を決める補助であり、call graph、permission、runtime readinessの確定証拠ではない。

## 22. 現在できること

### 22.1 今すぐlocalで使える

- CLI helpとcatalog確認
- schema/config validation
- fixture/local sourceによるStrategy Lab / Authoring
- backtest suite、comparison、stress、rolling、report
- Strategy Review packet / decision record
- AI review packet / note / structured finding
- Strategy lifecycle artifact生成
- Crypto Perp local/no-cash artifact chain
- NDX local DAG / manual review pack / gate
- paper artifact / operations report
- Trade[XYZ] historical/read-only artifact inspection
- runtime artifact validation

### 22.2 条件付きで使える

- public network source refresh: explicit opt-inが必要
- credentialed read-only probe: env credentialが必要
- normal paper observation:新しいtrading dayのevidenceが必要
- actual-cash rows / gate: cash ledgerまたはmeasurement artifactが必要
- A1 Seed Foundry: `origin/main`またはA1 worktree側で利用可能。現在のlocal mainにはない

### 22.3 現在証明されていない

- profit
- actual cash profitability
- production live trading
- wallet integration
- signing integration
- exchange write integration
- Bitget production order lifecycle
- Bitget demo full order lifecycle
- production account readiness
- tiny-live measurementの実運用成功
- Strategy Reviewからpaper/liveへの自動許可
- backtestからliveへの自動変換

## 23. Current docsの現実

### 23.1 有用な入口

- `docs/CURRENT_STATE.md`
- `docs/IMPLEMENTED_SURFACES.md`
- `docs/CURRENT_DOCS_INDEX_2026-07-05.md`
- `docs/CURRENT_GOAL_AND_DIRECTION_2026-07-05.md`
- `docs/NO_CASH_GOAL_PROGRESS_2026-07-05.md`
- `docs/CURRENT_ARTIFACT_SURFACE_REFERENCE_2026-07-05.md`

### 23.2 古さ

多くのcurrent entry docは2026-07-05時点の整理で、Seed Foundry A1 mergeや7月16日のbranch群より古い。主軸や安全境界は今も有用だが、command数、実装surface、次作業はGit/codeで再確認する。

### 23.3 Planの扱い

`plan/`と`資料/`は設計意図や将来像を理解する資料であり、current implementation proofではない。特にA2-A8、Hypothesis Search Engine、Portfolio Capacity / Replayの未統合部分を実装済みと数えない。

## 24. 現在の開発方向をどう読むか

同時に複数の方向性が存在する。

1. July 5 current docsのno-cash evidence quality向上
2. Seed Foundry Core v1 A1-A8
3. Hypothesis Search Engine / D01 Convex Campaignのplan-only検討
4. Crypto Perp Portfolio Capacity / Execution Replay

これらは一つの完成済みroadmapではない。

- A1だけが`origin/main`に統合済み
- A2-A8は文書上の後続stage
- Hypothesis Search EngineはPRE-CP0 / plan-onlyとして記録されている
- Portfolio Capacity / Replayはlocal planと別remote branchに進展があるが、origin/main統合状態ではない

次の実装を選ぶ前に、どの軸を優先するか明示する必要がある。

### 24.1 Hypothesis Search Engine / D01の現在地

`.ai-work/`に残る作業記録では、この方向は`PRE-CP0 / PLAN-ONLY`である。`src/sis/hypothesis_search/`は存在せず、CP0からCP11はすべて未着手と記録されている。

計画上の主要思想:

- 既存Strategy Authoring contractを利用し、新しいDSLを増やさない
- candidate / trialの完全なledgerを残す
- exact duplicateとnear duplicateを区別する
- cheap screen、bias kill、full backtestを分離する
- ROBUST、ASYMMETRIC、NOVELTYのresearch laneを持つ
- finalistだけのPBOを肯定証拠へ使わない
- sealed confirmationを探索と分離する
- DuckDBを再構築可能indexとし、immutable fragmentとmanifestをportable truthにする
- 最初のE2E adapterはCrypto Perpでもcoreはvenue-neutralに保つ

`D01_CONVEX_CAMPAIGN`は小資本、正の歪度、複数機体、Profit Vault、Ratchet、Reload、Rebaseを含む方向性メモである。資金保存、成功倍率、Vault再投入、Impact会計、ML label、leverage/notional、cluster定義などに未決事項があり、実装仕様として確定していない。

この方向を再開する場合、まずCP0の事実監査と未決事項の採否が必要であり、既存A1-A8やPortfolio Replayと暗黙に統合しない。

## 25. 技術的リスクと保守上の論点

### 25.1 Git topology risk

最大の即時risk。分岐を解消せずに新しい大変更を積むと、A1、graphify、計画、current docsが衝突する。

### 25.2 Documentation routing

current-doc checkerがfailしている。計画2本を正しいcurrent plan rootまたはarchiveへroutingし、リンクとchecker contractを同期する必要がある。

### 25.3 Surface breadth

241 public command、176 schema、多数artifactがあり、追加するたびCLI catalog、docs、schema、fixtures、test、rendering、migrationを揃える必要がある。

### 25.4 Artifact staleness

古いartifactが大量に残る。`latest` pathでもcode HEAD、input hash、generated_atを確認する。

### 25.5 Evidence quality

実装導線は厚いが、books/trades/replay、independent episode、regime分散、PBO/rolling evaluation、actual cashは弱いまたは未接続。

### 25.6 Permission vocabulary

status名が多い。human-facing outputでは、各statusが何を許可し、何を許可しないかを常に併記する。

### 25.7 Graph staleness

graphはlocal branch snapshotであり、origin/mainやremote feature branchを自動統合しない。code変更後はgraph updateが必要だが、branch差を解消してから対象rootを明示する。

### 25.8 Test temporary cleanup

Pytest cleanup warningはpass/failとは別だが、permission manipulationを含むtestの後始末が不安定な可能性を示す。

## 26. 再開時の推奨確認順

### 26.1 どの作業でも最初に確認

```bash
git status --short --branch --untracked-files=all
git branch --show-current
git log --oneline --decorate --graph --max-count=20 --all
git rev-parse HEAD
git rev-parse origin/main
```

### 26.2 Current repo理解

1. `AGENTS.md`
2. `.ai_memory/HANDOFF.md`
3. `docs/720-info/README.md`
4. この文書
5. `docs/CURRENT_STATE.md`
6. `docs/IMPLEMENTED_SURFACES.md`

### 26.3 対象domainの正本

- Strategy Lab: `src/sis/research/strategy_lab/`, `tests/strategy_authoring/`
- Backtest: `src/sis/backtest/`, `tests/backtest/`
- Crypto Perp: `src/sis/crypto_perp/`, `tests/crypto_perp/`
- Candidate: `src/sis/strategy_idea_candidates/`, 対応test/schema
- Seed A1: `origin/main:src/sis/strategy_idea_seeds/`またはA1 worktree
- NDX: `configs/research_layer_2_2/ndx/`, `src/sis/research/`, 対応test
- Operations: `src/sis/commands/`, `src/sis/tracking/`, `src/sis/validation/`

### 26.4 Verification

```bash
uv run python -V
uv run sis --help
uv run python scripts/check_cli_catalog.py
uv run python scripts/check_current_docs.py
./scripts/check
```

現状ではcurrent-doc routingを直さない限り`./scripts/check`は途中で停止する。

## 27. 変更作業の判断基準

### 27.1 先に分岐解消が必要な作業

- Seed Foundry A2以降
- local planとA1の両方へ触れる変更
- CLI catalogをさらに広げる変更
- docs current root再編
- Portfolio Capacity / Execution Replayのmain統合

### 27.2 強い停止条件

- target branchが不明
- local mainとorigin/mainのどちらを正本にするか未決
- user-owned diffと衝突
- schema migrationが必要だがreader/rollbackがない
- external network、credential、paper/live、課金が必要
- actual cashなしでprofit claimが必要になる
- A2以降を明示承認なしに開始する必要がある

## 28. Omission / Error Risk Pass

初稿の理解に対して、次の誤謬を排除した。

### 28.1 「A1は未実装」ではない

local checkoutにはないが`origin/main`へmerge済み。branch contextを付けて記述した。

### 28.2 「A1でSeed Foundry完成」ではない

A1はwalking product。Operational completionはA8。

### 28.3 「BACKTEST_CANDIDATE_HOLDならlive候補」ではない

artifactの`permits_live_order=false`と`live_conversion_allowed=false`を確認した。

### 28.4 「READ_ONLY_GOならexecution ready」ではない

同artifact内でexecution overallはdegraded。read-only/paper gateの意味に限定した。

### 28.5 「paper observation promotionならactual cash」ではない

paper、actual cash、liveを分離した。

### 28.6 「graphにあるので実装済み」ではない

graphのinferred relationとGit branch差を明示した。

### 28.7 「3132 testが通ったのでgreen」ではない

2 failedとcurrent-doc checker failureを残した。

### 28.8 「data/にあるのでcurrent」ではない

mtimeとsnapshot性を記録した。

### 28.9 「remote feature branchがあるのでmainで使える」ではない

origin/mainとの統合状態を分けた。

## 29. 最終評価

`marketlens-strike`は、仮説生成からreview/paper observationまでをartifactで分離し、false permissionを強く防ぐ研究基盤としてかなり広いsurfaceを持つ。実装量とtest量は大きく、特にStrategy Authoring、Backtest、Crypto Perp no-cash chain、review/operationsは厚い。

一方で、現実のボトルネックは「CLIやschemaがないこと」より次にある。

- branch topologyの整理
- evidence quality
- source coverageと高解像度execution data
- independent sample / bias evaluation
- stale artifact管理
- statusとpermissionの誤読防止
- docs routingとcurrent-doc freshness

このrepoを前進させる時は、新しいsurfaceを増やす前に、対象branch、evidence gap、permission boundary、stop conditionを明示する必要がある。

## 30. 調査コマンド記録

主要なread-only / verification command:

```bash
git status --short --branch --untracked-files=all
git branch --show-current
git rev-parse HEAD
git rev-parse origin/main
git log --oneline --decorate --graph --all
git diff --stat HEAD..origin/main
git ls-tree -r --name-only origin/main
git show origin/main:<path>

uv run python -V
uv run sis --help
uv run python scripts/check_cli_catalog.py
uv run python scripts/check_current_docs.py
uv run pytest -q

graphify query "..."

find src/sis -type f -name '*.py'
find tests -type f -name '*.py'
du -sh data
jq ... <artifact.json>
```

## 31. この文書の更新条件

次の場合は内容を再検証し、`更新日`を東京時間で更新する。

- local `main`と`origin/main`の分岐を解消した
- Seed Foundry A2以降を開始またはmergeした
- Portfolio Capacity / Execution Replayをmainへmergeした
- public CLI countまたはmajor command familyを変更した
- schemaやpermission vocabularyを変更した
- actual-cash / paper / live boundaryを変更した
- current-doc routingを整理した
- 主要artifactを新しいinputで再生成した
