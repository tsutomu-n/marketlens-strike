<!--
作成日: 2026-06-15_20:36 JST
更新日: 2026-06-15_20:36 JST
-->

# Backtest Capability Before / After Guide

## 結論

今の backtest は、「この repo の中で、安全に、同じ形式の artifact を作りながら、Strategy Authoring の結果を検査する仕組み」です。

実装完了後の backtest は、「今の安全な仕組みを中心に置いたまま、外部 OSS の検算、portfolio 比較、report、lookahead 検査、HFT や ML 系 framework の採用可否判断まで、同じ pack の中で説明できる仕組み」になります。

ただし、完了後も次の意味にはなりません。

- 自動で利益が出ることの証明
- paper trading 合格の証明
- live trading 可能の証明
- 取引所へ注文を出す機能
- wallet、signing、exchange write の解禁
- L2 / L3 order book や latency を使った HFT realism の実装済み宣言

大学の実験で例えると、今は「1つの主測定器で実験し、実験ノートをかなり丁寧に残せる状態」です。完了後は「主測定器はそのまま使い、別の測定器や校正表も並べて、結果がどこまで信用できるか説明できる状態」です。

## この文書の前提

この文書でいう「今の状態」は、2026-06-15_20:36 JST 時点で確認した current repo の状態です。

この文書でいう「実装完了後」は、次の計画の通常レーンが完了した状態です。

- [OSS_BACKTEST_CAPABILITY_EXPANSION_IMPLEMENTATION_PLAN_2026-06-15.md](OSS_BACKTEST_CAPABILITY_EXPANSION_IMPLEMENTATION_PLAN_2026-06-15.md)

Constraint Breaker Gate を通して制約を破る別レーンは、通常完了後のさらに先です。この文書では、まず通常レーンの完了後を中心に説明します。

## ひとことでいう変化

| 観点 | 今の状態 | 実装完了後 | 何がうれしいか |
|---|---|---|---|
| 標準 backtest engine | `strategy_authoring_native` が中心 | 変わらない | repo の安全境界と既存 artifact を壊さない |
| 初期資金 | `backtest.initial_capital_usd` を spec で指定できる | 維持され、各比較にも伝播する | return だけでなく USD 換算で理解できる |
| 評価期間 | `evaluation_start_at` / `evaluation_end_at` を spec で指定できる | pack 内の各検査でも同じ期間を使う | 「同じ試験範囲で比較した」と言える |
| 外部 OSS 実行 | `vectorbt`, `bt`, `empyrical-reloaded`, `quantstats` は optional extra として扱う | framework run、pack、summary、comparison の中でより一貫して扱う | 外部検算がバラバラの実験ではなくなる |
| report | native report と各種 artifact がある | external report / metrics / comparison がまとめて読める | 結果の説明がしやすくなる |
| lookahead 検査 | 既存の no-lookahead diff がある | 検査結果を `checked` / `verified` / `unverified` / risk としてより明確に残す | 「未来データを見ていないか」を説明しやすい |
| HFT 系 realism | L2 / L3 / tick / latency の readiness は限定的 | HftBacktest は採用ではなく readiness probe として扱う | データがないのに HFT 対応済みと誤認しない |
| qstrader | 候補としてはあるが標準ではない | local input contract を先に定義する | equities / ETF 型の検証を始める準備ができる |
| skfolio / Riskfolio-Lib | reference-only 候補 | portfolio validation / optimization contract として整理する | 集中リスクや portfolio 制約を検査する入口ができる |
| PyBroker | ML / walk-forward 候補 | local DataFrame input contract に閉じて検討する | 外部 data fetch や license risk を混ぜずに評価できる |
| NautilusTrader / Freqtrade / Qlib / FinRL | reference-only 候補 | artifact 上で reference-only と明示する | 採用したものと参考にしたものを混同しない |
| 制約を破る判断 | 手作業の議論になりやすい | Constraint Breaker Gate の scorecard で判断する | 「大きく変えるべきか」を感覚で決めない |

## 今できること

### 1. Strategy Authoring の backtest を安全に実行できる

今の中心は `uv run sis strategy-author-run --through backtest` です。

YAML spec から signal を作り、paper-only の backtest metrics と report を出します。live order、wallet、signing、exchange write は使いません。

これは「この戦略候補が、過去データ上でどう見えるか」を見るための研究用 backtest です。

### 2. 初期資金と評価期間を spec で指定できる

今の spec では、たとえば次のような条件を backtest に持たせられます。

```yaml
backtest:
  initial_capital_usd: 20000
  evaluation_start_at: 2026-01-01T00:00:00+00:00
  evaluation_end_at: 2026-02-01T00:00:00+00:00
```

これにより、次のような比較ができます。

- return が `5%` だった場合、`initial_capital_usd=20000` なら `net_pnl_usd=1000` と読める
- 2026年1月だけを評価する、など期間を固定できる
- `evaluation_end_at` は排他的境界として扱われるため、境界の signal を二重に数えにくい

大学生向けに言うと、これは「試験範囲」と「元手」を answer sheet に明記するようなものです。同じ問題を解いたか、同じ点数配分かが分かります。

### 3. pack で複数 artifact をまとめて作れる

`strategy-backtest-pack` は、単発 backtest だけでなく、suite、adapter spike、external result、stress、regime split、rolling stability、benchmark relative、data availability、baseline comparison、no-lookahead diff、execution simulation、assumption ledger、trial ledger、comparison、manifest などをまとめて扱う入口です。

今でも「成功した数字だけを見る」のではなく、仮定、欠損、比較、失敗、skip 状態を artifact として残す方向に寄っています。

### 4. optional OSS はあるが、標準 engine ではない

今の repo では、次の OSS が optional extra として扱われています。

- `vectorbt`
- `bt`
- `empyrical-reloaded`
- `quantstats`

これらは外部検算や report を強くするための道具です。ただし、標準 engine を置き換えるものではありません。

今の標準 engine は、引き続き `strategy_authoring_native` です。

## 実装完了後にできるようになること

### 1. 外部 OSS の検算が pack の中で読みやすくなる

今でも optional OSS を使う入口はありますが、完了後は「どの framework が、どの入力を、どの version で、どの mode で実行したか」を pack、comparison、summary でより一貫して読めるようになります。

大学のレポートで例えると、次の違いです。

- 今: 主実験の結果と、別の測定器の結果が別々の紙にある
- 完了後: 主実験、別測定器、校正情報、失敗した測定、使わなかった測定器まで同じ実験ノートに並ぶ

これにより、数字が良い時だけ都合よく見る運用を避けやすくなります。

### 2. `vectorbt` / `bt` / `empyrical-reloaded` / `quantstats` の役割が明確になる

完了後の整理は次の通りです。

| OSS | 役割 | 標準 engine になるか |
|---|---|---|
| `vectorbt` | signal runner / parameter sweep の外部検算 | ならない |
| `bt` | portfolio allocation / rebalance comparison | ならない |
| `empyrical-reloaded` | Sharpe、drawdown、annual return などの metrics 検算 | ならない |
| `quantstats` | report / tear sheet 生成 | ならない |

ポイントは、「外部 OSS を入れるほど偉い」のではなく、「この repo の backtest 結果を別角度から検査できること」です。

### 3. lookahead 検査の説明力が上がる

lookahead とは、過去の時点では本来見えない未来データを、戦略がうっかり使ってしまう問題です。

これは backtest でかなり危険です。未来を見ている戦略は、過去データでは強く見えますが、実運用では崩れやすいからです。

完了後は、no-lookahead 検査について次のような情報をより明確に残します。

- 何を検査したか
- 何を検査できなかったか
- replay が成立したか
- false negative risk が残るか
- どの artifact が根拠か

「検査した」と「完全に安全」を混同しないための改善です。

### 4. HFT 系 framework を、無理に採用せず readiness から判断できる

HftBacktest のような framework は、L2 / L3 order book、queue position、latency、tick replay などを見るには有力です。

しかし、この repo の標準 backtest pack には、まだそれを正しく使うための L2 / L3 / tick / latency data contract が十分ありません。

そのため完了後も、HftBacktest をいきなり標準 engine にしません。代わりに、次を判定します。

- 必要なデータがあるか
- timestamp の粒度は足りるか
- latency や queue の仮定を artifact に残せるか
- その framework を使う価値がある失敗例を fixture で示せるか

これは地味ですが重要です。データがないのに「HFT 対応」と言うより、できない理由を正しく残す方が実務では価値があります。

### 5. reference-only 候補を採用済みと混同しなくなる

完了後は、次のような候補を reference-only として明示します。

- `HftBacktest`
- `qstrader`
- `skfolio`
- `Riskfolio-Lib`
- `PyBroker`
- `Freqtrade`
- `NautilusTrader`
- `Qlib`
- `FinRL`

reference-only とは、「参考にはするが、この repo の標準 dependency や標準 runner として採用したわけではない」という意味です。

この区別がないと、README や report を読んだ人が「名前が出ているから使われている」と誤解します。完了後は、その誤解を減らします。

### 6. 大きな制約変更を scorecard で判断できる

もし将来、標準 engine を変える、重い dependency を入れる、外部 sandbox を使う、外部 data source を読む、といった大きな変更が必要になった場合は、通常タスクに混ぜません。

完了後は Constraint Breaker Gate で、次のように判断します。

- どの制約を破るのか
- それで何ができるようになるのか
- 今の仕組みではなぜ足りないのか
- license や Python 3.13 対応は問題ないか
- CI cost は重すぎないか
- rollback できるか
- 小さな proof fixture があるか

大学生向けに言うと、「すごそうだから採用」ではなく、「採用するとどの失敗を減らせるのか」を採点表で確認する形です。

## 実装完了後も変わらないこと

### 1. 標準 engine は `strategy_authoring_native` のまま

外部 OSS を増やしても、標準 engine は置き換えません。

これは保守性と安全境界のためです。外部 engine を主役にすると、artifact schema、CLI、dependency、license、CI cost、Python version、外部 data source の問題が一気に広がります。

まずは外部 OSS を「検算役」として使います。

### 2. live trading は始まらない

完了後も、backtest artifact から live order は出しません。

残る境界は次です。

- `paper_only=true`
- `permits_live_order=false`
- `wallet_used=false`
- `exchange_write_used=false`

つまり、これは取引所に注文するシステムではありません。研究と検査のための backtest system です。

### 3. 勝てる証明にはならない

backtest が良くても、それだけで alpha があるとは言えません。

理由は単純です。

- 過去データに偶然合っただけかもしれない
- 手数料や slippage が現実より甘いかもしれない
- データ欠損が結果を歪めているかもしれない
- future leakage が完全には排除できていないかもしれない
- 実運用では約定しない価格で約定したことになっているかもしれない

完了後に増えるのは、「勝てる保証」ではなく、「何を検査し、何がまだ怪しいかを説明する力」です。

## 利用者から見た変化

実装完了後、利用者は次のような読み方ができるようになります。

1. まず native backtest の結果を見る。
2. 同じ入力に対する optional OSS の結果を見る。
3. 期間、初期資金、source hash、framework version が揃っているか確認する。
4. benchmark、stress、regime、rolling stability を見る。
5. data availability と assumption ledger を見て、前提が弱い場所を確認する。
6. no-lookahead diff を見て、未来データ利用の疑いがどこまで検査されたか確認する。
7. reference-only 候補を見て、まだ採用していない理由を確認する。

これにより、単に「総リターンが高いから良い」とは判断しにくくなります。代わりに、「この結果はどの条件なら信じられるか」を考えやすくなります。

## コーダーから見た変化

実装完了後、コーダーにとって大きく変わるのは次です。

- 新しい能力を足すとき、どの schema と artifact に出すべきか分かる
- optional OSS の実行結果を pack / comparison / summary に接続できる
- reference-only 候補を adapter contract に混ぜず、責務を分けられる
- HFT や ML 系 framework を入れる前に、data readiness や license を artifact で判断できる
- 大きな dependency 追加を通常タスクに混ぜず、Constraint Breaker Gate に分離できる

つまり、完了後は「機能が増える」だけではありません。「増やしてよい機能」と「まだ増やすべきでない機能」を分けやすくなります。

## 具体例

### 例1: 1月だけ評価したい

今でも、spec に評価期間を書けば 1月だけを評価対象にできます。

完了後は、その評価期間が native metrics だけでなく、pack 内の外部 framework 比較、benchmark、data availability、no-lookahead などでも揃っていることを確認しやすくなります。

重要なのは、「同じ期間で比較した」と言えることです。

### 例2: `vectorbt` でも同じ方向の結果になるか見たい

今でも optional extra として `vectorbt` を使う入口はあります。

完了後は、`vectorbt` の結果が pack / comparison / summary により自然に出てきます。

ただし、`vectorbt` の結果が native と違った場合、それはすぐにどちらかが正しいという意味ではありません。入力、手数料、signal 解釈、position sizing、timestamp 境界の違いを確認するきっかけです。

### 例3: HFT framework を入れたい

完了後でも、HftBacktest をすぐ標準 engine にはしません。

先に readiness を見ます。

- order book depth はあるか
- tick data はあるか
- latency をどう置くか
- queue position の仮定をどう残すか
- native backtest では見えない失敗を本当に見つけられるか

この条件が揃ってから、Constraint Breaker Gate で isolated runner や optional extra を検討します。

## 最終的な機能変化の要約

今の backtest は、すでに「単純な toy backtest」ではありません。初期資金、評価期間、pack、比較、stress、data availability、no-lookahead、assumption ledger などを持つ、研究用の安全な backtest system です。

実装完了後は、そこに次の能力が足されます。

1. optional OSS 実行結果を、pack / comparison / summary へより一貫して流す能力
2. lookahead 検査の根拠と限界をより明確に残す能力
3. HFT / portfolio / ML 系 framework を、採用前に readiness と contract で評価する能力
4. reference-only と採用済み dependency を混同しない能力
5. 制約を破るべきかを、scorecard と rollback plan で判断する能力

一方で、完了後もこの repo は「安全な研究 backtest と検査 artifact の repo」です。

取引所に注文する repo になるわけではありません。
