<!--
作成日: 2026-06-17_10:00 JST
更新日: 2026-06-17_10:00 JST
-->

# Next Direction Current

## 結論

現時点の現実的な方向は、backtest-first / venue-neutral を維持しながら、Strategy Review の人間判断記録を次段検証の土台にし、future venue は local / fixture-first の read-only capability probe から始めることです。

これは確定ロードマップではありません。実装済み surface と未実装候補を混ぜず、次に狙いやすい方向、追加候補、優先しないことを分けるための current doc です。

## 正本

この文書は次を正本として読む:

- code: `src/`, `tests/`, `configs/`, `schemas/`, `scripts/`
- CLI help: `uv run sis --help`, `uv run sis strategy-review-record --help`
- current docs: `docs/CURRENT_STATE.md`, `docs/IMPLEMENTED_SURFACES.md`, `docs/REPO_CAPABILITIES_CURRENT_2026-06-16.md`, `docs/strategy_review/README.md`
- plan handoff: `plan/0609ここからの計画/03_venue_read_only_capability_probe/`

次は current proof として扱わない:

- stale plan
- historical audit
- `data/` runtime artifact
- old pass count / public command count snapshot

## Near-Term Practical Direction

1. Backtest-first / venue-neutral を継続する。
2. Strategy Review の `strategy-review-build` / `strategy-review-record` を、既存 artifact を人間が読み、判断記録を残すための土台として使う。
3. `PAPER_OBSERVATION_CANDIDATE` は validation candidate としてのみ扱い、paper 実行許可や paper intent 生成許可とは読まない。
4. future venue は schema や paper path を広げる前に、local / fixture-first の read-only capability probe で「何を知っていて、何を試していないか」を artifact 化する。

## Implementation-Ready Candidate

### `venue-read-only-probe`

最も実装準備が進んでいる候補は、`plan/0609ここからの計画/03_venue_read_only_capability_probe/` です。

この slice で許すこと:

- local / fixture-first の probe model
- `bitget_futures`, `hyperliquid_perp`, `bitget_demo`, `trade_xyz` の capability / suitability 状態の整理
- JSON summary と Markdown report の生成
- default path で external API、credentials、wallet、exchange write、live order を使わないことの明示

この slice で許さないこと:

- network API call
- credentialed probe
- new credential name
- account / balance / position / fill / order read
- order submit / cancel / close
- `VenueId` widening
- Strategy Lab schema widening
- paper execution enablement
- live execution enablement
- dependency addition

## Needs A New Explicit Plan

次は、進める前に別の明示計画が必要です。

- paper bridge validation
- Strategy Case registry
- UI
- credentialed Bitget read-only network probe
- credentialed Hyperliquid read-only network probe
- Bitget demo order lifecycle
- production venue schema widening

## Not On Current Roadmap

次は現行 roadmap には入れません。実施するなら別計画、承認、stop condition が必要です。

- production live trading
- wallet / signing
- exchange write
- Bitget futures / Hyperliquid perp を Strategy Lab schema に入れること
- backtest pass から paper ready / live ready を主張すること
- `READ_ONLY_GO` を live ready と読むこと
- `catalog known` を venue enabled と読むこと
- `read-only probe` を network readiness と読むこと

## 誤読防止

- `計画あり` は `実装決定` ではない。
- `catalog known` は `venue enabled` ではない。
- `read-only probe` は `network readiness` ではない。
- `PAPER_OBSERVATION_CANDIDATE` は paper 実行許可ではない。
- `READ_ONLY_GO` は live ready ではない。
- fixed public command count は current truth ではない。確認時点で `uv run sis --help` を再実行する。
