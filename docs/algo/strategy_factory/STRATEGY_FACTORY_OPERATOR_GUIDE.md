<!--
作成日: 2026-06-17_23:38 JST
更新日: 2026-06-17_23:38 JST
-->

# Strategy Factory Operator Guide Markdown 正本

この文書は [STRATEGY_FACTORY_OPERATOR_GUIDE.html](STRATEGY_FACTORY_OPERATOR_GUIDE.html) の文章正本です。

HTML は見た目つきの別表示です。内容を更新する時は、この Markdown を先に直し、HTML はこの文書と矛盾しないように更新します。実装コード、生成済み artifact、paper / live の許可はこの文書では変わりません。

## 結論

このガイドは、Strategy Parts Catalog を「眺める資料」ではなく、1作戦1枚の候補シート、重複判定、reject taxonomy、gate review へ流すための運用ガイドです。

目的は、作戦案を増やすことではありません。弱い候補を早く落とし、残った候補だけを Strategy Lab の paper-only artifact chain に送ることです。

paper-only とは、本物のお金を使わない紙上運用という意味です。このガイドは live order、wallet、signing、exchange write、実資金注文を許可しません。

## このガイドの位置づけ

作戦パーツは、直接注文に変えるものではありません。

仮説、必要データ、止め方、baseline を揃え、次の gate へ進めるかを判断するために使います。

流れ:

1. 入力: 作戦パーツを読む。
2. 作業: 1候補1枚に整理する。
3. Gate: 落とす理由を固定する。
4. 出力: Strategy Lab へ送る候補だけを残す。

## 使うドキュメントと役割

この順番で使うと、候補の量産、重複、根拠のない実装を避けやすくなります。

| Document | 役割 |
|---|---|
| [../STRATEGY_PARTS_CATALOG.md](../STRATEGY_PARTS_CATALOG.md) | 部品の入力、出力、失敗モード、検証指標を見る |
| [../STRATEGY_BLUEPRINTS.md](../STRATEGY_BLUEPRINTS.md) | 部品を組み合わせた候補例を見る |
| [SIGNAL_CANDIDATE_TEMPLATE.md](SIGNAL_CANDIDATE_TEMPLATE.md) | 1作戦1枚で候補を書く |
| [ARCHETYPE_REQUIRED_INPUTS.md](ARCHETYPE_REQUIRED_INPUTS.md) | archetype ごとの必須入力と最低検査を見る |
| [DUPLICATE_CONTROL.md](DUPLICATE_CONTROL.md) | 似た候補を統合、棄却、variant 化する |
| [GATE_REVIEW_CHECKLIST.md](GATE_REVIEW_CHECKLIST.md) | 次の状態へ進めてよいかを判定する |

## 最小運用ループ

最初から generator 実装へ行かず、候補シートと gate review を通します。

gate に通らない候補は、reject taxonomy code を残して止めます。

1. 部品を選ぶ: Parts Catalog から必要部品を選ぶ。
2. 1枚に書く: 仮説、trigger、invalidation、baseline を固定する。
3. 入力を確認する: archetype 別の必須データと時刻を確認する。
4. 重複を潰す: threshold 違いは新候補にしない。
5. gate 判定する: 進めるか、落とすか、保留かを記録する。

正本の状態遷移は [FACTORY_WORKFLOW.md](FACTORY_WORKFLOW.md) です。このガイドでは新しい状態名を増やしません。

## Gate ごとの判断

状態は次の流れで扱います。

```text
idea -> specified -> data-ready -> backtest-ready -> backtested -> paper-observing -> continue/rejected/archived
```

Strategy Lab への接続は状態名ではなく、`paper-observing` へ進むための実装ルートです。

### `idea -> specified`: 作戦として読めるか

- 1文の仮説がある。
- archetype が1つに決まっている。
- trigger、invalidation、baseline がある。
- signal と order を混ぜていない。

### `specified -> data-ready`: データが取れるか

- required inputs が列名かデータ項目で書ける。
- historical data または安全な paper collection で取れる。
- `observed_at` または利用可能時刻を記録できる。
- 欠損率、遅延、timezone の扱いが決まっている。

### `data-ready -> backtest-ready`: 検証前の事故を防ぐ

- feature time <= decision time を検査できる。
- cost / slippage 前提がある。
- no-trade conditions がある。
- reject rules が先に書かれている。

### `backtest-ready -> backtested`: 結果を盛らない

- baseline comparison がある。
- cost / slippage 込みで見る。
- trade count が十分。
- parameter neighborhood を見る。

### `backtested -> paper-observing`: paper 観測へ送れるか

- in-sample だけではない。
- paper の価格参照が決まっている。
- expected fill と observed fill の差を記録できる。
- live execution なしで観測できる。

### `any -> rejected`: 早く落とす

- invalidation がない。
- baseline がない。
- 必要データが安全に取れない。
- live 実行しないと基本仮説を検証できない。

## 作戦パーツの言い換え

| Repo 用語 | 一般的な言い換え |
|---|---|
| Universe Selector | 何を売買対象にするか決める部品 |
| Data Collector | 判断材料を集め、時刻つきで保存する部品 |
| Feature Factory | 生データを判断に使える数字へ変換する部品 |
| Regime Detector | 今が trend、range、panic などどの相場か見る部品 |
| Signal Generator | 売買候補を出す部品。注文を出す部品ではない |
| Participation Filter | 良いシグナルでも入らない局面を除外する部品 |
| Position Sizer | 勝てそうだから大きく張るのではなく、負けた時の損失からサイズを決める部品 |
| Exit Module | 利確、損切り、縮小、時間切れを決める部品 |
| Risk Guard | 日次損失、連敗、異常データ、API障害などで止める部品 |
| Evaluation Harness | baseline、cost、walk-forward、stress を同じ物差しで見る部品 |

## 例: Trend + OrderBook Confirmation

Blueprint を候補シートへ落とすと、次のように最低限の判断項目が埋まります。

| 項目 | 記入例 | 見る理由 |
|---|---|---|
| `hypothesis` | 長期トレンド方向の押し目だけを、板の厚みが戻った時に入ると、entry 直後の逆行が減る | 何を改善するかを1文で固定する |
| `archetype` | `pullback` | Required Inputs と duplicate key を決める |
| `required_inputs` | `long_ma`, `ma_slope`, `distance_to_ma`, `short_momentum`, `spread_bps`, `imbalance` | 取得できないデータに依存していないか見る |
| `baseline` | 板フィルタなしの trend pullback | 板フィルタが本当に改善したか分けて測る |
| `invalidation` | pullback low 割れ、または trend regime 解除 | 負けた時にどこで仮説が壊れるか固定する |
| `reject_if` | trade count が baseline の30%未満、または cost 込みで改善が消える | 後から都合よく採用しないため |

## Strategy Lab へ送る時の読み替え

Factory docs は候補設計の入口です。Strategy Lab は、残した候補を paper-only artifact chain に落とす実装ルートです。

| Factory 側 | Strategy Lab 側 | 注意 |
|---|---|---|
| Signal Candidate Sheet | `StrategyExperimentSpec` | 現行 CLI は任意 spec runner ではない。実装時は registered generator に落とす |
| archetype / family | `strategy_family` | 検証可能な family 名にする。`ai` や `latest` は避ける |
| variant / threshold | `parameter_hash` | threshold 違いは新戦略ではなく variant として扱う |
| reject taxonomy | `rejection_reasons` / `block_reasons` | 自由文だけでなく固定コードを残す |
| paper observing entry | `PaperIntentPreview` | paper-only。live order ではない |

## やってはいけない使い方

作戦パーツを便利に使うほど、signal と order、研究と実運用を混ぜる危険が増えます。

安全な読み方:

- 作戦は候補シートへ落としてから評価する。
- baseline と invalidation がない候補は止める。
- 似た候補は duplicate key でまとめる。
- reject 理由を taxonomy code で残す。
- paper-only preview は仮注文案として扱う。

危険な読み方:

- Signal Generator を order generator と読む。
- 勝率や SNS 由来の利益主張を根拠にする。
- threshold 違いを別戦略として量産する。
- backtest なしで paper に進める。
- paper artifact を live-ready 証明にする。

## 確認コマンド

リンク、HTML 構文、repo 標準チェックを確認します。

```bash
uv run python scripts/check_current_docs.py
uv run python -c "from html.parser import HTMLParser; from pathlib import Path; HTMLParser().feed(Path('docs/algo/strategy_factory/STRATEGY_FACTORY_OPERATOR_GUIDE.html').read_text(encoding='utf-8')); print('html_parse=ok')"
git diff --check
./scripts/check
```
