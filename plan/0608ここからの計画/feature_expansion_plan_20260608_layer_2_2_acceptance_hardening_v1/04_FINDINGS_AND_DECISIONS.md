<!--
作成日: 2026-06-08_19:23 JST
更新日: 2026-06-08_19:23 JST
-->

# 04_FINDINGS_AND_DECISIONS

## Finding 1: 旧ZIPを新規実装指示として渡すのは誤り

現Repoには、v2/v5で計画したLayer 2.2 foundationとExit Gate Review Harnessがすでに大部分実装されている。したがって、旧ZIPを「これを作って」と渡すと、重複実装や巻き戻しが起きる。

決定:

```text
旧ZIPは historical design background として使う。
現在の実装は、Repo code/tests/schemas/config/CLI helpを正本にする。
```

## Finding 2: Exit Gateの意味論に監査価値がある

現行`exit_gate.py`には以下の意味論を必ず固定する必要がある。

```text
APPROVE_2_3:
  second_review_required=false
  unresolved_human_decisions=[]
  blocker_count=0
  freeze_manifestあり

REVISE_2_2:
  freeze_manifestなし

REJECT_SEED:
  freeze_manifestなし
```

特に、以下は許容しない。

```text
APPROVE_2_3 + second_review_required=true
APPROVE_2_3 + freeze_manifestなし
REVISE_2_2 + freeze_manifestあり
REJECT_SEED + freeze_manifestあり
```

## Finding 3: HIGH findingの扱いは仕様として明確化が必要

推奨仕様:

```text
HIGH finding with human_decision_id and resolved:
  APPROVE_2_3可。ただしhigh_countは残す。

HIGH finding without human_decision_id:
  REVISE_2_2。なぜなら解消不能なHIGH findingは2.3へ進めないため。

HIGH finding with unresolved human_decision_id:
  REVISE_2_2。
```

## Finding 4: BLOCKERはhuman resolutionで通さない

推奨仕様:

```text
BLOCKER > 0:
  常に REVISE_2_2
  freeze_manifestなし
```

理由: BLOCKERを「人間が許容」として通すと、review gateの意味が崩れる。

## Finding 5: REJECT_SEEDは明示確認が必要

現行方針を維持する。

```text
overall_decision=REJECT_SEED だけでは即REJECTしない。
causal_misspecification / temporal_leakage 等の重大findingにhuman resolutionがある場合だけ REJECT_SEED。
それ以外は REVISE_2_2。
```
