# Live Evidence Runner Hardening

## 目的

`scripts/refresh_live_evidence.sh` は live evidence 取得から report 再生成までを一気に流せるが、現状は「今走らせるべきか」「最低限の収集量があるか」を途中で止められない。ここでは runner を運用向けに強化する仕様を定義する。

## 現状の課題

- 推奨 live window 外でもそのまま収集と report 更新に進めてしまう。
- pricing / metadata / raw quote がほぼ空でも後段の normalize や Go/No-Go へ進んでしまう。
- `diagnose-quotes` が venue 一括実行なので、`QQQ` / `SPY` / `XAU` のどこに問題があるか追いづらい。
- shell 版と PowerShell 版の拡張方針が未定義で、将来 drift しやすい。

## 目標動作

runner は次の順で動く。

1. 引数と option を検証する。
2. `uv` / `bun` の利用可否を確認する。
3. `next-live-window` で `QQQ` / `SPY` / `XAU` の推奨枠を表示する。
4. `--dry-run` ならここで終了する。
5. 推奨枠外なら `--force` なしでは停止する。
6. `bun run gtrade:collect-window` で pricing websocket と trading variables を収集する。
7. sidecar pricing / sidecar metadata / raw quotes の行数を確認する。
8. 収集量が足りれば quote 再生成と report 更新へ進む。
9. `diagnose-quotes` は symbol 別に出す。
10. 最後に decision と主要 artifact を summary 表示する。

## CLI 契約

shell:

```bash
bash scripts/refresh_live_evidence.sh [duration_minutes] [metadata_interval_seconds] [--dry-run] [--force]
```

PowerShell:

```powershell
./scripts/refresh_live_evidence.ps1 [-DurationMinutes 120] [-MetadataIntervalSeconds 60] [-DryRun] [-Force]
```

意味:

- `duration_minutes`
  - 収集時間。既定値は `120`
- `metadata_interval_seconds`
  - trading variables 取得間隔。既定値は `60`
- `--dry-run` / `-DryRun`
  - preflight だけ表示して終了する
- `--force` / `-Force`
  - 推奨 live window 外でも収集を続行する

## Preflight と停止条件

通常実行では、`next-live-window` の推奨開始・終了時刻を見て「今が推奨収集帯か」を判定する。推奨帯の外なら停止し、利用者に `--force` を促す。

想定メッセージ:

```txt
ERROR:
Current time is outside recommended gTrade live window.
Use --force to collect anyway.
```

`--dry-run` では停止条件の判定結果も表示するが、データ収集や artifact 更新は一切行わない。

## 収集後の最低行数チェック

収集直後に、少なくとも次を確認する。

- gTrade pricing rows `> 0`
- gTrade metadata rows `>= expected_snapshots * 0.8`
- raw quote rows `> 0`

`expected_snapshots` は `duration_minutes * 60 / metadata_interval_seconds` で計算する。閾値未満なら normalize 以降へ進まず終了する。

想定メッセージ:

```txt
ERROR:
Insufficient gTrade metadata rows.
Expected at least 96, got 12.
```

## Diagnostics 出力

`diagnose-quotes` は少なくとも次の 3 回を実行する。

```bash
uv run sis diagnose-quotes --venue gtrade --symbol QQQ
uv run sis diagnose-quotes --venue gtrade --symbol SPY
uv run sis diagnose-quotes --venue gtrade --symbol XAU
```

これにより、index session と commodity session のズレを出力上で分離できる。

## 最終 Summary

完了時には、人が次に判断するための短い summary を表示する。

表示項目:

- quotes / normalized / cost matrix / go-no-go / evidence の主要 path
- global decision
- symbol 別 diagnostics の主要値
- `--force` 利用有無

表示例:

```txt
Live Evidence Refresh Summary

Artifacts:
  quotes: data/raw/quotes/gtrade/2026-05-22.jsonl
  normalized: data/normalized/quotes.parquet
  cost_matrix: data/research/venue_cost_matrix.csv
  go_no_go: data/research/go_no_go_report.md

Decision:
  CONDITIONAL_GO_NEEDS_LIVE_WINDOW

Diagnostics:
  QQQ stale_rate=0.01 tradable_rate=0.98 missing_mark=0
  SPY stale_rate=0.01 tradable_rate=0.98 missing_mark=0
  XAU stale_rate=0.02 tradable_rate=0.95 missing_mark=0
```

## 実装順

1. shell 版に `--dry-run` と symbol 別 diagnostics を追加する。
2. shell 版に window 判定と row count gate を追加する。
3. 最終 summary を追加する。
4. PowerShell 版を同じ挙動に揃える。
5. runbook と smoke test を更新する。

## 非目標

- 新しい market calendar ルールの追加
- Go/No-Go 算出ロジックそのものの変更
- live data を fixture として repository に保存すること
- scheduler `schedule_live_evidence.sh` の仕様変更
