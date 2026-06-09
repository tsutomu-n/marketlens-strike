<!--
作成日: 2026-06-08_20:18 JST
更新日: 2026-06-08_20:18 JST
-->

# 01_GOAL

## 目的

現Repoの Layer 2.2 DAG artifact `HYP-NDX-001` を、実データ化に進めるための **Layer 2.3 Preflight / Feature Panel / Open Gap Residual** として実装する。

## 完成状態

次が確認できれば完成。

```text
- Layer 2.2 exit decision を入力として2.3開始可否を確認できる
- required / optional / deferred source を解決した Data Source Resolution artifact が生成される
- fixture inputから NDX feature panel parquet を生成できる
- feature panel manifest に dag_id / dag_artifact_hash / source_ts_max / feature_ts / missing policy が残る
- feature leakage check が same-day close や future source timestamp を拒否する
- rolling OLS による expected_qqq_gap と open_gap_residual を生成できる
- open_gap_residual artifact が dag_artifact_hash と model_config_hash を持つ
- residual diagnostics report が raw correlation / factor exposure / sample counts / rejection hints を出す
```

## ユーザーが使えるようになるもの

```text
uv run sis research-ndx-source-resolve ...
uv run sis research-ndx-feature-panel ...
uv run sis research-ndx-residual ...
uv run sis research-ndx-diagnostics ...
```

ただし、これらは **研究artifact生成用** であり、売買シグナル、paper/live注文、backtest結果ではない。

## 完成扱いにしないもの

```text
- alpha確認
- profitability claim
- Strategy Lab export readiness
- backtest readiness
- paper readiness
- live readiness
- production data readiness
```
