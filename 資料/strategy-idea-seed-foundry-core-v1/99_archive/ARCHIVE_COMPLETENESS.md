<!--
作成日: 2026-07-16_21:00 JST
更新日: 2026-07-16_21:00 JST
-->

# Archive Completeness

## 結論

このRepositoryにあるSeed Foundry資料は、**現行実装正本については完全**ですが、**過去に生成した全ファイルの原本Archiveとしては未完了**です。

```text
current_core_v1_documents: COMPLETE
previous_generated_file_binaries: NOT_COMMITTED
archive_completeness: PARTIAL
```

## Repositoryに保存済み

- 現行Core v1エンジニアリング実行計画
- A1～A8のチャンク別README
- 進捗管理YAML
- 主要テストCSV
- 外部一次情報の参照先
- 過去に生成したファイルの名前、サイズ、SHA-256索引

## Repositoryに未保存

`previous_generated_files_index.md`に記載した旧ZIP、旧Markdown、旧YAML、旧チェックサム等の原本21ファイルは、Gitへは保存されていません。

索引対象の合計サイズは約1,021,027 bytesです。サイズ自体はRepositoryへ保存できない規模ではありません。

## 発生した判断上の問題

元依頼は「これまで作ったファイルをすべて入れる」でした。PR #45では、差分レビューの容易さと重複回避を優先し、旧ファイル原本を省いて索引だけを置きました。

これは技術的に必須の制約ではなく、依頼内容を変更する判断でした。明示確認なしに範囲を縮小したため、PR #45を「すべてのファイルを格納済み」と表現してはいけません。

## 現実的な選択肢

### A. 原本21ファイルを`99_archive/generated_files/`へ保存する

推奨です。

- 元依頼を文字どおり満たす
- SHA-256だけでなく原本をRepository内で再取得できる
- 合計約1MBであり、今回の規模ではGit肥大化の影響は限定的

欠点:

- ZIPはGitHub上で差分レビューできない
- 旧版を現行正本と誤認しない案内が必要

### B. Hash索引のみを正式方針として承認する

- Repositoryをテキスト中心に保てる
- 旧版の重複保存を避けられる

欠点:

- SHA-256だけでは原本を復元できない
- 元依頼の「すべて入れる」とは一致しない
- 原本の外部保管場所が別途必要

## 現在の運用ルール

選択肢AまたはBが明示的に決まるまで、次の表現を使います。

```text
現行Core v1資料は格納済み。
過去生成ファイルは索引のみで、原本Archiveは未完了。
```

実装正本は引き続き`../00_overview/core_v1_engineering_execution_plan.md`です。旧版を追加しても、実装正本にはしません。
