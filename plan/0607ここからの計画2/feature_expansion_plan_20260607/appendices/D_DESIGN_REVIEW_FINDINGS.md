<!--
作成日: 2026-06-07_20:25 JST
更新日: 2026-06-07_20:25 JST
-->

# Appendix D: Design Review Findings

## 採用した修正

### 1. 2.2単体ではなく前段contract込みにする

理由:

```text
DAGだけ作ると、node / role / proxy / temporal availability の前提が曖昧になる。
```

採用:

```text
Scope → Seed → Mechanism Parts → Data Sources → Variable Inventory → Causal Roles → Temporal Availability → Core DAG
```

### 2. 2.2は汎用、NDXはconfig専用にする

採用:

```text
src/sis/research/dag/           汎用
src/sis/research/hypothesis/    汎用
configs/research_layer_2_2/ndx/ NDX専用
```

### 3. NDX / QQQ / NQを分離する

採用:

```text
NDX: index concept
QQQ: observed ETF proxy
NQ: optional futures price discovery proxy
```

### 4. Index methodology部品を追加する

採用:

```text
NDX_INDEX_METHODOLOGY
NDX_WEIGHT_CAP_PRESSURE
NDX_FAST_ENTRY_FLOW
NDX_REBALANCE_FLOW
```

Phase A/Bでは計算しない。Mechanism partとcounter-DAGとして持つ。

### 5. Counter-DAGを増やす

最低8本。推奨12本。

### 6. Linter rule v2を追加する

outcome-to-treatmentだけでは弱いので、role consistency、temporal layer、data source tier、counter-DAG minimumまで見る。

### 7. 初期PRでは外部API禁止

Phase A/Bはartifact contractとlinterだけ。実データ取得はPhase C以降。

## 不採用にした案

### 1. 最初からfeature panelを作る

不採用理由:

```text
DAG前提が固まる前にデータ計算へ進むと、バックテスト沼に戻る。
```

### 2. 最初からStrategy Lab exportする

不採用理由:

```text
2.2と後段評価が混ざる。
```

### 3. 最初からDoWhy / causal-learnを入れる

不採用理由:

```text
依存とデータが必要。初期2.2はDAG artifactとlinterが先。
```

### 4. NQ futuresを初期必須にする

不採用理由:

```text
データ取得元が未決定。Phase A/Bではdeferred optional。
```
