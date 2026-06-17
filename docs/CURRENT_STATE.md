<!--
作成日: 2026-05-25_19:45 JST
更新日: 2026-06-17_22:22 JST
-->

# Current State

この文書は `marketlens-strike` の現在地を短く読むための入口です。実装の正本は `src/`、`tests/`、`schemas/`、`configs/`、`scripts/`、CLI help、生成済み artifact です。

## 結論

- 現在の開発主軸は backtest-first / venue-neutral。Trade[XYZ] は実装済みの主要 venue だが、当面の注文口前提にはしない。
- いま使える主要 surface は Strategy Lab / Strategy Authoring / backtest pack / Strategy Review / NDX local research gates / read-only Trade[XYZ] / paper operations / operations audit。詳細は [IMPLEMENTED_SURFACES.md](IMPLEMENTED_SURFACES.md) を読む。
- 専門用語を減らして「できること / できないこと」を読む場合は [REPO_CAPABILITIES_PLAIN_JA_2026-06-17.md](REPO_CAPABILITIES_PLAIN_JA_2026-06-17.md) を読む。
- 実務的な次方向と外部入力時の再確認は [NEXT_DIRECTION_CURRENT.md](NEXT_DIRECTION_CURRENT.md) を読む。
- `READ_ONLY_GO`、Strategy Review の `READY_FOR_HUMAN_REVIEW`、backtest pack validation `PASS` は、paper execution permission、alpha proof、live readiness ではない。
- `data/` は runtime / generated state。fresh checkout では必要な artifact を再生成する。

## 現在できること

| 目的 | 読むもの |
|---|---|
| 実装済み surface を確認する | [IMPLEMENTED_SURFACES.md](IMPLEMENTED_SURFACES.md) |
| 技術詳細の capability catalog を見る | [REPO_CAPABILITIES_CURRENT_2026-06-16.md](REPO_CAPABILITIES_CURRENT_2026-06-16.md) |
| Strategy Lab / Strategy Authoring を使う | [strategy_research_lab/README.md](strategy_research_lab/README.md) |
| backtest pack / optional framework / robustness を見る | [backtest/README.md](backtest/README.md) |
| Strategy Review packet と operator record を使う | [strategy_review/README.md](strategy_review/README.md) |
| NDX local research gates を見る | [research/ndx/README.md](research/ndx/README.md) |
| Strategy Lifecycle / paper observation status を見る | [strategy_lifecycle/README.md](strategy_lifecycle/README.md) |
| venue capability boundary を見る | [venues/read_only_capability_probe.md](venues/read_only_capability_probe.md) |
| operator 手順を見る | [OPERATIONS_RUNBOOK.md](OPERATIONS_RUNBOOK.md) と [runbooks/README.md](runbooks/README.md) |

## 境界

- `VenueId` は現行 schema では `trade_xyz` と `bitget_demo`。`bitget_futures` と `hyperliquid_perp` は catalog-only / disabled。
- `bitget_demo` は demo execution surface。production Bitget live readiness ではない。
- Trade[XYZ] read-only execution state collection は public user address と明示 opt-in がある時だけ外部 `/info` read を行う。wallet、signing、exchange write、live order は使わない。
- `PaperIntentPreview` は paper-only の仮注文意図。live order として扱わない。
- Strategy Review は existing artifact を読む human-review packet と operator decision record。paper execution や live trading を許可しない。
- NDX Layer 2.2-2.8 は local research / paper-observation gate。alpha、account readiness、wallet readiness、exchange-write readiness を証明しない。
- `micro_live` 系 code は存在するが、標準 operator CLI の live execution surface としては exposed していない。

## まだ証明していないこと

- production live order smoke。
- signing / wallet / exchange write integration。
- Bitget credentialed read-only network smoke。
- Bitget demo order lifecycle。
- live order preview / 注文候補生成の正式 command surface。
- Alpaca credentials ありの API connectivity smoke。
- Strategy Review や backtest validation からの paper / live permission。

## 外部入力待ち

- Trade[XYZ] execution state collection: `SIS_TRADE_XYZ_EXECUTION_STATE_USER_ADDRESS=<public-user-address>` と `SIS_TRADE_XYZ_EXECUTION_STATE_COLLECTOR_ENABLED=1` が必要。
- Bitget demo read-only network smoke: `BITGET_DEMO_API_KEY`、`BITGET_DEMO_API_SECRET`、`BITGET_DEMO_PASSPHRASE` が必要。
- normal paper observation: 新しい trading day を含む evidence が必要。同日 artifact の再実行だけでは normal observation の日数は増えない。

外部入力が来た時は [NEXT_DIRECTION_CURRENT.md](NEXT_DIRECTION_CURRENT.md) の `External Input Restart Checklist` を読む。

## Source Of Truth

優先順位:

1. `src/`, `tests/`, `configs/`, `schemas/`, `scripts/`
2. CLI help: `uv run sis --help`
3. generated runtime artifacts under `data/`
4. tracked docs under `docs/`
5. `plan/` historical planning records
6. `docs/archive/` and `plan/archive/`

archive 配下は historical context です。現行判断の正本にはしません。

## Recommended Read Order

1. [CURRENT_STATE.md](CURRENT_STATE.md)
2. [REPO_CAPABILITIES_PLAIN_JA_2026-06-17.md](REPO_CAPABILITIES_PLAIN_JA_2026-06-17.md)
3. [CODE_STATUS.md](CODE_STATUS.md)
4. [IMPLEMENTED_SURFACES.md](IMPLEMENTED_SURFACES.md)
5. [NEXT_DIRECTION_CURRENT.md](NEXT_DIRECTION_CURRENT.md)
6. [backtest/README.md](backtest/README.md)
7. [strategy_review/README.md](strategy_review/README.md)
8. [strategy_review/OPERATOR_REVIEW_PACKET_RECIPE.md](strategy_review/OPERATOR_REVIEW_PACKET_RECIPE.md)
9. [research/ndx/README.md](research/ndx/README.md)
10. [strategy_lifecycle/README.md](strategy_lifecycle/README.md)
11. [OPERATIONS_RUNBOOK.md](OPERATIONS_RUNBOOK.md)
12. [plan/README.md](../plan/README.md)

## Verification

固定の pass count はこの文書に置かない。作業時点で次を再実行する。

```bash
uv run python -V
uv run sis --help
uv run python scripts/check_current_docs.py
./scripts/check
```

runtime artifact を更新する場合:

```bash
uv run sis phase-gate-review
uv run sis strategy-paper-observation-status
uv run sis refresh-operations-artifacts
```
