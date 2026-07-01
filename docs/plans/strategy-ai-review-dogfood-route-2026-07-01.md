<!--
作成日: 2026-07-01_22:59 JST
更新日: 2026-07-01_22:59 JST
-->

# Strategy AI Review Dogfood And Route Plan

## 目的

Strategy AI Review の既存 `packet -> note -> structured findings` を 1 件通し、Markdown が人間レビューに使えること、permission false / lineage / typed refs が保たれることを確認する。その後、`context_sections` schema 互換判断を反映し、Case Lite / Daily Brief / Workbench Viewer から AI review structured findings を見落としにくい表示導線へ接続する。

## 制約

- 外部 AI API、外部送信、credential、wallet、signing、exchange write、paper/live/tiny-live execution は使わない。
- `data/` は runtime/generated state で gitignore 対象。dogfood artifact は実行確認に使い、repo に固定する成果物は docs と tests に残す。
- AI recommendation / structured findings は operator decision、stage decision、paper permission、live permission ではない。
- 既存 `strategy_ai_review_note.v1` / `strategy_ai_review_structured_findings.v1` の意味は変えない。
- `strategy_ai_review_packet.v1` の `context_sections` は Pydantic model では default empty list なので、schema も古い v1 artifact を壊さない方向を優先する。

## 確認した正本

- `AGENTS.md`
- `./.ai_memory/HANDOFF.md`
- `docs/strategy_ai_review/README.md`
- `docs/strategy_case_lite/README.md`
- `docs/strategy_daily_brief/README.md`
- `docs/strategy_workbench_viewer/README.md`
- `src/sis/strategy_ai_review/`
- `src/sis/strategy_case_lite/`
- `src/sis/strategy_daily_brief/`
- `src/sis/strategy_workbench_viewer/`
- `schemas/strategy_ai_review_packet.v1.schema.json`
- `schemas/strategy_ai_review_structured_findings.v1.schema.json`
- `schemas/strategy_case_lite.v1.schema.json`
- `schemas/strategy_daily_brief.v1.schema.json`
- `tests/strategy_ai_review/`
- `tests/strategy_case_lite/`
- `tests/strategy_daily_brief/`
- `tests/strategy_workbench_viewer/`
- CLI help for `strategy-ai-review-*`, `strategy-case-lite-update`, `strategy-daily-brief`, and `strategy-workbench-viewer-build`

## Checkpoints

### CP1: Dogfood one AI review chain

対象:

- `tests/strategy_ai_review/test_strategy_ai_review_dogfood.py`
- `docs/final-summary.md`

実装方針:

1. tmp fixture で `strategy_case_lite.v1` を作る。
2. service か CLI を使って `strategy_ai_review_packet.json` を作る。
3. manual/local note として `strategy_ai_review_note.json` を作る。
4. manual structured findings input を使って `strategy_ai_review_structured_findings.json` / `.md` を作る。
5. Markdown に `finding_count`, `source_note`, `source_packet`, `Evidence Refs`, boundary text が出ることを検査する。
6. JSON で `auto_applied=false`, `permission_allowed=false`, `paper_execution_allowed=false`, `live_allowed=false` を検査する。
7. `source_note.input_hash == source_packet.ai_input_hash` と typed evidence refs を検査する。

完了条件:

- 1 件の chain が自動テストと実行ログで確認できる。
- Markdown が human review input として読める最低限の見出し、finding、typed refs、boundary を持つ。
- AI output が permission に昇格しない。

### CP2: `context_sections` required compatibility decision

対象:

- `schemas/strategy_ai_review_packet.v1.schema.json`
- `tests/strategy_ai_review/test_strategy_ai_review.py`
- `docs/strategy_ai_review/README.md`
- `docs/final-summary.md`

実装方針:

1. `context_sections` を `required` から外す。
2. property 自体は維持し、new packet は今まで通り `context_sections: []` か allowlisted sections を出す。
3. schema validation test で、古い v1 風 artifact が `context_sections` なしでも通ることを追加する。
4. README に「新規生成は出すが、古い v1 artifact 互換のため required ではない」と明記する。

完了条件:

- 古い `strategy_ai_review_packet.v1` artifact を再生成なしで schema validation できる余地が残る。
- new artifact の安全な allowlist behavior は維持される。

### CP3: Case / Daily Brief / Workbench route

対象:

- `src/sis/strategy_case_lite/models.py`
- `src/sis/strategy_case_lite/service.py`
- `schemas/strategy_case_lite.v1.schema.json`
- `tests/strategy_case_lite/test_strategy_case_lite.py`
- `src/sis/strategy_daily_brief/models.py`
- `src/sis/strategy_daily_brief/service.py`
- `src/sis/strategy_daily_brief/rendering.py`
- `schemas/strategy_daily_brief.v1.schema.json`
- `tests/strategy_daily_brief/test_strategy_daily_brief.py`
- `src/sis/strategy_workbench_viewer/summary.py`
- `src/sis/strategy_workbench_viewer/summary_fields.py`
- `tests/strategy_workbench_viewer/test_strategy_workbench_viewer.py`
- `docs/strategy_case_lite/README.md`
- `docs/strategy_daily_brief/README.md`
- `docs/strategy_workbench_viewer/README.md`
- `docs/final-summary.md`

実装方針:

1. Case Lite で `strategy_ai_review_structured_findings.v1` を known artifact type として扱う。
2. Case Lite の open action は structured findings の先頭 `recommended_next_action` を拾う。
3. Case Lite の status は `finding_set_status` を拾い、latest hash も `strategy_ai_review_structured_findings` で残す。
4. Daily Brief に `ai_review_follow_up` category と count を追加し、structured findings を human-review follow-up として出す。
5. Daily Brief の reason は permission ではなく「AI review structured findings require human inspection」とする。
6. Workbench compact summary で `finding_set_id`, `finding_set_status`, `finding_count`, `source_note`, `source_packet`, `source_note_recommendation`, first finding type / severity / impact / next action を出す。
7. Viewer status badge は既存 `artifact_status` の status keys に `finding_set_status` を追加して表示する。

完了条件:

- `strategy-case-lite-update --artifact <structured findings>` で known artifact type と open action が出る。
- `strategy-daily-brief --data-dir <dir>` で AI review follow-up count と item が出る。
- `strategy-workbench-viewer-build --artifact <structured findings>` で AI review summary が manifest / HTML に出る。
- いずれも paper/live permission は false のまま。

## Critique 1: ご都合主義の排除

- 「dogfoodした」と言うだけでは弱い。generated runtime artifact は gitignore なので、テストと final-summary に検証観点を残す。
- structured findings を Case/Daily Brief/Viewer に入れても、operator decision へ直結してはいけない。表示カテゴリは follow-up / human inspection に限定する。
- `context_sections` を required のまま「再生成すればよい」とするのは、v1 互換として雑。Pydantic model は default empty list なので schema required を外す方が code truth と整合する。
- Daily Brief に専用 category を足すと schema additive ではあるが、既存 artifact reader が enum を厳格に見る場合は影響がある。今回は Daily Brief 自体の new output schema と tests を更新し、古い Daily Brief artifact を再検証する要件は置かない。

修正:

- CP1 は runtime artifact の生成だけでなく pytest で固定する。
- CP2 は A案、つまり v1互換重視で `context_sections` required を外す。
- CP3 は permission ではなく follow-up / inspection として表示する。

## Critique 2: 抜け漏れとより良い実務案

- `strategy_ai_review_packet.v1` / `note.v1` を Case Lite に全部流すと noise が増える。Case/Daily Brief の明示 route は最終成果物である structured findings に絞る。
- CLI に新しい専用 option を増やすより、既存 `--artifact` と schema auto-detection を活かす方が小さい。`--artifact` help と README で known schema を追記すれば十分。
- Workbench は Markdownもスキャンできるが、JSON manifest の compact summary が弱いと一覧で判断しづらい。JSON structured findings の compact summary を足す。
- 実AIを呼ばずに dogfood するため、note は local/manual record として作る。これは既存設計の「AI回答の記録」に沿っており、外部送信禁止にも反しない。

修正:

- CP3 の表示対象は `strategy_ai_review_structured_findings.v1` に限定する。
- Workbench summary は JSON artifact にだけ足し、Markdown preview は既存 viewer に任せる。
- `docs/action-required.md` は作らない。現時点でユーザー判断必須の blocker はない。

## テスト方針

- RED: Case Lite / Daily Brief / Workbench 連結テストを追加し、現行では structured findings が generic / 専用カテゴリなし / compact summary不足になることを確認する。
- GREEN: 最小実装で追加テストを通す。
- Focused:
  - `uv run pytest tests/strategy_ai_review tests/strategy_case_lite tests/strategy_daily_brief tests/strategy_workbench_viewer -q`
  - `uv run sis strategy-ai-review-packet-build --help`
  - `uv run sis strategy-ai-review-note-record --help`
  - `uv run sis strategy-ai-review-findings-structure --help`
  - `uv run sis strategy-case-lite-update --help`
  - `uv run sis strategy-daily-brief --help`
  - `uv run sis strategy-workbench-viewer-build --help`
- Repo:
  - `uv run python scripts/check_current_docs.py`
  - `uv run python scripts/check_cli_catalog.py`
  - `git diff --check`
  - `./scripts/check`

## 破壊的変更

なし。schema enum/category の追加と `context_sections` required 緩和は互換性を上げる変更。Daily Brief の新規 category は新しい artifact output の表現追加であり、外部副作用はない。

## ロールバック方針

この plan、追加テスト、schema/model/service/docs/final-summary の差分を revert する。runtime `data/` artifact は gitignore 対象なので rollback 対象外。
