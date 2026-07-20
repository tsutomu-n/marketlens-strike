<!--
作成日: 2026-06-27_11:32 JST
更新日: 2026-07-20_20:03 JST
-->

# Final Summary

## 結論

Strategy Idea Seed Foundry Core v1のA1 Technical Walking Productを実装した。

```text
IMPLEMENTATION_COMPLETE=true
CURRENT_DATA_OPERATIONAL=true
A1_GATE=CONTINUE_A2
```

`CONTINUE_A2`はA2開始許可ではなく、A1の技術Gateを満たしたという判定だけを示す。この作業ではA2以降を実装していない。

## ゴール

現行Source Rootまたは忠実なFixtureから、Funding CrowdingとVolatility Compression / ReleaseのTechnical Seedを決定論的に生成し、全Generation Attempt、Materialized Seed、Source Capability、Run Manifest、Seed Set JSON、MarkdownまでArtifact化する。

## 作業ブランチ

```text
ai/seed-foundry-a1-technical-walking-product-20260716-1654
```

開始点:

```text
c8c950d2cb5677ed233ade7d8ac15a5f07979095
```

## 達成したこと

- Common Seed EnvelopeとTechnical Payloadを分離した。
- 全12 BoundaryをPydanticの`Literal[False]`とJSON Schemaの`const: false`で固定した。
- Source Probeで次を独立分類した。
  - `HISTORICAL`
  - `SNAPSHOT_ONLY`
  - `FORWARD_ONLY`
  - `MISSING`
  - `INVALID`
  - `UNKNOWN`
- Ticker SnapshotをHistorical Mark、Index、Open Interestへ昇格させない。
- Mechanism Pack、Operator Catalog、Source Capability、Axis展開からSeedを生成する。
- 全組合せをGeneration AttemptとしてLedgerへ残す。
- Invalid type/unit、最低契約欠落、Exact duplicate、Budget pruneをReason Code付きでAttempt止まりにする。
- Seed ID、Technical Signature、Payload Hash、Seed Set semantic hashを決定論的にした。
- Long/Short、Continuation/Reversal、Historical Source、`DATA_REQUIRED`を同じSeed Setへ生成した。
- Public CLIを追加した。
- Candidate、Backtest、Paper、Liveへ接続していない。

## 追加CLI

```bash
uv run sis strategy-idea-seeds-technical-build \
  --source-root <path> \
  --mechanism-pack <path> \
  --operator-catalog <path> \
  --out <path>
```

## 生成Artifact

```text
<out>/
├── seed_run_manifest.json
├── source_capabilities.json
├── technical/
│   ├── technical_attempts.jsonl
│   └── technical_payloads.jsonl
└── review/
    ├── strategy_idea_seed_set.json
    └── strategy_idea_seed_set.md
```

## Fixture実行結果

```text
status=pass
attempt_count=16
seed_count=16
data_required_count=8
```

Fixture Source Capability:

```text
candles_5m=HISTORICAL
funding_rows=HISTORICAL
ticker_rows=SNAPSHOT_ONLY
mark_index_history=MISSING
open_interest_history=MISSING
trade_tape_history=MISSING
order_book_history=MISSING
liquidation_history=MISSING
```

## Local Source実行結果

入力:

```text
/home/tn/projects/marketlens-strike/data/strategy_idea_candidates/btc-perp/bitget_public_source/source_root
```

結果:

```text
status=pass
attempt_count=16
seed_count=16
data_required_count=8
candles_5m=HISTORICAL, rows=516
funding_rows=HISTORICAL, rows=105
ticker_rows=FORWARD_ONLY, rows=39
```

履歴がないMark/Index/Open Interest、Trade Tape、Order Book、Liquidationは`MISSING`として記録し、該当仮説を`DATA_REQUIRED`で保持した。

## 主な変更ファイル

- `src/sis/strategy_idea_seeds/`
- `src/sis/commands/strategy_idea_seeds.py`
- `schemas/strategy_idea_seed*.schema.json`
- `configs/strategy_idea_seeds/`
- `tests/strategy_idea_seeds/`
- `tests/fixtures/strategy_idea_seeds/a1_source_root/`
- `src/sis/cli.py`
- `docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md`

## 実行した確認

```text
uv run pytest tests/strategy_idea_seeds -q
PASS

uv run python scripts/check_cli_catalog.py
PASS

uv run python scripts/check_current_docs.py
PASS

./scripts/check
PASS
Ruff lint/format: PASS
Pyrefly: 0 errors
ty: PASS
```

`graphify update .`は専用worktreeに`graphify-out`の基盤がなく、`No code files found`で更新対象を検出できなかった。コード・テスト・Git Gateの成功には影響しない。

## A1完了条件

| 条件 | 判定 |
|---|---|
| FixtureからTechnical Seed生成 | PASS |
| Historical Source Seed | PASS |
| DATA_REQUIRED Seed | PASS |
| Long / Short | PASS |
| Continuation / Reversal | PASS |
| 全AttemptをLedgerへ保存 | PASS |
| Manifest件数とArtifact件数一致 | PASS |
| 同一入力でID安定 | PASS |
| 全Boundary false | PASS |
| Candidate / Backtest / Paper / Live非出力 | PASS |
| CLI / Schema / Test / full check | PASS |

## 未実行・未確認

- 外部Network Source取得は実行していない。
- A2以降のArchive、Resume、ML、LLM、Mutation、Cluster、Orchestratorは未実装。
- Seedの利益性、Backtest結果、Execution、Cost、Paper、Liveは評価していない。

## 破壊的変更

なし。新規Domain、Schema、Config、Fixture、Public CLIの加算的変更である。

## 依存関係変更

なし。

## 移行手順

不要。既存Candidate、Backtest、Paper、LiveのArtifactとCLIを置換しない。

## ロールバック

このA1ブランチで追加したSeed Domain、Schema、Config、Fixture、Test、CLI登録、CLI Catalog行だけを手動で戻す。既存Source Rootとruntime dataは変更しない。

## Known Gaps

- Historical Mark/Index/Open Interestは存在しない。
- Trade Tape、Order Book、Liquidation Historyは存在しない。
- Mechanismの因果と利益性は未検証。
- A1は小規模JSON/JSONL Artifactのみで、A2のArchive/Resume基盤を持たない。

## 次に検討すべき事項

A2へ進む場合も別Branch・別Checkpointとし、A1のSeed契約と禁止境界を維持する。

## 2026-07-20 ローカルmain文書統合

### ゴール

統合基準commit `427de2b62ebb21a613793aee92b1d49bbe69e09c` のA1実装を正本としつつ、分岐したローカル`main`にのみ存在したリポジトリ理解レポート、調査文書、実装前設計を安全に再配置する。

### 作業ブランチ

`ai/reconcile-main-20260720-1949`

### 達成したこと

- リポジトリ理解レポートを`docs/720-info/`に保全した。
- 仮説探索エンジンの調査・意思決定文書を`docs/plans/`に統合した。
- Execution Replay文書は未実装の設計案であることと、実装前の再検証条件を明記した。
- PR #46マージ前のSeed Foundry指示を、実行禁止の履歴資料として`plan/archive/`に移した。
- `.serena/project.yml`の無関係なtemplateドリフトは移植しなかった。
- A2、Execution Replay実装、製品コード変更は行っていない。

### 破壊的変更と依存関係変更

どちらもなし。

### 実行した確認

- リポジトリ外のdetached worktreeで`./scripts/check`: PASS。
- Ruff lint / format: PASS。
- current-docs: PASS。
- CLI catalog: PASS。
- Pyrefly: 0 errors。
- ty: PASS。
- Pytest: PASS（1 skip）。
- `graphify update .`: PASS。48726 nodes / 70584 edgesを生成した。

Pytest終了時に、権限制御fixtureが作る一時ディレクトリの掃除警告が出た。テスト結果は成功で、製品ツリーの変更や実行時データの欠損はない。

### 移行とロールバック

自動移行は行わない。必要な場合のみ、検証済み統合ブランチを人間が`main`へ取り込む。ロールバックはこのブランチを使用せず、統合基準commit `427de2b`を維持することで完了する。

### 残った課題

- Execution Replayの設計は現行コードに対する再検証と明示承認が必要。
- A2開始判定は本統合と分ける。
- 更新後の`graphify-out/graph.json`は約50 MiBで、HTML visualizationは48726 nodesが上限を超えるため生成されない。クエリ用JSONとreportは使用可能だが、Git履歴サイズとブラウザ可視化は別途管理判断が必要。
- push、remote branch作成、`main`への取り込みは未実施。
