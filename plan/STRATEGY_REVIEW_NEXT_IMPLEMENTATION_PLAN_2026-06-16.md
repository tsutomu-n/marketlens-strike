<!--
作成日: 2026-06-16_20:23 JST
更新日: 2026-06-16_20:23 JST
-->

# Strategy Review Builder 次期実装 最終計画

## 結論

次に実装するものは、既存の `strategy-review-build` をいきなり大きく拡張することではない。まず **Review Builder Contract Audit / Hardening** を入れ、その後に **Strategy Authoring / Lifecycle section** を追加する。

最終決定した実装順は次の通り。

```text
PR-REVIEW-00.1: Review Builder Contract Audit and Hardening
  目的: review_manifest / review.md を将来の Review Packet / UI / paper bridge の土台として安全に固定する。

PR-REVIEW-01: Add Strategy Authoring and Lifecycle Sections to Strategy Review
  目的: review.md を「backtest artifact要約」から「戦略レビュー資料」へ進化させる。
```

`PR-REVIEW-00.1` が通るまで、`operator_review.yaml`、paper bridge、Strategy Case registry、Svelte UI、Bitget / Hyperliquid production対応には進まない。

---

## 背景

現行実装済みの `strategy-review-build` は、既存artifactから `review.md` と `review_manifest.json` を生成する最小縦切りである。この方向性は維持する。

ただし、この成果物は今後の次の土台になる。

- 人間レビュー用のMarkdown資料
- source artifact provenance
- 後続のoperator review
- Svelte UIの入力
- paper observation bridgeの前段

したがって、次の実装では「表示項目を増やす」前に、contractとして曖昧な部分を潰す。

---

## 目的

### 全体目的

MarketLens Strike において、既存のStrategy Authoring / Backtest / Lifecycle artifactを、人間がレビュー可能なMarkdown資料へ変換する仕組みを、安全で再利用可能なパッケージとして強化する。

### PR-REVIEW-00.1 の目的

`review_manifest.json` と `review.md` の契約を固める。

具体的には次を達成する。

1. `builder_safety` と `source_safety` を分離する。
2. path / hash / review_id のvalidationを強化する。
3. `missing`、`invalid`、`blocked` を明確に分離する。
4. `--replace-existing` により上書き挙動を明示する。
5. Pydantic model と tracked JSON Schema のズレをtestで検出する。
6. dogfoodで実artifactに対して `review.md` が読めることを確認する。

### PR-REVIEW-01 の目的

`review.md` に次の2つのセクションを追加し、レビュー資料としての価値を上げる。

1. Strategy Authoring section
2. Strategy Lifecycle section

これにより、レビュー者が次を1つのMarkdownで把握できるようにする。

- この戦略は何をするのか。
- どのauthoring specに基づくのか。
- backtest / lifecycle上どの状態なのか。
- paperへ進む前に何が不足しているのか。

---

## 制約

## グローバル制約

次は絶対条件とする。

```text
- read-only 実装にする。
- live order を許可しない。
- wallet secret を使わない。
- signing を使わない。
- exchange write を使わない。
- external API fetch を入れない。
- backtest engine を追加しない。
- Strategy Case registry を作らない。
- Svelte UI を作らない。
- paper bridge を作らない。
- lifecycle decision の意味を変更しない。
- alpha / paper readiness / live readiness を自動判定しない。
- pyproject.toml / uv.lock を変更しない。
- generated artifact を source-controlled truth として扱わない。
```

## path / provenance 制約

`review_manifest.json` に出すpathは次を満たす。

```text
- repo-relative POSIX path にする。
- absolute path を出さない。
- ../ を含めない。
- backslash を含めない。
- source artifact が存在する場合のみ sha256 を計算する。
- hash形式は sha256:<64 lowercase hex> に固定する。
```

## review_id 制約

`review_id` は出力pathに使うため、必ずvalidationする。

許可pattern:

```regex
^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$
```

禁止例:

```text
../x
/tmp/x
.hidden
a/b
a\b
空文字
```

## safety 制約

`safety` は1層にしない。必ず次の2層に分ける。

```json
{
  "builder_safety": {
    "permits_live_order": false,
    "live_conversion_allowed": false,
    "wallet_used": false,
    "signing_used": false,
    "exchange_write_used": false
  },
  "source_safety": {
    "status": "PASS",
    "boundary_violation_count": 0,
    "unknown_boundary_count": 0,
    "observed_flags": {
      "permits_live_order": false,
      "live_conversion_allowed": false,
      "wallet_used": false,
      "signing_used": false,
      "exchange_write_used": false
    }
  }
}
```

意味:

```text
builder_safety:
  strategy-review-build 自身が live / wallet / signing / exchange write を使わないこと。

source_safety:
  入力source artifactから読み取れた境界状態。
```

`source_safety.status` は次のenumにする。

```text
PASS
UNKNOWN
BLOCKED
```

---

## review_status の定義

`review_status` は「戦略が良いか」ではなく、**レビュー資料として読めるか** を表す。

```text
READY_FOR_HUMAN_REVIEW
  必須artifactが存在し、読めて、hash計算でき、manifest schema-validで、builder_safety PASS、source_safety PASS。

INCOMPLETE_ARTIFACTS
  欠損artifactがある、または source_safety UNKNOWN。lenient modeでは exit 0。

INVALID_INPUT
  artifactは存在するが、JSON破損、schema mismatch、path validation failure、hash計算不能などでレビュー信頼性が壊れている。

BLOCKED_BOUNDARY_VIOLATION
  入力artifact上で live / wallet / signing / exchange write 等の境界違反が検出された。
```

重要:

```text
backtest pack validation が FAIL でも、artifactとして読めるなら review_status は READY_FOR_HUMAN_REVIEW になり得る。
これは「失敗した戦略をレビューできる」という意味であり、戦略評価ではない。
```

---

## パッケージ責務

単一責務を保つため、`src/sis/strategy_review/` は次の構成にする。

```text
src/sis/strategy_review/
  __init__.py
  manifest.py
  provenance.py
  sections.py
  renderer.py
  service.py
```

## `manifest.py`

責務:

```text
- Pydantic model
- enum
- review_id validation
- schema-facing contract
- safety model
- summary model
```

含めるmodel候補:

```text
ReviewStatus
SourceSafetyStatus
SourceArtifactStatus
BuilderSafety
SourceSafety
ReviewPaths
SourceArtifact
ReviewSummary
StrategyReviewManifest
```

禁止:

```text
- ファイル読み込み
- hash計算
- Markdown生成
- Typer依存
```

## `provenance.py`

責務:

```text
- repo-relative POSIX path 正規化
- absolute path / ../ / backslash 拒否
- file existence check
- sha256:<64 hex> 計算
- SourceArtifact の基本構築
```

公開関数候補:

```python
validate_review_id(review_id: str) -> str
repo_relative_posix_path(path: Path, *, repo_root: Path) -> str
build_source_artifact(
    *,
    artifact_key: str,
    path: Path,
    required: bool,
    repo_root: Path,
) -> SourceArtifact
compute_sha256_prefixed(path: Path) -> str
```

禁止:

```text
- Markdown生成
- backtest summary 解釈
- Typer依存
```

## `sections.py`

責務:

```text
- source artifact から review.md のセクション情報を作る。
- Markdown本文全体のrenderingはしない。
```

PR-REVIEW-00.1では最小でよい。PR-REVIEW-01で本格利用する。

公開class候補:

```python
@dataclass(frozen=True)
class ReviewSection:
    section_id: str
    title: str
    status: str
    markdown: str
    source_artifact_keys: tuple[str, ...]
```

PR-REVIEW-01で追加するsection:

```text
BacktestPackSection
AuthoringSpecSection
LifecycleReviewSection
```

## `renderer.py`

責務:

```text
- StrategyReviewManifest と ReviewSection 群から review.md を生成する。
- section order を固定する。
- missing / invalid / blocked を上部に出す。
- readiness proof ではない固定文を入れる。
- source hash table を出す。
```

禁止:

```text
- file write
- hash計算
- CLI option処理
```

## `service.py`

責務:

```text
- orchestration
- 既存 build_strategy_backtest_artifact_summary(...) の呼び出し
- source artifact 情報の集約
- manifest組み立て
- renderer呼び出し
- review.md / review_manifest.json のwrite
- exit判断に必要なresult object返却
```

禁止:

```text
- Typer-specific error message依存
- live / paper / execution変更
- external API fetch
```

## `src/sis/commands/strategy_review.py`

責務:

```text
- Typer CLI wrapper
- option定義
- service呼び出し
- exit code変換
- stdout/stderrへの最小summary表示
```

禁止:

```text
- business logic
- Markdown生成
- hash計算
```

---

# PR-REVIEW-00.1: Review Builder Contract Audit and Hardening

## 目的

`review_manifest.json` と `review.md` を、将来のReview Packet / UI / paper bridgeの土台として安全に使えるcontractへ強化する。

## 対象ファイル

```text
schemas/strategy_review_manifest.v1.schema.json
src/sis/strategy_review/manifest.py
src/sis/strategy_review/provenance.py
src/sis/strategy_review/renderer.py
src/sis/strategy_review/service.py
src/sis/commands/strategy_review.py
tests/strategy_review/test_strategy_review_manifest_schema.py
tests/strategy_review/test_strategy_review_provenance.py
tests/strategy_review/test_strategy_review_build.py
tests/strategy_review/test_strategy_review_cli.py
tests/strategy_review/test_strategy_review_rendering.py
docs/strategy_review/README.md
```

`provenance.py` と `test_strategy_review_provenance.py` がまだ無い場合は追加する。

## 実装タスク

### T0: 現状確認

実行:

```bash
git status --short --branch --untracked-files=all
uv run sis --help
uv run sis strategy-review-build --help
uv run pytest -q tests/strategy_review
```

確認:

```text
- strategy-review-build が存在する。
- review.md / review_manifest.json が生成できる。
- 現在のmanifest shapeを確認する。
- builder_safety / source_safety が未分離なら修正対象にする。
```

### T1: Manifest model / schema 更新

作業:

```text
1. manifest.py に BuilderSafety / SourceSafety を追加する。
2. safety 単一fieldがある場合は builder_safety / source_safety に分割する。
3. review_status定義をこの計画の定義へ合わせる。
4. source_safety.status enum を PASS / UNKNOWN / BLOCKED にする。
5. schemas/strategy_review_manifest.v1.schema.json を更新する。
```

受入条件:

```text
- builder_safety は全flag false const。
- source_safety.status が enum検証される。
- source_safety BLOCKED の場合、review_status は BLOCKED_BOUNDARY_VIOLATION。
- source_safety UNKNOWN の場合、review_status は INCOMPLETE_ARTIFACTS。
- manifest JSONがschema-valid。
```

### T2: Provenance validation 実装

作業:

```text
1. provenance.py を追加または強化する。
2. review_id validation を実装する。
3. repo-relative POSIX path正規化を実装する。
4. absolute path / ../ / backslash を拒否する。
5. sha256:<64 hex> 計算を実装する。
```

受入条件:

```text
- valid review_id が通る。
- invalid review_id が ValueError または domain error になる。
- source pathはmanifest内でrepo-relative POSIX pathになる。
- missing artifact は sha256=null または省略になる。
- existing artifact は sha256:<64 lowercase hex> になる。
```

### T3: `--replace-existing` 実装

CLI option:

```bash
--replace-existing / --no-replace-existing
```

default:

```text
--no-replace-existing
```

挙動:

```text
- review_dir が存在しない: 作成して続行。
- review_dir が存在し、--replace-existingなし: exit 2。既存ファイルを変更しない。
- review_dir が存在し、--replace-existingあり: review.md / review_manifest.json を再生成。
```

受入条件:

```text
- 無意識の上書きを防げる。
- 明示flagで再生成できる。
- exit 2時にfailure reasonがstdout/stderrに出る。
```

### T4: Source safety extraction

作業:

```text
1. build_strategy_backtest_artifact_summary(...) の出力から読み取れるboundary fieldsをsource_safetyへ反映する。
2. 読み取れないsourceは UNKNOWN として扱う。
3. true flag が1つでもある場合は BLOCKED にする。
```

対象flag:

```text
permits_live_order
live_conversion_allowed
wallet_used
signing_used
exchange_write_used
venue_write_used
```

補足:

```text
- venue_write_used が既存artifactに存在する場合は source_safety.observed_flags に含めてよい。
- builder_safety には venue_write_used を入れる場合も、従来flagとの互換を壊さない。
```

受入条件:

```text
- boundary violation fixture で BLOCKED_BOUNDARY_VIOLATION になる。
- unknown boundary fixture で INCOMPLETE_ARTIFACTS になる。
- PASS fixture で READY_FOR_HUMAN_REVIEW になる。
```

### T5: Renderer hardening

作業:

```text
1. review.md冒頭に review_status / source_safety / missing / invalid / blocked counts を出す。
2. readiness proofではない固定文を冒頭付近に出す。
3. source hash tableを出す。
4. missingとinvalidを別セクションで出す。
5. source_safety UNKNOWNを目立たせる。
```

固定文:

```text
このreviewは人間の戦略レビュー用artifactです。
alpha、paper readiness、live readinessを証明しません。
backtest pack validation が PASS の場合でも、戦略の収益性、paper移行可否、live実行可否は証明されません。
```

受入条件:

```text
- review.md の上部だけで状態が分かる。
- missing / invalid / blocked が下部に埋もれない。
- pack validation PASS がreadiness proofでないことが明記される。
```

### T6: stdout / exit behavior audit

CLI出力に最低限含める。

```text
review_status=<...>
review_dir=<...>
manifest_path=<...>
markdown_path=<...>
missing_required_count=<...>
invalid_required_count=<...>
boundary_violation_count=<...>
```

exit code:

```text
READY_FOR_HUMAN_REVIEW: 0
INCOMPLETE_ARTIFACTS + lenient: 0
INCOMPLETE_ARTIFACTS + strict: 2
INVALID_INPUT: 2
BLOCKED_BOUNDARY_VIOLATION: 2
unexpected exception: 1
```

受入条件:

```text
- lenient missing は exit 0 だが stdout上でINCOMPLETEと分かる。
- strict missing は可能な限りoutputを書いて exit 2。
- invalid input は exit 2。
- boundary violation は exit 2。
```

### T7: Dogfood

実artifactで最低3本確認する。

```bash
uv run sis strategy-review-build \
  --review-id dogfood-complete-001 \
  --out data/strategy_reviews \
  --replace-existing \
  --pack-path data/research/backtest_pack/strategy_backtest_pack.json \
  --validation-path data/research/backtest_pack/strategy_backtest_pack_validation.json
```

```bash
uv run sis strategy-review-build \
  --review-id dogfood-missing-001 \
  --out data/strategy_reviews \
  --replace-existing \
  --pack-path data/research/backtest_pack/not_found.json \
  --validation-path data/research/backtest_pack/not_found_validation.json
```

```bash
uv run sis strategy-review-build \
  --review-id dogfood-strict-missing-001 \
  --out data/strategy_reviews \
  --replace-existing \
  --strict \
  --pack-path data/research/backtest_pack/not_found.json \
  --validation-path data/research/backtest_pack/not_found_validation.json
```

確認観点:

```text
- review.mdを3分で読んで状態が分かるか。
- source_safety UNKNOWN / BLOCKED が分かるか。
- missing / invalid の違いが分かるか。
- source path / hash を追跡できるか。
- readiness proofではない固定文が目に入るか。
```

## テスト方針

### Unit tests

```text
tests/strategy_review/test_strategy_review_manifest_schema.py
tests/strategy_review/test_strategy_review_provenance.py
tests/strategy_review/test_strategy_review_build.py
tests/strategy_review/test_strategy_review_rendering.py
```

検査内容:

```text
- valid manifest passes JSON Schema.
- bare hex hash rejected.
- sha256:<64 hex> accepted.
- builder_safety flags are false const.
- source_safety status enum works.
- invalid review_id rejected.
- invalid path rejected.
- existing file gets prefixed hash.
- missing file gets missing status.
- boundary true fixture becomes BLOCKED.
```

### CLI tests

```text
tests/strategy_review/test_strategy_review_cli.py
```

検査内容:

```text
- --help works.
- valid build exits 0.
- lenient missing exits 0.
- strict missing exits 2.
- invalid review_id exits 2.
- existing output without --replace-existing exits 2.
- existing output with --replace-existing succeeds.
```

### Golden Markdown tests

```text
tests/strategy_review/test_strategy_review_rendering.py
```

検査内容:

```text
- section order stable.
- timestamp injectable or normalized.
- fixed warning sentence present.
- missing / invalid / blocked appear near top.
- source hash table present.
```

### Focused verification

```bash
uv run sis strategy-review-build --help
uv run pytest -q tests/strategy_review tests/backtest/test_artifact_summary_registry.py tests/strategy_authoring/test_cli_bundle.py
uv run python scripts/check_current_docs.py
git diff --check
```

### Full verification

```bash
./scripts/check
```

`./scripts/check` が環境や時間で失敗した場合は、失敗コマンド、失敗箇所、未検証範囲を最終報告に残す。

## PR-REVIEW-00.1 完了条件

```text
1. builder_safety と source_safety が分離されている。
2. review_id validation がある。
3. repo-relative POSIX path validation がある。
4. sha256:<64 lowercase hex> hashが出る。
5. missing / invalid / blocked が分離される。
6. --replace-existing がある。
7. lenient / strict のexit挙動が仕様通り。
8. review.md冒頭で状態とwarningが分かる。
9. review_manifest.json が schema-valid。
10. 既存 strategy-backtest-artifact-summary の意味を変えていない。
11. live / wallet / signing / exchange write を触っていない。
12. new dependency なし。
13. focused verification が通る。
14. ./scripts/check を試行し、結果を報告できる。
```

---

# PR-REVIEW-01: Add Strategy Authoring and Lifecycle Sections

## 目的

`review.md` を「backtest artifact summary」から「戦略レビュー資料」へ拡張する。

最初に追加するsourceは2つだけにする。

```text
1. strategy_authoring_spec
2. strategy_lifecycle_review
```

paper observation、operator review、paper bridgeはまだ入れない。

## 対象ファイル

```text
src/sis/strategy_review/manifest.py
src/sis/strategy_review/provenance.py
src/sis/strategy_review/sections.py
src/sis/strategy_review/renderer.py
src/sis/strategy_review/service.py
src/sis/commands/strategy_review.py
schemas/strategy_review_manifest.v1.schema.json
tests/strategy_review/test_strategy_review_sections.py
tests/strategy_review/test_strategy_review_authoring_section.py
tests/strategy_review/test_strategy_review_lifecycle_section.py
tests/strategy_review/test_strategy_review_cli.py
docs/strategy_review/README.md
```

## CLI options

追加する。

```bash
--authoring-spec PATH
--lifecycle-review PATH
```

使用例:

```bash
uv run sis strategy-review-build \
  --review-id dogfood-authoring-lifecycle-001 \
  --out data/strategy_reviews \
  --replace-existing \
  --pack-path data/research/backtest_pack/strategy_backtest_pack.json \
  --validation-path data/research/backtest_pack/strategy_backtest_pack_validation.json \
  --authoring-spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml \
  --lifecycle-review data/research/strategy_lifecycle/strategy_lifecycle_review.json
```

## 実装タスク

### T1: Source artifact keys 追加

追加key:

```text
authoring_spec
lifecycle_review
```

受入条件:

```text
- source_artifacts[] に authoring_spec / lifecycle_review が出る。
- missingの場合も review.md / manifest に missing として出る。
- hash / path validation は既存provenance処理を再利用する。
```

### T2: AuthoringSpecSection 実装

目的:

```text
戦略が何をするのかをreview.mdで読めるようにする。
```

抽出するfield候補:

```text
schema_version
strategy_id
strategy_family
strategy_version
execution_venue
symbol / execution_symbol
timeframe
side / side_column
entry / long_entry / short_entry summary
close / reduce / add / rebalance presence
exit settings summary
sizing summary
risk_throttle / portfolio constraints summary
order / execution constraints summary
```

注意:

```text
- すべてのDSL詳細を完全展開しない。
- まずは存在・概要・主要field pathを出す。
- unknown fieldは壊さず「unparsed/available in source」として扱う。
```

受入条件:

```text
- review.md に Strategy Definition section が出る。
- strategy_id / timeframe / execution venue / entry-exit概要が読める。
- YAML parse失敗時は INVALID_INPUT。
- schema未検証でも読める範囲を出せる場合は warning を出す。
```

### T3: LifecycleReviewSection 実装

目的:

```text
lifecycle上の状態をreview.mdで読めるようにする。
```

抽出するfield候補:

```text
schema_version
review_id / run_id / strategy_id if present
lifecycle_decision
backtest_acceptance_decision
paper_observation_status
phase_gate_summary
boundary flags
block reasons
next recommended action if present
```

注意:

```text
- ELIGIBLE_FOR_LIVE_CANARY_PLAN を live許可と書かない。
- lifecycle review は live order を許可しない、と固定文を入れる。
```

受入条件:

```text
- review.md に Lifecycle Summary section が出る。
- lifecycle decision が読める。
- live許可ではないことが明記される。
- missing lifecycle review は lenientでmissing表示。
```

### T4: Renderer統合

PR-REVIEW-01後のsection order:

```text
1. Review Status
2. Human Review Warning
3. Strategy Definition
4. Source Artifacts
5. Backtest Pack Summary
6. Lifecycle Summary
7. Safety Boundary
8. Missing / Invalid / Blocked
9. Next Human Review Checklist
10. Source Hash Table
```

受入条件:

```text
- Strategy Definition がBacktest Summaryより前に出る。
- Lifecycle Summary がSafety Boundaryより前に出る。
- Missing / Invalid / Blocked は上部にもsummaryとして出る。
```

## テスト方針

### Unit tests

```bash
uv run pytest -q \
  tests/strategy_review/test_strategy_review_sections.py \
  tests/strategy_review/test_strategy_review_authoring_section.py \
  tests/strategy_review/test_strategy_review_lifecycle_section.py
```

### CLI tests

```bash
uv run pytest -q tests/strategy_review/test_strategy_review_cli.py
```

追加検査:

```text
- --authoring-spec 指定時にsource artifactが増える。
- --lifecycle-review 指定時にsource artifactが増える。
- missing optional sourceは lenient exit 0。
- strict時のrequired/optional扱いが仕様通り。
```

PR-REVIEW-01では、`authoring_spec` と `lifecycle_review` は初期defaultでは optional とする。必須化は後続で判断する。

## PR-REVIEW-01 完了条件

```text
1. --authoring-spec が使える。
2. --lifecycle-review が使える。
3. review.md に Strategy Definition section が出る。
4. review.md に Lifecycle Summary section が出る。
5. Strategy Definition は戦略概要を人間が読める粒度で出す。
6. Lifecycle Summary は live許可と誤読されない。
7. source_artifacts[] に authoring_spec / lifecycle_review が出る。
8. missing / invalid / blocked の扱いがPR-REVIEW-00.1と一貫する。
9. new dependency なし。
10. existing command compatibility を壊さない。
11. focused verification が通る。
```

---

# Dogfood判定基準

PR-REVIEW-00.1 と PR-REVIEW-01 の各完了後、実際の `review.md` を読み、次を人間が確認する。

```text
1. 3分以内にreview_statusが分かるか。
2. このreviewがreadiness proofでないと分かるか。
3. どのsource artifactに基づくか分かるか。
4. source safetyがPASS / UNKNOWN / BLOCKEDのどれか分かるか。
5. 戦略が何をしているか分かるか。
6. lifecycle上の状態が分かるか。
7. 次に人間が見るべき不足が分かるか。
```

6または7が満たせない場合は、paper bridgeやoperator reviewへ進まず、renderer / section を修正する。

---

# まだやらないこと

次の実装ではやらない。

```text
- operator_review.yaml
- APPROVE_FOR_PAPER bridge
- paper observation start command
- Strategy Case registry
- Svelte UI
- Bitget / Hyperliquid production venue対応
- Crypto perp data collector
- 新backtest engine
- 自動alpha判定
- 自動paper承認
- external API fetch
- new dependency追加
```

---

# Stop conditions

次のいずれかが出たら実装を止め、計画を更新する。

```text
- 既存 strategy-backtest-artifact-summary のcontractを破壊しないと実装できない。
- source_safety を正しく判定するには外部API fetchが必要になる。
- live / wallet / signing / exchange write に触る必要が出た。
- new dependency が必要になった。
- Strategy Case registry / UI / paper bridge が混入しそうになった。
- generated artifactをsource-controlled truthにする必要が出た。
- authoring spec sectionの完全parseがPRを巨大化させる。
- lifecycle decisionの意味を変える必要が出た。
```

---

# 最終検証コマンド

PR-REVIEW-00.1 / PR-REVIEW-01 共通。

## Focused

```bash
uv run sis strategy-review-build --help
uv run pytest -q tests/strategy_review tests/backtest/test_artifact_summary_registry.py tests/strategy_authoring/test_cli_bundle.py
uv run python scripts/check_current_docs.py
git diff --check
```

## Full

```bash
./scripts/check
```

## Dogfood

```bash
uv run sis strategy-review-build \
  --review-id dogfood-001 \
  --out data/strategy_reviews \
  --replace-existing \
  --pack-path data/research/backtest_pack/strategy_backtest_pack.json \
  --validation-path data/research/backtest_pack/strategy_backtest_pack_validation.json
```

PR-REVIEW-01後:

```bash
uv run sis strategy-review-build \
  --review-id dogfood-authoring-lifecycle-001 \
  --out data/strategy_reviews \
  --replace-existing \
  --pack-path data/research/backtest_pack/strategy_backtest_pack.json \
  --validation-path data/research/backtest_pack/strategy_backtest_pack_validation.json \
  --authoring-spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml \
  --lifecycle-review data/research/strategy_lifecycle/strategy_lifecycle_review.json
```

---

# 実装者への作業順序

```text
1. このドキュメントを読む。
2. アップロード済みの Strategy Review Builder implementation plan と差分を確認する。
3. PR-REVIEW-00.1 だけを実装する。
4. Focused verification を通す。
5. Dogfood review.md を生成して読む。
6. Dogfoodで問題がなければ PR-REVIEW-01 に進む。
7. PR-REVIEW-01 で authoring / lifecycle sections を追加する。
8. Focused verification と Dogfoodを再実行する。
9. ./scripts/check を試す。
10. 失敗がある場合は、失敗コマンド・原因・未検証範囲をPR本文に残す。
```

---

# 変更理由

元計画は、最初の `strategy-review-build` としては妥当だった。ただし、実装後の次手としては次の抜けが残る。

```text
- builder自身の安全性とsource artifactの安全性が混ざる危険。
- source_safety UNKNOWNをREADY扱いする誤謬リスク。
- missing と invalid が読書面で同列化する危険。
- review_id / output path のpath traversalリスク。
- 無意識の上書きリスク。
- Pydantic model と JSON Schema の二重管理リスク。
- backtest要約だけでは「戦略が何をしているか」が見えない問題。
```

この計画では、それらを `PR-REVIEW-00.1` と `PR-REVIEW-01` に分けて解消する。

