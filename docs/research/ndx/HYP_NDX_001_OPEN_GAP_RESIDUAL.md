<!--
作成日: 2026-06-07_19:37 JST
更新日: 2026-06-07_19:37 JST
-->

# HYP-NDX-001 Open Gap Residual

HYP-NDX-001 は QQQ open gap から既知ファクター由来の expected move を差し引いた residual が、同日 open-to-close return に情報を持つ可能性を記述する Core DAG である。

この文書は alpha、causal effect、backtest成績、paper-ready、live-ready を主張しない。DAGは真因果の証明ではなく、研究仮説の構造化 artifact である。

中心構造:
- SPY / SMH / DGS10 / VIX / mega-cap basket -> expected NDX move
- QQQ open gap and expected NDX move -> open gap residual
- open gap residual -> QQQ open-to-close return

反証DAGは必須 artifact として `configs/research_layer_2_2/ndx/counter_dags.yaml` に保存する。
