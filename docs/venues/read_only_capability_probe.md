<!--
作成日: 2026-06-17_10:50 JST
更新日: 2026-06-17_10:50 JST
-->

# Venue Read-only Capability Probe

## 結論

`venue-read-only-probe` は、現行 catalog にある venue の capability boundary を local artifact にする fixture-first command です。

これは Bitget / Hyperliquid 本番対応、network readiness、credential readiness、paper permission、live permission ではありません。

## Command

```bash
uv run sis venue-read-only-probe
```

出力:

```text
data/ops/venue_read_only_probe_summary.json
data/reports/venue_read_only_probe.md
```

summary schema:

```text
schemas/venue_read_only_probe_summary.v1.schema.json
```

## What It Records

対象 venue:

- `trade_xyz`
- `bitget_demo`
- `bitget_futures`
- `hyperliquid_perp`

各 venue について次を記録します。

- capability / suitability catalog に存在するか
- current `VenueId` として有効か
- Strategy Lab schema / evaluation plan / paper candidate / paper intent / paper execution / live execution が有効か
- read-only network / credentialed read-only が有効か
- external API、credentials、wallet、signing、exchange write、live order、network attempt を使ったか
- 試していない理由
- block reason
- 次の action

## Non-Claims

この command は次を証明しません。

- Bitget production readiness
- Hyperliquid direct trading readiness
- network connectivity
- account readiness
- credential readiness
- paper readiness
- live readiness
- wallet readiness
- signing readiness
- exchange-write readiness

`catalog known` は `venue enabled` ではありません。`read-only probe` は `network readiness` ではありません。

## Per-Venue Interpretation

| Venue | Meaning |
|---|---|
| `trade_xyz` | implemented proxy / research / read-only surface。direct Hyperliquid ではない |
| `bitget_demo` | demo fixture surface。production Bitget Futures ではない |
| `bitget_futures` | known future venue。現行 schema / paper / network / live は disabled |
| `hyperliquid_perp` | known future direct Hyperliquid perp venue。Trade[XYZ] proxy ではない |

## Strategy Review Boundary

この artifact は Strategy Review へ自動連携しません。

理由:

- Strategy Review は strategy artifact を人間が読むための surface。
- この artifact は venue capability boundary。
- 将来 Strategy Review の source artifact として参照する場合も、別 plan が必要。

## Separate Plan Required

次は別 plan が必要です。

- credentialed Bitget read-only network probe
- credentialed Hyperliquid read-only network probe
- Bitget demo order lifecycle
- paper bridge validation
- Strategy Case registry
- UI
- production venue schema widening
- paper / live execution enablement
