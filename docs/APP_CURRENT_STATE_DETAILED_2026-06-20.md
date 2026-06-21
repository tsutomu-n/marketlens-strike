<!--
作成日: 2026-06-20_20:32 JST
更新日: 2026-06-21_19:07 JST
-->

# marketlens-strike アプリ現状詳細ガイド

## 結論

`marketlens-strike` は、画面をクリックして使う一般的なWebアプリではなく、ターミナルから `uv run sis ...` で使う Python 3.13 のCLIアプリです。

中心機能は、売買戦略をいきなり本番注文に出すことではありません。戦略案をファイルにする、入力データの前提を検査する、過去データで試す、人間が読むレビュー資料を作る、ペーパー観察の証拠を読む、次の段階に進めるかをローカル生成物で確認することです。

現時点でできないことは、本番の自動売買、ウォレット操作、署名、取引所への書き込み、production live trading、backtestだけによる利益保証です。

## この文書の根拠

この文書は次を確認して書いています。

- `README.md`
- `docs/CURRENT_STATE.md`
- `docs/IMPLEMENTED_SURFACES.md`
- `docs/REPO_CAPABILITIES_CURRENT_2026-06-16.md`
- `docs/REPO_CAPABILITIES_PLAIN_JA_2026-06-17.md`
- `docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md`
- `docs/STRATEGY_AND_BACKTEST_USER_GUIDE.md`
- `docs/ARCHITECTURE_AND_PHASES.md`
- `docs/OPERATIONS_RUNBOOK.md`
- `docs/STRATEGY_OPERATIONS_WORKBENCH_COMPLETION_AUDIT_2026-06-19.md`
- `plan/0621ここから01/marketlens-strike-crypto-perp-mvp-final-plan-2026-06-20/`
- `src/sis/cli.py`
- `src/sis/commands/`
- `src/sis/crypto_perp/`
- `src/sis/strategy_*`
- `src/sis/research/`
- `src/sis/real_market/`
- `src/sis/tracking/`
- `src/sis/backtest/`
- `src/sis/paper/`
- `src/sis/execution/`
- `src/sis/reports/`
- `src/sis/ops/`
- `src/sis/risk/`
- `src/sis/state/`
- `src/sis/venues/trade_xyz/`
- `schemas/`
- `tests/`
- `uv run sis --help`

固定のコマンド数、テスト件数、runtime artifactの数値はこの文書には写しません。確認時は次を再実行します。

```bash
uv run python -V
uv run sis --help
uv run python scripts/check_cli_catalog.py
uv run python scripts/check_current_docs.py
./scripts/check
```

## 追加調査で補った点

初稿では、Strategy Operations Workbench、backtest、paper観察の説明を厚めに書きました。一方で、repo全体のアプリ機能としては次の説明が薄かったため、この版で補いました。

- research data ingest、feature panel、signal build、cost matrix。
- `real_market` と `tracking` の役割。
- optional backtest framework、external framework contract、legacy `build-backtest`。
- Trade[XYZ] pure backtestがPython API surfaceであり、public CLIではないこと。
- daemon、state export / restore、monitoring、kill-switch、notificationなどのruntime補助。
- `risk` / halt policy系の補助コマンド。
- execution系CLI名を、本番注文可能と誤読しないための境界。
- Crypto Perp Truth-Cycle MVPがM11まで実装済みであること。
- Crypto Perpはshort固定ではなく、`REVERSAL_SHORT`、`CONTINUATION_LONG`、`NO_TRADE` を同格に扱うこと。
- Crypto PerpのM09 tiny live measurementはmock testまでで、実ネットワーク測定は未実行かつ別承認が必要であること。

## アプリの全体像

このアプリは、売買戦略の研究と検証を安全側に倒して進めるための作業台です。

大きく分けると、次の領域があります。

| 領域 | 何をするか | 本番注文との関係 |
|---|---|---|
| Strategy Input / Idea | 戦略の前提データとアイデアを検査する | 注文しない |
| Research Data / Feature | 市場データ、マクロデータ、特徴量、signalを作る | 注文しない |
| Strategy Research Lab | 戦略候補、signal、評価、paper-only previewを作る | 注文しない |
| Strategy Authoring | YAMLで戦略ルールを書き、検証・説明・backtestする | 注文しない |
| Backtest | 過去データで戦略を試し、弱点を調べる | 将来利益の保証ではない |
| Strategy Review | 人間が読むレビュー資料と判断記録を作る | 許可証ではない |
| Strategy Operations Workbench | stage、観察、drift、learning、scale計画を生成物でつなぐ | 実運用そのものではない |
| Paper Operations | 本番資金を使わないpaper用生成物を扱う | live orderではない |
| Crypto Perp Truth-Cycle | Bitget public dataからevent、decision、outcome、cash ledger、tournamentまでの検証生成物を作る | 自動売買ではない |
| NDX Research Gates | NDX / QQQ系研究を段階的に検査する | 研究用のローカルgate |
| Trade[XYZ] / Venue | 読み取り専用のデータ収集やvenue境界確認をする | wallet / signing / writeなし |
| Operations / Audit / Remediation | 現状確認、監査bundle、修復計画を作る | readinessの種類を分けて読む |
| Runtime / Risk / State | daemon、kill-switch、state export、halt policyを扱う | 安全補助でありlive許可ではない |

## 使い方の基本

セットアップの入口です。

```bash
uv sync --dev --locked
uv run python -V
uv run sis --help
```

全体検証の入口です。

```bash
./scripts/check
```

`./scripts/check` は、依存関係の同期、Python version、Ruff、format check、current docs check、Pyrefly、ty、Pytestをまとめて確認します。

## いまできること

### 1. 戦略の入力データ契約を検査できる

戦略を作る前に、「その戦略がどのデータを前提にしているか」を機械で読めるファイルにできます。

主なコマンド:

```bash
uv run sis strategy-input-contract-validate --help
uv run sis strategy-intake-validate --help
```

できること:

- 入力データのpath、hash、schema versionを記録する。
- そのデータがいつ利用可能だったかを `available_at` として扱う。
- 欠落した必須データ、hash不一致、境界違反を検出する。
- 戦略アイデアを `READY_FOR_AUTHORING_DRAFT`、`NEEDS_SPEC`、`NEEDS_DATA_CHECK`、`NEEDS_RISK_SPEC`、`REJECT` のような入口判定に分ける。

注意:

`READY_FOR_AUTHORING_DRAFT` は「戦略定義の下書きに進めそう」という意味です。paper実行、live実行、利益保証ではありません。

### 2. 戦略をYAMLで書ける

このrepoでは、戦略ルールを主にYAMLで書きます。YAMLは人間が読める設定ファイルです。

主なコマンド:

```bash
uv run sis strategy-author-init
uv run sis strategy-author-validate --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml
uv run sis strategy-author-explain --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml
uv run sis strategy-author-run --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml --through backtest
```

できること:

- 対象銘柄、買い条件、売り条件、損切り、利確、保有時間を定義する。
- 手数料、滑り、失敗条件を設定する。
- YAMLが形として正しいかを検査する。
- 戦略を説明文にする。
- local fixtureや生成物を使ってbacktestまで進める。

注意:

YAMLの検証通過やbacktest通過は、paper注文や本番注文の許可ではありません。

### 3. Strategy Research Labで候補作りからpaper-only previewまで進められる

Strategy Research Labは、戦略アイデアをsignal、評価、候補、昇格判断、paper-onlyの仮注文意図までつなぐための作業台です。

主なコマンド:

```bash
uv run sis strategy-preview
uv run sis strategy-experiment-run --spec path/to/strategy_experiment.yaml
uv run sis evaluate-strategy-lab
uv run sis build-paper-candidate-pack
uv run sis promotion-decision --decision hold
uv run sis build-paper-intent-preview
```

できること:

- 戦略実験の設定からsignalを作る。
- signalを評価する。
- paper候補packを作る。
- hold / promoteなどの判断を生成物として残す。
- paper-onlyの仮注文意図を作る。

注意:

`PaperIntentPreview` は「本番注文ではない仮の注文意図」です。live orderに変換してよい、という意味ではありません。

### 4. 研究データ、特徴量、signalを作れる

Strategy Labやbacktestの前段として、研究用の市場データ、マクロデータ、イベントカレンダー、特徴量、signalを作れます。

主なコマンド:

```bash
uv run sis ingest-research-data
uv run sis build-event-calendar
uv run sis build-feature-panel
uv run sis build-signals
uv run sis check-research-quality
uv run sis build-cost-matrix
uv run sis alpaca-smoke
```

できること:

- Yahoo FinanceやFRED系の読み取りデータから研究用panelを作る。
- event calendarを研究用Parquetに正規化する。
- market panel、macro panel、event calendarからfeature panelを作る。
- feature panelからStrategy Labのsignal artifactを作る。
- normalized quoteからvenue cost matrixとoperator reportを作る。
- Alpaca market-dataの読み取り接続smokeを実行する。
- `real_market` と `tracking` で、実市場データとvenue側データの差分や品質を見られる形にする。

注意:

ここでの外部データ取得は研究用の読み取りです。live order、wallet、signing、exchange writeは行いません。credentialが必要なsmokeは、接続確認であって注文準備完了ではありません。

### 5. 過去データでbacktestできる

backtestは、過去データで戦略がどう動いたかを調べる機能です。

主なコマンド:

```bash
uv run sis strategy-backtest-suite --help
uv run sis strategy-backtest-pack --help
uv run sis strategy-backtest-pack-validate --help
uv run sis strategy-backtest-artifact-summary --help
uv run sis strategy-backtest-html-report --help
uv run sis strategy-backtest-framework-run --help
uv run sis strategy-backtest-qstrader-contract --help
uv run sis strategy-backtest-pybroker-contract --help
uv run sis build-backtest --help
```

できること:

- 戦略の単体backtestを作る。
- 複数条件のbacktest suiteを回す。
- benchmarkと比較する。
- stress条件をかける。
- no-lookahead検査で未来情報利用の疑いを減らす。
- data availabilityでデータ欠損を見る。
- HTML reportで損益グラフ、取引一覧、benchmark比較を見る。
- optional dependencyがある場合、vectorbt / bt / quantstatsなどの外部framework surfaceを扱う。
- QSTrader / PyBrokerなどの外部framework向けcontract artifactを作る。
- legacy bridgeとして `build-backtest` を使う。

注意:

backtestは「過去ならこうだった」という検査です。将来の利益、実口座の安全性、paper実行許可、live実行許可を証明しません。Trade[XYZ] pure backtest v0.1は実装済みですが、public CLIではなくPython API surfaceです。`build-backtest` とは別物として読みます。

### 6. 人間が読むStrategy Review packetを作れる

Strategy Reviewは、backtest結果や関連ファイルを集めて、人間が読めるレビュー資料にする機能です。

主なコマンド:

```bash
uv run sis strategy-review-build --help
uv run sis strategy-review-record --help
```

できること:

- `review.md` を作る。
- `review_manifest.json` を作る。
- 人間が読んだ判断を `operator_review.yaml` として記録する。
- review対象ファイルのhashを保存し、あとで同じものを読んだか確認する。
- input contractやstrategy ideaを任意の読み取り専用sourceとして含める。

注意:

`operator_review.yaml` は「人間が読んだ」という記録です。paper execution permissionやlive permissionではありません。

### 7. Strategy Operations Workbenchのfirst sliceが使える

Strategy Operations Workbenchは、戦略を「思いつき、backtest、review、paper観察、drift確認、学習、次の計画」へ進めるための生成物連鎖です。

実装済みの主なコマンド:

```bash
uv run sis strategy-stage-policy-validate --help
uv run sis strategy-stage-decision --help
uv run sis strategy-paper-smoke-plan --help
uv run sis strategy-runtime-observation-ingest --help
uv run sis strategy-drift-review --help
uv run sis strategy-learning-ledger-update --help
uv run sis strategy-revision-request-build --help
uv run sis strategy-revision-request-review --help
uv run sis strategy-authoring-update-handoff --help
uv run sis strategy-case-lite-update --help
uv run sis strategy-daily-brief --help
uv run sis strategy-ai-review-packet-build --help
uv run sis strategy-ai-review-note-record --help
uv run sis strategy-model-run-record --help
uv run sis strategy-micro-live-plan --help
uv run sis strategy-live-observation-ingest --help
uv run sis strategy-scale-decision --help
uv run sis strategy-next-scale-plan --help
uv run sis strategy-workbench-viewer-build --help
```

できること:

- stage policyで進行条件を定義する。
- stage decisionで次の段階に進める証拠があるかを判定生成物にする。
- paper smoke planを作る。
- paper runtime observationを読み込む。
- backtestとpaper runtimeの差をdrift reviewにする。
- 学習イベント、改訂要求、人間レビュー、authoring update handoffを作る。
- 戦略ごとの簡易timelineを作る。
- daily briefでその日の確認対象をまとめる。
- AIレビュー用packetとAI noteを記録する。
- model runやoptimizer trialを台帳に残す。
- micro live plan、live observation ingest、scale decision、next scale planを生成物として扱う。
- static HTML viewerを作る。

注意:

このfirst sliceは、artifact / review / gate / observation / planningの仕組みです。production live trading、Svelte UI、wallet、signing、exchange write、実際のscale-up executionは含みません。

### 8. ペーパー観察の現在地を確認できる

ペーパー観察は、本番資金を使わずに、候補戦略が想定通りに紙上の注文や約定として記録されるかを見る段階です。

主なコマンド:

```bash
uv run sis strategy-paper-observation-cycle --help
uv run sis strategy-paper-observation-append --help
uv run sis strategy-paper-observation-status --help
```

できること:

- paper observation sessionを作る。
- 既存sessionに追記する。
- normal observationとsmoke observationを分けて状態確認する。
- live order、wallet、signing、exchange writeが混ざっていないかを確認する。

注意:

smokeは短い動作確認です。normal paper observation passの代わりにはなりません。同じ日のartifactを何度も作り直しても、複数取引日の観察にはなりません。

### 9. NDX / QQQ系の研究gateをローカルで回せる

NDX / QQQ系の研究について、データ源、特徴量、残差、review、paper observationの段階をローカル生成物で確認できます。

主なコマンド:

```bash
uv run sis research-layer22-validate --root configs/research_layer_2_2/ndx
uv run sis research-layer22-export --root configs/research_layer_2_2/ndx --out data/research/ndx
uv run sis research-layer22-review-pack --root configs/research_layer_2_2/ndx --out data/research/ndx/review
uv run sis research-layer22-review-import --pack data/research/ndx/review/llm_review_input.json --result data/research/ndx/review/llm_review_result.json
uv run sis research-layer22-exit-gate --root configs/research_layer_2_2/ndx --pack data/research/ndx/review/llm_review_input.json --review data/research/ndx/review/normalized_review.json --out data/research/ndx/review
uv run sis research-ndx-source-resolve --root configs/research_layer_2_2/ndx --out data/research/ndx
uv run sis research-ndx-feature-panel --root configs/research_layer_2_2/ndx --input-root tests/fixtures/ndx --out data/research/ndx
uv run sis research-ndx-residual --feature-panel data/research/ndx/ndx_feature_panel.parquet --out data/research/ndx
uv run sis research-ndx-residual-validate --root configs/research_layer_2_2/ndx --artifact-dir data/research/ndx --reports-dir data/reports --out data/research/ndx
```

できること:

- Layer 2.2のDAG設定を検査する。
- manual review用packを作る。
- feature panelを作る。
- residualを計算する。
- residual validationを行う。
- research-only exportやpaper observation reviewへ進めるための生成物を作る。

注意:

NDX gateは研究用のローカルgateです。alpha、backtest readiness、paper readiness、live readiness、account readiness、wallet readiness、exchange-write readinessを証明しません。

### 10. Trade[XYZ]の読み取り専用データ収集ができる

Trade[XYZ]は実装済みのvenue surfaceです。ただし、現在の開発主軸はvenue-neutral / backtest-firstです。

主なコマンド:

```bash
uv run sis probe trade-xyz
uv run sis collect-trade-xyz-quotes --write-summary --write-report
uv run sis collect-trade-xyz-data-cycle
uv run sis build-trade-xyz-data-readiness
uv run sis trade-xyz-collection-status
uv run sis validate-artifacts --strict
uv run sis phase-gate-review
```

できること:

- quoteを読み取り専用で収集する。
- WebSocket quoteやREST parityを検査する。
- reference data、signal candles、funding historyを生成物にする。
- data readinessを確認する。
- local artifactをschemaで検証する。
- `src/sis/backtest/engine/` と `src/sis/backtest/trade_xyz/` のPython APIでTrade[XYZ] pure backtest v0.1を扱う。

注意:

Trade[XYZ]の読み取り専用execution state collectionは、public user addressと明示opt-inが必要です。wallet、signing、exchange write、live orderは使いません。Trade[XYZ] pure backtestはpublic CLIではありません。

### 11. Crypto Perp Truth-Cycleの検証生成物を作れる

Crypto Perp Truth-Cycleは、暗号資産perpの急変イベントを、取引前提の物語ではなく証拠の連鎖として検証するためのMVPです。

主なコマンド:

```bash
uv run sis crypto-perp-config-validate --help
uv run sis crypto-perp-probe --help
uv run sis crypto-perp-probe-audit --help
uv run sis crypto-perp-raw-refresh --help
uv run sis crypto-perp-refresh --help
uv run sis crypto-perp-watchdeck --help
uv run sis crypto-perp-decision-record --help
uv run sis crypto-perp-outcome-record --help
uv run sis crypto-perp-account-probe --help
uv run sis crypto-perp-order-preview --help
uv run sis crypto-perp-tiny-live-measurement --help
uv run sis crypto-perp-tournament-rows-preview --help
uv run sis crypto-perp-tournament-report --help
uv run sis crypto-perp-tournament-gate --help
```

できること:

- lab configを検証する。
- Bitget public provider probeを行い、raw snapshotをimmutableに残し、probe auditでevent候補へ進める品質かを確認する。
- universe diff、ticker snapshot、15分足履歴、candle finality、gap、non-final bar qualityを確認する。
- slow / fast / near-miss eventを検出し、direction-neutralなevent artifactとevent cardを作る。
- candidateだけ高解像度に記録するraw-first capture manifestを作る。
- prospectiveな `SHORT` / `LONG` / `NO_TRADE` decisionと、matured outcomeをCLIで生成物に残す。
- credential redactionつきのread-only account snapshotと、exchange writeしないorder previewを作る。
- mock-onlyのtiny live measurement artifact、reduce-only close preview、flat reconciliationを扱う。
- actual cash ledger、execution replay、actual vs simulated fill bias calibrationを作る。
- matured outcomeから、before-cost proxyの `REVERSAL_SHORT`、`CONTINUATION_LONG`、`NO_TRADE` rows previewを作る。
- `REVERSAL_SHORT`、`CONTINUATION_LONG`、`NO_TRADE` を同じevent setで比較するtournament reportをCLIで作る。
- tournament reportから、actual cash不足、event不足、NO_TRADE leader、largest loss、profit concentration、operator timeを読んで次actionをlocal gate artifactにする。
- tournament reportをStrategy Input ContractへつなぐWorkbench bridge helperを使う。

注意:

この機能は、急騰後shortが勝つ前提ではありません。`REVERSAL_SHORT`、`CONTINUATION_LONG`、`NO_TRADE`、データ不足の `UNKNOWN` / `INCONCLUSIVE_DATA` を分けて扱います。primary metricは勝率やSharpeではなく、可能な範囲では `actual_cash_result_usd` です。

M09のtiny live measurementは、コードとmock testはありますが、実ネットワーク測定は実行済みではありません。実行には別の明示承認、`SIS_ENABLE_TINY_LIVE_MEASUREMENT=1`、`--confirm-live`、confirmation phrase、isolated margin、withdrawal disabled API key、IP restriction、max notional 25 USD、max open positions 1、no existing position、no existing open order、reduce-only close、flat reconciliationが必要です。

### 12. Execution / Paper / Bot系の状態確認ができる

本番注文ではなく、状態確認、paper、read-onlyの領域です。

主なコマンド:

```bash
uv run sis bot-preview
uv run sis execution-snapshot
uv run sis execution-venue-comparison
uv run sis execution-venue-diagnostics
uv run sis execution-read-only-surfaces
uv run sis venue-read-only-probe
uv run sis bitget-demo-smoke
uv run sis paper-step
uv run sis paper-from-intents --intents-path data/bot/paper_intent_preview.json
uv run sis paper-report
uv run sis paper-operations-cycle
```

できること:

- HOLD previewを作る。
- execution snapshotを作る。
- venue比較や診断を作る。
- venue read-only capabilityの境界を確認する。
- Bitget demo adapterのlocal / mock-first smokeを確認する。
- paper intentからpaper flow用の生成物を作る。

注意:

`bot-preview` はread-only HOLD previewです。wallet、signing、exchange writeは行いません。execution系には `order-status`、`estimate-order`、`balance-status`、`fill-status`、`cancel-order`、`close-position`、`reconcile-positions` もありますが、adapter境界に依存する状態確認・補助surfaceとして読みます。これらの名前があることを、production live order pathが完成している証拠として読んではいけません。Bitget demoはmock-firstで `external_write_enabled=false`、`exchange_write_used=false` を明示します。

### 13. Runtime / Risk / State補助を扱える

実運用そのものではなく、paper / read-only運用を安全に管理するための補助surfaceがあります。

主なコマンド:

```bash
uv run sis check-halt-policy
uv run sis check-timeframe
uv run sis market-session
uv run sis next-live-window
uv run sis daemon-manifest
uv run sis daemon-dry-run
uv run sis daemon-run --max-cycles 1
uv run sis export-state
uv run sis restore-state
uv run sis monitoring-status
uv run sis kill-switch --enable --reason manual
uv run sis schedule-run
uv run sis render-alert
uv run sis notification-outbox
uv run sis healthcheck
```

できること:

- halt policyやtimeframeの条件を確認する。
- 市場sessionや次のwindowを確認する。
- boundedなdaemon dry-run / runを実行する。
- SQLite stateをexport / restoreする。
- monitoring snapshot、kill-switch、schedule、alert、notification outboxを扱う。

注意:

daemonやkill-switchがあることは、本番自動売買が完成しているという意味ではありません。`daemon-run` は指定コマンドを周期実行する補助で、標準ではpaper系commandを対象にします。`--forever` は長時間実行になり得るため、実務では停止条件とkill-switchを先に確認します。

### 14. Operations / Audit / Remediationを作れる

運用状態、監査、修復計画を生成物にできます。

主なコマンド:

```bash
uv run sis operations-dashboard
uv run sis operations-bundle
uv run sis operations-timeline
uv run sis operations-audit-pack
uv run sis audit-dashboard
uv run sis audit-bundle
uv run sis current-state-index
uv run sis readiness-snapshot
uv run sis remediation-planner
uv run sis remediation-execution-plan
uv run sis remediation-session
uv run sis remediation-scoreboard
uv run sis refresh-operations-artifacts
```

できること:

- 現在状態をまとめる。
- readiness snapshotを作る。
- audit bundleを作る。
- remediation planを作る。
- 操作結果や証拠を生成物として残す。

注意:

readinessは「何に対する準備か」を必ず分けて読みます。read-only readiness、paper readiness、live readinessは別物です。

## いまできないこと

次は現時点の標準operator pathではできません。

- production live trading
- standard public live execution CLI
- wallet操作
- signing
- exchange write
- 実口座への本番注文
- backtestだけでの利益保証
- Strategy Reviewからのpaper実行許可
- Strategy Reviewからのlive実行許可
- smoke passをnormal paper passとして扱うこと
- `PaperIntentPreview` をlive orderに変換すること
- Strategy Authoring YAMLの自動改訂適用
- AI / ML / optimizer判断の自動採用
- Svelte UIアプリとしての操作画面
- 実際のscale-up execution
- daemon / scheduleがあることを根拠にした無人live運用
- execution系CLI名だけを根拠にした本番注文実行
- Bitget demo smokeを根拠にしたproduction Bitget readiness
- Crypto Perp M09 mock testを根拠にした実ネットワークtiny live実行済み扱い
- Crypto Perp tournamentを根拠にした利益保証
- `REVERSAL_SHORT` だけを特別扱いするshort固定schema

## 代表的な実行ルート

外部APIや取引所接続を使わず、戦略からbacktest HTMLまで見る最短寄りのルートです。

```bash
uv run python scripts/seed_strategy_authoring_baseline_data.py
uv run sis strategy-author-validate --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml
uv run sis strategy-author-run --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml --through backtest
uv run sis strategy-backtest-pack --benchmark-series-path docs/strategy_research_lab/examples/external_benchmark_series.csv
uv run sis strategy-backtest-pack-validate
uv run sis strategy-backtest-artifact-summary
uv run sis strategy-backtest-html-report
```

このルートで確認できること:

- YAML戦略が検証を通るか。
- signalとbacktest metricsを生成できるか。
- backtest packを作れるか。
- pack validationを実行できるか。
- HTML reportで結果を読めるか。

このルートで確認できないこと:

- 実市場で利益が出るか。
- paper orderを実行してよいか。
- live order、wallet、signing、exchange writeが動くか。
- Bitget / Hyperliquid production venueとして使えるか。

## 主な生成物の読み方

このアプリは、CLIがJSON、Markdown、HTML、Parquetなどの生成物を作り、それを次のCLIや人間が読む構造です。

| 生成物 | わかりやすい説明 | 読み方 |
|---|---|---|
| `strategy_input_contract.v1` | 戦略が前提にする入力データの契約書 | データの出所、hash、利用可能時刻、欠落を読む |
| `strategy_idea.v1` | 戦略の種 | 仮説、比較対象、失敗条件、リスクを読む |
| `data_snapshot_manifest.v1` | データsnapshotの記録 | データ範囲、hash、作成元を読む |
| `feature_snapshot_manifest.v1` | 特徴量snapshotの記録 | どの特徴量をどの時点で作ったかを読む |
| `strategy_signal_manifest.v1` | signal生成の記録 | generator、入力、出力、hashを読む |
| `cost_snapshot` / cost matrix | 手数料やコスト前提 | venueごとのコスト前提を読む |
| `strategy_authoring_spec.v1` | YAML戦略定義 | どの条件で入退出するかを読む |
| `strategy_authoring_backtest_result.v1` | 単体backtest結果 | trade数、return、drawdown、合格判定を読む |
| `strategy_backtest_pack.v1` | backtest関連生成物の束 | どの結果を含めたかを読む |
| `strategy_backtest_pack_validation.v1` | backtest packの検証結果 | 欠損、hash、no-live境界を読む |
| `strategy_review_manifest.v1` | review packetの根拠 | reviewが読んだsource artifactを読む |
| `operator_strategy_review.v1` | 人間レビューの記録 | reviewer、decision、rationale、permission falseを読む |
| `strategy_stage_policy.v1` | 段階ごとの進行条件 | paper smoke、normal paper、drift、micro live plan条件を読む |
| `strategy_stage_decision.v1` | 次段階判定 | 何が通り、何が不足しているかを読む |
| `strategy_runtime_observation_manifest.v1` | paper runtime観察の読み込み結果 | fills、blocked、no-fill、spread、quote ageを読む |
| `paper_vs_backtest_drift_review.v1` | backtestとpaper runtimeの差分 | 想定と実観察のズレを読む |
| `strategy_learning_event.v1` | 学習イベント | 修正すべき発見と理由を読む |
| `strategy_revision_request.v1` | 改訂要求 | 何を直すべきかを読む |
| `strategy_case_lite.v1` | 戦略ごとの簡易timeline | 戦略の履歴を読む |
| `strategy_daily_brief.v1` | 日次確認リスト | 今日見るべきartifactを読む |
| `strategy_ai_review_packet.v1` | AIレビュー用packet | AIに渡す安全な要約範囲を読む |
| `strategy_model_run.v1` | model runの記録 | modelやoptimizerの結果を記録として読む |
| `strategy_micro_live_plan.v1` | micro live前の計画 | 実行許可ではなく人間確認用計画として読む |
| `strategy_live_observation_manifest.v1` | 既存canary evidenceの読み込み | live実行ではなく既存証拠の観察として読む |
| `strategy_scale_decision.v1` | 拡大判断 | scale-up実行ではなく判断材料として読む |
| `strategy_next_scale_plan.v1` | 次の拡大計画 | execution permissionではなく計画として読む |
| `strategy_workbench_viewer.v1` | static viewerの根拠 | どのartifactをHTMLに並べたかを読む |
| `venue_read_only_probe_summary.v1` | venue境界確認 | no-network / no-write境界を読む |
| `crypto_perp_lab_config.v1` | Crypto Perp検証設定 | public data、境界、thresholdを読む |
| `crypto_perp_provider_probe.v1` | Bitget public probe結果 | どのpublic endpointを読み、raw snapshotを残したかを読む |
| `crypto_perp_probe_audit.v1` | public probe後の品質検査 | endpoint、row count、raw snapshot欠落、event refresh可否を読む |
| `crypto_perp_universe_snapshot.v1` | 対象銘柄 universe | universe diffやinstrument metadataを読む |
| `crypto_perp_raw_refresh.v1` | audit済みrawからの再生成記録 | universe、market、quality、event候補、known gapsを読む |
| `crypto_perp_market_snapshot.v1` | ticker / candle snapshot | 価格、15分足、finality、品質を読む |
| `crypto_perp_event.v1` | 急変event | eventの方向、特徴量、品質、near-missを読む |
| `crypto_perp_decision.v1` | prospective decision | `SHORT` / `LONG` / `NO_TRADE` と理由を読む |
| `crypto_perp_outcome.v1` | matured outcome | decision後に何が起きたかを読む |
| `crypto_perp_capture_manifest.v1` | candidate recorderの記録 | raw-first segment、sequence、checksumを読む |
| `crypto_perp_account_snapshot.v1` | read-only account snapshot | credential redactionとread-only境界を読む |
| `crypto_perp_order_preview.v1` | non-writing order preview | `side`、`entry_vwap`、book side、clientOid、no-write境界を読む |
| `crypto_perp_live_measurement.v1` | tiny live measurement記録 | mock / live区分、guard、reduce-only close、flat reconciliationを読む |
| `crypto_perp_cash_ledger.v1` | actual cash ledger | 実損益、fee、funding、cash basisを読む |
| `crypto_perp_execution_replay.v1` | replay calibration | simulated fillとactual fillの差を読む |
| `crypto_perp_tournament_rows_preview.v1` | outcomeから作る3action rows preview | before-cost proxyでありactual cashではないことをknown gaps込みで読む |
| `crypto_perp_tournament_report.v1` | 仮説比較report | `REVERSAL_SHORT`、`CONTINUATION_LONG`、`NO_TRADE`を同一event setで読む |
| `crypto_perp_tournament_gate.v1` | tournament後のlocal gate | tiny live承認準備へ進むか、actual cash再生成 / event追加 / revisionへ戻すかを読む。Daily Brief / Workbench Viewer でも索引対象 |

## 用語集

### repo / repository

コード、文書、設定、テストをまとめた作業場所です。この文書では `/home/tn/projects/marketlens-strike` を指します。

### workspace

開発作業をしているディレクトリ全体です。このrepoではrepo rootとほぼ同じ意味で使われます。

### CLI

Command Line Interfaceの略です。ブラウザ画面ではなく、ターミナルから実行するコマンドです。このrepoの主な入口は `uv run sis ...` です。

### `uv`

Pythonの依存関係と実行環境を管理するツールです。このrepoでは `uv sync --dev --locked` や `uv run sis ...` を使います。

### `sis`

このrepoのCLIアプリ名です。`pyproject.toml` の script entrypointで `sis = "sis.cli:main"` として登録されています。

### artifact / 生成物

コマンド実行で作られるJSON、Markdown、HTML、Parquetなどの結果ファイルです。人間が読むものも、次のコマンドが読むものもあります。

### schema

生成物の形を決めるルールです。どの項目が必要か、値の種類は何か、許される値は何かを定義します。

### manifest

生成物の目録です。どのファイルを読んだか、hashは何か、いつ作ったか、境界違反があるかを記録します。

### hash / sha256

ファイル内容から計算する指紋のような値です。同じファイルを読んだか、途中で変わっていないかを確認するために使います。

### YAML

人間が読み書きしやすい設定ファイル形式です。このrepoでは戦略定義や設定に使います。

### JSON

機械が読みやすいデータ形式です。多くの生成物はJSONです。

### JSONL / NDJSON

1行に1つのJSONを書く形式です。ledgerのような追記型の記録に使います。

### Parquet

表形式データを効率よく保存するファイル形式です。特徴量や研究データの保存に使います。

### Strategy

売買戦略です。どの銘柄を見るか、いつ買うか、いつ売るか、どれくらいの損失で止めるかなどのルールです。

### Strategy Lab

戦略アイデアからsignal、評価、候補、paper-only previewまでをつなぐ研究用の作業台です。

### Strategy Authoring

YAMLで戦略ルールを書き、検証、説明、backtestへ進める仕組みです。

### signal

買い、売り、見送りなどの判断材料です。実注文ではありません。

### candidate

検証対象として残した候補です。合格や注文許可ではありません。

### promotion decision

候補を次の段階へ進めるか、保留するかなどの判断記録です。paper / liveの許可とは分けて読みます。

### PaperIntentPreview

本番資金を使わないpaper用の仮注文意図です。live orderではありません。

### backtest

過去データで戦略を試すことです。将来の利益保証ではありません。

### benchmark

比較対象です。戦略が市場平均や単純な保有と比べてどうかを見るために使います。

### stress

手数料増加、滑り、悪条件などを加えて、戦略が壊れやすいかを見る検査です。

### no-lookahead

未来の情報を使っていないかを調べる検査です。未来情報を使うと、backtestが実際より良く見えることがあります。

### data availability

必要なデータが十分にあるかを見ることです。データ欠損が多いと、backtest結果の信頼性は下がります。

### feature panel

価格、マクロ、イベントなどから作った特徴量の表です。戦略のsignal生成や研究に使います。

### real_market

実市場側の価格やマクロデータを扱う領域です。venue execution側のquoteとは分けて読みます。

### tracking

実市場データとvenue側データの差分や品質を見て、取引可能か、比較可能かを確認する領域です。

### cost matrix

venueや銘柄ごとの手数料、spread、滑りなどのコスト前提をまとめた表です。backtestや判断の前提になります。

### return

どれくらい増減したかを表す値です。returnだけで戦略の良し悪しは決めません。

### drawdown

途中でどれくらい大きく負けたかを表す値です。損失の深さを見るために使います。

### slippage / 滑り

想定価格と実際に約定した価格のズレです。本番に近づくほど重要になります。

### cost / 手数料

取引にかかる費用です。手数料を甘く見ると、backtestが実際より良く見えます。

### Strategy Review

backtestや関連生成物を、人間が読みやすいreview packetにする仕組みです。判断記録も残せますが、注文許可ではありません。

### operator

このアプリを操作し、資料を読んで判断する人間です。

### human-in-the-loop

機械だけで自動決定せず、人間の確認や判断を必ず挟む運用です。

### Strategy Operations Workbench

戦略の入力、review、stage判定、paper smoke、runtime observation、drift review、learning、scale計画を生成物でつなぐ作業台です。実運用botそのものではありません。

### Crypto Perp Truth-Cycle

Bitget public dataからevent snapshot、event card、prospective decision、matured outcome、cash ledger、tournamentへつなぐ検証用artifact chainです。自動売買botではなく、証拠を残して仮説を比較するための仕組みです。

### event card

Crypto Perp eventを人間が読みやすいMarkdownにしたものです。eventの方向、特徴量、品質、判断材料を読むためのカードで、注文指示ではありません。

### prospective decision

未来の結果を見る前に記録する判断です。Crypto Perpでは `SHORT`、`LONG`、`NO_TRADE` を扱います。勝てると決めた方向を後から選ぶことを避けるための記録です。

### matured outcome

prospective decisionの後、指定した観察窓が終わってから作る結果記録です。decision時点で見えなかった結果を分けて扱うために使います。

### actual cash

実際のcash basisで見た損益です。Crypto Perpでは、可能な範囲で勝率やSharpeよりも `actual_cash_result_usd` を優先して読みます。

### tournament

同じevent setに対して複数の仮説を比べるreportです。Crypto Perpでは `REVERSAL_SHORT`、`CONTINUATION_LONG`、`NO_TRADE` を同格に扱い、データ不足は `INCONCLUSIVE_DATA` として残します。`crypto-perp-tournament-rows-preview` が作るrowsは outcome 由来の before-cost proxy で、実約定、fee、funding、slippage込みのactual cashではありません。preview artifactをreport入力にした場合、この不足はknown gapsとしてreportへ継承されます。

### tournament gate

tournament reportを読んで、tiny live承認準備へ進めるか、actual cash再生成、event追加、event定義見直しへ戻すかを分けるlocal artifactです。`READY_FOR_HUMAN_TINY_LIVE_REVIEW` でも、live実行許可ではありません。

### stage policy

次の段階へ進む条件を定義した設定です。たとえばpaper smoke、normal paper observation、drift reviewなどの条件を持ちます。

### stage decision

stage policyと証拠を読んで、次の段階に進めるかを記録した生成物です。許可証ではありません。

### paper

本番資金を使わない検証です。本番注文ではありません。

### paper smoke

paper workflowの短い動作確認です。normal paper observation passではありません。

### normal paper observation

短いsmokeではなく、通常基準でpaper観察を積むことです。日数、約定、品質などの条件を分けて読みます。

### runtime observation

実行時の観察結果を読むことです。このrepoの該当機能はpaper runtime artifactの読み込みが中心です。

### drift review

backtestで想定した結果と、paper runtimeで観察した結果のズレを見るレビューです。

### learning ledger

観察やdrift reviewから得た学びを追記していく台帳です。

### revision request

戦略や前提を直すべき点を、人間が確認できる改訂要求としてまとめた生成物です。

### AI review

AIに読ませるための安全な要約packetや、AIのコメントを記録する仕組みです。自動採用はしません。

### optional framework

標準機能とは別に、vectorbt、bt、quantstatsなどの外部ライブラリを使う補助経路です。依存関係やライセンス、結果の意味を分けて読みます。

### legacy bridge

古い流れとの互換入口です。`build-backtest` はこの文脈で読み、Trade[XYZ] pure backtestのPython APIとは分けます。

### model run

モデルやoptimizerの結果を記録することです。このrepoでは記録が中心で、自動採用や自動実行ではありません。

### optimizer

条件やパラメータを探す仕組みです。結果が良く見えても、過剰最適化の危険があります。

### micro live plan

小さなlive観察へ進む前の計画生成物です。micro live execution permissionではありません。

### live

本番取引です。実口座、署名、取引所書き込み、実資金のリスクを含む領域です。

### canary

本格展開前の小さな観察単位です。このrepoのlive observation ingestは既存canary evidenceを読む境界であり、新規live注文を出す意味ではありません。

### scale decision

規模を拡大するかどうかの判断材料です。scale-up executionそのものではありません。

### static viewer

既存の生成物をHTMLとして並べる読み取り用ビューアです。artifactを編集したり、paper / liveを許可したりしません。

### NDX / QQQ

米国株指数やETFに関する研究対象です。このrepoではNDX / QQQ系の研究gateが実装されています。

### Layer 2.2 / 2.3 / 2.4

NDX研究の段階名です。DAG、特徴量、残差、validationなどを段階的に確認するためのローカル研究gateです。本番注文の段階ではありません。

### venue

取引所や取引先のことです。このrepoではTrade[XYZ]やBitget demoなどが文脈に出ます。

### Trade[XYZ]

このrepoに実装されている主要venue surfaceです。読み取り専用データ収集やbacktest文脈で使われますが、現在の標準主軸はvenue-neutralです。

### Bitget demo

Bitgetの本番ではなくdemo検証用のsurfaceです。`configured` は本番接続や注文成功を意味しません。

### read-only

読み取り専用です。外部の口座や取引所の状態を書き換えない、注文しない、という意味です。

### mock-first

最初にmockやlocal状態で確認し、外部APIや外部書き込みへ暗黙に進まない設計です。Bitget demo smokeはこの境界で読みます。

### credential

API key、secret、passphraseなどの認証情報です。存在しても、ただちに本番注文許可を意味しません。

### wallet

資金やアカウントを操作するための財布・認証領域です。このrepoの現行標準pathでは使いません。

### signing

取引所やウォレットに対する署名処理です。注文や資金操作に関わるため、現行標準pathでは扱いません。

### exchange write

取引所へ注文やキャンセルなどの書き込みをすることです。このrepoの現行標準operator pathでは許可しません。

### halt policy

損失や異常時に停止するためのルールです。安全補助であり、利益を保証する仕組みではありません。

### kill-switch

運用を止めるための手動または状態ベースの停止機構です。これがあることは、無人live運用が完成しているという意味ではありません。

### daemon

同じ処理を一定間隔で繰り返す実行補助です。このrepoではpaper / read-only文脈の補助として読み、live自動売買完成とは扱いません。

### state store

実行状態を保存する場所です。このrepoでは `data/state/marketlens.sqlite` などのSQLite stateが文脈に出ます。

### SQLite

ファイル1つで使える軽量データベースです。state保存や再開補助に使われます。

### readiness

準備状態です。read-only readiness、paper readiness、live readiness、wallet readinessは別物です。どれについての準備かを必ず分けて読みます。

### gate

次の段階へ進む前の確認関門です。gate通過は、そのgateの範囲に限った意味です。

### fail closed

条件が足りない時に安全側へ倒して止めることです。取引や次段階へ勝手に進まない設計です。

### leakage

未来の情報や本来使えない情報が検証に混ざることです。backtestが実際より良く見える原因になるため、no-lookaheadやdata availabilityで疑いを減らします。

## 誤読しやすい表示

| 表示 | 正しい意味 | 誤読してはいけない意味 |
|---|---|---|
| `PASS` | その検査に通った | 利益保証、paper許可、live許可 |
| `READ_ONLY_GO` | read-only / paper gateの範囲で確認が進められる | live trading ready |
| `READY_FOR_AUTHORING_DRAFT` | Strategy Authoring下書きに進める候補 | paper / live許可 |
| `READY_FOR_PAPER_SMOKE_PLAN` | paper smoke plan生成に進める候補 | paper order実行許可 |
| `READY_TO_RUN_SMOKE_CYCLE` | smoke cycle実行計画ができた | normal paper pass |
| `PAPER_OBSERVATION_CANDIDATE` | 次の検証候補 | paper実行許可 |
| `READY_FOR_HUMAN_REVIEW` | 人間レビュー資料を読める状態 | 合格、取引許可 |
| `READY_FOR_HUMAN_DRIFT_REVIEW` | drift reviewを人間が読む状態 | micro live許可 |
| `LIVE_OBSERVATION_INGESTED` | 既存canary evidenceを読んだ | live実行済み、scale-up許可 |
| `READY_FOR_HUMAN_SCALE_REVIEW` | scale判断を人間が読む状態 | scale-up実行許可 |
| `READY_FOR_HUMAN_NEXT_SCALE_REVIEW` | next scale planを人間が読む状態 | next-scale実行許可 |
| `backtest_passed=true` | YAML内の閾値を満たした | alpha証明 |
| `crypto_perp_live_measurement.v1` | tiny live measurementの記録形式 | 実ネットワーク測定済みの証明 |
| `REVERSAL_SHORT` | 比較対象の仮説の1つ | short固定の勝ち前提 |
| `NO_TRADE` | 取引しない判断または比較対象 | 失敗や未実装 |
| `actual_cash_result_usd` | cash basisの主要評価値 | 単体で将来利益を保証する値 |

## どの文書を読めばよいか

| 知りたいこと | 読む文書 |
|---|---|
| 技術者向けではない利用者目線の説明 | [APP_USER_GUIDE_NON_TECHNICAL_2026-06-20.md](APP_USER_GUIDE_NON_TECHNICAL_2026-06-20.md) |
| 最短の現在地 | [CURRENT_STATE.md](CURRENT_STATE.md) |
| 機能一覧 | [IMPLEMENTED_SURFACES.md](IMPLEMENTED_SURFACES.md) |
| 専門用語少なめの機能説明 | [REPO_CAPABILITIES_PLAIN_JA_2026-06-17.md](REPO_CAPABILITIES_PLAIN_JA_2026-06-17.md) |
| 技術寄りの詳細 | [REPO_CAPABILITIES_CURRENT_2026-06-16.md](REPO_CAPABILITIES_CURRENT_2026-06-16.md) |
| CLIコマンド一覧 | [REPO_CLI_CATALOG_CURRENT_2026-06-17.md](REPO_CLI_CATALOG_CURRENT_2026-06-17.md) |
| 戦略とbacktestの人間向け説明 | [STRATEGY_AND_BACKTEST_USER_GUIDE.md](STRATEGY_AND_BACKTEST_USER_GUIDE.md) |
| AI / Codex向けの戦略操作ガイド | [AI_AGENT_STRATEGY_BACKTEST_GUIDE.md](AI_AGENT_STRATEGY_BACKTEST_GUIDE.md) |
| Strategy Review | [strategy_review/README.md](strategy_review/README.md) |
| Backtest | [backtest/README.md](backtest/README.md) |
| Strategy Research Lab | [strategy_research_lab/README.md](strategy_research_lab/README.md) |
| NDX研究 | [research/ndx/README.md](research/ndx/README.md) |
| Paper observation / lifecycle | [strategy_lifecycle/README.md](strategy_lifecycle/README.md) |
| Crypto Perp Truth-Cycle MVP | [../plan/0621ここから01/marketlens-strike-crypto-perp-mvp-final-plan-2026-06-20/00_READ_ME_FIRST.md](../plan/0621ここから01/marketlens-strike-crypto-perp-mvp-final-plan-2026-06-20/00_READ_ME_FIRST.md) |
| Operations | [OPERATIONS_RUNBOOK.md](OPERATIONS_RUNBOOK.md) |
| Trade[XYZ]初心者向け | [trade_xyz_bot_beginner_guide.md](trade_xyz_bot_beginner_guide.md) |

## 実務上の読み方

このrepoで「できる」と書いてあるものの多くは、local fileを読み書きするartifact workflowです。

外部API、wallet、signing、exchange write、live orderに接続する機能として読んではいけません。

何かの判断をする時は、次の順で確認します。

1. `uv run sis --help` で実際にCLIにあるかを見る。
2. 対象コマンドの `--help` を見る。
3. `schemas/` で生成物の形を見る。
4. `tests/` で期待挙動を見る。
5. `docs/` は読みやすい入口として使う。
6. `data/` のruntime artifactは、必要なら再生成して読む。

## 現状の一言まとめ

`marketlens-strike` は、個人システムトレーダーが戦略を雑に本番投入しないための、CLI中心の研究・backtest・review・paper観察・Crypto Perp検証・安全gate作業台です。

現時点で強いのは、証拠を残しながら「まだ進めない理由」を見える化することです。

現時点で未完なのは、本番運用、実注文、ウォレット、署名、取引所書き込み、フルUI、実際のscale-up executionです。
