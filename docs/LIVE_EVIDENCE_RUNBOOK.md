# Live Evidence Runbook

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

PowerShell 環境では以下:

```powershell
./scripts/refresh_live_evidence.ps1 -DurationMinutes 120 -MetadataIntervalSeconds 60
```

## 実行内容

1. `bun run collect:window` で pricing websocket と trading-variables を同時収集
2. `uv run sis log-quotes --venue gtrade --replace` で pricing + metadata を統合
3. `uv run sis normalize-quotes`
4. `uv run sis build-cost-matrix`
5. `uv run sis build-backtest`
6. `uv run sis diagnose-quotes`
7. `uv run sis check-go-no-go`
8. `uv run sis build-evidence-card`
9. `uv run sis validate-artifacts --strict`

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
- schema違反:
  - `uv run sis validate-artifacts --strict` の指摘パスを修正して再実行
