# Algo Strategy System Guide

調査元: `/home/tn/Docs/algo/obsidian-vault`  
現行方針: 古い発掘ログではなく、戦略を作るための部品と検証手順に再構成する。

## 結論

vaultのノート群から見える有効な方向性は、単一の聖杯ロジックではなく、次のような分業型の戦略システムです。

```text
Universe Selector
  -> Data Collector
  -> Feature Factory
  -> Regime Detector
  -> Signal Generator
  -> Participation Filter
  -> Position Sizer
  -> Exit Module
  -> Risk Guard
  -> Execution Adapter
  -> Monitoring / Evaluation
```

特に使う価値が高い軸は次の6つです。

- トレンド追随: 長期方向と短期エントリーを分ける。
- 板/マイクロ構造: 方向予測より、入ってよい瞬間と約定品質を見る。
- レジーム判定: 1本の万能戦略ではなく、市場状態で戦略を切り替える。
- リスクガード: シグナルより停止条件、サイズ、損失制限を重視する。
- イベント観測: Pump.fun/Solana/Meme系は、まず売買ではなくイベントデータ収集から始める。
- トークン安全性: freeze authority、mint authority、rug/sniper誘引、bot wallet露出を取引前の除外条件にする。

## 戦略設計の原則

### 1. 予測より分業

価格を直接当てるモデルを中核にしすぎない。モデルは次の用途に寄せる。

- 取引してよい局面かを判定する。
- レジームを分類する。
- サイズを調整する。
- 危険局面を除外する。
- 複数戦略の配分を調整する。

### 2. エントリーより見送り

vault内の有用なノートは、エントリー条件だけでなく、見送る条件を多く含んでいます。

- 低流動性
- 異常スプレッド
- 急変直後
- dev/insider保有偏り
- token ageが短すぎる/長すぎる
- SOL地合い悪化
- 板の吸収がない
- ニュースやテーマの根拠が薄い

このため、最初に作るべきものは「Signal Generator」ではなく「Participation Filter」です。

### 3. Meme/Pump.fun系は観測から

Pump.fun、BullX、NeoBullX、Meme token系のノートには具体的な閾値や勝率主張が多いですが、実運用に近いほど誇張や生存者バイアスのリスクが高いです。

最初の扱い:

- 売買Botではなくイベント収集Botにする。
- market cap、liquidity、token age、volume、dev/insider比率、新規ウォレット買い、social有無を保存する。
- 1分、5分、15分、60分、24時間後のリターンをラベル化する。
- 約定不能、スリッページ、手数料、API遅延を悪めに入れる。

### 4. 悪用可能なノートは防御目的だけに使う

`Rugg`, `Sniper`, `freeze`, `Photon/NeoBullX wallet` 系のノートには、攻撃的または秘匿情報を含むものがあります。これらは収益機会として扱わず、次の防御目的に限定します。

- 凍結権限、mint権限、owner権限の有無を確認する。
- sniperが反応しやすい条件を、買い条件ではなく危険シグナルとして記録する。
- wallet/private key/API keyが含まれるノートはsource-onlyまたは除外にする。
- トークン作成側の悪用手順はdocsへ展開しない。

### 5. 検証仕様を先に固定

戦略アイデアを増やすほど過学習しやすくなります。実装前に最低限の検証仕様を固定します。

- time-series split
- walk-forward
- transaction cost
- slippage
- stress period
- Monte Carlo
- parameter stability
- leakage check
- minimum trade count
- stop condition

## 優先する実験仮説

### A. Trend + OrderBook

目的:
- 長期トレンドで方向を決め、板でエントリー可否を絞る。

使う部品:
- Regime Detector
- Signal Generator
- Participation Filter
- Execution Adapter

主な検証:
- 板フィルタあり/なしで、entry直後の逆行、スリッページ、勝率、MDDが改善するか。

### B. Regime + RiskGuard

目的:
- 同じシグナルでも、市場状態ごとにサイズ、停止条件、exitを変える。

使う部品:
- Regime Detector
- Position Sizer
- Exit Module
- Risk Guard

主な検証:
- 全期間固定パラメータより、DD、CVaR、連敗長が改善するか。

### C. Pump.fun Event Watcher

目的:
- Meme tokenの売買ではなく、卒業前後や初回バウンスのイベントをデータ化する。

使う部品:
- Universe Selector
- Data Collector
- Feature Factory
- Evaluation Harness

主な検証:
- 各条件が将来リターンにどの程度寄与するか。条件を重ねすぎた時にtrade countが消えないか。

### D. Feature Factory + Walk-Forward

目的:
- 指標や特徴量を増やしても、検証ゲートを通ったものだけ残す。

使う部品:
- Feature Factory
- Evaluation Harness
- Monitoring Layer

主な検証:
- 追加特徴量がwalk-forward、コスト込み、複数期間で改善するか。

### E. Token Safety Gate

目的:
- Solana/Meme tokenに参加する前に、売買不能、凍結、rug、bot wallet露出を検知して除外する。

使う部品:
- Universe Selector
- Data Collector
- Token Safety Filter
- Risk Guard

主な検証:
- 除外したトークンの事後リターン、凍結/売買不能/流動性喪失の発生率、false positiveを記録する。

## 採用しない方がよい考え方

- ノート内の勝率や収益倍率をそのまま信じる。
- 価格予測モデルに売買判断を丸投げする。
- バックテストで良い期間だけを見て採用する。
- 手数料、スリッページ、約定不能を後回しにする。
- APIキーや秘密鍵を含むノートをdocsへ生コピーする。
- 実行Botを先に作り、データ品質や検証を後から考える。
- sniperを誘引するトークン設計やrug手法を戦略化する。
- 凍結権限やmint権限の確認なしにMeme tokenへ参加する。
- Web/API公開面のWAF、rate limit、認証、ログを運用後回しにする。

## 次の実装に進む条件

コード実装へ進む前に、最低限次が揃っている状態を完了とします。

- [STRATEGY_PREP_WORKFLOW.md](STRATEGY_PREP_WORKFLOW.md) の準備完了条件を満たしている。
- [EXPERIMENT_SCORECARD.md](EXPERIMENT_SCORECARD.md) で候補が `prepare` または `observe-first` になっている。
- 戦略が部品単位で説明できる。
- 入力データと出力シグナルが明確。
- 使わない条件、停止条件、捨て条件がある。
- 検証方法が `RESEARCH_VALIDATION_PLAYBOOK.md` に沿っている。
- 秘匿情報や外部副作用がない。
