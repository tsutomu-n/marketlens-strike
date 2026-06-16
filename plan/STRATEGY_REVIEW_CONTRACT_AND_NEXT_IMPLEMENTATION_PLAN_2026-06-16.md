<!--
作成日: 2026-06-16_21:45 JST
更新日: 2026-06-16_21:45 JST
-->

# Strategy Review Builder Contract Hardening / Next Implementation Plan

## 0. 結論

次に実装するべきものは、`PR-REVIEW-00.1: Review Manifest Contract Hardening` である。

既存の `strategy-review-build` は、既存 artifact から `review.md` と `review_manifest.json` を作る薄い read-only builder として正しい方向にある。ただし、後続の `Strategy Authoring / Lifecycle section`、`operator_review.yaml`、paper bridge、Svelte UI がこの出力を土台にするため、先に manifest contract を固める必要がある。

本計画の最終順序は次の通り。

```text
1. PR-REVIEW-00.1
   Review Manifest Contract Hardening
   builder/source safety分離、path validation、replace-existing、atomic write、schema alignment

2. Dogfood Gate
   complete / missing / strict missing / invalid / boundary fixtureで実読確認

3. PR-REVIEW-01
   Strategy Authoring / Lifecycle sections

4. PR-REVIEW-02
   Review Packet Hardening
   golden fixture / checklist / operator recipe

5. PR-OPERATOR-00
   operator_review.yaml

6. PR-PAPER-00
   APPROVE_FOR_PAPER bridge

7. PR-CASE-00
   Strategy Case registry

8. PR-UI-00
   Svelte viewer
```

本ドキュメントは、コーダーがこのまま読んで実装できる粒度で、目的、制約、対象ファイル、実装タスク、テスト方針、完了条件を定義する。

---

## 1. 背景

現行 repo は、Strategy Authoring、Backtest、Lifecycle、Paper operation などの artifact を作る能力をすでに持つ。現在の不足は、新しい backtest engine や Strategy Case registry ではなく、散らばった既存 artifact を人間レビュー用の `review.md` と機械検証用の `review_manifest.json` に変換する安定した read-only contract である。

既存計画では、最初に `strategy-review-build` を追加し、`data/strategy_reviews/{review_id}/review.md` と `review_manifest.json` を出す薄い builder とする方針が採用されている。この主方針は維持する。

ただし、追加監査により、次の契約漏れを修正する必要がある。

- builder 自身の安全性と source artifact の安全性が混同されるリスク。
- `review_status` が「戦略評価」と誤読されるリスク。
- `missing` と `invalid` の扱いが弱いリスク。
- source artifact に `bytes` / `detected_schema_version` / `error` がなく、将来 UI・再生成・監査で弱いリスク。
- path traversal / absolute path / hidden path / secret path の検査漏れ。
- 既存 review directory の無自覚な上書き。
- strict mode 失敗時に壊れた output が残るリスク。
- Pydantic model と tracked JSON Schema のズレ。
- CLI の exit code だけを見て、stdout/stderr に machine-readable summary がないリスク。

---

## 2. 外部仕様から採用する設計原則

### 2.1 Provenance

W3C PROV は、provenance を「データや物を作ることに関与した entities / activities / people の情報で、品質・信頼性・信用性評価に使えるもの」と定義する。

この計画では、次の対応を採用する。

- source artifact は entity として扱う。
- `strategy-review-build` 実行は activity として扱う。
- `review_manifest.json` は `review.md` の根拠台帳として扱う。
- builder 自身の行為と、source artifact の安全性を分ける。

参考: https://www.w3.org/TR/prov-overview/

### 2.2 Resource path / bytes / hash

Frictionless Data Resource 仕様は、resource metadata に `path`、`bytes`、`hash` を持てる設計を示す。また local POSIX path は相対 sibling / child に制限し、absolute path `/` と parent path `../` はセキュリティ上禁止する方針を示す。

この計画では、次の対応を採用する。

- manifest path は repo-relative POSIX path に統一する。
- `/tmp/foo.json`、`../foo.json`、`data/../.env`、`a\b` を拒否する。
- source artifact には `sha256:<64 hex>` と `bytes` を記録する。
- hash 形式は既存 repo contract に合わせ、`sha256:<64 hex>` とする。

参考: https://specs.frictionlessdata.io/data-resource/

### 2.3 Pydantic / JSON Schema

Pydantic は `BaseModel.model_json_schema()` により JSON Schema Draft 2020-12 / OpenAPI 3.1 互換の schema を生成できる。

この repo では、詳細 validation は Pydantic model、tracked JSON Schema は artifact interoperability guard として扱う。したがって、Pydantic model と tracked JSON Schema の alignment test を必須にする。

参考: https://docs.pydantic.dev/latest/concepts/json_schema/

### 2.4 Typer CLI testing

Typer は `CliRunner` で command を invoke し、`exit_code` と output を assert する testing pattern を公式に示す。

この計画では、次を必須テストにする。

- lenient missing: exit 0。
- strict missing: output を可能な限り書いた上で exit 2。
- invalid input: exit 2。
- boundary violation: exit 2。
- stdout/stderr に review status と output path が出る。

参考: https://typer.tiangolo.com/tutorial/testing/

---

## 3. 全体目的

`strategy-review-build` の出力 contract を、後続 PR が依存できる安定した read-only artifact にする。

具体的には、次を達成する。

1. `review_manifest.json` を Pydantic model / JSON Schema / test で固定する。
2. builder 自身の安全性と source artifact の安全性を分ける。
3. source artifact の path / hash / bytes / detected schema / error を記録する。
4. missing / invalid / boundary blocked を明確に分ける。
5. path traversal、absolute path、secret path を拒否する。
6. review directory の上書きを `--replace-existing` なしでは禁止する。
7. atomic write により、壊れた manifest が残らないようにする。
8. CLI の exit code と stdout/stderr contract を固定する。
9. `review.md` の冒頭で readiness proof ではないことを明示する。

---

## 4. グローバル制約

全 PR に共通する制約。

```text
- Python 3.13 / uv 前提を維持する。
- new dependency を追加しない。
- pyproject.toml / uv.lock を変更しない。
- read-only builder のままにする。
- external API fetch を追加しない。
- wallet / signing / exchange write / live order に触らない。
- PaperIntentPreview を live order に変換しない。
- Strategy Case registry はまだ作らない。
- Svelte UI はまだ作らない。
- paper bridge はまだ作らない。
- lifecycle decision の意味を変更しない。
- backtest engine を追加しない。
- alpha / paper readiness / live readiness を自動判定しない。
- generated data under data/ は runtime output であり、source-controlled truth にしない。
- existing `strategy-backtest-artifact-summary` の意味を壊さない。
```

---

## 5. パッケージ責務

### 5.1 `src/sis/strategy_review/manifest.py`

責務:

- Pydantic model 定義。
- enum 定義。
- `review_id` validation。
- manifest-level invariant validation。
- builder safety / source safety model。
- source artifact model。

含めない:

- filesystem I/O。
- Markdown rendering。
- CLI handling。

### 5.2 `src/sis/strategy_review/provenance.py`

責務:

- repo root 解決。
- repo-relative POSIX path 正規化。
- path traversal / absolute / hidden / secret path rejection。
- source artifact exists / bytes / sha256 計算。
- schema_version の軽量検出。
- source artifact status 判定の素材を返す。

含めない:

- review_status の最終決定。
- Markdown rendering。
- CLI handling。

### 5.3 `src/sis/strategy_review/service.py`

責務:

- use case orchestration。
- 既存 `build_strategy_backtest_artifact_summary(...)` の呼び出し。
- source artifact records の組み立て。
- builder_safety / source_safety / summary / review_status の決定。
- atomic write の制御。
- output result と exit intention の返却。

含めない:

- CLI option parsing。
- Markdownの細かい表現ロジック。

### 5.4 `src/sis/strategy_review/renderer.py`

責務:

- manifest と summary から `review.md` を生成。
- section order の固定。
- warning / missing / invalid / blocked 表示。
- source hash table。
- readiness proof ではない固定文。

含めない:

- filesystem I/O。
- source artifact 読み取り。

### 5.5 `src/sis/commands/strategy_review.py`

責務:

- Typer command wrapper。
- CLI option 定義。
- service 呼び出し。
- stdout/stderr summary 出力。
- exit code 変換。

含めない:

- business logic。
- artifact summary parsing。
- Markdown rendering。

---

## 6. Review status contract

`review_status` は「戦略が良いか」ではなく、「レビュー資料として読めるか」を表す。

| status | 意味 | lenient exit | strict exit |
|---|---|---:|---:|
| `READY_FOR_HUMAN_REVIEW` | 必須 artifact が存在し、読め、hash 計算済み。source safety が BLOCKED ではない | 0 | 0 |
| `INCOMPLETE_ARTIFACTS` | 欠損 artifact または source safety unknown があるが、review は生成可能 | 0 | 2 |
| `INVALID_INPUT` | artifact は存在するが壊れている、schema不一致、path不正、JSON parse不可、hash不可 | 2 | 2 |
| `BLOCKED_BOUNDARY_VIOLATION` | source artifact に live / wallet / signing / exchange write 混入 | 2 | 2 |

重要:

- `pack_validation=FAIL` でも artifact として読めるなら `READY_FOR_HUMAN_REVIEW` でよい。
- `READY_FOR_HUMAN_REVIEW` は paper 承認ではない。
- `READY_FOR_HUMAN_REVIEW` は alpha 証明ではない。
- `READY_FOR_HUMAN_REVIEW` は live readiness ではない。

---

## 7. Safety contract

### 7.1 `builder_safety`

builder 自身が何をしたかを表す。原則すべて false const。

```json
{
  "permits_live_order": false,
  "live_conversion_allowed": false,
  "wallet_used": false,
  "signing_used": false,
  "exchange_write_used": false
}
```

### 7.2 `source_safety`

入力 artifact から観測された boundary state を表す。

```json
{
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
```

`source_safety.status` enum:

```text
PASS
UNKNOWN
BLOCKED
```

判定:

```text
- source artifact から safety fields を確認でき、全て false -> PASS
- safety fields がない / 部分的にしか読めない -> UNKNOWN
- どれか true -> BLOCKED
```

---

## 8. Path validation contract

### 8.1 `review_id`

pattern:

```text
^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$
```

valid examples:

```text
dogfood-001
ndx_smoke.001
20260616-review
reviewA
```

invalid examples:

```text
../x
/x
.hidden
a/b
a\b
""
```

### 8.2 source artifact path

source artifact paths must be repo-relative POSIX paths.

allowed:

```text
data/research/backtest_pack/strategy_backtest_pack.json
docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml
```

rejected:

```text
/tmp/foo.json
../foo.json
data/../.env
a\b
.hidden
file:///tmp/foo.json
http://example.com/foo.json
https://example.com/foo.json
.env
configs/.env
```

Implementation rule:

```text
1. Reject any string containing backslash.
2. Reject empty path.
3. Reject absolute path.
4. Reject path segments equal to "..".
5. Reject first segment starting with ".".
6. Reject any segment in secret denylist: .env, .env.local, id_rsa, id_ed25519, credentials, secrets.
7. Resolve repo_root / path.
8. Ensure resolved path is inside repo_root.
9. Store normalized POSIX relative path in manifest.
```

---

## 9. Manifest contract

### 9.1 Top-level shape

```json
{
  "schema_version": "strategy_review_manifest.v1",
  "review_id": "dogfood-001",
  "created_at": "2026-06-16T12:00:00Z",
  "review_status": "READY_FOR_HUMAN_REVIEW",
  "strict": false,
  "producer": {
    "tool": "sis",
    "command": "strategy-review-build",
    "schema_version": "strategy_review_manifest.v1"
  },
  "paths": {
    "review_dir": "data/strategy_reviews/dogfood-001",
    "review_markdown_path": "data/strategy_reviews/dogfood-001/review.md",
    "manifest_path": "data/strategy_reviews/dogfood-001/review_manifest.json"
  },
  "source_artifacts": [],
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
  },
  "summary": {
    "missing_required_count": 0,
    "invalid_required_count": 0,
    "boundary_violation_count": 0,
    "unknown_boundary_count": 0
  }
}
```

### 9.2 `source_artifacts[]`

```json
{
  "artifact_key": "pack",
  "path": "data/research/backtest_pack/strategy_backtest_pack.json",
  "exists": true,
  "required": true,
  "status": "present",
  "sha256": "sha256:0000000000000000000000000000000000000000000000000000000000000000",
  "bytes": 12345,
  "detected_schema_version": "strategy_backtest_pack.v1",
  "error": null,
  "summary": {}
}
```

`status` enum:

```text
present
missing
invalid
blocked
```

rules:

```text
- missing: exists=false, sha256=null, bytes=null, detected_schema_version=null, error may be null or short reason.
- present: exists=true, sha256 required, bytes required.
- invalid: exists=true, error required.
- blocked: exists=true, error required, source_safety.status=BLOCKED.
```

---

## 10. Markdown contract

`review.md` must contain these sections in this order.

```text
1. Summary
2. Readiness Disclaimer
3. Source Artifact Status
4. Backtest Pack / Validation Summary
5. Safety Boundary
6. Missing / Invalid / Blocked Details
7. Source Hash Table
8. Next Human Review Checklist
```

### 10.1 Mandatory disclaimer

The following meaning must be present near the top, in Japanese:

```text
この review は人間の戦略レビュー用 artifact です。
alpha、paper readiness、live readiness を証明しません。
pack validation が PASS の場合でも、戦略の収益性、paper移行可否、live実行可否は証明されません。
```

### 10.2 Summary block

The first section must show:

```text
review_status
source_safety.status
missing_required_count
invalid_required_count
boundary_violation_count
unknown_boundary_count
human action
readiness proof: false
```

---

# 11. PR-REVIEW-00.1: Review Manifest Contract Hardening

## 11.1 目的

`review_manifest.json` / `review.md` の出力 contract を、後続 PR が安全に依存できる状態にする。

## 11.2 制約

```text
- new dependency を追加しない。
- read-only のままにする。
- CLI name は `strategy-review-build` のまま。
- output files は `review.md` と `review_manifest.json` のみ。
- Strategy Case registry は作らない。
- operator_review.yaml は作らない。
- paper bridge は作らない。
- Svelte UI は作らない。
```

## 11.3 対象ファイル

### 変更

```text
schemas/strategy_review_manifest.v1.schema.json
src/sis/strategy_review/manifest.py
src/sis/strategy_review/provenance.py
src/sis/strategy_review/renderer.py
src/sis/strategy_review/service.py
src/sis/commands/strategy_review.py
```

### 追加または更新テスト

```text
tests/strategy_review/test_strategy_review_manifest_schema.py
tests/strategy_review/test_strategy_review_manifest_model_schema_alignment.py
tests/strategy_review/test_strategy_review_path_validation.py
tests/strategy_review/test_strategy_review_cli.py
tests/strategy_review/test_strategy_review_build.py
tests/strategy_review/test_strategy_review_rendering.py
```

### 原則変更しない

```text
pyproject.toml
uv.lock
src/sis/backtest/artifact_summary.py
src/sis/backtest/artifact_summary_registry.py
```

既存 artifact summary builder に不具合が見つかった場合は、PR-REVIEW-00.1に混ぜず別PRにする。

---

## 11.4 実装タスク

### T0: Baseline confirmation

#### 目的

現状 contract を再確認し、PR 範囲外の変更を避ける。

#### 実行コマンド

```bash
git status --short --branch --untracked-files=all
uv run sis --help
uv run sis strategy-review-build --help
uv run sis strategy-backtest-artifact-summary --help
sed -n '1,220p' schemas/strategy_review_manifest.v1.schema.json
sed -n '1,260p' src/sis/strategy_review/manifest.py
sed -n '1,260p' src/sis/strategy_review/service.py
sed -n '1,260p' src/sis/strategy_review/renderer.py
```

#### 完了条件

```text
- strategy-review-build が存在する。
- 現行 manifest schema の差分対象を把握した。
- 既存 tests/strategy_review が存在する場合は対象を把握した。
- 作業前 git status を記録した。
```

---

### T1: Manifest model update

#### 目的

Pydantic model を新 contract に更新する。

#### 対象ファイル

```text
src/sis/strategy_review/manifest.py
```

#### 作業

1. `ReviewStatus` enum を定義または更新する。
2. `SourceArtifactStatus` enum を定義または更新する。
3. `SourceSafetyStatus` enum を定義する。
4. `BuilderSafety` model を追加する。
5. `SourceSafety` model を追加する。
6. `ProducerInfo` model を追加する。
7. `SourceArtifact` model に次を追加する。
   - `bytes: int | None`
   - `detected_schema_version: str | None`
   - `error: str | None`
8. 既存 `safety` field を `builder_safety` と `source_safety` に置換する。
9. invariant validation を追加する。
   - `present` は `exists=true`, `sha256`, `bytes` required。
   - `missing` は `exists=false`。
   - `invalid` は `error` required。
   - `blocked` は `error` required。
   - builder safety flags は false only。

#### 完了条件

```text
- Pydantic model で valid manifest を構築できる。
- safety 2層分離が model に反映されている。
- invalidな status / safety / hash を model validation で拒否できる。
```

---

### T2: JSON Schema update

#### 目的

tracked JSON Schema を新 contract に更新する。

#### 対象ファイル

```text
schemas/strategy_review_manifest.v1.schema.json
```

#### 作業

1. `builder_safety` を追加し、各 flag を `const: false` にする。
2. `source_safety` を追加する。
3. `producer` を追加する。
4. `source_artifacts[].bytes` を追加する。
5. `source_artifacts[].detected_schema_version` を追加する。
6. `source_artifacts[].error` を追加する。
7. `sha256` pattern を `^sha256:[a-f0-9]{64}$` に固定する。
8. `review_status` enum を固定する。
9. `source_artifacts[].status` enum を固定する。

#### 完了条件

```text
- valid fixture が jsonschema validation を通る。
- bare hex hash が落ちる。
- builder_safety true が落ちる。
- missing source artifact は sha256 なしで通る。
```

---

### T3: Provenance / path validation

#### 目的

source path / review_id / hash / bytes / schema detection を再利用可能な単一責務 module に分離する。

#### 対象ファイル

```text
src/sis/strategy_review/provenance.py
```

#### 必須関数

```python
def validate_review_id(review_id: str) -> str: ...

def normalize_repo_relative_posix_path(path: str, *, repo_root: Path) -> str: ...

def collect_source_artifact(
    *,
    artifact_key: str,
    path: str,
    required: bool,
    repo_root: Path,
) -> SourceArtifact: ...

def detect_json_schema_version(path: Path) -> str | None: ...

def compute_sha256(path: Path) -> str: ...
```

#### path validation details

Must reject:

```text
empty string
absolute path
backslash path
parent traversal
first segment starting with dot
secret path segment
file://, http://, https://
resolved path outside repo_root
```

#### secret denylist minimum

```text
.env
.env.local
.envrc
id_rsa
id_ed25519
credentials
credential
secrets
secret
```

#### 完了条件

```text
- valid repo-relative POSIX paths normalize successfully.
- invalid examples fail with deterministic error messages.
- sha256 returns `sha256:<64 hex>`.
- bytes is file size in bytes.
- JSON artifact with `schema_version` returns detected_schema_version.
- YAML artifact with `schema_version` may return detected_schema_version if parser is already available; otherwise null is acceptable for PR-REVIEW-00.1.
```

---

### T4: Service update

#### 目的

new manifest contract を使って `review.md` / `review_manifest.json` を生成する。

#### 対象ファイル

```text
src/sis/strategy_review/service.py
```

#### 作業

1. `review_id` を `validate_review_id()` で検査する。
2. `--out` から review_dir を決める。
3. 既存 review_dir があり `replace_existing=false` なら error にする。
4. `build_strategy_backtest_artifact_summary(...)` を引き続き使う。
5. source artifact を `collect_source_artifact()` で収集する。
6. source safety を artifact summary / source artifact の内容から判定する。
7. review_status を contract に従って決定する。
8. `review.md` を renderer で生成する。
9. manifest を Pydantic validation する。
10. JSON Schema validation も実施する。
11. tmp file に書く。
12. tmp -> final へ atomic replace する。
13. strict mode の場合も、生成可能な output を書いた上で exit intention を返す。

#### `replace_existing` behavior

```text
review_dir absent -> create
review_dir exists and replace_existing=false -> INVALID_INPUT / exit 2
review_dir exists and replace_existing=true -> write tmp then replace output files
```

既存dirを完全削除しない。`review.md` と `review_manifest.json` のみ置換する。

#### 完了条件

```text
- review_manifest.json が新 contract で出る。
- review.md が出る。
- replace_existing=false で既存dirを拒否する。
- replace_existing=true で再生成できる。
- strict missing は output を書いて exit intention 2 を返す。
- boundary violation は exit intention 2 を返す。
```

---

### T5: Renderer update

#### 目的

人間が誤読しない review.md を出す。

#### 対象ファイル

```text
src/sis/strategy_review/renderer.py
```

#### section order

```text
1. Summary
2. Readiness Disclaimer
3. Source Artifact Status
4. Backtest Pack / Validation Summary
5. Safety Boundary
6. Missing / Invalid / Blocked Details
7. Source Hash Table
8. Next Human Review Checklist
```

#### Mandatory wording meaning

Markdown must contain Japanese text equivalent to:

```text
この review は人間の戦略レビュー用 artifact です。
alpha、paper readiness、live readiness を証明しません。
pack validation が PASS の場合でも、戦略の収益性、paper移行可否、live実行可否は証明されません。
```

#### 完了条件

```text
- review_status is visible near the top.
- missing / invalid / blocked are not buried at the bottom.
- source_safety is visible.
- source hash table includes path, status, bytes, sha256, detected_schema_version.
- no automatic APPROVE / paper recommendation is emitted.
```

---

### T6: CLI update

#### 目的

CLI option と exit/output contract を固定する。

#### 対象ファイル

```text
src/sis/commands/strategy_review.py
src/sis/cli.py
```

#### CLI options

```text
--review-id TEXT           required
--out PATH                 default: data/strategy_reviews
--strict / --no-strict     default: --no-strict
--replace-existing         default: false
--pack-path PATH           default: data/research/backtest_pack/strategy_backtest_pack.json
--validation-path PATH     default: data/research/backtest_pack/strategy_backtest_pack_validation.json
```

#### stdout summary minimum

Command must print at least:

```text
review_status=<status>
review_dir=<path>
markdown_path=<path>
manifest_path=<path>
missing_required_count=<n>
invalid_required_count=<n>
boundary_violation_count=<n>
```

#### exit code

```text
READY_FOR_HUMAN_REVIEW -> 0
INCOMPLETE_ARTIFACTS lenient -> 0
INCOMPLETE_ARTIFACTS strict -> 2
INVALID_INPUT -> 2
BLOCKED_BOUNDARY_VIOLATION -> 2
unexpected exception -> 1
```

#### 完了条件

```text
- uv run sis --help lists strategy-review-build.
- uv run sis strategy-review-build --help lists all options.
- stdout summary is stable and testable.
- strict / lenient behavior is fixed by tests.
```

---

### T7: Test updates

#### 目的

contract hardening を回帰不能にする。

#### 対象ファイル

```text
tests/strategy_review/test_strategy_review_manifest_schema.py
tests/strategy_review/test_strategy_review_manifest_model_schema_alignment.py
tests/strategy_review/test_strategy_review_path_validation.py
tests/strategy_review/test_strategy_review_cli.py
tests/strategy_review/test_strategy_review_build.py
tests/strategy_review/test_strategy_review_rendering.py
```

#### 必須テスト一覧

```text
1. valid manifest passes Pydantic and JSON Schema.
2. Pydantic-generated fixture validates against tracked JSON Schema.
3. tracked JSON Schema fixture validates against Pydantic model.
4. enum values align between model and schema.
5. builder_safety true is rejected.
6. source_safety BLOCKED yields BLOCKED_BOUNDARY_VIOLATION.
7. sha256:<64 hex> accepted.
8. bare 64 hex rejected.
9. missing artifact may omit sha256 and bytes.
10. invalid artifact requires error.
11. invalid review_id rejected.
12. invalid source path rejected.
13. existing review_dir without --replace-existing exits 2.
14. --replace-existing regenerates output.
15. lenient missing exits 0 and prints INCOMPLETE_ARTIFACTS.
16. strict missing writes output and exits 2.
17. boundary violation writes output if possible and exits 2.
18. review.md contains readiness disclaimer.
19. source hash table contains bytes and detected_schema_version.
20. dynamic timestamp is injected or normalized for stable tests.
```

#### 完了条件

```text
uv run pytest -q tests/strategy_review passes.
```

---

### T8: Docs update

#### 目的

operator と future coder が contract を誤読しないようにする。

#### 対象ファイル

```text
docs/strategy_review/README.md
docs/backtest/README.md
plan/README.md
```

`docs/REPO_CAPABILITIES_CURRENT_2026-06-16.md` は、repo の current capability doc 更新方針に合う場合だけ更新する。広範囲のcurrent docs更新でPRが肥大化するなら後続PRに分ける。

#### 記載内容

```text
- strategy-review-build の目的。
- review.md / review_manifest.json の意味。
- review_status は資料生成品質であり戦略評価ではない。
- builder_safety / source_safety の違い。
- pack validation PASS は readiness proof ではない。
- strict / lenient の違い。
- --replace-existing の意味。
- 次PRで authoring / lifecycle sections を追加予定。
```

#### 完了条件

```text
uv run python scripts/check_current_docs.py passes.
```

---

## 11.5 PR-REVIEW-00.1 テスト方針

### Focused verification

```bash
uv run sis strategy-review-build --help
uv run pytest -q tests/strategy_review
uv run python scripts/check_current_docs.py
git diff --check
```

### Regression verification

```bash
uv run pytest -q \
  tests/strategy_review \
  tests/backtest/test_artifact_summary_registry.py \
  tests/strategy_authoring/test_cli_bundle.py
```

### Full verification

```bash
./scripts/check
```

`./scripts/check` が環境・時間・既存失敗で通らない場合は、PR final note に次を残す。

```text
- 実行コマンド
- 失敗箇所
- 既存失敗か新規失敗か
- 未検証範囲
```

---

## 11.6 PR-REVIEW-00.1 完了条件

```text
1. review_manifest.json が new contract で schema-valid。
2. Pydantic model と tracked JSON Schema の alignment tests がある。
3. builder_safety と source_safety が分離されている。
4. source_artifacts[] に bytes / detected_schema_version / error がある。
5. missing / invalid / blocked が status と Markdown で区別される。
6. review_id validation がある。
7. repo-relative POSIX path validation がある。
8. secret / absolute / parent traversal paths が拒否される。
9. --replace-existing なしで既存dirを上書きしない。
10. atomic write になっている。
11. strict missing は output を書ける範囲で書いた後 exit 2。
12. lenient missing は exit 0 だが INCOMPLETE_ARTIFACTS を stdout / Markdown 冒頭に出す。
13. boundary violation は BLOCKED_BOUNDARY_VIOLATION で exit 2。
14. review.md に readiness disclaimer がある。
15. CLI stdout summary が test されている。
16. new dependency なし。
17. live / wallet / signing / exchange write に触らない。
18. Focused verification が通る。
```

---

# 12. Dogfood Gate

PR-REVIEW-00.1 完了後、次に Dogfood Gate を実行する。

## 12.1 目的

contractが実テストで正しくても、実際に人間が読む review として機能するか確認する。

## 12.2 実行ケース

### Case A: complete

```bash
uv run sis strategy-review-build \
  --review-id dogfood-complete-001 \
  --out data/strategy_reviews \
  --pack-path data/research/backtest_pack/strategy_backtest_pack.json \
  --validation-path data/research/backtest_pack/strategy_backtest_pack_validation.json
```

### Case B: missing lenient

```bash
uv run sis strategy-review-build \
  --review-id dogfood-missing-001 \
  --out data/strategy_reviews \
  --pack-path data/research/backtest_pack/not_found.json \
  --validation-path data/research/backtest_pack/not_found_validation.json
```

### Case C: missing strict

```bash
uv run sis strategy-review-build \
  --review-id dogfood-strict-missing-001 \
  --out data/strategy_reviews \
  --strict \
  --pack-path data/research/backtest_pack/not_found.json \
  --validation-path data/research/backtest_pack/not_found_validation.json
```

### Case D: replace existing

```bash
uv run sis strategy-review-build \
  --review-id dogfood-complete-001 \
  --out data/strategy_reviews \
  --pack-path data/research/backtest_pack/strategy_backtest_pack.json \
  --validation-path data/research/backtest_pack/strategy_backtest_pack_validation.json
```

Expected: exit 2 without `--replace-existing`.

### Case E: invalid path

```bash
uv run sis strategy-review-build \
  --review-id dogfood-invalid-path-001 \
  --out data/strategy_reviews \
  --pack-path ../.env
```

Expected: exit 2.

## 12.3 判定観点

```text
1. review.md 冒頭だけで status が分かるか。
2. readiness proof ではないことが明確か。
3. source_safety が分かるか。
4. missing / invalid / blocked が埋もれていないか。
5. source path / hash / bytes が読めるか。
6. 次に人間が見るべき artifact が分かるか。
7. Dogfood complete で Strategy Authoring section がないことが不便かを判断する。
```

## 12.4 Dogfood 完了条件

```text
- review.md は3分以内に状態把握できる。
- INCOMPLETE / INVALID / BLOCKED が誤読されない。
- PR-REVIEW-01 の必要性が明確に判断できる。
```

---

# 13. PR-REVIEW-01: Add Strategy Authoring and Lifecycle Sections

## 13.1 目的

`review.md` を backtest artifact 要約から、戦略レビュー資料に近づける。

PR-REVIEW-00.1 では「artifact が揃っているか」「安全境界はどうか」を固めた。PR-REVIEW-01 では、「この戦略が何をしているか」と「lifecycle上どう扱われているか」を review に追加する。

## 13.2 制約

```text
- PR-REVIEW-00.1 の manifest contract を壊さない。
- input artifact が missing でも lenient mode では review を生成する。
- read-only のままにする。
- paper bridge は作らない。
- operator_review.yaml は作らない。
- Strategy Case registry は作らない。
- UI は作らない。
```

## 13.3 対象ファイル

### 変更 / 追加

```text
src/sis/strategy_review/sections.py
src/sis/strategy_review/renderer.py
src/sis/strategy_review/service.py
src/sis/commands/strategy_review.py
src/sis/strategy_review/manifest.py
schemas/strategy_review_manifest.v1.schema.json
```

### テスト

```text
tests/strategy_review/test_strategy_review_sections.py
tests/strategy_review/test_strategy_review_authoring_section.py
tests/strategy_review/test_strategy_review_lifecycle_section.py
tests/strategy_review/test_strategy_review_cli.py
tests/strategy_review/test_strategy_review_rendering.py
```

## 13.4 CLI追加option

```text
--authoring-spec PATH
--lifecycle-review PATH
```

Both optional.

## 13.5 Section model

`sections.py` に最小抽象を置く。

```python
@dataclass(frozen=True)
class ReviewSection:
    section_id: str
    title: str
    status: Literal["present", "missing", "invalid", "blocked"]
    markdown: str
    source_artifact_keys: tuple[str, ...]
```

大きな adapter registry は作らない。PR-REVIEW-01では関数ベースでよい。

## 13.6 AuthoringSpecSection

### 目的

戦略の概要を review に出す。

### 読むファイル

`strategy_authoring_spec.v1` YAML。

### 抽出する情報

実装は可能な範囲でよいが、最低限次を試みる。

```text
schema_version
strategy_id
strategy_family / family相当
execution_venue
timeframe
rules.side
entry / long_entry / short_entry の有無
close / reduce / add / rebalance の有無
exit stop / take / trailing / max holding の有無
sizing / notional / weight の有無
execution constraints: post_only / reduce_only / spread / depth / latency / queue gate の有無
```

キーが存在しない場合は `unknown` と表示する。

### Markdown出力

```md
## Strategy Definition

- strategy_id: ...
- timeframe: ...
- execution_venue: ...
- side: ...
- entry rules: present / missing / unknown
- exit rules: present / missing / unknown
- sizing / risk: ...
- execution constraints: ...
```

### 完了条件

```text
- authoring spec が present なら Strategy Definition section が出る。
- missingなら missingとして出る。
- invalid YAMLなら INVALID_INPUT または section invalid になる。
- secret pathは拒否される。
```

## 13.7 LifecycleReviewSection

### 目的

既存 lifecycle review の decision / boundary を review に出す。

### 読むファイル

`strategy_lifecycle_review.v1` JSON。

### 抽出する情報

```text
schema_version
decision
backtest acceptance summary
paper observation status if present
phase gate summary if present
boundary violation count or flags
permits_live_order / live_conversion_allowed / wallet_used / venue_write_used / exchange_write_used if present
```

存在しないfieldは `unknown`。

### Markdown出力

```md
## Lifecycle Summary

- lifecycle decision: ...
- backtest acceptance: ...
- paper observation: ...
- boundary: PASS / UNKNOWN / BLOCKED
- live allowed: false / unknown / blocked
```

### 完了条件

```text
- lifecycle review が present なら summary section が出る。
- lifecycle review の decision を live permission と誤読しない固定文が出る。
- source safety が BLOCKED の場合は review_status が BLOCKED_BOUNDARY_VIOLATION になる。
```

## 13.8 Manifest update

`source_artifacts[]` に次の `artifact_key` を追加する。

```text
authoring_spec
lifecycle_review
```

Existing manifest fields are additive only. Existing readers must not break.

## 13.9 PR-REVIEW-01 テスト方針

```text
1. authoring spec present -> Strategy Definition section appears.
2. authoring spec missing -> section marks missing.
3. authoring spec invalid YAML -> invalid.
4. lifecycle review present -> Lifecycle Summary appears.
5. lifecycle review missing -> section marks missing.
6. lifecycle boundary true -> BLOCKED_BOUNDARY_VIOLATION.
7. missing optional authoring/lifecycle in lenient mode does not fail if not required.
8. strict behavior is documented and tested if those inputs are marked required.
9. manifest remains schema-valid.
10. PR-REVIEW-00.1 tests still pass.
```

## 13.10 PR-REVIEW-01 完了条件

```text
1. --authoring-spec が指定できる。
2. --lifecycle-review が指定できる。
3. review.md に Strategy Definition が出る。
4. review.md に Lifecycle Summary が出る。
5. lifecycle decision が live permission と誤読されない。
6. source_artifacts[] に authoring_spec / lifecycle_review が入る。
7. missing / invalid / blocked のcontractを壊さない。
8. new dependency なし。
9. Focused verification が通る。
```

---

# 14. PR-REVIEW-02: Review Packet Hardening

## 14.1 目的

`review.md` を毎回同じ観点で読める標準資料にする。

## 14.2 対象ファイル

```text
src/sis/strategy_review/checklist.py
src/sis/strategy_review/renderer.py
src/sis/strategy_review/sections.py

tests/strategy_review/test_strategy_review_golden.py
tests/strategy_review/test_strategy_review_checklist.py

docs/strategy_review/OPERATOR_REVIEW_RECIPE.md
```

## 14.3 実装内容

```text
1. golden markdown fixture: complete / missing / blocked。
2. Human Review Checklist 生成。
3. OPERATOR_REVIEW_RECIPE.md 作成。
4. sample output を test fixture として固定。
5. readiness proofではない固定文のsnapshot test。
```

## 14.4 完了条件

```text
1. complete / missing / blocked のgolden fixtureがある。
2. Human Review Checklist が review.md に出る。
3. missing artifact がある場合、checklist に不足が反映される。
4. OPERATOR_REVIEW_RECIPE.md がある。
5. Markdown section order が固定されている。
6. new dependency なし。
```

---

# 15. PR-OPERATOR-00: Operator Strategy Review Artifact

## 15.1 目的

人間レビュー結果を `operator_review.yaml` として残す。

## 15.2 まだやらないこと

```text
- paper flow には渡さない。
- paper observation を開始しない。
- live には絶対に触らない。
```

## 15.3 CLI案

```bash
uv run sis strategy-review-record \
  --review-dir data/strategy_reviews/dogfood-001 \
  --decision HOLD \
  --notes "paper intent preview不足のためHOLD"
```

## 15.4 decision enum

```text
REJECT
REVISE
HOLD
APPROVE_FOR_PAPER
```

## 15.5 完了条件

```text
1. operator_review.yaml が作れる。
2. review_manifest.json の review_id と一致しなければ exit 2。
3. APPROVE_FOR_PAPER 以外は paper_allowed=false。
4. live_allowed=false は常に固定。
5. paper flow へはまだ渡さない。
```

---

# 16. PR-PAPER-00: Approved Review to Paper Observation

## 16.1 目的

`operator_review.decision == APPROVE_FOR_PAPER` の review だけ、既存 paper flow へ渡す。

## 16.2 必須条件

```text
operator_review.decision == APPROVE_FOR_PAPER
operator_review.live_allowed == false
review_manifest.builder_safety all false
review_manifest.source_safety.status == PASS
paper intent preview exists
lifecycle boundary violationなし
```

## 16.3 完了条件

```text
1. 未承認reviewはpaperに渡せない。
2. source_safety UNKNOWN/BLOCKED ではpaperに渡せない。
3. live / wallet / signing / exchange_write に触らない。
4. 既存 paper系 command / artifact を使う。
5. 新paper engineを作らない。
```

---

# 17. Stop conditions

次のいずれかが出たら実装を止め、計画を更新する。

```text
- `strategy-backtest-artifact-summary` の contract を壊さないと実装できない。
- hash format を `sha256:<64 hex>` から変えたくなった。
- new dependency が必要になった。
- live / wallet / signing / exchange write に触る必要が出た。
- Strategy Case registry / UI / paper bridge が PR-REVIEW-00.1 に混入しそうになった。
- generated artifact を source-controlled truth にする必要が出た。
- external API fetch が必要になった。
- source artifact content を丸ごと Markdown に貼り付けたくなった。
- secret path や absolute path を許可したくなった。
```

---

# 18. Final verification commands

## PR-REVIEW-00.1 minimum

```bash
uv run sis strategy-review-build --help
uv run pytest -q tests/strategy_review
uv run python scripts/check_current_docs.py
git diff --check
```

## PR-REVIEW-00.1 regression

```bash
uv run pytest -q \
  tests/strategy_review \
  tests/backtest/test_artifact_summary_registry.py \
  tests/strategy_authoring/test_cli_bundle.py
```

## Full

```bash
./scripts/check
```

---

# 19. Coder handoff checklist

実装者は次の順で作業する。

```text
1. この計画書と AGENTS.md を読む。
2. T0 baseline confirmation を実行する。
3. PR-REVIEW-00.1 だけを実装する。
4. manifest.py を更新する。
5. schema を更新する。
6. provenance.py を追加する。
7. service.py を更新する。
8. renderer.py を更新する。
9. CLI option / stdout / exit code を更新する。
10. tests/strategy_review を更新する。
11. docs/strategy_review/README.md を更新する。
12. focused verification を通す。
13. regression verification を通す。
14. ./scripts/check を試す。
15. Dogfood Gate は PR-REVIEW-00.1 の後に実施する。
```

---

# 20. 最終判断

本計画の最重要点は、`strategy-review-build` を「便利なMarkdown生成コマンド」ではなく、後続の Review Packet / Operator Review / Paper Bridge / Svelte UI が依存する artifact contract として扱うことである。

このため、次の4点は省略不可。

```text
1. builder_safety / source_safety 分離
2. repo-relative POSIX path validation
3. atomic write + --replace-existing
4. Pydantic model / tracked JSON Schema alignment test
```

これを先に固めれば、後続の authoring/lifecycle section、operator review、paper bridge は小さく安全に実装できる。

