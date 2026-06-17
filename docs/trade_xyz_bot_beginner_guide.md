<!--
作成日: 2026-06-17_22:53 JST
更新日: 2026-06-17_22:53 JST
-->

# Trade[XYZ] Bot 準備ガイド Markdown 正本

この文書は [trade_xyz_bot_beginner_guide.html](trade_xyz_bot_beginner_guide.html) の文章正本です。

HTML は見た目つきの別表示です。内容を更新する時は、この Markdown を先に直し、HTML はこの文書と矛盾しないように更新します。実装コード、生成済み data artifact、paper / live の許可はこの文書では変わりません。

## 最初に読む注意

Trade[XYZ] は実装済みの読み取り専用・研究用 surface ですが、現在の repo の既定主軸ではありません。明示的に Trade[XYZ] を扱う時だけ読む guide です。

いまの標準方針は、venue-neutral / research-first / backtest-first です。つまり、まず研究データ、検証、backtest、paper-only 観測を進めます。本物のお金を使う live execution には進みません。

この guide の安全な読み方:

- できる: Trade[XYZ] の対象確認、価格収集、読み取り専用状態の確認、bot 前の材料整理。
- 途中: bot 判断メモや paper-only の下書き確認。
- できない: wallet、秘密鍵、署名、exchange write、実資金注文、通常 CLI からの live bot 実行。

## 1. これは何？

現実の市場の動きと Trade[XYZ] 側の価格を見比べて、「今は取引してよさそうか」を調べるための準備システムです。

ただし、これは本番の自動売買 bot ではありません。秘密鍵、wallet、本物のお金を使った自動発注は扱いません。

## 2. 今できること

### 対象一覧を作る

どの銘柄を見るかを一覧にします。Trade[XYZ] の発注用 ID も、取得できる場合はここで解決します。

```bash
uv run sis probe trade-xyz
```

### 価格を集める

Trade[XYZ] から価格、板、集計用の要約を集めます。

```bash
uv run sis collect-trade-xyz-quotes --write-summary --write-report
```

### 生データだけ集める

あとで別に整理したい時は、生の価格メモだけ保存できます。

```bash
uv run sis collect-trade-xyz-quotes --no-normalize
```

### 現実市場を調べる

現実市場の価格や特徴を作ります。特徴とは、あとで判断に使う材料のことです。

```bash
uv run sis ingest-research-data
uv run sis build-feature-panel
uv run sis build-signals
```

### 仮想取引で試す

本物のお金を使わず、もし取引したらどうなりそうかを練習できます。

```bash
uv run sis paper-operations-cycle
```

## 3. 今の状態まとめ

できること:

- 銘柄リストと発注用 ID を作る。
- Trade[XYZ] の価格を集める。
- 価格を計算しやすい表に変換する。
- 現実市場のデータ作成と仮想取引の入口を使う。
- Trade[XYZ] の読み取り専用状態を確認する。

途中のこと:

- bot の判断メモは作れる。
- ただし v1 では「今は取引しない」という判断と理由を出すところが中心。
- 注文候補を通常運用として出す段階ではない。

まだしないこと:

- 本番自動売買。
- wallet や秘密鍵の利用。
- 署名。
- exchange write。
- 通常 CLI からの micro live 実行。
- Strategy Lab や PaperIntentPreview を live-ready 証明として読むこと。

## 4. データの流れ

1. 銘柄リスト: 見る対象を決める。
2. 価格メモ: Trade[XYZ] の今の価格を集める。
3. 現実市場: 現実の株や ETF の動きを見る。
4. 比較: Trade[XYZ] と現実市場のズレを見る。
5. 判定: 取引するか、待つかを決める準備をする。

ここでの「判定」は実行許可ではありません。人間が読む材料を整理するだけです。

## 5. Strategy Lab と PaperIntentPreview

Strategy Lab は研究室です。売買アイデアをそのまま注文にせず、signal、trial、candidate、promotion decision の順に分けて確認します。

PaperIntentPreview は下書きです。paper runner に渡す仮の注文意図であり、使う前に最新価格で再確認します。本番注文には変換しません。

ここで止める境界:

- TradeCandidate は候補です。利益の証明ではありません。
- PaperCandidatePack は候補の束です。live readiness の証明ではありません。
- PaperIntentPreview は paper-only の下書きです。実注文ではありません。

## 6. NDX / QQQ との関係

NDX / QQQ の研究経路は、Trade[XYZ] bot とは別の research-first 経路です。

この repo には NDX Layer 2.2 以降の研究 gate や Strategy Lab export の文書がありますが、それらは Trade[XYZ] の live 許可ではありません。NDX / QQQ の venue suitability や paper path が fail-closed なら、そこで止めます。

一般的に言うと、fail-closed とは「危ないか不明なら止める」という意味です。止まった状態は失敗ではなく、安全側の結果です。

## 7. 出力ファイルの意味

| 名前 | 普通の言葉での意味 |
|---|---|
| registry | 見るべき銘柄のリスト。学校の出席名簿のようなもの。 |
| raw quotes | 取ってきた価格情報をそのまま保存したメモ。 |
| normalized quotes | あとで計算しやすいように整えた価格表。 |
| strategy signals | Strategy Lab が作る「見てよさそう」という研究メモ。注文ではありません。 |
| paper intent preview | 仮想取引用の注文下書き。paper 専用で、本番発注には使いません。 |
| readiness | bot の前に「準備できているか」を見る健康診断。 |
| phase gate | 次の段階へ進んでよいかを止める関門。 |
| paper | 本物のお金を使わない練習取引。 |

## 8. Bot 前の安全確認

bot 前に見るべきこと:

- 価格は新しいか。
- 買う値段と売る値段の差が広すぎないか。
- 注文できる量が足りるか。
- 現実市場と Trade[XYZ] 側の価格がズレすぎていないか。
- 情報源は信用できるか。
- 市場が閉まっている時間や大きなニュースの近くではないか。

これらは「進めてよいか」を判断する材料です。ひとつでも不明なら止める方に倒します。

## 9. Bot 化前に足りないもの

足りないもの:

- 価格の健康診断を、毎回迷わず読める形にする。
- bot 用の判断メモを、人間が読みやすい形にする。
- 「取引しない理由」を明確に残す。
- 注文の下書きは paper-only に限定する。
- 銘柄リスト、価格、現実市場、比較、判定をまとめて更新する入口を整理する。

現在の bot preview は、「今は取引しない」と理由を書く入口です。

```bash
uv run sis bot-preview
```

## 10. 次に作るもの

Trade[XYZ] bot decision preview は、本物の注文を出す前に「今はやめる」と、その理由を人間が読める形にするものです。

想定出力:

```text
data/bot/bot_decision.json
data/reports/bot_orders_preview.md
```

## 11. 今後どうするか

1. 証跡確認: 読み取り専用ゲート結果を毎回確認する。
2. 価格チェック: Trade[XYZ] 要約と診断を bot 判断に渡す。
3. 準備判定: phase gate の結果を bot 前の健康診断として読む。
4. 判断メモ: `bot_decision.json` に「今は取引しない」と理由を書く。
5. HOLD preview: `bot_orders_preview.md` で注文候補なしと理由を人間が読める形にする。
6. まだ本番にしない: paper と preview で確認し、wallet や秘密鍵は使わない。

## 12. 想定出力の例

| Path | 概要 |
|---|---|
| `data/ops/trade_xyz_quote_collection_summary.json` | 価格データの健康診断。新しいか、差が広すぎないか、量が足りるかを見る。 |
| `data/ops/pr12_fresh_read_only_smoke_summary.json` | 60 分以上の読み取り専用確認が通ったかをまとめた証跡。 |
| `data/ops/phase_gate_review_summary.json` | bot を作る前に、準備ができているかをまとめた判定。 |
| `data/research/strategy_signals.parquet` | Strategy Lab の研究メモ。売買候補の材料で、注文ではない。 |
| `data/bot/paper_intent_preview.json` | paper 専用の注文下書き。使う前に最新価格で再確認する。 |
| `data/bot/bot_decision.json` | bot の判断メモ。v1 では「今は取引しない」と、その理由を書く。 |
| `data/reports/bot_orders_preview.md` | 注文候補なしの確認ページ。wallet や秘密鍵は使わない。 |

## 13. よくある誤解

価格を集めたら bot 完成か:

違います。価格は材料です。まだ安全判定と注文下書きが必要です。

仮想取引 OK は本番 OK か:

違います。仮想取引は練習です。本番には秘密鍵、wallet、失敗時の停止策が必要です。

micro live があるなら自動売買 OK か:

違います。micro live は小さな安全確認用です。普通の bot として公開されていません。

PaperIntentPreview は本番注文か:

違います。paper 専用の下書きです。最新価格で再確認し、本物の発注には変換しません。

NDX / QQQ の研究 gate が進んだら Trade[XYZ] も本番 OK か:

違います。研究 gate は venue ごとの live 許可ではありません。

## 14. 絶対に誤解しないこと

- この段階では、本物のお金で自動売買しない。
- 秘密鍵や wallet は使わない。
- 署名や exchange write は使わない。
- micro live は安全確認用のコードで、普通の bot として公開されていない。
- Strategy Lab の出力や PaperIntentPreview を、本番注文や本番準備完了と勘違いしない。
- 古い gTrade / Ostium 用の判定を、Trade[XYZ] の準備完了と勘違いしない。
- `READ_ONLY_GO` は読み取り専用・paper gate の結果であり、live trading 許可ではない。

## 関連資料

- [CURRENT_STATE.md](CURRENT_STATE.md): repo 全体の現在地を読む入口。
- [REPO_CAPABILITIES_PLAIN_JA_2026-06-17.md](REPO_CAPABILITIES_PLAIN_JA_2026-06-17.md): できること / できないことを専門用語少なめで説明する文書。
- [NEXT_DIRECTION_CURRENT.md](NEXT_DIRECTION_CURRENT.md): 外部入力が来た時の再確認 checklist。
- [OPERATIONS_RUNBOOK.md](OPERATIONS_RUNBOOK.md): 運用手順の入口。
- [runbooks/TRADE_XYZ_RUNBOOK.md](runbooks/TRADE_XYZ_RUNBOOK.md): Trade[XYZ] を明示的に扱う時の runbook。
- [strategy_research_lab/08_CURRENT_CAPABILITIES.md](strategy_research_lab/08_CURRENT_CAPABILITIES.md): Strategy Research Lab で現在できること。
- [trade_xyz_bot_beginner_guide.html](trade_xyz_bot_beginner_guide.html): この guide の見た目つき HTML 版。
