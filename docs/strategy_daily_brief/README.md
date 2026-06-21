<!--
作成日: 2026-06-19_01:09 JST
更新日: 2026-06-21_21:12 JST
-->

# Strategy Daily Brief

## 結論

`strategy-daily-brief` は、`data/` 配下の strategy artifact を走査し、今日見るべきものを 1 枚の JSON / Markdown にまとめる first slice です。

これは permission artifact ではありません。paper order、live order、wallet、signing、exchange write は実行しません。

## Command

```bash
uv run sis strategy-daily-brief \
  --data-dir data \
  --out data/reports/strategy_daily_brief
```

出力:

```text
data/reports/strategy_daily_brief/
  strategy_daily_brief.json
  strategy_daily_brief.md
```

## 見るもの

`strategy_daily_brief.v1` は次を一覧化します。Markdown summary には Crypto Perp gate / truth-cycle follow-up の件数も出ます。

- `broken_artifact`: JSON として読めない、または `schema_version` がない artifact。
- `pending_human_review`: `READY_FOR_HUMAN_*`、`READY_FOR_HUMAN_MICRO_LIVE_REVIEW`、`READY_FOR_HUMAN_SCALE_REVIEW`、`READY_FOR_HUMAN_NEXT_SCALE_REVIEW`、`LIVE_OBSERVATION_INGESTED`、`BLOCKED_CANARY`、`HUMAN_REVIEW_REQUIRED` など、人間判断が必要な artifact。
- `crypto_perp_gate_follow_up`: Crypto Perp tournament gate の `READY_FOR_HUMAN_TINY_LIVE_REVIEW`、`NEEDS_ACTUAL_CASH`、`NEEDS_MORE_EVIDENCE`、`HOLD_NO_TRADE_LEADS`、`REVISE_OR_RETIRE` など、次に読むべき gate artifact。
- `crypto_perp_truth_cycle_follow_up`: Crypto Perp truth-cycle status の `cycle_status`、先頭の `next_steps`、`stop_reasons`、先頭の `stage_checklist` blocker を日次確認へ出す artifact。
- `normal_paper_gap`: normal paper の fills / trading days gap が残っている stage decision。
- `drift_review_needed`: `READY_FOR_DRIFT_REVIEW` の stage decision。
- `learning_request_pending`: revision request / authoring update handoff の人間対応待ち。
- `boundary_violation`: live / wallet / signing / exchange write 系 true flag が混入した artifact。

## 境界

- Daily Brief は読み取り索引です。
- `total_item_count=0` は paper pass や live readiness ではありません。
- `pending_human_review` や `drift_review_needed` は次に読むべき artifact の表示であり、自動実行指示ではありません。
- `crypto_perp_gate_follow_up` が `READY_FOR_HUMAN_TINY_LIVE_REVIEW` を示す場合でも、Daily Brief の reason は `separate human approval is required before any tiny live measurement; this is not live execution permission` として読みます。tiny live 実行許可ではありません。
- `crypto_perp_truth_cycle_follow_up` が `READY_FOR_HUMAN_TINY_LIVE_REVIEW` を示す場合も、別承認待ちでありlive実行許可ではありません。
- `crypto_perp_truth_cycle_follow_up` は次に読むべき欠損や停止理由の索引です。`first stage blocker: probe_audit via --probe-audit` のような表示は、先に埋める artifact / CLI option を示すだけで、public network、credential、order、live 実行許可ではありません。
- `data/` 配下は runtime / generated state です。fresh checkout では空または存在しないことがあります。

## Verification

```bash
uv run pytest tests/strategy_daily_brief -q
uv run sis strategy-daily-brief --help
uv run python scripts/check_current_docs.py
```
