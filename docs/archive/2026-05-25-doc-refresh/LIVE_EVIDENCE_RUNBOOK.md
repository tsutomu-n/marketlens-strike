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
uv run python scripts/run_live_evidence.py --duration-minutes 120 --metadata-interval-seconds 60
```

主要 option:
- `--duration-minutes`: 取得分数（デフォルト 120）
- `--metadata-interval-seconds`: metadata 間隔秒（デフォルト 60）
- `--dry-run`: preflight だけ表示して終了する
- `--force`: 推奨 live window 外でも収集を続行する
- `--run-id`: run 識別子を固定したい時に使う
- `--manifest-path`: manifest JSON の出力先を固定したい時に使う

互換 wrapper:
- `bash scripts/refresh_live_evidence.sh ...`
- `./scripts/refresh_live_evidence.ps1 ...`

例:

```bash
uv run python scripts/run_live_evidence.py --dry-run
uv run python scripts/run_live_evidence.py --duration-minutes 120 --metadata-interval-seconds 60 --force
```

PowerShell 環境では以下:

```powershell
./scripts/refresh_live_evidence.ps1 --duration-minutes 120 --metadata-interval-seconds 60
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
ログは `logs/live_evidence/live_evidence_YYYYMMDD_HHMM.log`、manifest は `logs/live_evidence/manifests/live_evidence_*.json` に出力する。

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
11. 終了後 180 秒待って Markdown / HTML / follow-up report を自動生成

実際の runner は次の安全策を入れている:

1. `uv` / `bun` の存在確認
2. `next-live-window` による `QQQ` / `SPY` / `XAU` の推奨枠表示
3. `--dry-run` なら収集せず終了
4. 推奨枠外では `--force` なしなら停止
5. 同時実行を file lock で拒否
6. sidecar metadata / pricing の増分行数チェック
7. 軽微な収集不足や一時失敗には限定 retry を行う
8. `log-quotes --replace` 後の raw quote 行数チェック
9. `diagnose-quotes --venue gtrade --symbol ...` を symbol 別に実行
10. run manifest に step status / retry / counts / failure reason を記録
11. 最後に artifact path と decision の summary を表示

## 生成物

- `data/raw/sidecar/gtrade/YYYY-MM-DD.jsonl`
- `data/raw/sidecar/gtrade-pricing/YYYY-MM-DD.jsonl`
- `data/raw/quotes/gtrade/YYYY-MM-DD.jsonl`
- `data/normalized/quotes.parquet`
- `data/research/venue_cost_matrix.csv`
- `data/research/backtest_metrics.json`
- `data/research/go_no_go_report.md`
- `data/evidence/evidence_card_*.json`
- `logs/live_evidence/manifests/live_evidence_*.json`
- `docs/live_evidence_reports/live_evidence_report_*.md`
- `docs/live_evidence_reports/live_evidence_report_*.html`
- `docs/live_evidence_reports/live_evidence_followup_*.md`

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
- `partial_failed`:
  - manifest の failed step と retry 回数を確認
  - raw / diagnostics / follow-up を見て失敗箇所だけ修正して再実行
- schema違反:
  - `uv run sis validate-artifacts --strict` の指摘パスを修正して再実行
