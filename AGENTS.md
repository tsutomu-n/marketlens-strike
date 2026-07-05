<!--
作成日: 2026-05-30_21:32 JST
更新日: 2026-06-26_16:12 JST
-->

# Repository Guidelines

Last updated: 2026-06-26_16:12 Asia/Tokyo. Keep this guide concise; no fixed word limit.

## Scope

This file is the repo-local guide for `marketlens-strike`. Follow the global Codex defaults first, then apply this file for repository-specific choices. If the global defaults and this file conflict, this repo-local guide wins for this workspace.

## Codex Loading

Codex reads this file when a new run or TUI session starts. Restart Codex or start a fresh session after materially editing this file.

If `./.ai_memory/HANDOFF.md` exists, read it first for restart state before choosing the next action. Treat it as the restart artifact only; code, tests, schemas, config, lockfiles, CI, and CLI help remain the implementation source of truth.

## Source Of Truth

Code, tests, schemas, config, lockfiles, CI, and CLI help are authoritative. Prefer `src/`, `tests/`, `schemas/`, `pyproject.toml`, `.python-version`, `uv.lock`, `.github/workflows/ci.yml`, `scripts/check`, and `uv run sis --help` over README, docs, plans, or generated artifacts. Docs summarize current state; `plan/` and `docs/archive/` are context, not current proof. Do not copy changing pass counts, artifact snapshots, or phase-gate values into this file; record commands instead.

## Project Structure

`marketlens-strike` is a Python 3.13 CLI workspace for research, read-only evidence, Strategy Lab workflows, paper operations, and safety gates. Core code lives in `src/sis/`. `src/sis/cli.py` builds the Typer root app; command implementations live under `src/sis/commands/`. Domain code includes `venues/trade_xyz`, `backtest`, `research/strategy_lab`, `research_protocol`, `paper`, `execution`, `risk`, `tracking`, and `validation`.

Tests live in `tests/` with focused slices under `tests/backtest/` and `tests/strategy_authoring/`. Docs are in `docs/`, plans in `plan/`, schemas in `schemas/`, templates in `templates/`, and examples/config in `configs/`. `data/`, `logs/`, and `.tmp/` are runtime/generated state.

## Default Scope Bias

When the user does not specify a scope, prefer research/backtest-first and venue-neutral work. Use the NDX Layer 2.2 DAG foundation for NDX research tasks. Prefer Strategy Lab authoring or backtest-first workflows when a task does not explicitly require venue-specific work.

The Layer 2.2 review harness is local/manual review plumbing only. It does not prove alpha, feature-panel readiness, residual correctness, Strategy Lab export readiness, backtest readiness, paper readiness, live readiness, account readiness, wallet readiness, or exchange-write readiness.

Trade[XYZ] remains implemented code and historical/read-only venue context, but it is no longer the default product axis, primary execution path, or primary next action. Do not introduce new Trade[XYZ] assumptions, collectors, readiness claims, or order-path work unless the user explicitly scopes the task to Trade[XYZ].

## Commands

- `uv sync --dev --locked`: install locked dependencies.
- `uv run python -V`: confirm Python 3.13.
- `uv run sis --help`: inspect the actual public CLI surface.
- `./scripts/check` or `just check`: run locked sync, Python version, Ruff lint/format check, current-docs check, Pyrefly, ty, and Pytest.
- `uv run python scripts/check_current_docs.py`: verify current-doc links, EOF, and legacy-root references.
- `uv run sis research-layer22-validate --root configs/research_layer_2_2/ndx`: validate the local-only NDX Layer 2.2 DAG foundation.
- `uv run sis research-layer22-export --root configs/research_layer_2_2/ndx --out data/research/ndx`: export Layer 2.2 DAG artifacts without fetching data.
- `uv run sis research-layer22-review-pack --root configs/research_layer_2_2/ndx --out data/research/ndx/review`: build the local/manual Layer 2.2 review pack.
- `uv run sis research-layer22-review-import --pack data/research/ndx/review/llm_review_input.json --result data/research/ndx/review/llm_review_result.json`: validate and normalize a manual review JSON result.
- `uv run sis research-layer22-exit-gate --root configs/research_layer_2_2/ndx --pack data/research/ndx/review/llm_review_input.json --review data/research/ndx/review/normalized_review.json --out data/research/ndx/review`: decide whether Layer 2.2 can advance to Layer 2.3.
- `uv run sis phase-gate-review`: review the read-only/paper gate.

CI also runs `bun install --frozen-lockfile` for lockfile integrity. Normal development is Python/uv-first; `package.json` is not the main app entrypoint.

## Coding And Workflow

Start with read-only inspection. Use `rg`, `rg --files`, CLI help, tests, schemas, and config before editing. Preserve local patterns and keep changes scoped.

Use 4-space Python indentation, explicit public type hints, and small modules aligned to domain boundaries. Keep reusable logic out of command wrappers when practical. New or heavily edited Python files should stay at 800 lines or fewer. Strategy Authoring enforces this with `tests/strategy_authoring/test_module_boundaries.py`.

Trade[XYZ] pure backtest v0.1 is a Python API surface, not a public CLI, and should be treated as an isolated venue-specific surface. `uv run sis build-backtest` is a separate legacy/bridge command. Micro-live code exists, but standard operator CLI live execution is not exposed. `READ_ONLY_GO` means read-only/paper gate only; it does not prove wallet, signing, exchange write, or production live trading readiness.

## Document Timestamps

For every documentation file created or edited by the agent, add or update a hidden metadata header near the top of the file.

For Markdown files, use exactly:

```markdown
<!--
作成日: YYYY-MM-DD_HH:mm JST
更新日: YYYY-MM-DD_HH:mm JST
-->
```

Use Tokyo time. `作成日` is the original document creation time and must not change after first creation. Update `更新日` whenever the document content is materially edited. Place the header at the top of the file, after shebang or frontmatter only if required. Do not add it to generated files, vendored files, lockfiles, binary files, or files where comments are invalid. If a format has no safe comment syntax, do not invent one; use the repository-specific rule.


'*.md'ファイルをTerminalに出力、表示するときは、フルパスを書く。

## Testing And PRs

Add focused Pytest coverage near changed behavior. Prefer deterministic fixtures; avoid live market responses unless testing explicit read-only evidence flow.

PRs should state purpose, changed commands or artifacts, verification run, and any live-readiness boundary. Keep commits scoped and separate formatting from behavior changes.

Keep secrets out of git. Runtime settings come from `.env`; start from `configs/env.example` for normal repo settings and `.env.example` for the Alpaca runbook.

# AI開発作業ルール

このリポジトリで作業するAIエージェントは、以下のルールに従う。

## 基本方針

ユーザーからゴールが与えられたら、ユーザーの追加アクションなしで進められる範囲を最大限進め、ゴール達成を目指す。

質問で作業を止めない。判断が必要な事項が出た場合は、以下の優先順位で処理する。

1. 既存コード・既存ドキュメント・既存テストから判断する
2. 安全で保守的な仮定を置いて進める
3. 複数案を比較し、リスクが小さい案を採用する
4. ユーザー判断が必須の事項のみ `docs/action-required.md` に記録する

## 禁止事項

以下は、明示指示がない限り実行しない。

* 課金が発生する操作
* 本番環境へのデプロイ
* 外部サービスへのデータ送信
* 秘密情報・認証情報・APIキーの作成、変更、削除
* 既存データの不可逆削除
* `git push`
* ユーザー作業中の変更の上書き
* 目的と無関係な大規模リファクタ

## 許可事項

ゴール達成に必要で、禁止事項に該当しない範囲では、以下を許可する。

* 既存コードの変更
* 必要な新規ファイルの作成
* テストの追加・修正
* ドキュメントの作成・更新
* 依存関係の追加・入れ替え
* 破壊的変更
* アーキテクチャ変更
* 内部実装の大幅な整理

ただし、依存関係の追加・入れ替え・破壊的変更・アーキテクチャ変更を行う場合は、必ず専用ブランチを作成してから作業する。

## ブランチ作業ルール

作業開始時に、まず現在のGit状態を確認する。

```bash
git status --short
git branch --show-current
```

### 専用ブランチが必要な作業

以下のいずれかに該当する場合は、必ず専用ブランチを作成してから作業する。

* 破壊的変更
* 依存関係の追加・削除・大幅な入れ替え
* ディレクトリ構成の変更
* アーキテクチャ変更
* 既存API・関数・型・DBスキーマの変更
* 大規模リファクタ
* 複数ファイルにまたがる仕様変更
* 既存挙動を変える可能性がある変更

### ブランチ名

ブランチ名は以下の形式にする。

```txt
ai/<task-slug>-YYYYMMDD-HHMM
```

例：

```txt
ai/refactor-auth-flow-20260626-1615
ai/breaking-schema-cleanup-20260626-1615
ai/replace-state-layer-20260626-1615
```

### ブランチ作成

作業前に専用ブランチを作成する。

```bash
git switch -c ai/<task-slug>-YYYYMMDD-HHMM
```

既に適切なAI作業ブランチ上にいる場合は、新しいブランチを作らず、そのブランチで続行してよい。
ただし、ブランチ名・現在の状態・続行理由を `.ai-work/state.md` に記録する。

## 既存の未コミット変更の扱い

作業開始時点で未コミット変更がある場合は、絶対に上書きしない。

まず以下を実行して状態を記録する。

```bash
git status --short
git diff --stat
```

必要に応じて、作業前の差分を `.ai-work/pre-existing.diff` に保存する。

```bash
git diff > .ai-work/pre-existing.diff
```

未コミット変更がゴールに関係する可能性がある場合は、それを前提として慎重に作業する。

未コミット変更がゴールと無関係で、作業の衝突リスクが高い場合は、無理に変更せず、`docs/action-required.md` に判断事項として記録する。

## コミットルール

`git push` は禁止する。

ローカルコミットは、ユーザーが明示的に許可した場合、または作業単位を安全に保存する必要がある場合のみ行ってよい。

ローカルコミットを行う場合は、以下を守る。

* `.ai-work/` をコミットしない
* 秘密情報を含めない
* テストまたは確認結果を記録してからコミットする
* コミットメッセージは作業内容が分かるものにする

例：

```txt
ai: implement checkpoint 01 data model cleanup
ai: add regression tests for import flow
ai: update docs for breaking config change
```

## 作業状態の管理

作業開始時に `.ai-work/` を作成する。

`.ai-work/` は一時作業メモ用であり、`.gitignore` 対象にする。

最低限、以下を作成・更新する。

* `.ai-work/state.md`
* `.ai-work/checkpoints.md`
* `.ai-work/notes.md`

`.ai-work/state.md` には以下を記録する。

* ゴール
* 現在のブランチ
* 作業開始時のGit状態
* 現在のチェックポイント
* 完了済みチェックポイント
* 未完了チェックポイント
* 重要な判断
* 未解決事項
* 最終更新内容

## 作業ループ

ゴール達成まで、以下のループを繰り返す。

### 1. Diagnose

現状を調査する。

確認対象：

* ディレクトリ構成
* 主要ファイル
* 既存仕様
* 既存ドキュメント
* 既存テスト
* ビルド・lint・型チェック設定
* ゴールに関係する実装箇所
* 壊してはいけない既存挙動
* 現在のGitブランチ
* 作業開始時点の未コミット変更

ゴールとの差分を整理し、完了判定可能なチェックポイントに分割する。

各チェックポイントには以下を持たせる。

* ID
* 目的
* 依存関係
* 対象ファイル
* 完了条件
* 想定リスク
* 破壊的変更の有無
* ブランチ作業の要否

### 2. Select

未完了チェックポイントのうち、依存関係上もっとも近いものを1つ選ぶ。

複数チェックポイントを同時に処理しない。
ただし、分離すると不自然・非効率・危険な場合は、理由を記録した上でまとめて処理してよい。

対象チェックポイントが破壊的変更を含む場合は、専用ブランチ上で作業していることを確認する。

### 3. Plan

対象チェックポイントの実装計画を作成し、`docs/plans/` に保存する。

計画には必ず以下を含める。

* チェックポイントID
* 目的
* 現状
* 制約
* 対象ファイル
* 実装方針
* 実装手順
* テスト方針
* 完了条件
* 失敗条件
* 影響範囲
* ロールバック方針
* 代替案
* 未解決事項
* 破壊的変更の有無
* ブランチ名
* 移行が必要な場合の移行手順

この計画は、別のコーダーが読んでも作業を完了できる粒度にする。

### 4. Critique

実装前に、作成した計画を必ず批判的に見直す。

以下を確認する。

* ゴールに直接近づく計画か
* 理想的なご都合主義のナラティブになっていないか
* 抜け漏れがないか
* 既存仕様を壊す可能性がないか
* テストで検知できない破壊がないか
* 変更範囲が過剰ではないか
* より単純で安全な方法がないか
* 依存関係追加の価値がコストを上回るか
* 破壊的変更をする合理性があるか
* 破壊的変更を避けた場合の不利益は明確か
* ロールバック可能か
* 将来の保守性を損なわないか
* コーダーが迷わず実装できる粒度か

問題があれば、実装前に計画を修正する。

### 5. Execute

計画に従って実装する。

実装時は以下を守る。

* 専用ブランチ上で作業する
* 対象チェックポイントに必要な変更へ集中する
* 不要なリファクタを混ぜない
* 暫定対応をした場合は理由を記録する
* 破壊的変更をした場合は影響範囲と移行方法を記録する
* エラーを隠さない
* テストを通すためだけのハードコードをしない
* 既存の未コミット変更を上書きしない

### 6. Verify

可能な範囲で確認を行う。

優先順位：

1. 既存テスト
2. 新規テスト
3. 型チェック
4. lint
5. ビルド
6. 最小動作確認
7. 回帰確認

破壊的変更を行った場合は、変更対象の主要ユースケースについて最小動作確認を行う。

実行できなかった確認がある場合は、理由を記録する。

テストが通っても、仕様と実装が整合していなければ完了扱いにしない。

### 7. Record

チェックポイント完了後、`.ai-work/state.md` を更新する。

記録する内容：

* 完了した内容
* 現在のブランチ
* 変更したファイル
* 実行した確認
* 失敗した確認
* 未実行の確認と理由
* 破壊的変更の有無
* 依存関係変更の有無
* 残った課題
* 次に処理すべきチェックポイント
* ユーザー判断が必要な事項

未完了チェックポイントがあれば `Select` に戻る。

## 完了条件

すべてのチェックポイントが完了したら、`docs/final-summary.md` を作成する。

`docs/final-summary.md` には以下を含める。

* ゴール
* 作業ブランチ
* 達成したこと
* 変更した主なファイル
* 実行した確認
* 未実行の確認と理由
* 残った課題
* ユーザー判断が必要な事項
* 破壊的変更の有無
* 破壊的変更の理由
* 依存関係変更の有無
* 移行手順
* ロールバック方法
* 次に検討すべき事項

最後に、最終状態を簡潔に報告する。
