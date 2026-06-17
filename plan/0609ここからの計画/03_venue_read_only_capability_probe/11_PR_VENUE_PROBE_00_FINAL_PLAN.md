<!--
作成日: 2026-06-17_10:40 JST
更新日: 2026-06-17_10:40 JST
-->

# PR-VENUE-PROBE-00 Final Implementation Plan

## 結論

次に実装するものは `PR-VENUE-PROBE-00: Fixture-first Venue Read-only Capability Probe` です。

目的は Bitget / Hyperliquid 本番対応ではありません。現行 catalog にある 4 venue について、何が known で、何が enabled で、何を試しておらず、何を許可していないかを local artifact として機械的に残すことです。

この文書を実装正本にします。既存の `01_GOAL.md` から `10_CODER_HANDOFF_PROMPT.md` は背景と分割計画として維持しますが、実装者はこの文書を先に読み、矛盾がある場合はこの文書を優先してください。

## Step 0: Current Proof

実装前に、現在の Review Builder / Operator Review 実装が本当に存在し、docs が通ることを確認します。

```bash
uv run python -V
uv run sis --help
uv run sis strategy-review-build --help
uv run sis strategy-review-record --help
uv run python scripts/check_current_docs.py
```

`./scripts/check` は重いので、PR 実装前の必須ではありません。ただし完了前には必ず実行します。

期待:

- `strategy-review-build` が CLI help に出る。
- `strategy-review-record` が CLI help に出る。
- `venue-read-only-probe` はまだ存在しない。
- current-doc checker が通る。

## 目的

4 venue の capability boundary を、network / credentials / order path なしで local に記録できるようにする。

対象 venue:

- `trade_xyz`
- `bitget_demo`
- `bitget_futures`
- `hyperliquid_perp`

解決するリスク:

- `catalog known` を `venue enabled` と誤読する。
- `bitget_demo` を production Bitget Futures と誤読する。
- Trade[XYZ] を direct Hyperliquid と誤読する。
- future venue を Strategy Lab schema / paper path に先に入れてしまう。
- read-only probe を network readiness と誤読する。

## 非目的

この PR で次は実装しない。

- external network call
- Bitget / Hyperliquid credentials
- new credential name
- account / balance / position / fill / order read
- signing
- wallet access
- order submit / cancel / amend / close
- `VenueId` widening
- Strategy Lab schema widening
- `evaluation_plan.mls.v1` target widening
- Strategy Review integration
- paper bridge validation
- Strategy Case registry
- UI
- paper execution enablement
- live execution enablement
- dependency addition

## 最終設計判断

### 出力パス

この PR では repo 既存の ops/report 慣習に合わせて fixed latest artifact を出します。

```text
data/ops/venue_read_only_probe_summary.json
data/reports/venue_read_only_probe.md
```

`data/venues/read_only_probe/{run_id}/...` の run-specific directory は、この PR では作りません。監査性のため、`run_id` は summary / report / stdout に field として入れます。履歴保存が必要になったら、別 PR で operation manifest / bundle 方針と合わせて追加します。

テストでは `SIS_DATA_DIR` を temp directory に向けます。

### Strategy Review との関係

この PR では Strategy Review に渡しません。

理由:

- この artifact は strategy evaluation ではなく venue capability boundary です。
- `strategy-review-build` / `strategy-review-record` は既存 strategy artifact を読む surface であり、venue readiness を拡張する場所ではありません。
- 将来参照する場合は、別 plan で Strategy Review の source artifact として読むだけにします。

### 実装場所

builder は command wrapper から分離します。

- pure builder: `src/sis/venues/read_only_probe.py`
- CLI: `src/sis/commands/execution.py`

`src/sis/commands/execution.py` が膨らみすぎる場合でも、この PR では registration split だけに留め、domain logic は `src/sis/venues/read_only_probe.py` に置きます。

## Artifact Contract

### Summary

Schema file:

```text
schemas/venue_read_only_probe_summary.v1.schema.json
```

Top-level required fields:

```text
schema_version: const "venue_read_only_probe_summary.v1"
run_id: string
generated_at: string
status: enum ["blocked", "not_configured", "fixture_only"]
external_api_used: const false
credentials_used: const false
wallet_used: const false
signing_used: const false
exchange_write_used: const false
live_order_submitted: const false
network_attempted: const false
venue_count: integer
venues: array
```

Per-venue required fields:

```text
venue_id
venue_family
asset_universe
known_in_capability_catalog
known_in_suitability_catalog
current_venue_id_enabled
schema_enabled
strategy_lab_enabled
evaluation_plan_enabled
paper_enabled
paper_candidate_enabled
paper_intent_enabled
read_only_network_enabled
credentialed_read_only_enabled
paper_execution_enabled
live_enabled
external_api_used
credentials_used
wallet_used
signing_used
exchange_write_used
live_order_submitted
network_attempted
read_only_probe_status
read_only_probe_mode
credential_status
not_attempted_reasons
block_reasons
notes
next_action
```

Allowed values:

```text
read_only_probe_status:
  - local_capability_only
  - blocked_by_capability
  - not_configured

read_only_probe_mode:
  - fixture_only

credential_status:
  - not_required
  - not_checked
```

Forbidden wording in machine fields:

```text
ready
approved
connected
account_ready
live_ready
production_ready
```

### Expected Venue Rows

`trade_xyz`:

- `known_in_capability_catalog=true`
- `known_in_suitability_catalog=true`
- `current_venue_id_enabled=true`
- `schema_enabled=true`
- `strategy_lab_enabled=true`
- `evaluation_plan_enabled=true`
- `paper_enabled=true`
- `read_only_network_enabled=true`
- `credentialed_read_only_enabled=false`
- `paper_execution_enabled=true`
- `live_enabled=false`
- `network_attempted=false`
- `read_only_probe_status=local_capability_only`
- `credential_status=not_required`
- `block_reasons` includes live disabled reason

`bitget_demo`:

- `known_in_capability_catalog=true`
- `known_in_suitability_catalog=true`
- `current_venue_id_enabled=true`
- `schema_enabled=true`
- `strategy_lab_enabled=true`
- `evaluation_plan_enabled=false`
- `paper_enabled=true`
- `read_only_network_enabled=false`
- `credentialed_read_only_enabled=false`
- `paper_execution_enabled=true`
- `live_enabled=false`
- `network_attempted=false`
- `read_only_probe_status=local_capability_only`
- `credential_status=not_checked`
- `block_reasons` includes evaluation-plan disabled, read-only-network disabled, live disabled

`bitget_futures`:

- `known_in_capability_catalog=true`
- `known_in_suitability_catalog=true`
- `current_venue_id_enabled=false`
- `schema_enabled=false`
- `strategy_lab_enabled=false`
- `evaluation_plan_enabled=false`
- `paper_enabled=false`
- `paper_candidate_enabled=false`
- `paper_intent_enabled=false`
- `read_only_network_enabled=false`
- `credentialed_read_only_enabled=false`
- `paper_execution_enabled=false`
- `live_enabled=false`
- `network_attempted=false`
- `read_only_probe_status=blocked_by_capability`
- `credential_status=not_checked`
- `block_reasons` includes schema disabled, paper disabled, read-only-network disabled, live disabled

`hyperliquid_perp`:

- `known_in_capability_catalog=true`
- `known_in_suitability_catalog=true`
- `current_venue_id_enabled=false`
- `schema_enabled=false`
- `strategy_lab_enabled=false`
- `evaluation_plan_enabled=false`
- `paper_enabled=false`
- `paper_candidate_enabled=false`
- `paper_intent_enabled=false`
- `read_only_network_enabled=false`
- `credentialed_read_only_enabled=false`
- `paper_execution_enabled=false`
- `live_enabled=false`
- `network_attempted=false`
- `read_only_probe_status=blocked_by_capability`
- `credential_status=not_required`
- `block_reasons` includes schema disabled, paper disabled, read-only-network disabled, live disabled

### Report

Markdown report path:

```text
data/reports/venue_read_only_probe.md
```

Must include:

- title
- `run_id`
- `generated_at`
- top-level status
- artifact paths
- one section per venue
- explicit non-claims:
  - no external API used
  - no credentials used
  - no wallet used
  - no signing used
  - no exchange write used
  - no live order submitted
  - no network attempted
- next action per venue
- final boundary note:
  - `catalog known` is not `venue enabled`
  - read-only probe is not network readiness
  - this report is not paper / live permission

## 対象ファイル

### Add

- `src/sis/venues/read_only_probe.py`
- `schemas/venue_read_only_probe_summary.v1.schema.json`
- `tests/test_venue_read_only_probe.py`
- `tests/test_venue_read_only_probe_cli.py`
- `docs/venues/read_only_capability_probe.md`

### Modify

- `src/sis/commands/execution.py`
  - add `venue-read-only-probe`
  - call pure builder
  - write summary / report
  - echo status fields
- `tests/test_strategy_lab_schemas.py`
  - add the new schema to schema parse inventory if that test owns schema inventory
  - add or keep assertions that future venues are not in Strategy Lab execution-venue schemas
- `tests/test_venue_capabilities.py`
  - add drift guard only if not fully covered by new probe tests
- `README.md`
  - add command / doc link only after implementation
- `docs/CURRENT_STATE.md`
  - add current state summary only after implementation
- `docs/IMPLEMENTED_SURFACES.md`
  - add implemented surface row only after implementation
- `docs/REPO_CAPABILITIES_CURRENT_2026-06-16.md`
  - add capability summary only after implementation

### Do Not Modify

- `src/sis/venues/ids.py`
- `schemas/strategy_signal.v1.schema.json`
- `schemas/trade_candidate.v1.schema.json`
- `schemas/paper_intent_preview.v1.schema.json`
- `schemas/evaluation_plan.mls.v1.schema.json`
- `src/sis/research/strategy_lab/`
- `src/sis/paper/`
- `src/sis/strategy_review/`
- `pyproject.toml`
- `uv.lock`

## Implementation Tasks

### T1. Red tests for pure builder

Add `tests/test_venue_read_only_probe.py`.

Tests:

- builder returns top-level `schema_version=venue_read_only_probe_summary.v1`
- `venue_count=4`
- venues are exactly `trade_xyz`, `bitget_demo`, `bitget_futures`, `hyperliquid_perp`
- all top-level safety fields are false
- every venue has all required fields
- every venue has `network_attempted=false`
- future venues are `blocked_by_capability`
- `bitget_demo` is not production Bitget
- `hyperliquid_perp` is not Trade[XYZ]
- `current_venue_id_enabled` matches `VENUE_IDS`
- no env values are read or serialized

Run:

```bash
uv run pytest -q tests/test_venue_read_only_probe.py
```

Expected before implementation: fail.

### T2. Implement pure builder

Add `src/sis/venues/read_only_probe.py`.

Required functions:

```python
def build_venue_read_only_probe_summary(
    *,
    generated_at: str | None = None,
    run_id: str | None = None,
) -> dict[str, object]: ...

def build_venue_read_only_probe_report(summary: Mapping[str, object]) -> str: ...
```

Rules:

- Build from `VENUE_CAPABILITY_CATALOG`, `VENUE_SUITABILITY_CATALOG`, and `VENUE_IDS`.
- Fail closed if catalog keys diverge.
- Do not read `os.environ`.
- Do not import adapters or network clients.
- Do not call `get_settings()`.
- Do not call Strategy Review, Strategy Lab, paper, or execution adapter code.
- Use deterministic `generated_at` / `run_id` when passed from tests.
- If generated internally, use UTC ISO timestamp and a stable non-secret run id derived from timestamp or UUID.

### T3. Add JSON Schema

Add `schemas/venue_read_only_probe_summary.v1.schema.json`.

Schema requirements:

- const false for:
  - `external_api_used`
  - `credentials_used`
  - `wallet_used`
  - `signing_used`
  - `exchange_write_used`
  - `live_order_submitted`
  - `network_attempted`
- require all top-level fields and per-venue fields listed above
- `additionalProperties=false` at top-level and per-venue object level unless an existing schema style in this repo forbids it
- enums for status fields
- string arrays for `not_attempted_reasons`, `block_reasons`, `notes`

Tests:

- generated summary validates with `jsonschema`
- schema parses in existing schema inventory test if applicable
- schema rejects any safety field set to true

### T4. Add CLI

Modify `src/sis/commands/execution.py`.

Command:

```bash
uv run sis venue-read-only-probe
```

No options in PR00.

Writes:

```text
{settings.data_dir}/ops/venue_read_only_probe_summary.json
{settings.data_dir}/reports/venue_read_only_probe.md
```

Stdout must include:

```text
status=<status>
run_id=<run_id>
venue_count=<count>
external_api_used=False
credentials_used=False
wallet_used=False
signing_used=False
exchange_write_used=False
network_attempted=False
summary_path=<path>
report_path=<path>
```

Exit behavior:

- exit `0` when artifacts are written, even if future venues are blocked
- exit `2` only for unexpected internal errors such as catalog mismatch or write failure

Do not add network mode flags.

### T5. Add CLI tests

Add `tests/test_venue_read_only_probe_cli.py`.

Tests:

- `SIS_DATA_DIR` temp path writes summary/report
- command exits `0`
- stdout contains safety false fields
- stdout does not contain secret-like env values
- summary path and report path exist
- summary includes 4 venues
- summary says no network attempted
- future venues are blocked
- command works with empty Bitget env values

Run:

```bash
uv run pytest -q tests/test_venue_read_only_probe_cli.py
```

### T6. Guard no schema / venue widening

Add or keep tests proving:

- `src/sis/venues/ids.py` still has only `trade_xyz`, `bitget_demo`
- `strategy_signal.v1.schema.json` enum remains `trade_xyz`, `bitget_demo`
- `trade_candidate.v1.schema.json` enum remains `trade_xyz`, `bitget_demo`
- `paper_intent_preview.v1.schema.json` enum remains `trade_xyz`, `bitget_demo`
- `evaluation_plan.mls.v1.schema.json` target remains `trade_xyz`

Run:

```bash
uv run pytest -q tests/test_venue_capabilities.py tests/test_venue_suitability.py tests/test_strategy_lab_schemas.py
git diff -- src/sis/venues/ids.py schemas/strategy_signal.v1.schema.json schemas/trade_candidate.v1.schema.json schemas/paper_intent_preview.v1.schema.json schemas/evaluation_plan.mls.v1.schema.json
```

Expected git diff output: empty.

### T7. Docs

Add `docs/venues/read_only_capability_probe.md`.

Required content:

- purpose
- command
- output paths
- fields explained
- explicit non-claims
- per-venue interpretation
- why Strategy Review is not integrated in PR00
- what requires a separate plan

Then update:

- `README.md`
- `docs/CURRENT_STATE.md`
- `docs/IMPLEMENTED_SURFACES.md`
- `docs/REPO_CAPABILITIES_CURRENT_2026-06-16.md`

Use Tokyo timestamp metadata for every edited Markdown doc.

## Test Plan

### Focused red / green

```bash
uv run pytest -q tests/test_venue_read_only_probe.py
uv run pytest -q tests/test_venue_read_only_probe_cli.py
uv run pytest -q tests/test_venue_capabilities.py tests/test_venue_suitability.py tests/test_strategy_lab_schemas.py
```

### CLI smoke

```bash
uv run sis venue-read-only-probe
```

Expected stdout includes:

```text
status=fixture_only
venue_count=4
external_api_used=False
credentials_used=False
wallet_used=False
signing_used=False
exchange_write_used=False
network_attempted=False
```

### Docs / whitespace

```bash
uv run python scripts/check_current_docs.py
git diff --check
```

### Final gate

```bash
./scripts/check
```

## Completion Criteria

This PR is complete only when all items are true:

1. `uv run sis venue-read-only-probe --help` works.
2. `uv run sis venue-read-only-probe` writes both artifacts.
3. Summary validates against `schemas/venue_read_only_probe_summary.v1.schema.json`.
4. Summary contains exactly 4 venue rows.
5. Top-level safety fields are all false.
6. Per-venue safety fields are all false.
7. `network_attempted=false` at top-level and per venue.
8. `bitget_futures` is known but disabled / blocked.
9. `hyperliquid_perp` is known but disabled / blocked.
10. `bitget_demo` is clearly demo-only and not production Bitget.
11. `trade_xyz` is clearly proxy/read-only and not direct Hyperliquid.
12. No env values, credentials, secrets, API keys, passphrases, private keys, or tokens appear in stdout or artifacts.
13. `src/sis/venues/ids.py` is unchanged.
14. Strategy Lab schemas listed in T6 are unchanged.
15. `pyproject.toml` and `uv.lock` are unchanged.
16. No Strategy Review integration is added.
17. No paper bridge, Strategy Case registry, UI, network probe, or live path is added.
18. Focused tests pass.
19. `uv run python scripts/check_current_docs.py` passes.
20. `git diff --check` passes.
21. `./scripts/check` passes.

## Stop Conditions

Stop and ask before proceeding if implementation seems to require:

- external API call
- env credential read
- new credential name
- network client import
- account / balance / position / fill / order read
- signing or wallet logic
- exchange write path
- `VenueId` widening
- Strategy Lab schema widening
- paper execution enablement
- live execution enablement
- dependency addition
- changing `pyproject.toml` or `uv.lock`
- changing Strategy Review behavior
- making generated artifacts easier to read as ready than blocked

## 抜け・漏れ・誤謬リスク Pass

Known risks and mitigations:

- Risk: `read_only_network_enabled=true` on `trade_xyz` may be read as network attempted.
  - Mitigation: include separate `network_attempted=false` and report non-claim.
- Risk: `bitget_demo` credentials may be read by accident through existing smoke code.
  - Mitigation: builder must not import adapters, healthcheck, or read env.
- Risk: future venues may enter Strategy Lab schemas accidentally.
  - Mitigation: guard tests and final `git diff` against schema / `VenueId` files.
- Risk: run history may be requested later.
  - Mitigation: include `run_id` now, defer run-specific directories to separate plan.
- Risk: Strategy Review integration is tempting after artifact exists.
  - Mitigation: explicitly out of scope; future source-artifact integration requires a new plan.
- Risk: `paper_enabled` may be ambiguous.
  - Mitigation: keep separate `paper_candidate_enabled`, `paper_intent_enabled`, and `paper_execution_enabled`.

## After This PR

Only after this PR is complete and reviewed, choose one separately planned next step:

1. credentialed Bitget read-only network probe
2. credentialed Hyperliquid read-only network probe
3. paper bridge validation
4. Strategy Case registry
5. UI

Do not combine any of those with `PR-VENUE-PROBE-00`.
