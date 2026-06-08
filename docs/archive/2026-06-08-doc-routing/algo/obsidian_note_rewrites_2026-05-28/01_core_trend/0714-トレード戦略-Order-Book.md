# 0714-トレード戦略-Order-Book

## このノートの扱い

注文簿を「儲かるシグナル」と見るのではなく、参加してよいかを判断する短期マイクロストラクチャ部品として扱う。

## 元ノートの要旨

板の深さ、不均衡、傾斜、クラスタリング、プロファイル分析、機械学習によるパターン検出を通じて優位性を得るという内容。

## 今日時点での補正

注文簿は情報量が多いが、最も劣化しやすいデータでもある。bot戦略では、方向予測よりも「スプレッドが広いから見送る」「薄いからサイズを落とす」「板が消えたから停止する」用途が先。

## 理想的ナラティブ / 誤謬リスク

- `PREDICTION_OVERCLAIM`: 板パターンから価格変動を安定して読めるという前提。
- `EXECUTION_GAP`: 見えている板に自分の注文が同じ条件で約定するという前提。
- `MEV_LATENCY_ARMS_RACE`: 低遅延業者に不利な領域へ入る可能性。

## 戦略部品への分解

- `Participation Filter`: spread、depth、imbalance、cancel spike。
- `Position Sizer`: 板厚に応じた最大サイズ。
- `Execution Adapter`: maker/taker、post-only、IOCの使い分け。
- `Risk Guard`: 板消失、約定遅延、急拡大スプレッドで停止。

## 実験に落とすなら

方向予測ではなく、注文簿条件を入れることで既存シグナルのスリッページと約定失敗率が改善するかを測る。板データの保存粒度、タイムスタンプ、取得遅延を必ず記録する。

## 採用条件

同じシグナルに対し、注文簿フィルタありで実現約定コストが下がること。

## 捨て条件

バックテスト上の板価格を使うと良いが、ライブ観測で再現できない場合。

## 現在性チェック

取引所ごとの order book API、rate limit、snapshot/delta仕様を確認する。

## 関連 docs

- `../STRATEGY_BLUEPRINTS.md`
- `../RESEARCH_VALIDATION_PLAYBOOK.md`

## 原ノート

- `../obsidian_note_copies/01_core_trend/0714-トレード戦略-Order-Book.md`

