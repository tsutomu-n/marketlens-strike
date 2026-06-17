<!--
作成日: 2026-06-17_10:00 JST
更新日: 2026-06-17_12:00 JST
-->

# Next Direction Current

## 結論

現時点の現実的な方向は、backtest-first / venue-neutral を維持しながら、Strategy Review の人間判断記録と paper observation の通常threshold状態を次段検証の土台にすることです。

これは確定ロードマップではありません。実装済み surface と未実装候補を混ぜず、次に狙いやすい方向、追加候補、優先しないことを分けるための current doc です。

## 正本

この文書は次を正本として読む:

- code: `src/`, `tests/`, `configs/`, `schemas/`, `scripts/`
- CLI help: `uv run sis --help`, `uv run sis strategy-review-record --help`
- current docs: `docs/CURRENT_STATE.md`, `docs/IMPLEMENTED_SURFACES.md`, `docs/REPO_CAPABILITIES_CURRENT_2026-06-16.md`, `docs/strategy_review/README.md`
- plan handoff: `plan/0609ここからの計画/03_venue_read_only_capability_probe/`
- implementation sequence: `docs/NEXT_IMPLEMENTATION_SEQUENCE_CURRENT.md`

次は current proof として扱わない:

- stale plan
- historical audit
- `data/` runtime artifact
- old pass count / public command count snapshot

## Near-Term Practical Direction

1. Backtest-first / venue-neutral を継続する。
2. Strategy Review の `strategy-review-build` / `strategy-review-record` を、既存 artifact を人間が読み、判断記録を残すための土台として使う。
3. `PAPER_OBSERVATION_CANDIDATE` は validation candidate としてのみ扱い、paper 実行許可や paper intent 生成許可とは読まない。
4. paper observation は normal threshold と smoke threshold を分けて読む。smoke pass は normal paper observation pass ではない。
5. future venue は `venue-read-only-probe` dogfood 済みで、現時点では `NO_ACTION`。schema や paper path は広げない。

## Implementation-Ready Candidate

### Strategy Review dogfood

すぐ実行できる候補は、`strategy-review-build` / `strategy-review-record` の dogfood です。

この slice で許すこと:

- `data/strategy_reviews/<review_id>/review.md` の生成
- `data/strategy_reviews/<review_id>/review_manifest.json` の生成
- `operator_review.yaml` の記録と `--validate-existing`
- tracked dogfood decision の作成
- paper / live permission ではないことの明示

この slice で許さないこと:

- network API call
- credentials
- paper order 実行
- live execution enablement
- `PAPER_OBSERVATION_CANDIDATE` を paper permission と読むこと

### Paper observation status artifact

次に実装価値がある候補は、Strategy Lifecycle 用の paper observation status artifact です。

目的:

- normal session と smoke session を分けて読む。
- `NEEDS_MORE_PAPER_OBSERVATION` と smoke `PASS_PAPER_OBSERVATION_REVIEW` を混同しない。
- lifecycle の `CONTINUE_PAPER_OBSERVATION` を live readiness と読まない。

実装候補:

- command: `strategy-paper-observation-status`
- output: `data/research/strategy_lifecycle/paper_observation_status.json`
- report: `data/reports/paper_observation_status.md`

## Needs A New Explicit Plan

次は、進める前に別の明示計画が必要です。

- paper bridge validation
- Strategy Case registry
- UI
- credentialed Bitget read-only network probe
- credentialed Hyperliquid read-only network probe
- Bitget demo order lifecycle
- production venue schema widening

## Completed / Paused Candidate

### `venue-read-only-probe`

`venue-read-only-probe` は実装済みで、dogfood decision は `NO_ACTION`。

これは Bitget / Hyperliquid production readiness、credentialed read-only network readiness、paper readiness、live readiness を証明しない。

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
