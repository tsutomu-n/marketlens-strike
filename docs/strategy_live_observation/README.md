<!--
作成日: 2026-06-19_01:31 JST
更新日: 2026-06-19_01:31 JST
-->

# Strategy Live Observation

## 結論

`strategy-live-observation-ingest` は、live execution を実行する command ではありません。

既存の micro live canary audit bundle と任意の Markdown report / micro live plan を read-only で読み、`strategy_live_observation_manifest.v1` JSON と Markdown summary を作ります。

## Command

```bash
uv run sis strategy-live-observation-ingest \
  --strategy-id ndx-breakout-001 \
  --audit-bundle data/ops/micro_live_audit_bundle.json \
  --report data/reports/micro_live_safety_report.md \
  --micro-live-plan data/strategy_micro_live_plans/ndx-breakout-001/strategy_micro_live_plan.json \
  --out data/strategy_live_observations
```

## Output

```text
data/strategy_live_observations/<strategy-id>/
  strategy_live_observation_manifest.json
  strategy_live_observation.md
```

## 読むもの

- micro live canary status。
- blocked reasons。
- symbol、side、quantity、notional、leverage。
- schedule cancel、order submit、order status、cancel、close status。
- filled / rejected / canceled / close submitted の観測。
- account snapshot の有無、equity、available cash。

account address は出力 manifest に引き継がない。

## Boundary

- live order を実行しない。
- paper runtime observation と混ぜない。
- scale-up permission ではない。
- production live readiness ではない。
- wallet、signing、exchange write は使わない。

## Verification

```bash
uv run pytest tests/strategy_live_observation tests/test_micro_live_canary.py -q
uv run sis strategy-live-observation-ingest --help
uv run python scripts/check_current_docs.py
```
