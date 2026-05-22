# 15. Coder Handoff Checklist

## 実装前確認

- [ ] 目的を理解: 売買Botではなく研究用Go/No-Go Engine
- [ ] 短期スキャルピング禁止を理解
- [ ] gTrade先行、Ostium後続を理解
- [ ] raw保存の重要性を理解
- [ ] mark/index/bid/ask/oracle_tsを混同しない

## 必須成果物

- [ ] `data/registry/gtrade_instrument_registry.json`
- [ ] `data/raw/quotes/gtrade/YYYY-MM-DD.jsonl`
- [ ] `data/normalized/quotes.parquet`
- [ ] `data/research/venue_cost_matrix.csv`
- [ ] `data/research/go_no_go_report.md`
- [ ] `data/evidence/evidence_card_*.json`

## 受け入れ基準

- [ ] `uv run sis --help` が動く
- [ ] `uv run sis probe gtrade` が動く
- [ ] `npm run gtrade:probe` がJSONLを出す
- [ ] `uv run sis normalize-quotes` がParquetを出す
- [ ] `uv run sis check-go-no-go` がMarkdownを出す
- [ ] `1m` と `5m` がBLOCKされる

## 禁止事項

- [ ] 初期実装で実注文しない
- [ ] 短期スキャルピング実装しない
- [ ] 新venueを増やさない
- [ ] 個別株へ広げない
- [ ] raw payloadを捨てない
- [ ] mark/indexを1つのpriceに潰さない
