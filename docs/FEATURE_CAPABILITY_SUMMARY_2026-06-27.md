<!--
作成日: 2026-06-27_09:40 JST
更新日: 2026-06-27_09:40 JST
-->

# Feature Capability Summary 2026-06-27

## 結論

`marketlens-strike` は、自動で儲かる売買 bot ではない。主な価値は、戦略アイデアを検証可能な形にし、過去データや観察結果で弱点を見つけ、人間が判断できる成果物を残すことにある。

この資料は、プログラム構造ではなく「何ができるか」を機能別にまとめる。各機能について、目的、背景、期待する成果物、使う時の注意を整理する。

## 全体でできること

| 機能群 | 目的 | 背景 | 期待する成果物 |
|---|---|---|---|
| 戦略アイデア整理 | 曖昧な戦略案を検証できる形にする。 | 思いつきや感覚のままだと、後から良し悪しを判断できない。 | 戦略仕様、入力条件、前提、失敗条件、検証対象の整理。 |
| Backtest | 戦略を過去データに当て、弱点を探す。 | 過去に良かっただけでは将来の利益は証明できないが、明らかな破綻や過剰最適化は見つけやすい。 | backtest 結果、比較表、stress 結果、regime 別結果、HTML report。 |
| Strategy Review | 人間が読めるレビュー資料を作る。 | 数値だけでは判断できず、前提、データ、結果、リスクをまとめて見る必要がある。 | review packet、operator review record、判断理由の記録。 |
| Paper / observation | 本番資金を使わず、動作や観察状況を見る。 | backtest と実際の観察にはズレが出る。いきなり本番に進むと危険。 | paper observation status、paper cycle record、runtime observation、drift review。 |
| Strategy improvement loop | 検証結果から改善材料を作る。 | 戦略は一度作って終わりではなく、観察、失敗、修正候補の記録が必要。 | learning ledger、revision request、authoring update handoff。 |
| Strategy case management | 戦略ごとの履歴を追えるようにする。 | 複数戦略や複数 artifact が増えると、何を見たか分からなくなる。 | strategy case lite、case index、daily brief、workbench viewer。 |
| AI review support | AI に渡す材料と AI の意見を記録する。 | AI の助言をそのまま採用すると危険。入力と出力を限定し、記録する必要がある。 | AI review packet、AI review note。 |
| NDX research gate | NDX / QQQ 系研究を段階的に進める。 | 研究仮説、データ、特徴量、残差検証を段階ごとに分けないと、都合の良い結論になりやすい。 | DAG artifact、review pack、feature panel、residual validation、paper-observation gate。 |
| Crypto Perp Truth-Cycle | 暗号資産 perpetual の event から仮説検証までを記録する。 | 短期イベントはデータ欠損、取引コスト、実約定との差が大きく、実験記録を残さないと判断が歪む。 | raw snapshot、probe audit、event card、decision ledger、outcome ledger、tournament report、truth-cycle status。 |
| Venue / data boundary | 取引所や外部データの安全境界を確認する。 | read-only、demo、paper、live を混ぜると危険。 | read-only probe、quote report、data readiness、phase gate、execution snapshot。 |
| Operations / audit | 状態、証拠、未解決事項を運用者向けにまとめる。 | 検証が増えるほど、何が止まっているか、何が足りないかが見えにくくなる。 | operations dashboard、audit bundle、readiness snapshot、remediation plan。 |

## 1. 戦略アイデア整理

目的:
戦略の「入口」を曖昧な文章から、検証できる材料へ変える。

背景:
売買戦略は、買う条件、売る条件、見ているデータ、失敗条件が曖昧だと、backtest しても意味が薄い。良い結果が出ても、何が効いたのか分からない。

期待する成果物:

- 戦略の入力条件。
- 売買判断の根拠。
- 使うデータの一覧。
- 既知の前提と不明点。
- authoring 用の戦略仕様。
- 検証に進めるかどうかの判断材料。

注意:
整理できたことは、利益が出ることを意味しない。検証に進む準備ができたという意味に留める。

## 2. Backtest

目的:
戦略を過去データで試し、利益だけでなく弱点、偏り、条件依存を見つける。

背景:
戦略は過去の一期間だけ良く見えることがある。比較、stress、regime split、rolling stability などを使い、都合の良い結果だけを見ないようにする。

期待する成果物:

- backtest result。
- benchmark 比較。
- stress test。
- regime 別評価。
- rolling stability。
- no-lookahead 確認。
- assumption ledger。
- backtest pack。
- HTML report。

注意:
backtest pass は、本番許可でも paper 実行許可でもない。過去データでの検査結果である。

## 3. Strategy Review

目的:
戦略と検証結果を、人間がレビューできる資料にする。

背景:
数字だけでは判断できない。どのデータを使い、どんな前提で、どの結果を見て、何をリスクと判断したかを残す必要がある。

期待する成果物:

- review packet。
- review manifest。
- operator review record。
- 判断理由。
- 見た artifact の一覧。

注意:
review record は「読んだ」「判断した」記録であり、本番注文の許可ではない。

## 4. Paper / Observation

目的:
本番資金を使わずに、戦略や観察 flow の状態を見る。

背景:
backtest と paper observation は別物である。実際には約定しにくい、観察日数が足りない、spread が大きい、想定より取引が少ない、といったズレが出る。

期待する成果物:

- paper operation report。
- paper observation status。
- runtime observation manifest。
- paper vs backtest drift review。
- normal observation に足りない条件の一覧。

注意:
paper observation が進んでも、live readiness は証明しない。

## 5. Strategy Improvement Loop

目的:
検証結果や観察結果から、次の改善候補を作る。

背景:
戦略は「作る、試す、直す」を繰り返す。失敗理由を記録しないと、同じ仮説を何度も試したり、都合の良い改善だけを採用したりしやすい。

期待する成果物:

- learning ledger。
- revision request。
- revision request review。
- authoring update handoff。
- 改善候補と採否理由。

注意:
改善候補は自動適用しない。人間が内容を確認してから戦略仕様へ反映する。

## 6. Strategy Case Management

目的:
戦略ごとの履歴、状態、関連 artifact を追えるようにする。

背景:
戦略、backtest、review、paper observation、AI note が増えると、どの資料が最新で、何を見て判断したか分からなくなる。

期待する成果物:

- strategy case lite。
- strategy case index。
- daily brief。
- static workbench viewer。
- 戦略別の artifact timeline。

注意:
これは DB registry や full workflow system ではない。source artifact を勝手に編集しない。

## 7. AI Review Support

目的:
AI に見せる材料を整理し、AI の意見を記録する。

背景:
AI に丸投げすると、根拠が薄い改善案や過剰な楽観を採用しやすい。入力資料を限定し、出力を記録として扱う必要がある。

期待する成果物:

- AI review packet。
- AI review note。
- AI 指摘の記録。
- 人間確認が必要な論点。

注意:
AI note は自動採用しない。戦略や artifact を自動で書き換えるものではない。

## 8. NDX Research Gate

目的:
NDX / QQQ 系の研究を段階に分け、仮説、データ、特徴量、残差検証を整理する。

背景:
市場研究は、都合の良い指標や期間を選ぶと簡単に良く見える。DAG、review、feature panel、residual validation を分けて、研究の弱点を見つけやすくする。

期待する成果物:

- research DAG。
- manual review pack。
- normalized review。
- feature panel。
- residual validation。
- Strategy Lab export。
- paper-observation gate。

注意:
NDX research gate の通過は、alpha proof や live readiness ではない。

## 9. Crypto Perp Truth-Cycle

目的:
暗号資産 perpetual のイベント仮説を、取得データ、判断、結果、比較まで一連の記録にする。

背景:
短期 crypto event は、raw data の欠損、非確定足、取引コスト、実約定との差、方向選択のバイアスが出やすい。都合の良い勝ちだけを拾わないため、event から outcome までを記録する。

期待する成果物:

- provider probe。
- raw snapshot。
- probe audit。
- event card。
- decision ledger。
- outcome ledger。
- tournament rows。
- tournament report。
- tournament gate。
- truth-cycle status。
- dogfood pack。

注意:
`READY_FOR_HUMAN_TINY_LIVE_REVIEW` は、人間レビュー候補であり、live execution permission ではない。

## 10. Venue / Data Boundary

目的:
取引所、データ取得、read-only / demo / paper / live の境界を確認する。

背景:
外部サービスや取引所に触る機能は、読み取り、demo、paper、本番注文を混ぜると危険である。何が許可されていて、何が未証明かを artifact にする必要がある。

期待する成果物:

- venue read-only probe。
- quote collection report。
- normalized quote data。
- data readiness report。
- execution snapshot。
- phase gate review。
- venue diagnostics。

注意:
read-only probe は network readiness、credential readiness、paper readiness、live readiness を証明しない。

## 11. Operations / Audit / Remediation

目的:
現在の状態、足りない証拠、止まっている理由、次に確認することを運用者向けにまとめる。

背景:
artifact が増えるほど、何が完了していて、何が未確認で、どこで止まっているかが見えにくくなる。運用者が見る dashboard と audit pack が必要になる。

期待する成果物:

- operations dashboard。
- operations bundle。
- audit bundle。
- readiness snapshot。
- current-state index。
- remediation plan。
- remediation scoreboard。
- weekly review。

注意:
operations の `GO` や `READ_ONLY_GO` は、文脈を限定して読む。本番取引の許可に読み替えない。

## 12. 利用者向け説明と判断補助

目的:
技術者でない人や、利益目線で判断する人が、できることとできないことを誤解しないようにする。

背景:
検証ツールは「勝てる bot」と誤読されやすい。実際には、戦略を検査し、資料を作り、止める理由を見つけるためのアプリである。

期待する成果物:

- 非技術者向け guide。
- detailed current-state guide。
- practical decision note。
- individual trader assessment。
- docs / directory structure triage。

注意:
判断補助 docs は正本ではない。投資判断や本番運用判断には、必ず code、CLI、schema、tests、最新 artifact を確認する。

## 何ができないか

- 自動で儲かる戦略を保証する。
- backtest pass だけで alpha を証明する。
- paper observation だけで live readiness を証明する。
- wallet、signing、exchange write を標準 operator path で許可する。
- AI の提案を自動採用する。
- external API や取引所本番操作を承認なしに進める。
- runtime artifact の現在値を docs だけで保証する。

## 読む順番

1. この文書。
2. `docs/CURRENT_STATE.md`
3. `docs/IMPLEMENTED_SURFACES.md`
4. 目的別 docs:
   - 戦略作成: `docs/strategy_research_lab/README.md`
   - backtest: `docs/backtest/README.md`
   - review: `docs/strategy_review/README.md`
   - NDX: `docs/research/ndx/README.md`
   - Crypto Perp: `docs/runbooks/CRYPTO_PERP_TRUTH_CYCLE_RUNBOOK.md`
   - venue boundary: `docs/venues/read_only_capability_probe.md`
   - docs / structure: `docs/CURRENT_DOCS_AND_STRUCTURE_TRIAGE_2026-06-27.md`

## 検証方法

この文書は機能説明であり、runtime 値の正本ではない。現時点の CLI / docs 整合は次で確認する。

```bash
uv run python scripts/check_current_docs.py
uv run python scripts/check_cli_catalog.py
git diff --check
```
