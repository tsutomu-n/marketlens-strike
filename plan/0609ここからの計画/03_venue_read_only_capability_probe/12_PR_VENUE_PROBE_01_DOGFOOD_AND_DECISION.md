<!--
作成日: 2026-06-17_11:16 JST
更新日: 2026-06-17_11:20 JST
-->

# PR-VENUE-PROBE-01 Dogfood And Decision Plan

## 結論

次にやるなら、実装拡張ではなく `PR-VENUE-PROBE-01: Dogfood And Decision` です。

目的は、実装済みの `venue-read-only-probe` を local-only で実行し、生成された summary / report を読んで、次に進めるべき計画を決めることです。

この PR では credentialed network probe、paper bridge、Strategy Review 連携、schema widening、order path は実装しません。

重要: この PR の既定ゴールは「次へ進むこと」ではありません。実出力を読んだ結果、追加実装しない判断を残すことも成功です。

## 目的

`venue-read-only-probe` の出力が、次の誤読を機械的に防げるか確認します。

- `catalog known` を `venue enabled` と読む。
- `bitget_demo` を production Bitget Futures と読む。
- Trade[XYZ] を direct Hyperliquid と読む。
- `read-only probe` を network readiness と読む。
- `PAPER_OBSERVATION_CANDIDATE` または paper-related flag を paper 実行許可と読む。
- `READ_ONLY_GO` を live ready と読む。

確認後、次に進める候補を1つだけ decision artifact に残します。

## 制約

この PR で許可すること:

- `uv run sis venue-read-only-probe` の local 実行。
- 生成された summary / report の内容確認。
- 誤読を誘う文言があれば docs または report text の局所修正。
- decision artifact の追加。
- local-only test / docs check / full check。
- report が単体で読めない場合の文言修正。

この PR で禁止すること:

- external network call。
- credentials / env secret の追加、参照、検証。
- Bitget / Hyperliquid API call。
- wallet access。
- signing。
- exchange write。
- order submit / cancel / amend / close。
- `VenueId` widening。
- Strategy Lab schema widening。
- `evaluation_plan.mls.v1` target widening。
- Strategy Review 連携。
- paper bridge validation。
- Strategy Case registry。
- UI。
- dependency addition。

停止条件:

- `venue-read-only-probe` が credentials、network、adapter、exchange client、wallet、signer、order path に触れている疑いがある。
- summary schema と実出力が一致しない。
- output が `ready` / `approved` / `connected` / `live_ready` / `production_ready` などの誤読しやすい machine field を含む。
- `bitget_futures` または `hyperliquid_perp` が enabled / paper / live に見える出力になっている。
- report だけを読んだ人が `bitget_demo` を production Bitget、または Trade[XYZ] を direct Hyperliquid と読める。
- 修正が schema / auth / external API / paper path / live path に波及しそう。

## 対象ファイル

Read-only で確認するファイル:

- `src/sis/venues/read_only_probe.py`
- `src/sis/commands/execution.py`
- `schemas/venue_read_only_probe_summary.v1.schema.json`
- `docs/venues/read_only_capability_probe.md`
- `tests/test_venue_read_only_probe.py`
- `tests/test_venue_read_only_probe_cli.py`

必要な場合だけ局所修正してよいファイル:

- `src/sis/venues/read_only_probe.py`
- `docs/venues/read_only_capability_probe.md`
- `README.md`
- `docs/CURRENT_STATE.md`
- `docs/IMPLEMENTED_SURFACES.md`
- `docs/REPO_CAPABILITIES_CURRENT_2026-06-16.md`
- `tests/test_venue_read_only_probe.py`
- `tests/test_venue_read_only_probe_cli.py`

追加する decision artifact:

- `plan/0609ここからの計画/03_venue_read_only_capability_probe/13_PR_VENUE_PROBE_01_DECISION.md`

原則として触らないファイル:

- `src/sis/venues/ids.py`
- `schemas/strategy_signal.v1.schema.json`
- `schemas/trade_candidate.v1.schema.json`
- `schemas/paper_intent_preview.v1.schema.json`
- `schemas/evaluation_plan.mls.v1.schema.json`
- `pyproject.toml`
- `uv.lock`

## 実行手順

### Step 0: Current proof

```bash
uv run python -V
uv run sis --help
uv run sis venue-read-only-probe --help
uv run python scripts/check_current_docs.py
```

期待:

- `venue-read-only-probe` が CLI help に存在する。
- current-doc checker が通る。
- Python は repo の locked runtime と一致する。

### Step 1: Dogfood 実行

repo の `data/` を汚さないため、temp data dir で実行します。

```bash
tmpdir="$(mktemp -d)"
SIS_DATA_DIR="$tmpdir/data" uv run sis venue-read-only-probe
find "$tmpdir/data" -maxdepth 3 -type f | sort
```

期待する生成物:

```text
$tmpdir/data/ops/venue_read_only_probe_summary.json
$tmpdir/data/reports/venue_read_only_probe.md
```

### Step 2: Summary を確認

```bash
jq '.schema_version, .status, .venue_count, .external_api_used, .credentials_used, .wallet_used, .signing_used, .exchange_write_used, .live_order_submitted, .network_attempted' "$tmpdir/data/ops/venue_read_only_probe_summary.json"
jq -r '.venues[] | [.venue_id, .current_venue_id_enabled, .schema_enabled, .strategy_lab_enabled, .evaluation_plan_enabled, .paper_enabled, .read_only_network_enabled, .credentialed_read_only_enabled, .live_enabled, .read_only_probe_status] | @tsv' "$tmpdir/data/ops/venue_read_only_probe_summary.json"
uv run python - <<'PY' "$tmpdir/data/ops/venue_read_only_probe_summary.json"
import json
import sys
from pathlib import Path

from jsonschema import validate

summary_path = Path(sys.argv[1])
schema_path = Path("schemas/venue_read_only_probe_summary.v1.schema.json")
validate(
    instance=json.loads(summary_path.read_text(encoding="utf-8")),
    schema=json.loads(schema_path.read_text(encoding="utf-8")),
)
print("schema_valid=true")
PY
```

期待:

- top-level safety flags はすべて `false`。
- `venue_count` は `4`。
- `bitget_futures` は current venue / schema / Strategy Lab / evaluation plan / paper / read-only network / credentialed read-only / live がすべて disabled。
- `hyperliquid_perp` は current venue / schema / Strategy Lab / evaluation plan / paper / read-only network / credentialed read-only / live がすべて disabled。
- `bitget_demo` は production Bitget ではないことが summary と report の両方で読める。
- `trade_xyz` は direct Hyperliquid ではないことが summary と report の両方で読める。
- summary は `schemas/venue_read_only_probe_summary.v1.schema.json` に直接 validate できる。

### Step 3: Report を確認

```bash
sed -n '1,240p' "$tmpdir/data/reports/venue_read_only_probe.md"
```

確認観点:

- 人間が読んでも `catalog known` と `enabled` を混同しない。
- `read-only network enabled` と `network attempted` を混同しない。
- future venues が disabled である理由が venue ごとに読める。
- next action が network / credentials / paper / live を勝手に始める表現になっていない。
- report 単体で `bitget_demo` が production Bitget ではないことを読める。
- report 単体で Trade[XYZ] が direct Hyperliquid ではないことを読める。

### Step 4: 誤読リスク検索

```bash
rg -n "ready|approved|connected|account_ready|live_ready|production_ready|credentialed|network readiness|paper ready|live ready" "$tmpdir/data/ops/venue_read_only_probe_summary.json" "$tmpdir/data/reports/venue_read_only_probe.md"
```

判定:

- machine field に `ready` / `approved` / `connected` / `account_ready` / `live_ready` / `production_ready` が出たら修正対象。
- prose に `credentialed` や `network readiness` が出ること自体は許容するが、「未証明」「未実施」「別計画が必要」と読めない場合は修正対象。
- `credentialed_read_only_enabled: False` のような disabled field は修正対象ではない。

### Step 5: Decision artifact を作成

`13_PR_VENUE_PROBE_01_DECISION.md` に次を記録します。

必須項目:

- 作成日 / 更新日 metadata。
- dogfood 実行コマンド。
- 生成 artifact path。
- summary / report の `sha256sum`。
- schema validation 結果。
- 4 venue の確認結果。
- 誤読リスク検索結果。
- 修正したファイルがあれば一覧。
- 次の判断を1つだけ選ぶ。
- temp artifact は repo に commit しない。必要な証跡は decision artifact に hash と要約だけ残す。

次の判断候補:

- `NO_ACTION`: 現時点では追加実装しない。
- `PLAN_CREDENTIAL_READ_ONLY_PROBE`: credentialed read-only network probe の計画に進む。
- `PLAN_PAPER_BRIDGE_VALIDATION`: paper bridge validation の計画に進む。
- `PLAN_STRATEGY_CASE_REGISTRY`: Strategy Case registry の計画に進む。
- `FIX_PROBE_WORDING_ONLY`: 実装拡張せず、文言修正だけ行う。

判断の書き方:

```markdown
## Decision

Selected: `<one of the allowed decisions>`

Reason:

- ...

Not selected:

- `PLAN_CREDENTIAL_READ_ONLY_PROBE`: ...
- `PLAN_PAPER_BRIDGE_VALIDATION`: ...
- `PLAN_STRATEGY_CASE_REGISTRY`: ...
- `FIX_PROBE_WORDING_ONLY`: ...
```

判断基準:

- `NO_ACTION`: summary / report が十分に明確で、追加修正も次計画も不要な場合だけ選ぶ。
- `FIX_PROBE_WORDING_ONLY`: artifact の意味は正しいが、report / docs の人間向け表現だけが弱い場合に選ぶ。
- `PLAN_CREDENTIAL_READ_ONLY_PROBE`: credentialed network なしでは次の実務判断ができないと、dogfood 証跡から言える場合だけ選ぶ。
- `PLAN_PAPER_BRIDGE_VALIDATION`: venue boundary ではなく paper path の検証が次のボトルネックだと、dogfood 証跡から言える場合だけ選ぶ。
- `PLAN_STRATEGY_CASE_REGISTRY`: venue boundary と paper path よりも、strategy artifact の整理が次のボトルネックだと、dogfood 証跡から言える場合だけ選ぶ。

## テスト方針

局所確認:

```bash
uv run sis venue-read-only-probe --help
tmpdir="$(mktemp -d)"
SIS_DATA_DIR="$tmpdir/data" uv run sis venue-read-only-probe
uv run pytest -q tests/test_venue_read_only_probe.py tests/test_venue_read_only_probe_cli.py
uv run python scripts/check_current_docs.py
```

修正した場合の追加確認:

```bash
uv run pytest -q tests/test_venue_capabilities.py tests/test_venue_suitability.py tests/test_strategy_lab_schemas.py tests/test_bitget_demo_cli.py
git diff --check
```

完了前の確認:

```bash
./scripts/check
```

ガード確認:

```bash
git diff -- src/sis/venues/ids.py schemas/strategy_signal.v1.schema.json schemas/trade_candidate.v1.schema.json schemas/paper_intent_preview.v1.schema.json schemas/evaluation_plan.mls.v1.schema.json pyproject.toml uv.lock
```

期待:

- guard 対象ファイルに差分がない。
- `./scripts/check` が通る。

## 完了条件

完了にはすべて必要です。

- `venue-read-only-probe` を temp `SIS_DATA_DIR` で dogfood 済み。
- summary / report を人間が読み、4 venue の境界を確認済み。
- 誤読リスク検索を実施済み。
- 誤読を誘う文言があれば局所修正済み。
- `13_PR_VENUE_PROBE_01_DECISION.md` に判断を1つだけ記録済み。
- 禁止スコープに触れていない。
- guard 対象ファイルに差分がない。
- local checks が通っている。
- 完了報告で、この PR が credentialed read-only network readiness、paper readiness、live readiness を証明しないことを明記している。
