# PR-00 Python 3.13 migration plan

Status: historical. 現行コードでは PR-00 は完了済みであり、この文書は当時の implementation contract と acceptance record として読む。

## 結論

PR-00のゴールは、repoのactive runtime、CI、lockfile、developer setupを Python 3.13 前提へ揃え、`./scripts/check` が通る状態にすることです。

## Goal

PR-00完了時点で、次を満たす。

- `.python-version` が `3.13`
- `pyproject.toml` の `requires-python` が `>=3.13,<3.14`
- Ruff target が `py313`
- pyrefly python version が `3.13`
- `uv.lock` が Python 3.13 前提で再生成済み
- CI が Python 3.13 を install する
- `scripts/check` が `uv run python -V` を表示する
- README の通常セットアップが `uv sync --dev --locked` 前提
- active docs の Python 3.14 前提が消えている
- `./scripts/check` が成功する

## Non-goals

PR-00では次をしない。

- `ostium-python-sdk` などの dependency 削除
- gTrade / Ostium sidecar archive
- `package.json` / `bun.lock` の sidecar workspace 変更
- `src/sis/models.py` や schema v2 の変更
- Trade[XYZ] code path 追加
- live execution / micro live canary 追加
- historical report / generated evidence の書き換え

## Target files

必ず編集対象に含める。

```text
pyproject.toml
.python-version
uv.lock
.github/workflows/ci.yml
scripts/check
README.md
docs/CURRENT_STATE.md
docs/CODE_STATUS.md
docs/OPERATIONS_RUNBOOK.md
```

必要時のみ作成する。

```text
docs/python_313_migration_notes.md
```

## Exact implementation plan

1. Read current runtime settings.

   ```bash
   rg -n "3\\.14|3\\.13|py314|py313|requires-python|python-version|uv sync|uv lock|uv run python -V" \
     pyproject.toml .python-version .github/workflows/ci.yml README.md \
     docs/CURRENT_STATE.md docs/CODE_STATUS.md docs/OPERATIONS_RUNBOOK.md \
     scripts/check uv.lock
   ```

2. Update Python version files and tool targets.

   Expected changes:

   ```text
   .python-version: 3.13
   pyproject.toml requires-python: >=3.13,<3.14
   pyproject.toml tool.ruff.target-version: py313
   pyproject.toml tool.pyrefly.python-version: 3.13
   .github/workflows/ci.yml: uv python install 3.13
   ```

3. Update `scripts/check`.

   Insert `uv run python -V` immediately after `uv sync --dev --locked`.

   Target shape:

   ```bash
   uv sync --dev --locked
   uv run python -V
   uv run ruff check .
   uv run pyrefly check
   uv run pytest -q
   ```

4. Update README setup commands.

   Standard setup should use locked sync.

   ```bash
   uv python install 3.13
   uv lock --python /usr/bin/python3.13
   uv sync --dev --locked
   uv run python -V
   uv run sis --help
   ```

   Add or preserve a short note:

   ```text
   依存を変更した場合のみ uv lock --python /usr/bin/python3.13 を実行し、uv.lock を更新する。
   通常のセットアップ・CI・merge前確認では uv sync --dev --locked を使う。
   ```

5. Update active docs only for Python version / setup truth.

   Update:

   ```text
   docs/CURRENT_STATE.md
   docs/CODE_STATUS.md
   docs/OPERATIONS_RUNBOOK.md
   ```

   Do not rewrite gTrade / Ostium descriptions in PR-00. They belong to PR-01 / PR-02.

6. Regenerate lockfile.

   Preferred command:

   ```bash
   uv lock --python /usr/bin/python3.13
   ```

   Fallback if environment-specific behavior blocks the preferred command:

   ```bash
   uv python pin 3.13
   uv lock
   ```

   Then verify locked sync:

   ```bash
   uv sync --dev --locked
   ```

7. Run acceptance checks.

   ```bash
   uv sync --dev --locked
   uv run python -V
   uv run ruff check .
   uv run pyrefly check
   uv run pytest -q
   ./scripts/check
   ```

## Historical artifact exclusion

Do not edit historical generated evidence.

Excluded from PR-00 No-Go checks:

```text
docs/live_evidence_reports/
past generated run artifacts
historical traceback
archive reports
```

Rationale:

```text
Historical generated artifacts under docs/live_evidence_reports/ may still contain Python 3.14 paths or tracebacks. They are immutable evidence records and are intentionally excluded from the active runtime migration scope.
```

## Failure notes

Create `docs/python_313_migration_notes.md` only if migration-related commands fail.

Create it when any of these fail:

- `uv lock`
- `uv sync --dev --locked`
- dependency compatibility on Python 3.13
- `uv run ruff check .`
- `uv run pyrefly check`
- `uv run pytest -q`
- `./scripts/check` for Python 3.13 migration reasons

Template:

````md
# Python 3.13 Migration Notes

## Environment

- uv:
- python:
- command:
- timestamp:

## Failure

```text
<failure log>
```

## Root cause

- dependency:
- file:
- reason:

## Minimal fix

- changed files:
- rationale:

## Out of scope

- sidecar:
- historical artifacts:
````

## Failure handling policy

Python 3.13 migration failures:

```text
Fix inside PR-00 with the smallest scoped change.
```

Existing sidecar failures unrelated to Python 3.13:

```text
Record command, log, cause, and out-of-scope rationale in docs/python_313_migration_notes.md.
Do not redesign sidecars in PR-00.
```

## Done definition

PR-00 is done only when all are true.

- `.python-version` is `3.13`
- `pyproject.toml` has `requires-python = ">=3.13,<3.14"`
- `pyproject.toml` has `target-version = "py313"`
- `pyproject.toml` has `python-version = "3.13"` under pyrefly
- `uv.lock` is regenerated for Python 3.13
- `.github/workflows/ci.yml` installs Python 3.13
- `scripts/check` includes `uv run python -V`
- `./scripts/check` logs Python 3.13.x
- README setup uses `uv sync --dev --locked`
- README documents `uv lock --python /usr/bin/python3.13` for dependency updates
- active docs no longer describe Python 3.14 as the current runtime
- `uv sync --dev --locked` succeeds
- `uv run python -V` prints Python 3.13.x
- `uv run ruff check .` succeeds
- `uv run pyrefly check` succeeds
- `uv run pytest -q` succeeds
- `./scripts/check` succeeds, unless an existing sidecar-only failure is logged as out of scope
- historical artifacts are not rewritten

## Backout

Backout should only revert PR-00 touched files to the previous commit state:

```text
pyproject.toml
.python-version
uv.lock
.github/workflows/ci.yml
scripts/check
README.md
docs/CURRENT_STATE.md
docs/CODE_STATUS.md
docs/OPERATIONS_RUNBOOK.md
docs/python_313_migration_notes.md, if created
```

Do not touch PR-01+ migration files during PR-00 backout.
