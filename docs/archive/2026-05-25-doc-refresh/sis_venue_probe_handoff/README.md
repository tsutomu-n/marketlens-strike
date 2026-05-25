# sis-venue-probe 実装引き継ぎ資料

## 目的

`Ostium / gTrade` を対象に、`QQQ・SPY・XAU` を `4時間〜3日` の短期スイングで研究できるかを判定するための **Venue Research & Go/No-Go Engine** を実装する。

売買Botではない。最初に作るのは、実測調査・ログ保存・コスト集計・Go/No-Go判定ツールである。

## 固定方針

- 対象venue: `gTrade`, `Ostium`
- 対象商品: `QQQ`, `SPY`, `XAU`
- 主時間軸: `4h`, `1d`, `3d`
- 補助時間軸: `30m`, `5d`
- 禁止: `1s`, `5s`, `15s`, `1m`, `5m` の短期スキャルピング
- 初期実装: gTradeを先行し、Ostiumは未確定項目をprobeで潰す
- 規制・税務・利用規約: 研究目的のため、本資料では判断対象外

## ZIP内の構成

```txt
sis_venue_probe_handoff/
  docs/                         # 実装仕様書
  schemas/                      # JSON Schema
  configs/                      # policy / seed registry / env例
  templates/                    # report / matrix / evidence雛形
  starter_python/               # Python側の最小実装雛形
  starter_ts_gtrade_sidecar/    # gTrade SDK sidecar雛形
```

## 実装者が最初に読む順番

1. `docs/00_executive_brief.md`
2. `docs/01_scope_requirements.md`
3. `docs/04_architecture.md`
4. `docs/07_gtrade_sidecar_spec.md`
5. `docs/13_implementation_tasks.md`
6. `starter_python/README.md`
7. `starter_ts_gtrade_sidecar/README.md`

## 最初のDone条件

```txt
1. gTrade SPY/QQQ/XAU registry生成
2. gTrade trading-variables取得
3. gTrade sidecarが正規化JSONLを出力
4. Python側がJSONLをParquetへ変換
5. scalping_policyで1m/5mをBLOCK
6. venue_cost_matrix.csvを生成
7. go_no_go_report.mdを生成
```
