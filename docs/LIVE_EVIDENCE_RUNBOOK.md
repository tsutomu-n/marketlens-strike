# Live Evidence Runbook

runner の設計メモは [docs/LIVE_EVIDENCE_RUNNER_HARDENING.md](/home/tn/projects/marketlens-strike/docs/LIVE_EVIDENCE_RUNNER_HARDENING.md) を参照。

## 目的

gTrade tradable session中に quote window を取得し、`stale_rate` / `tradable_rate` blocker を解消する。

## 実行前確認

```bash
just check
uv run sis next-live-window --venue gtrade --symbol QQQ
uv run sis next-live-window --venue gtrade --symbol SPY
uv run sis next-live-window --venue gtrade --symbol XAU
```

確認ポイント:
- `recommended_start_jst` 以降に実行開始できること
- 取得時間は最低 60 分（推奨 120 分）

## 実行

```bash
bash scripts/refresh_live_evidence.sh 120 60
```

引数:
- 第1引数: 取得分数（デフォルト 120）
- 第2引数: metadata 間隔秒（デフォルト 60）

option:
- `--dry-run`: preflight だけ表示して終了する
- `--force`: 推奨 live window 外でも収集を続行する

例:

```bash
bash scripts/refresh_live_evidence.sh --dry-run
bash scripts/refresh_live_evidence.sh 120 60 --force
```

PowerShell 環境では以下:

```powershell
./scripts/refresh_live_evidence.ps1 -DurationMinutes 120 -MetadataIntervalSeconds 60
```

指定時刻に開始したい場合:

```bash
bash scripts/schedule_live_evidence.sh 22:45 120 60
```

日付つきの絶対指定もできる:

```bash
bash scripts/schedule_live_evidence.sh 2026-05-26T22:45 120 120
uv run python scripts/plan_live_evidence_run.py
uv run python scripts/plan_live_evidence_run.py --schedule
```

この scheduler は JST の `HH:MM` または `YYYY-MM-DDTHH:MM` を受け取る。
- `HH:MM`: 指定時刻が過ぎている場合は翌日の同時刻に回す
- `YYYY-MM-DDTHH:MM`: その日時に一度だけ待機し、過去日時は拒否する

`plan_live_evidence_run.py` は `QQQ` / `SPY` / `XAU` の共通推奨開始時刻を計算し、週末や市場休場日でも「次に3銘柄まとめて取るべき時刻」を出す。
ログは `logs/live_evidence/live_evidence_YYYYMMDD_HHMM.log` に出力する。

## 実行内容

1. `next-live-window` で QQQ / SPY / XAU の推奨収集枠を表示
2. `bun run gtrade:collect-window` で pricing websocket と trading-variables を同時収集
3. `uv run sis log-quotes --venue gtrade --replace` で pricing + metadata を統合
4. `uv run sis normalize-quotes`
5. `uv run sis build-cost-matrix`
6. `uv run sis diagnose-quotes --venue gtrade --symbol QQQ|SPY|XAU`
7. `uv run sis build-backtest`
8. `uv run sis check-go-no-go`
9. `uv run sis build-evidence-card`
10. `uv run sis validate-artifacts --strict`

実際の runner は次の安全策を入れている:

1. `uv` / `bun` の存在確認
2. `next-live-window` による `QQQ` / `SPY` / `XAU` の推奨枠表示
3. `--dry-run` なら収集せず終了
4. 推奨枠外では `--force` なしなら停止
5. sidecar metadata / pricing の増分行数チェック
6. `log-quotes --replace` 後の raw quote 行数チェック
7. `diagnose-quotes --venue gtrade --symbol ...` を symbol 別に実行
8. 最後に artifact path と decision の summary を表示

## 生成物

- `data/raw/sidecar/gtrade/YYYY-MM-DD.jsonl`
- `data/raw/sidecar/gtrade-pricing/YYYY-MM-DD.jsonl`
- `data/raw/quotes/gtrade/YYYY-MM-DD.jsonl`
- `data/normalized/quotes.parquet`
- `data/research/venue_cost_matrix.csv`
- `data/research/backtest_metrics.json`
- `data/research/go_no_go_report.md`
- `data/evidence/evidence_card_*.json`

## 判定

- `GO`: stale/tradable が閾値を満たし、after-cost backtest が成立
- `CONDITIONAL_GO_NEEDS_LIVE_WINDOW`: 実装は成立だが live window が不足
- `NO_GO_*`: コスト・鮮度・セッション条件で不成立

## blocker別の対応

- stale_rate が高い:
  - open session 中に再取得
  - pricing websocket 受信が継続しているか確認
- tradable_rate が低い:
  - `next-live-window` の推奨枠で再取得
  - index/commodity のセッション種別が一致しているか確認
- `Current time is outside recommended gTrade live window` で止まる:
  - 推奨枠まで待って再実行
  - 意図的に閉場帯を取りたい場合だけ `--force` を付ける
- `Insufficient gTrade metadata/pricing rows` で止まる:
  - websocket / backend 接続状態を確認
  - 収集時間と metadata 間隔が極端でないか確認
- schema違反:
  - `uv run sis validate-artifacts --strict` の指摘パスを修正して再実行
