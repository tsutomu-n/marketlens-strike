<!--
作成日: 2026-06-07_20:25 JST
更新日: 2026-06-07_20:25 JST
-->

# 01 Goal

## 目的

`marketlens-strike` に **Layer 2.2 Research DAG Compiler** を追加する。

目的は、NASDAQ単独研究の最初の仮説である `HYP-NDX-001 Open Gap Residual` を、売買ロジックではなく **研究仮説artifact** として定義・検査・出力できるようにすること。

## 完成扱いにする状態

次がすべてできれば、今回の機能拡張は完成扱いにする。

```text
1. NDX研究scopeを YAML で定義できる。
2. Seed registry を YAML で定義できる。
3. Mechanism parts を YAML で定義できる。
4. Data source contract を YAML で定義できる。
5. Variable inventory を YAML で定義できる。
6. Causal roles を YAML で定義できる。
7. Temporal availability を YAML で定義できる。
8. Core DAG を YAML で定義できる。
9. Core DAG を Pydantic model で validate できる。
10. Core DAG を linter で検査できる。
11. HYP-NDX-001 の counter-DAG を保存できる。
12. DAG から data requirements を生成できる。
13. DAG から Mermaid / JSON / Markdown report を生成できる。
14. すべて外部APIなし、credentialsなし、paper/live/orderなしで test できる。
```

## ユーザーに何が使えるようになるか

このPhaseの完了後、ユーザーは次を得る。

```text
- HYP-NDX-001 の Core DAG を人間レビューできる。
- DAG node / edge / role / proxy / temporal layer を機械可読に確認できる。
- outcome → treatment などの危険な edge を実装前に検出できる。
- Counter-DAG により、SPXだけ、金利だけ、SOXだけ、ETF noiseだけ等の反証経路を保存できる。
- Feature/residual/backtestに進む前に、2.2が完了したかを判断できる。
```

## 今回完成扱いにしないもの

以下は完成扱いに含めない。

```text
- QQQ / SPY / SMH / VIX / FRED の実データ取得
- NQ futures ingestion
- VXN ingestion
- feature_panel.parquet 生成
- open_gap_residuals.parquet 生成
- expected_ndx_move の rolling regression
- Numerai式 neutralization 計算
- Strategy Lab signal export
- evaluate-strategy-lab 実行
- backtest
- paper candidate
- PaperIntentPreview
- Bitget / Trade[XYZ] / Alpaca / yfinance / FRED への network call
- credentials 使用
- live / exchange write / wallet / signing
```

## 成功の判断文

最終レビューでは、以下の文を満たすことを確認する。

```text
HYP-NDX-001 は、2.2へ必要な前段contractとCore DAGがすべて定義され、
DAGの危険edge・role矛盾・temporal leakage・counter-DAG不足を検査でき、
Core DAG reportを生成できる。
ただし、まだ売買signal、backtest、paper/live注文には接続していない。
```
