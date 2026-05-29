# 08 Migration Branching And Commit Plan

## Branch Naming

```text
feature/strategy-research-lab-sl0
feature/strategy-signals-artifact-sl1
feature/evaluation-trial-ledger-sl2
feature/backtest-fixed-horizon-sl3
feature/trade-candidate-pack-sl4
feature/promotion-decision-sl5
feature/paper-intent-preview-sl6
feature/paper-from-intents-sl7
feature/retire-legacy-signals-sl8
```

## Commit Style

各PRは小commitで分ける。

例 SL0:

```text
chore: add strategy research lab package skeleton
feat: add symbol binding and strategy experiment spec models
feat: add data and feature snapshot manifests
feat: add strategy run profile guards
test: cover strategy lab specs and run profile guards
docs: add strategy research lab migration notes
```

## No Squash Until Reviewed

PRレビュー時は差分の意味を追いやすいよう、最初はsquashしない。

## Migration Principle

```text
- 新pathを作る
- 新pathにテストを足す
- 新pathをartifactへ接続する
- 旧pathをlegacy exportに落とす
- 最後に旧pathをactiveから外す
```

## Required Commands Before Merge

```bash
uv run ruff check .
uv run pyrefly check
uv run pytest -q
./scripts/check
uv run sis validate-artifacts --strict
uv run sis phase-gate-review
```
