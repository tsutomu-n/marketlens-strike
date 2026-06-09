<!--
作成日: 2026-06-08_19:23 JST
更新日: 2026-06-08_19:23 JST
-->

# 01_GOAL

## 目的

現在の`marketlens-strike`に実装済みのLayer 2.2 DAG foundation / Exit Gate Review Harnessを、2.3へ進める前に受入監査し、曖昧なExit Gate意味論をなくす。

## 完成扱い

以下がすべて満たされたら完成とする。

```text
1. 現RepoのLayer 2.2実装がcode truthとして再確認されている。
2. research-layer22-validate / export / review-pack が通る。
3. review-import がpack_hash / evidence_refs / severity_countsを拒否できる。
4. exit-gate が APPROVE_2_3 / REVISE_2_2 / REJECT_SEED を一貫して出せる。
5. APPROVE_2_3 の場合だけ freeze manifest が出る。
6. APPROVE_2_3 の場合 second_review_required=false が保証される。
7. second_review_required=true の場合、2.3へは進めない。
8. BLOCKER / unresolved human decision / current pack hash mismatch は確実に止まる。
9. tests/research と ./scripts/check が通る。
```

## ユーザーにとって使える状態

ユーザーは次を安全に判断できる。

```text
APPROVE_2_3:
  2.2をfreezeし、別計画で2.3 Feature / Residual Builderへ進める。

REVISE_2_2:
  Core DAG / roles / temporal availability / counter-DAG / review JSONを修正する。

REJECT_SEED:
  HYP-NDX-001を一旦棄却し、別Seedへ移る。
```

## 目的ではないもの

```text
利益検証
alpha証明
feature-panel readiness
residual correctness
Strategy Lab export readiness
backtest readiness
paper readiness
live readiness
```
