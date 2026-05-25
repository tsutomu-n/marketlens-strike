# XNYS Market Calendar

この文書は、live evidence で出てくる `XNYS` を運用目線で説明する。

## 結論

`XNYS` は New York Stock Exchange の市場カレンダーを指す識別子である。

この repo では、gTrade 上の `SPY/USD` と `QQQ/USD` を「米国株式・ETF 系の指数商品」として扱うため、取引可能な時間を `XNYS` の開場日・開場時間に合わせて判定している。

`XAU/USD` は金の商品なので、`XNYS` ではなく `GTRADE_COMMODITY` として別のカレンダーで判定する。

## 何を判定しているか

`XNYS` は「米国株式市場がその日に開いているか」を判定するために使う。

具体的には次を決める。

- その日が取引日か
- 次の市場 open はいつか
- 次の市場 close はいつか
- live evidence を取り始める推奨時刻はいつか
- live evidence を取り終える推奨時刻はいつか

この repo の実装では `exchange_calendars` の `XNYS` カレンダーを使う。

該当コード:

```text
src/sis/market_calendar.py
```

重要な分岐:

```python
INDEX_SYMBOLS = {"SPY", "QQQ"}
COMMODITY_SYMBOLS = {"XAU"}
```

`SPY` と `QQQ` は `XNYS`、`XAU` は `GTRADE_COMMODITY` に振り分ける。

## なぜ QQQ / SPY に XNYS が関係するか

`QQQ` と `SPY` は gTrade 上では `QQQ/USD`, `SPY/USD` として見えるが、中身は米国市場時間に連動する指数・ETF 系の商品として扱う。

そのため、土日、米国祝日、取引時間外に live evidence を集めても、次のような問題が起きやすい。

- `market_status` が closed になる
- `is_tradable` が false になる
- 価格が null になる
- stale rate や tradable rate が悪化する
- Go/No-Go 判定の材料として弱くなる

したがって、`QQQ` と `SPY` は `XNYS` が開いている時間帯に取る。

## XAU はなぜ別扱いか

`XAU` は gold 相当の商品で、米国株式市場そのものではない。

この repo では `XAU` を `GTRADE_COMMODITY` として扱い、概ね次のルールで判定している。

- 日曜 18:00 ET 以降に開く
- 月曜から木曜は 17:00-18:00 ET の日次 break を除いて開く
- 金曜 17:00 ET 以降は閉じる
- 土曜は閉じる

そのため、`XAU` は開いていても `QQQ` / `SPY` が閉じている日がある。

## 今回の 2026-05-25 の読み方

2026-05-25 は `QQQ` / `SPY` の `XNYS` 判定が休場だった。

一方で、`XAU` は取引可能な時間帯だった。

ただし live evidence planner は、標準では `QQQ`, `SPY`, `XAU` の3銘柄をまとめて評価する。つまり、3銘柄すべてで重なる推奨 window を選ぶ。

そのため、`XAU` だけが開いていても、`QQQ` / `SPY` が休場なら `2026-05-25` の実収集は採用されない。

今回の結論:

- `2026-05-25` に `XAU` 単独の実データは取得していない
- `2026-05-25` に `QQQ` / `SPY` の実データも取得していない
- これは runner が落ちたという意味ではない
- planner が3銘柄共通 window を待った結果である
- 次の共通 window は `2026-05-26 22:45 JST`

## 既存データとの関係

過去分 `2026-05-22` には、`QQQ`, `SPY`, `XAU` の実データが存在する。

確認済みの quote rows:

```text
data/raw/quotes/gtrade/2026-05-22.jsonl

QQQ: total=64 open_or_tradable=60 priced=60
SPY: total=64 open_or_tradable=60 priced=60
XAU: total=64 open_or_tradable=64 priced=60
```

一方で `2026-05-25` の実データファイルは存在しない。

```text
data/raw/sidecar/gtrade/2026-05-25.jsonl
data/raw/sidecar/gtrade-pricing/2026-05-25.jsonl
data/raw/quotes/gtrade/2026-05-25.jsonl
```

## 運用で見るべきコマンド

銘柄別の次回 window を見る。

```bash
uv run sis next-live-window --venue gtrade --symbol QQQ
uv run sis next-live-window --venue gtrade --symbol SPY
uv run sis next-live-window --venue gtrade --symbol XAU
```

3銘柄の共通 window を計画する。

```bash
uv run python scripts/plan_live_evidence_run.py --duration-minutes 120 --metadata-interval-seconds 60
```

実収集後に phase gate を見る。

```bash
uv run sis phase-gate-review
```

## 判断ルール

`XNYS` が休場の日に `QQQ` / `SPY` が取れていないことは、それだけでは障害ではない。

障害として扱うのは、次のような場合である。

- `XNYS` が開いているはずの window で runner が起動していない
- manifest が作られていない
- manifest はあるが `row_counts` が空
- `QQQ` / `SPY` / `XAU` の価格あり rows が十分に増えていない
- phase gate が `phase2_entry_allowed` を許可しない

