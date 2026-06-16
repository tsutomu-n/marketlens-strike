<!--
作成日: 2026-06-16_17:05 JST
更新日: 2026-06-16_17:09 JST
-->

# Strategy Review Builder implementation plan

## 結論

最初に作るべきものは、Strategy Case 管理基盤ではなく、既存 artifact を読んで人間 review 用の `review.md` と機械検証用の `review_manifest.json` を出す薄い read-only builder である。

採用方針:

- public CLI は repo 既存の flat command 形式に合わせ、初期名を `strategy-review-build` にする。
- 初期入力の中心は既存の `strategy-backtest-artifact-summary` 相当の artifact summary とする。
- 初期出力は `data/strategy_reviews/{review_id}/review.md` と `data/strategy_reviews/{review_id}/review_manifest.json` に限定する。
- manifest hash は既存 schema と同じ `sha256:<64 hex>` 形式にする。
- 欠損 artifact は隠さず `missing` として出す。`--strict` 指定時だけ exit code 2 にする。
- live、wallet、signing、exchange write、paper gate 作成、alpha 判定、UI、registry は初期対象外にする。

`資料/意見0616.md` の方向を主案として採用し、`資料/意見0616+.md` からは schema、hash provenance、strict/lenient、golden test、安全境界の考え方だけを採る。`意見0616+` の多数 adapter / Strategy Case registry / paper bridge は初期PRでは重い。

## Source inputs

この計画は次を読んで作成した。

- `/home/tn/projects/marketlens-strike/資料/意見0616.md`
- `/home/tn/projects/marketlens-strike/資料/意見0616+.md`
- `AGENTS.md`
- `plan/README.md`
- `docs/REPO_CAPABILITIES_CURRENT_2026-06-16.md`
- `docs/backtest/BACKTEST_TO_PAPER_OBSERVATION_BRIDGE_PLAN_2026-06-15.md`
- `docs/backtest/BACKTEST_TO_PAPER_OBSERVATION_EVIDENCE_MAP_2026-06-15.md`
- `uv run sis --help`
- `uv run sis strategy-backtest-artifact-summary --help`
- `schemas/strategy_backtest_pack.v1.schema.json`
- `schemas/strategy_backtest_pack_validation.v1.schema.json`
- `src/sis/backtest/artifact_summary.py`
- `src/sis/backtest/artifact_summary_registry.py`
- `tests/backtest/test_artifact_summary_registry.py`
- `tests/strategy_authoring/test_cli_bundle.py`
- `tests/strategy_authoring/test_module_boundaries.py`
- `pyproject.toml`
- `scripts/check`

外部調査は設計の補助としてのみ使う。実装 acceptance は repo の code、schema、CLI、tests を優先する。

- VectorBT docs: `Portfolio.from_signals` は signal 中心、複雑な order logic は `from_order_func`。
- NautilusTrader docs: 現実的な slippage / partial fill には L2/L3 order book 粒度が重要。
- scikit-learn `TimeSeriesSplit`: 時系列では未来で学習し過去で評価しない分割と `gap` が重要。
- Frictionless Data specs: resource/package metadata に path、bytes、hash を持たせる発想は参考になる。

## Confirmed repo facts

現行 repo で確認した事実:

- `uv run sis --help` には `strategy-backtest-artifact-summary`、`strategy-backtest-pack`、`strategy-backtest-pack-validate`、`strategy-backtest-acceptance`、`strategy-lifecycle-review`、`strategy-paper-observation-cycle` が存在する。
- `uv run sis --help` には `strategy-review` または `strategy-review-build` は存在しない。
- `strategy-backtest-artifact-summary` は read-only command で、default pack path は `data/research/backtest_pack/strategy_backtest_pack.json`。
- `strategy_backtest_pack.v1` と `strategy_backtest_pack_validation.v1` の hash 形式は bare hex ではなく `sha256:<64 hex>`。
- `strategy_backtest_pack.v1` は `paper_only=true`、`permits_live_order=false`、`live_conversion_allowed=false`、`wallet_used=false`、`exchange_write_used=false` を schema で固定している。
- `src/sis/backtest/artifact_summary.py` は `build_strategy_backtest_artifact_summary(...)` を提供している。
- `src/sis/backtest/artifact_summary_registry.py` は artifact が存在しない場合に `{"path": "...", "exists": false}` を返す。
- `tests/strategy_authoring/test_cli_bundle.py` は artifact summary の CLI 出力が pack / validation / boundary fields を含むことを検証している。
- `scripts/check` は locked sync、Python version、Ruff、current docs check、Pyrefly、ty、Pytest を実行する。

## Problem statement

現状の operator は、Strategy Authoring、backtest pack、artifact summary、lifecycle、paper observation の artifact を個別に読める。しかし、次の問いに1つの読書面で答えにくい。

1. この戦略の review に必要な artifact は揃っているか。
2. どの source path と hash に基づいた review なのか。
3. 欠損、境界違反、schema mismatch はどこにあるか。
4. backtest pack validation は PASS でも、alpha / paper / live readiness を証明していないことが明確か。
5. 人間が次に何を review すればよいか。

この問題を registry、UI、paper bridge、execution engine で解くと初期実装が大きくなる。まずは existing artifact summary を再利用し、1つの review folder を作る。

## Goal

次の command を追加する。

```bash
uv run sis strategy-review-build \
  --review-id ndx-smoke-001 \
  --out data/strategy_reviews \
  --pack-path data/research/backtest_pack/strategy_backtest_pack.json \
  --validation-path data/research/backtest_pack/strategy_backtest_pack_validation.json
```

期待出力:

```text
data/strategy_reviews/ndx-smoke-001/
  review.md
  review_manifest.json
```

`review.md` は人間 review 用で、`review_manifest.json` は再現性、欠損、hash、boundary flags、strict status を機械的に読める contract とする。

実行順序だけを追う場合は、同じディレクトリの `TASK_CHAIN.yaml` を使う。

## Non-goals

初期PRで扱わないもの:

- Strategy Case registry。
- UI / dashboard。
- artifact copy / bundle packaging。
- paper observation gate の新設。
- lifecycle decision の変更。
- live trading、wallet、signing、exchange write。
- external API fetch。
- backtest engine 追加。
- alpha 判定、paper readiness 判定、live readiness 判定。
- `strategy-backtest-artifact-summary` の意味変更。
- `pyproject.toml` / `uv.lock` の dependency 追加。

## Naming decisions

### CLI name

初期CLIは `strategy-review-build` にする。

理由:

- 現行 `sis` CLI は `strategy-backtest-pack`、`strategy-backtest-artifact-summary`、`strategy-lifecycle-review` のような flat command が多い。
- `strategy-review build` の group 化は将来サブコマンドが複数になる時に再検討できる。
- 初期PRで Typer group を作る理由が弱い。

### Directory and id

初期は `case_id` ではなく `review_id` を使う。

理由:

- `case_id` は Strategy Case registry の存在を示唆する。
- 初期成果物は registry object ではなく、1回分の review folder である。
- 後続で registry を作る場合、`review_id` は `case_id` 配下の child にできる。

### Manifest name and schema

- file: `review_manifest.json`
- schema: `strategy_review_manifest.v1`
- schema file: `schemas/strategy_review_manifest.v1.schema.json`
- hash pattern: `^sha256:[a-f0-9]{64}$`

## Artifact contract

`review_manifest.json` の初期必須 field:

```json
{
  "schema_version": "strategy_review_manifest.v1",
  "review_id": "ndx-smoke-001",
  "created_at": "2026-06-16T08:05:00Z",
  "review_status": "READY_FOR_HUMAN_REVIEW",
  "strict": false,
  "paths": {
    "review_dir": "data/strategy_reviews/ndx-smoke-001",
    "review_markdown_path": "data/strategy_reviews/ndx-smoke-001/review.md",
    "manifest_path": "data/strategy_reviews/ndx-smoke-001/review_manifest.json"
  },
  "source_artifacts": [],
  "safety": {
    "permits_live_order": false,
    "live_conversion_allowed": false,
    "wallet_used": false,
    "signing_used": false,
    "exchange_write_used": false
  },
  "summary": {
    "missing_required_count": 0,
    "invalid_required_count": 0,
    "boundary_violation_count": 0
  }
}
```

`source_artifacts[]` の初期 field:

- `artifact_key`: `pack`、`pack_validation`、`framework_run` など。
- `path`: repo relative POSIX path。
- `exists`: boolean。
- `required`: boolean。
- `status`: `present`、`missing`、`invalid`。
- `sha256`: `sha256:<64 hex>`。missing の場合は省略または `null`。
- `summary`: `strategy-backtest-artifact-summary` から転記する最小 summary。

`review_status`:

- `READY_FOR_HUMAN_REVIEW`: 必須 artifact が揃い、boundary violation がない。
- `INCOMPLETE_ARTIFACTS`: 欠損 artifact がある。lenient mode では exit 0。
- `INVALID_INPUT`: schema mismatch、読み込み不能、path validation failure。
- `BLOCKED_BOUNDARY_VIOLATION`: live / wallet / signing / exchange write の混入。

## Markdown contract

`review.md` は次を必ず含める。

- review id、作成時刻、input paths。
- "この review は alpha / paper readiness / live readiness を証明しない" という明示文。
- 必須 artifact 一覧と status。
- backtest pack / validation の要約。
- safety boundary fields。
- missing / invalid / blocked の理由。
- next human review checklist。
- source hash table。

Markdown は snapshot test しやすいように、dynamic timestamp を本文上部の1箇所に限定する。golden test では timestamp を固定 injection するか、timestamp 行だけ normalize する。

## Implementation tasks

### T0: Read-only baseline confirmation

目的:

- 実装前に、CLI、schema、artifact summary の現在値を再確認する。

作業:

```bash
git status --short --branch --untracked-files=all
uv run sis --help
uv run sis strategy-backtest-artifact-summary --help
sed -n '1,220p' schemas/strategy_backtest_pack.v1.schema.json
sed -n '1,220p' schemas/strategy_backtest_pack_validation.v1.schema.json
sed -n '1,260p' src/sis/backtest/artifact_summary.py
sed -n '1,260p' src/sis/backtest/artifact_summary_registry.py
```

受け入れ条件:

- `strategy-review-build` がまだ存在しないことを確認する。
- `strategy-backtest-artifact-summary` の default path がこの計画と衝突しない。
- hash pattern が `sha256:<64 hex>` であることを確認する。

### T1: Schema-first red test

対象ファイル:

- `schemas/strategy_review_manifest.v1.schema.json`
- `tests/strategy_review/test_strategy_review_manifest_schema.py`

作業:

1. 最小 valid manifest fixture を test 内または fixture file に置く。
2. `jsonschema` で valid manifest が通る test を書く。
3. bare hex hash が落ちる test を書く。
4. safety flags が true なら落ちる test を書く。
5. `source_artifacts[].exists=false` では `sha256` が不要である test を書く。

受け入れ条件:

- schema は `sha256:<64 hex>` を要求する。
- live / wallet / signing / exchange write 系は false const にする。
- `review_status` enum が固定される。

### T2: Core builder module

対象ファイル:

- `src/sis/strategy_review/__init__.py`
- `src/sis/strategy_review/manifest.py`
- `src/sis/strategy_review/renderer.py`
- `src/sis/strategy_review/service.py`
- `tests/strategy_review/test_strategy_review_build.py`

設計:

- CLI wrapper に logic を寄せない。
- `service.py` は input paths、review id、out dir、strict、created_at を受け、output path と status を返す。
- `service.py` は既存 `build_strategy_backtest_artifact_summary(...)` を呼ぶ。
- source artifact hash は実ファイルが存在する場合だけ計算する。
- repo relative path 文字列を使い、manifest を環境依存 path にしない。
- new dependency は追加しない。

受け入れ条件:

- minimum pack / validation fixture から `review.md` と `review_manifest.json` が生成される。
- missing path は manifest と markdown の両方に `missing` と出る。
- source file が存在する場合、manifest に `sha256:<64 hex>` が入る。
- boundary field が true に見える input は `BLOCKED_BOUNDARY_VIOLATION` になる。

### T3: CLI command

対象ファイル:

- `src/sis/commands/strategy_review.py`
- `src/sis/cli.py`
- `tests/test_cli_smoke.py`
- `tests/strategy_review/test_strategy_review_cli.py`

CLI:

```bash
uv run sis strategy-review-build --help
uv run sis strategy-review-build \
  --review-id test-review \
  --out data/strategy_reviews \
  --pack-path data/research/backtest_pack/strategy_backtest_pack.json \
  --validation-path data/research/backtest_pack/strategy_backtest_pack_validation.json
```

options:

- `--review-id TEXT`: required in PR-00。自動採番は後続でよい。
- `--out PATH`: default `data/strategy_reviews`。
- `--strict / --no-strict`: default `--no-strict`。
- `--pack-path PATH`: default は artifact summary command と同じ。
- `--validation-path PATH`: default は artifact summary command と同じ。
- artifact summary に既にある optional path options は、初期PRで必要最小限だけ expose する。全 options を一気に複製する場合は tests を増やす。

exit code:

- ready in lenient mode: 0。
- incomplete in lenient mode: 0。
- incomplete in strict mode: 2。
- invalid input: 2。
- boundary violation: 2。
- unexpected exception: 1。

受け入れ条件:

- `uv run sis --help` に command が出る。
- `uv run sis strategy-review-build --help` に options が出る。
- strict missing では output を可能な限り書いたうえで exit 2 にする。
- Typer exception message だけに依存せず、stdout/stderr に output path または failure reason を出す。

### T4: Renderer hardening

対象ファイル:

- `src/sis/strategy_review/renderer.py`
- `tests/strategy_review/test_strategy_review_rendering.py`

作業:

1. Markdown section order を固定する。
2. missing / invalid / boundary violation が上部に出るようにする。
3. "pack validation PASS is not alpha / paper / live proof" を固定文として入れる。
4. source hash table を入れる。
5. line wrapping と code block を安定させる。

受け入れ条件:

- golden snapshot が読みやすい。
- dynamic timestamp が test を壊さない。
- missing artifact が下部に埋もれない。

### T5: Docs and operator recipe

対象ファイル:

- `docs/strategy_review/README.md`
- `docs/backtest/README.md`
- `docs/REPO_CAPABILITIES_CURRENT_2026-06-16.md`
- `plan/README.md`

作業:

1. `docs/strategy_review/README.md` を作り、command と出力を説明する。
2. backtest docs から strategy review docs へ導線を張る。
3. current capability docs に「review builder は human-review artifact であり readiness proof ではない」と追記する。
4. すべての Markdown timestamp header を更新する。

受け入れ条件:

- docs が live readiness を誇張しない。
- generated artifact を current truth として扱わない。
- `scripts/check_current_docs.py` が通る。

### T6: Verification

最小検証:

```bash
uv run sis strategy-review-build --help
uv run pytest -q tests/strategy_review tests/backtest/test_artifact_summary_registry.py tests/strategy_authoring/test_cli_bundle.py
uv run python scripts/check_current_docs.py
```

最終検証:

```bash
./scripts/check
```

実装PRでは、少なくとも最小検証を通す。`./scripts/check` が時間や環境で失敗した場合は、失敗箇所、再現コマンド、未検証範囲を final report に残す。

## Suggested PR slices

### PR-REVIEW-00: Minimum useful vertical slice

含める:

- manifest schema。
- `src/sis/strategy_review/` の最小 service / renderer。
- `strategy-review-build` command。
- `review.md` / `review_manifest.json` output。
- strict / lenient behavior。
- focused tests。

含めない:

- Strategy Case registry。
- UI。
- lifecycle decision 変更。
- paper bridge。
- artifact bundle copy。

### PR-REVIEW-01: More source sections

含める候補:

- authoring spec/result summary section。
- lifecycle review summary section。
- paper observation summary section。
- optional path options の拡張。

条件:

- PR-REVIEW-00 の manifest を壊さない。
- missing を許容し、read-only のままにする。

### PR-REVIEW-02: Operator hardening

含める候補:

- docs / runbook。
- golden markdown fixture。
- sample output under ignored or test fixture path。
- review checklist refinement。

条件:

- readiness proof と誤読される表現を削る。

## Stop conditions

次のどれかが出たら、実装を止めて計画を更新する。

- `strategy-backtest-artifact-summary` の contract を壊さないと作れない。
- hash format を bare hex に変える必要が出た。
- live / wallet / signing / exchange write を触る必要が出た。
- new dependency が必要になった。
- registry、UI、paper gate、lifecycle decision change が PR-00 に混入しそうになった。
- generated artifact を source-controlled truth にする必要が出た。
- external API fetch が必要になった。
- command group `strategy-review build` にする明確な理由が出た。

## Corrections from the opinion drafts

修正済みの点:

- `strategy_backtest_pack_manifest.json` ではなく、現行 default は `data/research/backtest_pack/strategy_backtest_pack.json`。
- hash schema は bare 64 hex ではなく `sha256:<64 hex>`。
- `case_id` ではなく `review_id` から始める。
- `strategy-review build` ではなく、現行 CLI に合わせて `strategy-review-build` から始める。
- `意見0616+` の adapter 群を初期PRで全部作らない。
- artifact summary の既存 missing behavior を再利用し、欠損判定を二重実装しない。
- `pack_validation` PASS は alpha / paper / live readiness proof ではないと固定文にする。
- `filecite...` 形式の非portable citation は repo docs に持ち込まない。

## Risk audit

残る誤謬リスクと対策:

- リスク: `strategy-review-build` が readiness proof と誤読される。
  - 対策: Markdown と docs に "human review artifact only" を固定文で入れる。
- リスク: artifact summary の dynamic timestamp が snapshot test を不安定にする。
  - 対策: created_at injection または normalize helper を test に入れる。
- リスク: CLI option を artifact summary と完全同期しようとしてPRが大きくなる。
  - 対策: PR-00 は pack / validation / essential optional paths に絞る。拡張は PR-REVIEW-01。
- リスク: source path が absolute path になり環境依存になる。
  - 対策: repo root relative POSIX path に正規化する。
- リスク: source artifact を copy して generated data が肥大化する。
  - 対策: PR-00 は path と hash だけを持つ。
- リスク: missing artifact の lenient exit 0 が成功と誤読される。
  - 対策: `review_status=INCOMPLETE_ARTIFACTS` と markdown 上部 warning を必須にする。
- リスク: strict exit 2 の場合に output が書かれず、review できない。
  - 対策: 読める範囲の output を先に書き、最後に exit code を決める。
- リスク: `strategy-review-build` と将来の `strategy-review` group が競合する。
  - 対策: 初期は flat command。複数サブコマンドが必要になった時点で compatibility alias を計画する。

## Better option adopted

より良い案として、初期PRの中心を「新しい Strategy Case モデル」ではなく「既存 artifact summary の review 化」に変更する。

理由:

- 既存の `build_strategy_backtest_artifact_summary(...)` を使えるため、重複 loader を避けられる。
- 欠損 artifact の扱いが既にある。
- pack / validation / safety fields を現行 schema と合わせやすい。
- 人間 review に必要な価値が PR-00 で出る。
- registry や UI を後から足しても、`review_manifest.json` を stable input にできる。

## Coder handoff

実装者への指示:

1. この README と `AGENTS.md` を読む。
2. T0 の read-only confirmation を実行する。
3. PR-REVIEW-00 だけを実装する。
4. 先に schema と tests を書く。
5. `strategy-backtest-artifact-summary` の既存 builder を再利用する。
6. `review.md` と `review_manifest.json` 以外の runtime artifact は増やさない。
7. `review_manifest.json` は `schemas/strategy_review_manifest.v1.schema.json` で validation できるようにする。
8. live / wallet / signing / exchange write を触らない。
9. 最小検証を通してから docs を更新する。
10. 最後に `./scripts/check` を試す。
