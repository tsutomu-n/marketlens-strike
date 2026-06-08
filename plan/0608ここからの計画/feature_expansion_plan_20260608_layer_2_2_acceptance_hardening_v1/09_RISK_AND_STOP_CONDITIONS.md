<!--
作成日: 2026-06-08_19:23 JST
更新日: 2026-06-08_19:23 JST
-->

# 09_RISK_AND_STOP_CONDITIONS

## 主要リスク

### R1: 古いZIPを正本として再実装してしまう

対策:

```text
旧ZIPはhistorical design backgroundと明記する。
現Repoのcode/tests/config/schemas/CLI helpを正本にする。
```

### R2: second_review_required=trueなのにAPPROVE_2_3してしまう

対策:

```text
APPROVE_2_3 implies second_review_required=false をテストで固定する。
```

### R3: freeze manifestが不適切に出る

対策:

```text
freeze manifestはAPPROVE_2_3のみ。
REVISE_2_2 / REJECT_SEEDでは出さない。
```

### R4: LLMレビューに過剰依存する

対策:

```text
LLMはmanual review artifactであり、コード側のvalidator/importer/exit gateで拘束する。
LLM APIは導入しない。
```

### R5: 2.3へ進みたくなる

対策:

```text
このPRでは2.3へ進まない。
APPROVE_2_3が出た後、別計画で2.3を設計する。
```

## Stop Conditions

以下が必要になったら停止し、仕様確認に戻る。

```text
- pyproject.toml / uv.lock変更
- external API / credentials
- Strategy Lab schema変更
- paper/live/order path変更
- feature panel生成
- residual calculation
- backtest開始
- configs/research_layer_2_2/ndx/*.yamlの大幅改変
- current docsとコードが大きく矛盾
```
