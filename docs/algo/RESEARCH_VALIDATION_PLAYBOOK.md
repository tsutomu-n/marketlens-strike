# Research Validation Playbook

戦略候補を安全に捨てるための検証手順です。目的は、良い戦略を早く見つけることではなく、弱い仮説を早く落とすことです。

## 検証の順番

1. 仮説を1文で書く。
2. 使う部品を `STRATEGY_PARTS_CATALOG.md` から選ぶ。
3. 入力データ、出力シグナル、停止条件を固定する。
4. baselineを作る。
5. コストなしで粗く確認する。
6. 手数料、スリッページ、約定不能を入れる。
7. walk-forwardで見る。
8. stress periodとMonte Carloを見る。
9. parameter stabilityを見る。
10. 捨てるか、paper observationへ進める。

## 必須チェック

### Leakage Check

- 未来の価格、出来高、確定前の足、後から分かるオンチェーン値を使っていないか。
- 特徴量計算時に、対象時刻以降のデータが混ざっていないか。
- train/testの期間が重なっていないか。

### Cost Check

- maker/taker feeを入れる。
- spreadまたは想定slippageを入れる。
- DEX/Meme系では約定不能、遅延、不利約定を悪めに入れる。
- turnoverが増えた改善は、必ずコスト後で見る。

### Token Safety Check

- freeze authority、mint authority、holder concentration、liquidity状態を確認する。
- 権限情報を取れない場合は安全扱いにしない。
- sniper/rug関連ノートは防御的な除外条件にだけ使う。
- bot wallet、private key、API keyが含まれるノートは検証入力にしない。

### Walk-Forward Check

- 1回のtrain/test splitだけで採用しない。
- 各期間で同じ方向に改善するかを見る。
- 最適パラメータが期間ごとに大きく飛ぶ場合は不安定と扱う。

### Stress Check

- 高ボラ期間。
- 急落/急騰期間。
- 低流動性期間。
- API欠損またはデータギャップがある期間。
- トークン凍結、売買停止、pool流動性喪失。
- collector/dashboard/API公開面への過剰アクセス。

### Monte Carlo Check

- trade順序のシャッフル。
- return系列の再標本化。
- slippage悪化。
- 連敗集中。
- 勝率低下または平均損失拡大。

## 採用指標

最低限見る指標:

- net return
- profit factor
- max drawdown
- CVaR or tail loss
- Sharpe/Sortino
- trade count
- average holding period
- turnover
- exposure
- slippage sensitivity
- parameter stability

単独で採用理由にしない指標:

- 勝率
- gross return
- 最良期間のequity curve
- SNSや動画由来の利益主張
- in-sampleの高スコア

## 捨て条件

次のどれかに該当したら、原則として捨てるか、観測専用へ降格します。

- 手数料とスリッページ込みで期待値が消える。
- trade countが少なすぎる。
- walk-forwardで改善が再現しない。
- parameterを少し変えると壊れる。
- DDまたはCVaRがbaselineより悪い。
- liveで取得できないデータに依存している。
- 実装に秘密鍵や外部副作用が必要になる。
- 説明できない複雑さが増える。
- token authorityや売買可否の確認ができない。
- 攻撃的または不正な用途へ転用されうる。

## Paper Observationへ進める条件

コード実装前またはpaper運用前に、次を満たす必要があります。

- 仮説、部品、入力、出力、停止条件が文書化済み。
- baseline比較で改善がある。
- コスト込みでも期待値が残る。
- walk-forwardで最低限の再現性がある。
- リスクガードが定義済み。
- 収集データの欠損率と遅延を記録できる。

## Live Executionへ進める条件

このdocs更新時点ではlive executionは範囲外です。将来進める場合でも、最低限次が必要です。

- paper/live差分の記録。
- duplicate order防止。
- API rate limitとretry設計。
- hard stop。
- secret管理。
- 手動停止手順。
- 小額またはsandboxでの段階的検証。
- WAF/rate limit/auth/loggingなど公開面の保護。
