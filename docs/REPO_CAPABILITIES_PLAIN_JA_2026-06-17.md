<!--
作成日: 2026-06-17_17:50 JST
更新日: 2026-06-17_21:13 JST
-->

# いまのリポジトリでできること、できないこと

## 結論

このリポジトリは、売買戦略をいきなり本番注文に出すためのものではありません。

いまできることは、戦略案を作る、過去データで試す、人間が読むレビュー資料を作る、ペーパー観察の記録を読む、次に進んでよいかをローカルの証拠ファイルで確認することです。

いまできないことは、本番の自動売買、ウォレット操作、署名、取引所への書き込み、バックテストだけで「儲かる」「本番に出してよい」と証明することです。

## 追加調査での補正

前回版の大枠は正しいですが、実装済み機能のうち、Strategy Research Lab、paper operations、operations / audit / remediation、Trade[XYZ] pure backtest、Bitget demo smoke の説明が薄かったため補いました。

確認に使った主な根拠:

- `uv run sis --help`: 公開されている CLI コマンド一覧です。利用者が実行できる入口を確認しました。
- `docs/IMPLEMENTED_SURFACES.md`: 実装済みの主要機能を一覧化した文書です。
- `docs/REPO_CAPABILITIES_CURRENT_2026-06-16.md`: 技術寄りに詳細な capability catalog です。
- `data/research/strategy_lifecycle/paper_observation_status.json`: 現在の paper observation 状態を機械が読みやすい形でまとめた生成物です。

## まず知っておくこと

- `data/` は実行時に作られる生成物置き場です。git 管理外なので、新しい checkout では存在しないことがあります。
- コード、テスト、schema、CLI help が正本です。文書はそれらを読みやすくまとめたものです。
- `paper` は本番資金を使わない検証の意味です。本番注文ではありません。
- `live` は本番取引の意味です。このリポジトリの標準 operator CLI は、現時点で live 注文を許可していません。

## いまできること

### 1. 戦略案をファイルとして書ける

売買ルールを YAML という設定ファイルに書き、検証や説明をできます。たとえば、移動平均、RSI、ATR、ボリンジャーバンドのような指標、買い条件、売り条件、ポジションサイズ、損切りや利確のルールを扱えます。

主な入口:

```bash
uv run sis strategy-author-init
uv run sis strategy-author-validate --spec path/to/spec.yaml
uv run sis strategy-author-explain --spec path/to/spec.yaml
uv run sis strategy-author-run --spec path/to/spec.yaml --through backtest
```

ここで `path/to/spec.yaml` は、戦略ルールを書いた YAML ファイルへの例示パスです。

### 2. Strategy Research Lab で候補作りから paper-only preview まで進められる

Strategy Research Lab は、戦略アイデアを signal、評価、候補、昇格判断、paper-only の仮注文意図までつなぐための作業台です。

ここでいう signal は「買い・売り・見送りなどの判断材料」、candidate は「検証対象として残した候補」、paper-only preview は「本番注文ではない仮の注文意図」です。

主な入口:

```bash
uv run sis strategy-preview
uv run sis strategy-experiment-run --spec path/to/strategy_experiment.yaml
uv run sis evaluate-strategy-lab
uv run sis build-paper-candidate-pack
uv run sis promotion-decision --decision hold
uv run sis build-paper-intent-preview
```

ここで `path/to/strategy_experiment.yaml` は、Strategy Research Lab 用の実験設定を書いた YAML ファイルへの例示パスです。

この流れで作る `PaperIntentPreview` は、本番注文ではありません。paper-only の仮注文意図であり、live 変換は許可されません。

### 3. 過去データで戦略を試せる

過去の価格データを使い、戦略が過去にどう動いたかを試せます。単発の backtest だけでなく、期間を分けた検査、条件を変えた検査、ストレス検査、ベンチマーク比較もできます。

ただし、backtest は「過去ならこうだった」という検査です。将来の利益や本番安全性の証明ではありません。

主な入口:

```bash
uv run sis strategy-backtest-suite --help
uv run sis strategy-backtest-pack --help
uv run sis strategy-backtest-pack-validate --help
```

### 4. 人間が読むレビュー資料を作れる

backtest の結果や関連ファイルを集めて、人間が確認しやすい review packet を作れます。さらに、人間が読んだ事実を `operator_review.yaml` として記録し、あとで同じ資料を見ていたかを hash で確認できます。

これは「人間が確認した」という記録です。paper 実行や live 実行の許可ではありません。

主な入口:

```bash
uv run sis strategy-review-build --help
uv run sis strategy-review-record --help
```

### 5. ペーパー観察の現在地を確認できる

ペーパー観察とは、本番資金を使わずに、候補戦略が想定どおりに紙上の注文や約定として記録されるかを見る段階です。

現行レポートでは、通常のペーパー観察がまだ足りない状態です。

- 通常ペーパー観察の session 数: `8`
- smoke session 数: `1`
- 最新の通常 session: `local-paper-20260617-200702`
- 最新の通常判定: `NEEDS_MORE_PAPER_OBSERVATION`
- 最新の smoke 判定: `PASS_PAPER_OBSERVATION_REVIEW`
- 通常基準を満たしたか: `false`
- 最新通常 session の fills: `20 / 20`、不足 `0`
- 最新通常 session の trading days: `1 / 10`、不足 `9`
- smoke の合格を通常合格に数えるか: `false`
- 不足 artifact: なし
- 古い artifact: なし
- 禁止された live / wallet / exchange write の混入: なし
- 次の実務アクション: `continue_normal_paper_observation`
- live 注文許可: `false`

つまり、短縮検査である smoke は通っていますが、通常基準のペーパー観察はまだ不足しています。次は live ではなく、通常基準のペーパー観察を続けます。

ここでの「通常ペーパー観察の session 数」は、合格条件そのものではありません。一般的に言うと「観察を何回開始したか」の数です。通常基準の合格には、最新の通常 session そのものが `20 fills` と `10 trading days` を満たす必要があります。いまの最新通常 session は `20 fills` には到達しましたが、まだ `1 trading day` だけなので、通常基準を満たしたとは言えません。機械的に確認する場合は `latest_normal_requirement_gaps` を見ます。

ここでいう「続ける」は、同じ日の生成物を何度も作り直すことではありません。`trading days` は観測できた取引日の数なので、同じ取引日の fill を増やしても、`10 trading days` の代わりにはなりません。次に必要なのは、別の取引日を含む通常観察の証拠です。

また、`strategy-paper-observation-cycle` で同じ session id を使い回すことはできません。既存 session artifact がある場合は止まります。これは、どの入力ファイルから作られた観察なのかが曖昧になるのを避けるためです。

既存 session に1回分追記する場合は、専用の `strategy-paper-observation-append` を使います。これは既存 session manifest の hash を確認してから、同じ ledger に追記し、review / lifecycle / status を再生成します。

主な入口:

```bash
uv run sis strategy-paper-observation-append \
  --data-dir data \
  --artifact-dir data/research/ndx \
  --reports-dir data/reports \
  --session-manifest data/paper/observations/<session_id>/paper_observation_session_manifest.json

uv run sis strategy-paper-observation-status \
  --data-dir data \
  --out data/research/strategy_lifecycle \
  --reports-dir data/reports
```

ここで `data` は生成物の置き場、`data/research/strategy_lifecycle` は戦略の段階判断を置く場所、`data/reports` は人間向けレポートを置く場所です。

このレポートで判断できるのは、現在の生成物が「通常基準の paper 観察として十分か」「smoke だけの合格か」「古い生成物や不足があるか」「禁止された live 系の副作用が混ざっていないか」です。

このレポートだけでは、損益、将来の勝率、実口座の安全性、取引所接続の成功、本番注文の可否は判断できません。

### 6. NDX 系の研究ゲートをローカルで回せる

NDX / QQQ 系の研究について、データの出どころ、特徴量、残差検証、Strategy Lab への研究用 export、paper observation までの段階的な gate をローカル生成物として確認できます。

これは研究用の段階管理です。外部 API を勝手に呼ぶものでも、本番注文に接続するものでもありません。

主な入口:

```bash
uv run sis research-layer22-validate --root configs/research_layer_2_2/ndx
uv run sis research-ndx-source-resolve --root configs/research_layer_2_2/ndx --out data/research/ndx
uv run sis research-ndx-residual-validate --root configs/research_layer_2_2/ndx --artifact-dir data/research/ndx --reports-dir data/reports --out data/research/ndx
```

ここで `configs/research_layer_2_2/ndx` は NDX 研究の設定ディレクトリ、`data/research/ndx` は NDX 研究の生成物出力先、`data/reports` は人間向けレポートの出力先です。

### 7. paper operation artifact を扱える

paper operation は、本番資金を使わない paper 用の注文、約定、レポートの生成物を扱う領域です。

主な入口:

```bash
uv run sis paper-step
uv run sis paper-from-intents --intents-path data/bot/paper_intent_preview.json
uv run sis paper-report
uv run sis paper-operations-cycle
```

ここで `data/bot/paper_intent_preview.json` は、paper-only の仮注文意図を保存する生成物です。

注意点として、NDX / QQQ 系は valid な paper-observation evidence がない限り、paper candidate selection や legacy `paper-step` の注文生成で fail closed します。fail closed とは、条件が揃わない時に安全側へ倒して止めるという意味です。

### 8. 読み取り専用の venue 検査や運用状態確認ができる

Trade[XYZ] の読み取り専用データ収集、venue capability の境界確認、operations dashboard、phase gate、artifact validation を実行できます。

読み取り専用とは、外部の口座や取引所の状態を書き換えないという意味です。

主な入口:

```bash
uv run sis venue-read-only-probe
uv run sis collect-trade-xyz-quotes --write-summary --write-report
uv run sis validate-artifacts --strict
uv run sis phase-gate-review
```

operations / audit / remediation 系では、現状確認、監査用 bundle、修復計画、証拠の取り込み、readiness snapshot を作れます。

主な入口:

```bash
uv run sis operations-dashboard
uv run sis operations-bundle
uv run sis audit-bundle
uv run sis readiness-snapshot
uv run sis remediation-planner
```

ここで readiness snapshot は「何の準備ができているか」を見るための生成物です。live readiness と read-only / paper readiness は別物として読みます。

2026-06-17_20:17 JST の補助確認では、`diagnose-quotes --venue trade_xyz` は current Trade[XYZ] symbols の診断を出力し、`check-go-no-go` は `GO`、`build-evidence-card` は `data/evidence/evidence_card_20260617_111729.json` を生成しました。ただし、これらは補助レポートです。最終的な段階判断は `phase-gate-review` を見ます。

2026-06-17_20:44 JST に execution 系のローカル生成物も再計算しました。結果はまだ `degraded` です。Trade[XYZ] の読み取り専用 execution state collector は実装済みですが、通常実行では外部 API を勝手に呼ばず、public user address が未設定のため `trade_xyz_execution_state_user_address_missing` で止まります。Bitget demo は資格情報がなく read-only network probe も実行されていません。

2026-06-17_20:44 JST 時点では、`execution-drift-overview` と `phase-gate-review` の理由表示も補正済みです。現在の状態は「空の snapshot」とは扱わず、`trade_xyz_execution_state_user_address_missing` として表示します。次に必要な操作は `set_trade_xyz_execution_state_public_user_address`、つまり読み取り対象にする public user address を設定することです。

2026-06-17_19:24 JST のローカル再計算では、operations dashboard は `degraded` でした。これは「読み取り専用や paper gate が落ちた」という意味ではなく、Trade[XYZ] と Bitget demo の execution 状態がまだ揃っていないという意味です。`phase-gate-review` は `READ_ONLY_GO` のままですが、operations readiness と live readiness は未達です。

### 9. Trade[XYZ] pure backtest と Bitget demo smoke を扱える

Trade[XYZ] pure backtest v0.1 は実装済みですが、公開 CLI ではなく Python API です。`build-backtest` とは別のものとして読みます。

- `src/sis/backtest/engine/`: backtest の共通エンジン実装を置くディレクトリです。
- `src/sis/backtest/trade_xyz/`: Trade[XYZ] 向け backtest 実装を置くディレクトリです。
- `tests/backtest/`: backtest の挙動を確認する自動テストの置き場です。

Bitget demo smoke は local / mock-first の検証です。

```bash
uv run sis bitget-demo-smoke
```

`bitget-demo-smoke` の `status=configured` は、ローカル設定が揃ったという意味です。Bitget の network 接続、口座 readiness、注文送信、約定同期の成功ではありません。

## いまできないこと

- 本番の自動売買はできません。
- ウォレット操作、署名、取引所への書き込みはできません。
- 標準 operator CLI から live 注文を送ることはできません。
- Trade[XYZ] pure backtest を `uv run sis build-backtest` の入口で実行することはできません。pure backtest は Python API surface です。
- backtest だけで「儲かる」「paper に進めてよい」「live に進めてよい」とは言えません。
- smoke の合格を、通常のペーパー観察合格として扱うことはできません。
- paper operation の生成物を、そのまま live order として変換することはできません。
- Strategy Review の `operator_review.yaml` を、paper execution permission や live permission として読むことはできません。
- Bitget futures と Hyperliquid perp は、現時点では正式な Strategy Lab の取引先として使えません。
- `bitget_demo` は demo 検証用です。本番 Bitget futures readiness ではありません。
- Alpaca や Bitget などの credentialed external API を、暗黙に使う workflow にはしていません。
- `data/` にある生成物は git 管理外なので、fresh checkout でそのまま存在するとは限りません。

## 誤読しやすい言葉

- repo / リポジトリ: このコードと文書をまとめた作業場所です。
- CLI: ターミナルから実行するコマンド群です。ここでは `uv run sis ...` が主な入口です。
- artifact / 生成物: コマンド実行で作られる JSON、Markdown、Parquet などの結果ファイルです。
- schema: 生成物の形を決めるルールです。どの項目が必要か、値の種類は何かを定義します。
- backtest: 過去データで戦略を試すことです。将来利益の保証ではありません。
- paper: 本番資金を使わない検証です。本番注文ではありません。
- live: 本番取引です。実口座、署名、取引所書き込みを含む領域です。
- readiness: 準備ができているかの状態です。何に対する準備かを必ず分けて読みます。
- smoke: 短い動作確認です。通常基準を満たした証明ではありません。
- threshold / 基準: 合格に必要な最低条件です。たとえば約定数や観測日数です。
- lifecycle: 戦略が研究、backtest、paper 観察、次段階検討のどこにいるかを管理する流れです。
- hash: ファイルの内容から作る指紋です。前に見たファイルと同じかを確認するために使います。
- venue: 取引先や市場接続先のことです。ここでは Trade[XYZ]、Bitget demo などを指します。
- fail closed: 条件が揃わない時に、危険側へ進まず止める設計です。
- mock: 本物の外部サービスではなく、ローカルの代用品で動きを確認することです。
- API surface: コードから呼び出せる入口です。CLI とは違い、ターミナルの公開コマンドとは限りません。

## 主なファイルと役割

- `README.md`: リポジトリ全体の入口です。セットアップ、主要コマンド、読む順番をまとめています。
- `docs/CURRENT_STATE.md`: 現在の状態を短く読むための文書です。細かい実装履歴よりも、いまの判断を優先して読む場所です。
- `docs/IMPLEMENTED_SURFACES.md`: 実装済みの主要機能を一覧で確認する文書です。全体をざっと把握する時に使います。
- `docs/NEXT_DIRECTION_CURRENT.md`: 次にどの方向へ進むか、外部入力が来た時に何を再確認するかをまとめた文書です。paper / live 許可と read-only 確認を混同しないために使います。
- `docs/REPO_CAPABILITIES_CURRENT_2026-06-16.md`: できること、できないことを技術寄りに詳しく整理した文書です。この文書より詳細です。
- `docs/REPO_CAPABILITIES_PLAIN_JA_2026-06-17.md`: この文書です。専門用語を減らし、利用者向けに現在の範囲を説明します。
- `docs/strategy_lifecycle/README.md`: 戦略の段階管理と paper observation の入口です。
- `docs/strategy_lifecycle/PAPER_OBSERVATION_CYCLE.md`: paper observation の作り方、読むべき生成物、止める条件を説明する文書です。
- `docs/strategy_review/README.md`: Strategy Review の入口です。人間レビュー資料をどう作るかを確認できます。
- `docs/backtest/README.md`: backtest 関連の入口です。複数ある backtest surface の読み分けに使います。
- `docs/research/ndx/README.md`: NDX 研究 gate の入口です。Layer 2.2 以降の研究手順を確認できます。
- `docs/strategy_research_lab/README.md`: Strategy Research Lab の入口です。戦略アイデアから signal、評価、candidate、paper-only preview までの流れを確認できます。
- `docs/strategy_research_lab/08_CURRENT_CAPABILITIES.md`: Strategy Research Lab で現在できることを詳しく列挙した文書です。
- `docs/venues/read_only_capability_probe.md`: venue の読み取り専用 capability probe を説明する文書です。network readiness や live permission ではない点を確認できます。
- `src/sis/cli.py`: `sis` コマンド全体の登録場所です。どのコマンドが公開されているかを確認する時に見ます。
- `src/sis/commands/`: CLI コマンドの実装置き場です。各コマンドが何を読むか、何を出すかを確認する時に見ます。
- `src/sis/research/strategy_lab/`: Strategy Research Lab のモデルや処理を置くディレクトリです。
- `src/sis/execution/bitget_demo_adapter.py`: Bitget demo の local / mock-first adapter 実装です。本番 Bitget 接続の実装とは分けて読みます。
- `src/sis/venues/read_only_probe.py`: venue capability を読み取り専用で確認する処理です。外部書き込みをしない境界確認に使います。
- `configs/research_layer_2_2/ndx`: NDX 研究 gate の設定ディレクトリです。研究の部品、データ源、検査の流れを確認できます。
- `schemas/`: JSON などの生成物の形式ルールを置く場所です。ファイル構造の契約を確認できます。
- `tests/`: 自動テストの置き場です。現行仕様が壊れていないかを確認する証拠です。
- `scripts/check`: まとめて検証するためのスクリプトです。lint、型チェック、docs check、pytest をまとめて走らせます。
- `scripts/check_current_docs.py`: current docs のメタデータ、リンク、EOF、古い root path 参照を検査するスクリプトです。
- `data/research/strategy_lifecycle/paper_observation_status.json`: 現在の paper observation 状態を機械が読みやすい形でまとめた生成物です。
- `data/reports/paper_observation_status.md`: 現在の paper observation 状態を人間が読みやすい形でまとめた生成レポートです。
- `data/bot/paper_intent_preview.json`: paper-only の仮注文意図を保存する生成物です。本番注文ではありません。
- `data/research/ndx/paper_observation_review_decision.json`: NDX paper observation review の正本になる生成物です。通常観察が足りるか、まだ続けるかを記録します。
- `data/research/strategy_lifecycle/strategy_lifecycle_review.json`: backtest、paper observation、phase gate をまとめた段階判断の生成物です。
- `data/paper/observations/<session_id>/paper_observation_session_manifest.json`: session ごとの paper observation 記録の目次です。入力ファイル、hash、基準、paper-only 境界を記録します。

## 次にやるべきこと

現時点の実務的な次アクションは、通常基準の paper observation を続けることです。

Trade[XYZ] の public user address、Bitget demo の認証情報、新しい trading day の paper observation 証拠が揃った場合は、`docs/NEXT_DIRECTION_CURRENT.md` の `External Input Restart Checklist` を見て、read-only / observation として再確認します。

次にやるべきではないことは、smoke 合格を理由に live 実装や live 注文へ進むことです。
