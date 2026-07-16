<!--
作成日: 2026-07-16_16:56 JST
更新日: 2026-07-16_16:56 JST
-->

# Strategy Idea Seed Foundry Core v1 A1実装計画

## チェックポイントID

`A1 — Technical Walking Product`

## 目的

現行Bitget Public Source形式または忠実なFixtureから、Funding CrowdingとVolatility Compression / ReleaseのTechnical Seedを決定論的に生成し、全Attempt、Materialized Seed、Source Capability、Run Manifest、JSON/Markdown Review Artifactまで完走させる。

## 現状

- PR #45は`main`へsquash merge済み。
- 専用ブランチは`ai/seed-foundry-a1-technical-walking-product-20260716-1654`。
- Source RootはCandle/Fundingの履歴ParquetとTicker Snapshotを分離している。
- Seed専用Domain、Schema、CLIは未実装。

## 制約

- A1だけを実装する。
- Candidate、Backtest、Paper、Live、注文、Wallet、Signing、Exchange Writeへ接続しない。
- Common EnvelopeへTechnical固有Fieldを置かない。
- Profit score、Shortlist、Candidate exportを実装しない。
- Source不足を全体失敗にせず、`DATA_REQUIRED`とReason Codeで保持する。
- Ticker SnapshotをHistorical Mark/Index/Open Interestとして扱わない。
- 依存関係を追加しない。

## 対象ファイル

- 新規: `src/sis/strategy_idea_seeds/`配下のcommon/source/technical/storage、renderer、service。
- 新規: `src/sis/commands/strategy_idea_seeds.py`。
- 新規: Seed/Seed Set/Technical Payload/Attempt/Run Manifestの5 Schema。
- 新規: `configs/strategy_idea_seeds/`のOperator CatalogとMechanism Pack。
- 新規: `tests/strategy_idea_seeds/`と`tests/fixtures/strategy_idea_seeds/a1_source_root/`。
- 変更: `src/sis/cli.py`、`docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md`、`docs/final-summary.md`。

## 実装方針

1. Pydanticの厳格ModelでCommon Envelope、Boundary、Payload Ref、Attempt、Source Capability、Technical Payload、Manifestを定義する。
2. Domain canonical JSONとSHA-256 IDを純粋関数にする。Set-like Axisは正規化して列挙する。
3. Source Probeは8 Source Keyを独立分類し、Manifest、Parquet列、row count、snapshot属性を監査する。
4. Mechanism PackとOperator CatalogをYAMLからPydantic検証して読み込む。
5. Mechanism × Direction × Capture × Horizon × Lookback × Threshold × Source Requirementを安定順序で展開する。
6. 全組合せをAttempt化し、AST/type/unit/最低契約を検査する。
7. Exact duplicateを含む全AttemptをLedgerへ残し、有効な一意AttemptだけをSeed化する。
8. Seed IDはTechnical Payload hashを中心に作り、title、runtime timestamp、output path、Markdownへ依存させない。
9. Artifactを一時ファイルからatomic replaceし、最後にManifestを公開する。
10. CLIはPath解決、Service呼出し、summary/exit code変換だけにする。

## 実装手順

1. 必須テストの骨格を追加してREDを確認する。
2. Common Model、Boundary、canonicalization、IDを実装する。
3. Source ProbeとConfig Modelを実装する。
4. Axis Generator、Attempt検証、Seed Materializerを実装する。
5. Artifact writerとMarkdown rendererを実装する。
6. CLI登録とCLI Catalog更新を行う。
7. 忠実なParquet Fixtureを追加しE2Eを通す。
8. Local Source Rootでread-only smokeを行う。
9. focused tests、catalog check、full check、graphify updateを実行する。
10. `docs/final-summary.md`と`.ai-work/`へ結果を記録する。

## テスト方針

- Boundary true拒否。
- Title変更でSeed ID不変。
- Axis順序変更でSeed集合不変。
- Invalid type/unitはAttempt止まり。
- Historical Seedと`DATA_REQUIRED` Seedの同時生成。
- Ticker SnapshotのHistorical誤認防止。
- Duplicate AttemptのLedger保持。
- Candidate Artifact非生成。
- 同一Fixture二回実行で同一Seed ID。
- Manifest件数/hashとArtifact件数の一致。
- FixtureをPydanticとDraft 2020-12 JSON Schemaの両方で検証。

## 完了条件

- Long/Short、Continuation/Reversal、Historical、`DATA_REQUIRED`を含むSeed Setが生成される。
- 全AttemptがLedgerへ残る。
- Seed ID、Technical Signature、Payload Hash、Seed集合の意味内容が決定論的。
- 全Boundaryがfalse。
- 必須Artifactが揃い、Candidate/Backtest/Paper/Live Artifactがない。
- 指定CLIと全検証コマンドが成功する。

## 失敗条件

- 固定済みSeed JSONを返すだけになる。
- SnapshotをHistoricalとして扱う。
- Invalid AttemptがSeed化される、またはLedgerから消える。
- Common EnvelopeへTechnical専用Fieldが必要になる。
- 禁止範囲の型、コード、Artifactへ接続する。
- Profit score、Shortlist、Candidate exportを追加する。

## 影響範囲

新規Seed DomainとPublic CLI Catalogへの追加だけ。既存Candidate、Backtest、Paper、Liveの挙動は変更しない。

## ロールバック方針

このブランチで追加したSeed Domain、Schema、Config、Test、CLI登録、Catalog行、A1文書更新だけを手動で戻す。既存Sourceとruntime dataは変更しない。

## 代替案

- Candidate Domain再利用: status/shortlist責務が衝突するため不採用。
- TickerのMark/Index/OIをHistorical扱い: Snapshot契約違反のため不採用。
- Seedを先に作って不正を後段Kill: Attempt/Seed分離契約違反のため不採用。

## 未解決事項

Local Source Rootの実ファイルとManifestが現在も整合し、`CURRENT_DATA_OPERATIONAL=true`まで到達するかは実装後smokeで判定する。

## 破壊的変更

なし。新規Public CLI追加は加算的変更。

## ブランチ名

`ai/seed-foundry-a1-technical-walking-product-20260716-1654`

## 移行手順

不要。既存ArtifactやCLIを置換しない。
