# Appendix Materials

このフォルダーは、`../ONE_DOC_STRATEGY_TO_IMPLEMENTATION.md` を補助する付録です。長文だけでは伝わりにくい部分を、図表、カード、サンプル、チェックリスト、テンプレートに分解しています。

## 読む順番

1. `01_PIPELINE_DIAGRAMS.md`
   - 戦略準備からpaper観測までの流れを図で見る。
2. `02_COMPONENT_CARDS.md`
   - 各戦略部品の入力、出力、捨て条件、誤用を1枚カードで見る。
3. `03_REPO_IMPLEMENTATION_MAP.md`
   - このrepoのどこに何が対応するかを見る。
4. `04_ARTIFACT_EXAMPLES.md`
   - signal CSV、decision log、paper outputの具体例を見る。
5. `05_WORKED_EXAMPLE_TREND_PULLBACK.md`
   - Trend Pullbackを例に、仮説からpaper評価まで通して見る。
6. `06_VALIDATION_LEAKAGE_AND_WALK_FORWARD.md`
   - リーク、walk-forward、cost/slippage stressの具体例を見る。
7. `07_MODEL_AND_FEATURE_RISK_SHEETS.md`
   - LightGBM、時系列モデル、Polars、VectorBTの誤用リスクを見る。
8. `08_SOLANA_JITO_TOKEN_SAFETY_SHEETS.md`
   - Solana/Jito/token bot系をobserver-firstに直す。
9. `09_CHECKLISTS_AND_TEMPLATES.md`
   - 実験メモやレビューにそのまま使う。
10. `10_NARRATIVE_RISK_FLASHCARDS.md`
    - 理想的ナラティブを疑うための暗記カード。
11. `11_CURRENTNESS_SOURCE_NOTES.md`
    - 実装直前に再確認する公式資料。
12. `00_SOURCE_TO_APPENDIX_MAP.md`
    - 原ノート24本と付録の対応を見る。

## 使い方

- 戦略を考える時は、まず `09_CHECKLISTS_AND_TEMPLATES.md` の `Hypothesis Intake` を埋める。
- 部品が曖昧なら `02_COMPONENT_CARDS.md` で入力と出力を固定する。
- repoに実装する前に `03_REPO_IMPLEMENTATION_MAP.md` で触る場所と触らない場所を確認する。
- backtest結果が良く見えた時は `06_VALIDATION_LEAKAGE_AND_WALK_FORWARD.md` と `10_NARRATIVE_RISK_FLASHCARDS.md` で疑う。
- Solana/Meme token系は `08_SOLANA_JITO_TOKEN_SAFETY_SHEETS.md` を先に通す。

## 注意

- この付録は投資助言ではない。
- live executionや実弾運用は対象外。
- サンプルCSV/JSONLは実データではなく、形式説明用の例。
- API key、private key、seed phrase、wallet credentialの実値は置かない。
