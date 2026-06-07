<!--
作成日: 2026-06-07_19:17 JST
更新日: 2026-06-07_19:17 JST
-->

# 01 Goal

## 1. 目的

この開発の目的は、`marketlens-strike` に **Layer 2.2 DAG Compiler** を追加することである。

ただし、2.2を単体で作らない。2.2が安全に成立するため、次の最小前段も同時に作る。

```text
Layer 0:
  Scope / Universe / Boundary

Layer 1:
  Seed Registry
  Mechanism Parts Library

Layer 2.0:
  Variable Inventory

Layer 2.1:
  Causal Role Assignment
  Temporal Availability

Layer 2.2:
  Core DAG Contract
  DAG Validator
  Forbidden Edge Linter
  Counter-DAG
  DAG Export / Report
```

## 2. 最終的に使える状態

今回の完了時点で、コーダー・研究者・LLMが次を実行できる状態にする。

```text
1. NASDAQ / NDX研究のSeedをYAMLで登録できる。
2. Seedに対応するMechanism PartsをYAMLで登録できる。
3. DAGに入れる変数をVariable Inventoryとして登録できる。
4. 変数に因果ロールと時点利用可能性を付与できる。
5. HYP-NDX-001 Core DAGをYAMLで定義できる。
6. DAGをPydanticでvalidateできる。
7. 未来情報、outcome→treatment、forbidden edgeをlinterで拒否できる。
8. Counter-DAGを必須artifactとして保存できる。
9. DAGをJSON / Mermaid / Markdown reportへ出力できる。
10. data requirement を後続feature builderへ渡せる。
```

## 3. 初期対象

初期対象は **NASDAQ単独** である。

```text
primary:
  - Nasdaq-100 / NDX
  - QQQ
  - NQ futures は将来追加候補

known factors:
  - SPY / SPX broad market
  - US rates / DGS10
  - SOX or SMH semiconductor proxy
  - VIX / VXN volatility regime
  - mega-cap basket
```

## 4. 初期Core DAG

最初に登録するCore DAGは1本だけ。

```text
HYP-NDX-001:
  NDX / QQQ Open Gap Residual
```

構造は次。

```text
SPY / broad market
DGS10 / rates
SMH / semiconductor
VIX or VXN / vol regime
Mega-cap basket
  -> Expected NDX Open Move

Actual QQQ Open Gap - Expected NDX Open Move
  -> Open Gap Residual

Open Gap Residual
  -> QQQ Open-to-Close Return
```

## 5. 完成扱いにしないもの

この開発は以下を完成扱いにしない。

```text
- alpha発見
- causal effect推定
- backtest成績
- paper-ready
- live-ready
- Trade[XYZ] readiness
- Bitget demo network-ready
- 注文候補生成
```

## 6. 判断

この開発は、Strategy Labやbacktestを直接強化する前段である。最初に「DAGを安全に作れる状態」を作り、その後にFeature Panel、Residual Builder、Strategy Lab Exportへ進む。

## 7. 成功の一文定義

```text
HYP-NDX-001を、YAML → validation → lint → counter-DAG → data requirements → Mermaid/report まで再現可能に生成できる。
```
