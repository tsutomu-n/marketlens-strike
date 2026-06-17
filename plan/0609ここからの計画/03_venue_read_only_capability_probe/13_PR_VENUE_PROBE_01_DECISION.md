<!--
作成日: 2026-06-17_11:38 JST
更新日: 2026-06-17_11:38 JST
-->

# PR-VENUE-PROBE-01 Dogfood Decision

## 結論

Selected: `NO_ACTION`

`venue-read-only-probe` の dogfood 結果は、fixture-first venue boundary artifact として十分です。

次に credentialed read-only network probe、paper bridge validation、Strategy Case registry、Strategy Review 連携、schema widening、paper/live enablement へ進む根拠は、この dogfood からは出ていません。

## Dogfood Run

実行日時:

- `2026-06-17_11:38 JST`

実行コマンド:

```bash
tmpdir=$(mktemp -d)
SIS_DATA_DIR="$tmpdir/data" uv run sis venue-read-only-probe
find "$tmpdir/data" -maxdepth 3 -type f | sort
sha256sum "$tmpdir/data/ops/venue_read_only_probe_summary.json" "$tmpdir/data/reports/venue_read_only_probe.md"
```

生成 artifact:

```text
/tmp/tmp.rM2hbAehpV/data/ops/venue_read_only_probe_summary.json
/tmp/tmp.rM2hbAehpV/data/reports/venue_read_only_probe.md
```

この `/tmp` artifact は repo に commit しません。判断証跡はこの文書に hash と要約だけ残します。

Artifact hash:

```text
85363653a3ed8cd72bce9b28369728eda70cf249cdca180ec43b5ee6839b6a63  venue_read_only_probe_summary.json
71b83a9b203babd0f3c47f3f97691d853a547f92e8f3c6cd49c6229eb67aedbc  venue_read_only_probe.md
```

## Schema Validation

実行:

```bash
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

結果:

```text
schema_valid=true
```

## Summary Check

Top-level:

```text
schema_version=venue_read_only_probe_summary.v1
status=fixture_only
venue_count=4
external_api_used=false
credentials_used=false
wallet_used=false
signing_used=false
exchange_write_used=false
live_order_submitted=false
network_attempted=false
```

Venue rows:

| venue_id | current_venue_id_enabled | schema_enabled | strategy_lab_enabled | evaluation_plan_enabled | paper_enabled | read_only_network_enabled | credentialed_read_only_enabled | live_enabled | read_only_probe_status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `bitget_demo` | true | true | true | false | true | false | false | false | `local_capability_only` |
| `bitget_futures` | false | false | false | false | false | false | false | false | `blocked_by_capability` |
| `hyperliquid_perp` | false | false | false | false | false | false | false | false | `blocked_by_capability` |
| `trade_xyz` | true | true | true | true | true | true | false | false | `local_capability_only` |

確認結果:

- `bitget_futures` は catalog known だが current venue / schema / Strategy Lab / evaluation plan / paper / read-only network / credentialed read-only / live は disabled。
- `hyperliquid_perp` は catalog known だが current venue / schema / Strategy Lab / evaluation plan / paper / read-only network / credentialed read-only / live は disabled。
- `bitget_demo` は demo-only であり、production Bitget ではないことが report の `notes` に出る。
- `trade_xyz` は proxy surface であり、direct Hyperliquid ではないことが report の `notes` に出る。
- `read_only_network_enabled=true` の `trade_xyz` でも `network_attempted=false` であり、network readiness とは主張していない。

## Report Boundary Check

確認した report 行:

```text
notes: demo_only_not_production_bitget, local_env_presence_is_not_network_probe
notes: trade_xyz_proxy_surface, not_direct_hyperliquid, public_operator_live_command_absent
`catalog known` is not `venue enabled`.
Read-only probe is not network readiness.
This report is not paper / live permission.
```

評価:

- report 単体で `bitget_demo` を production Bitget と誤読しにくい。
- report 単体で Trade[XYZ] を direct Hyperliquid と誤読しにくい。
- report 単体で read-only probe を network readiness と誤読しにくい。

## Misread Risk Search

実行:

```bash
rg -n "ready|approved|connected|account_ready|live_ready|production_ready|credentialed|network readiness|paper ready|live ready" \
  "$tmpdir/data/ops/venue_read_only_probe_summary.json" \
  "$tmpdir/data/reports/venue_read_only_probe.md"
```

Hit の扱い:

- `credentialed_read_only_enabled: false`: disabled field なので問題なし。
- `write_separate_plan_for_credentialed_network_probe_before_any_enablement`: separate plan before enablement の明示なので問題なし。
- `Read-only probe is not network readiness.`: 非claimの明示なので問題なし。

修正対象:

- なし。

## Decision

Selected: `NO_ACTION`

Reason:

- summary は schema に直接 validate できた。
- top-level safety flags はすべて false。
- `bitget_futures` と `hyperliquid_perp` は enabled / paper / live に見えない。
- report 単体で `bitget_demo` と Trade[XYZ] の誤読境界を読める。
- 誤読リスク検索の hit は disabled field または明示的な非claimだけだった。
- dogfood 証跡から、credentialed network / paper bridge / Strategy Case registry へ今進む必要は出ていない。

Not selected:

- `PLAN_CREDENTIAL_READ_ONLY_PROBE`: credentials / external API / network を扱う別スコープに進む根拠は、この dogfood では出ていない。
- `PLAN_PAPER_BRIDGE_VALIDATION`: venue boundary artifact は paper path の実行許可や readiness を主張していない。paper bridge が次のボトルネックだとは言えない。
- `PLAN_STRATEGY_CASE_REGISTRY`: venue boundary の整理は十分で、strategy artifact registry が次に必要だとはこの dogfood からは言えない。
- `FIX_PROBE_WORDING_ONLY`: report に `notes` が出ており、現時点で追加文言修正は不要。

## Non-Claims

この decision は次を証明しません。

- Bitget production readiness。
- Hyperliquid direct trading readiness。
- credentialed read-only network readiness。
- account readiness。
- paper readiness。
- live readiness。
- wallet readiness。
- signing readiness。
- exchange-write readiness。

## Completion

PR-VENUE-PROBE-01 は完了です。

次の作業は、ユーザーが別途明示した場合だけ計画します。現時点では追加実装しません。
