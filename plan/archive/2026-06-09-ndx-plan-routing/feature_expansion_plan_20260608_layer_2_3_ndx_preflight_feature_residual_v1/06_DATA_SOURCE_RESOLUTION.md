<!--
作成日: 2026-06-08_20:18 JST
更新日: 2026-06-08_20:18 JST
-->

# 06_DATA_SOURCE_RESOLUTION

## Data Source Resolutionの目的

2.2 DAG上のproxyが、現実にどのデータsourceで再現可能かを、2.3の最初に固定する。

## required sources

| Source | Role | 初期provider | 注意 |
|---|---|---|---|
| QQQ | observed ETF proxy | fixture / local file | NDXそのものではない |
| SPY | broad market proxy | fixture / local file | broad beta |
| SMH | semiconductor proxy | fixture / local file | SOX直接ではない |
| VIX | volatility proxy | fixture / local file | VXN代替でありNasdaq-specificではない |
| DGS10 | rates proxy | fixture / local file | 同日open前利用可能性に注意 |
| mega_cap_basket | concentration proxy | fixture / local file | weighting ruleをmanifestに残す |

## optional/deferred

| Source | 初期扱い | 理由 |
|---|---|---|
| NDX | deferred | 指数reference。初期観測proxyはQQQ |
| NQ | deferred | futures data source未決定 |
| VXN | deferred | provider/license未決定 |
| SOX | deferred | direct index source未決定。SMHで代替 |
| QQQ premium/discount | deferred | ETF tracking noise反証用 |
| event calendar | deferred | macro/refutation用 |
| OPEX calendar | deferred | calendar/refutation用 |

## 出力JSON例

```json
{
  "schema_version": "ndx_data_source_resolution.v1",
  "generated_at": "2026-06-08T20:18:00+09:00",
  "dag_id": "HYP-NDX-001",
  "dag_artifact_hash": "sha256:...",
  "sources": [
    {
      "source_id": "QQQ",
      "status": "required",
      "proxy_for": ["qqq_open_gap", "qqq_open_to_close_return"],
      "initial_provider_mode": "fixture_or_local_file",
      "external_api_required": false,
      "credentials_required": false,
      "caveats": ["ETF proxy, not NDX index itself"]
    }
  ],
  "deferred_sources": [
    {
      "source_id": "NQ",
      "reason": "futures provider not selected",
      "required_for_initial_feature_panel": false
    }
  ]
}
```

## Stop conditions

```text
- required sourceがexternal APIなしでfixture/local fileから作れない
- DGS10/VIXの利用可能時刻を定義できない
- QQQをNDXそのものとして扱う必要が出る
- NQ/VXN/SOXを初期requiredにしたくなる
```
