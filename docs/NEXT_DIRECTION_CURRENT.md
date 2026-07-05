<!--
作成日: 2026-06-17_10:00 JST
更新日: 2026-07-05_11:55 JST
-->

# Next Direction Current

## 結論

この文書は互換入口です。現行の方向性は [CURRENT_GOAL_AND_DIRECTION_2026-07-05.md](CURRENT_GOAL_AND_DIRECTION_2026-07-05.md) に統合しました。

今後は次の順で読む。

1. [CURRENT_STATE.md](CURRENT_STATE.md)
2. [CURRENT_GOAL_AND_DIRECTION_2026-07-05.md](CURRENT_GOAL_AND_DIRECTION_2026-07-05.md)
3. [CURRENT_DOCS_INDEX_2026-07-05.md](CURRENT_DOCS_INDEX_2026-07-05.md)

旧 roadmap 本文、completed plan、dogfood log、固定 pass-count snapshot は current proof ではありません。履歴を探す場合だけ [archive/README.md](archive/README.md) と [../plan/README.md](../plan/README.md) から辿ります。

## External Input Restart Checklist

外部入力が来た場合も、paper / live 許可として読まない。まず code、CLI help、schema、tests、current docs を確認する。

### Trade[XYZ] Public User Address

- `SIS_TRADE_XYZ_EXECUTION_STATE_USER_ADDRESS=<public-user-address>`
- `SIS_TRADE_XYZ_EXECUTION_STATE_COLLECTOR_ENABLED=1`

これは read-only execution state collection の opt-in です。wallet、signing、exchange write、live order は許可しません。

### Bitget Demo Credentials

- `BITGET_DEMO_API_KEY`
- `BITGET_DEMO_API_SECRET`
- `BITGET_DEMO_PASSPHRASE`

これは demo read-only / smoke 用の再確認入力です。production Bitget live readiness ではありません。

### New Normal Paper Observation Evidence

新しい trading day を含む evidence だけが normal threshold の前進材料です。同日 artifact の rerun や fill 水増しは trading days を増やしません。

## Verification

```bash
uv run python scripts/check_current_docs.py
uv run python scripts/check_cli_catalog.py
uv run sis --help
```
