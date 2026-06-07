<!--
作成日: 2026-06-07_20:21 JST
更新日: 2026-06-07_20:21 JST
-->

# Feature Expansion Zip Intake Guide

## 結論

新しい機能拡張計画は、Zip の中で「何を作るか」「何を作らないか」「どのファイルに触るか」「どう検証するか」「どこで止まるか」が分かる形にする。

推奨形式は次。

```text
feature_expansion_plan_<yyyymmdd>/
  README.md
  MANIFEST.json
  01_GOAL.md
  02_SCOPE_AND_BOUNDARIES.md
  03_CURRENT_REPO_CONTEXT.md
  04_TASKS.md
  05_ACCEPTANCE.md
  06_TARGET_FILE_MAP.md
  07_TEST_PLAN.md
  08_RISK_AND_STOP_CONDITIONS.md
  09_OPEN_QUESTIONS.md
  10_IMPLEMENTER_CHECKLIST.md
  appendices/
    A_SCHEMA_SKETCHES.md
    B_CONFIG_EXAMPLES.md
    C_CODER_HANDOFF_PROMPT.md
```

## 必須情報

Zip には最低限、次を入れる。

```text
1. 目的
  - 何を完成扱いにするか
  - ユーザーに何が使えるようになるか

2. 非目的
  - 今回やらないこと
  - backtest / paper / live / external API / credentials / DB / deploy への影響有無

3. 現状理解
  - 参照した repo path
  - 参照した CLI help / tests / schemas / config
  - 既存実装のどこに接続する想定か

4. 作業単位
  - PR か task 単位で分ける
  - 各 task の入力、出力、変更ファイル、完了条件を書く

5. 触ってよい範囲
  - 追加・変更してよい path
  - 原則触らない path
  - 依存追加の有無

6. 検証
  - 最小テストコマンド
  - full check が必要か
  - 期待する出力

7. 停止条件
  - credentials が必要
  - 外部 API が必要
  - schema / DB / auth / deploy / CI に触る
  - paper/live order path に触る
  - 仕様判断が複数に分岐する
```

## MANIFEST.json に入れるもの

`MANIFEST.json` は Zip の目次として使う。最低限、次を入れる。

```json
{
  "created_at_jst": "YYYY-MM-DD_HH:mm JST",
  "title": "short plan title",
  "root_path": "feature_expansion_plan_<yyyymmdd>",
  "purpose": "one sentence purpose",
  "repo_assumption": {
    "repo": "marketlens-strike",
    "branch": "main",
    "base_head": "optional git hash if known"
  },
  "safety": {
    "external_api": "not_required | required | unknown",
    "credentials": "not_required | required | unknown",
    "paper_live_order": "not_touched | touched | unknown",
    "db_schema": "not_touched | touched | unknown",
    "dependency_change": "none | required | unknown"
  },
  "files": [
    "feature_expansion_plan_<yyyymmdd>/README.md",
    "feature_expansion_plan_<yyyymmdd>/01_GOAL.md"
  ]
}
```

## 各ファイルの役割

```text
README.md
  計画全体の結論、読み順、最重要の境界を書く。

01_GOAL.md
  完成状態を 1 つに絞る。抽象的な「改善」ではなく、確認可能な成果を書く。

02_SCOPE_AND_BOUNDARIES.md
  対象・非対象・安全境界を書く。特に external API、credentials、paper/live、DB、deploy は明記する。

03_CURRENT_REPO_CONTEXT.md
  既存コードの理解を書く。推測ではなく、確認した path、CLI、test、schema を書く。

04_TASKS.md
  コーダーが実装できる順番に task を分ける。各 task に target files と acceptance を付ける。

05_ACCEPTANCE.md
  完了条件を書く。コマンド、期待出力、生成物、未実装でよいものを明記する。

06_TARGET_FILE_MAP.md
  path 単位で、create / edit / no-touch を分ける。

07_TEST_PLAN.md
  先に追加するテスト、変更後に通すテスト、full check の要否を書く。

08_RISK_AND_STOP_CONDITIONS.md
  止まる条件と、止まった時にユーザーへ聞く質問を書く。

09_OPEN_QUESTIONS.md
  実装前に未解決なら危険な質問だけを書く。好みの質問や後回し可能な質問は分ける。

10_IMPLEMENTER_CHECKLIST.md
  実装者が順にチェックできる粒度にする。
```

## Zip に入れないもの

```text
入れない:
  - .env
  - credentials
  - API key
  - token
  - wallet / signing material
  - large raw data
  - generated cache
  - node_modules
  - .git
  - dist / build
  - logs with secrets
```

必要なら、実データは Zip に同梱せず、`data requirement` と `expected fixture shape` だけを書く。

## 受け取り後のこちらの確認手順

Zip を受け取ったら、まず次だけ確認する。

```text
1. Zip を展開せず目次を見る
2. MANIFEST.json を読む
3. README.md を読む
4. stop condition を確認する
5. repo の current code / tests / CLI help と照合する
6. 実装前に計画の抜け、漏れ、誤謬リスクを出す
```

外部 API、credentials、paper/live、DB、deploy、CI、依存追加に触れる計画なら、実装前に止めて確認する。

## 受け渡し時の短い依頼文

Zip と一緒に、次のように渡すと再開しやすい。

```text
この Zip を feature expansion plan として読んでください。
まず MANIFEST.json と README.md を読み、repo の current code / tests / CLI help と照合してください。
古い chat transcript には依存しないでください。
実装前に、抜け、漏れ、誤謬リスクと stop condition を確認してください。
問題なければ 04_TASKS.md の T1 から進めてください。
```

