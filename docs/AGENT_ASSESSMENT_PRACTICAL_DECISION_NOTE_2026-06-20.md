<!--
作成日: 2026-06-20_09:09 JST
更新日: 2026-06-20_09:13 JST
-->

# Agent Assessment Practical Decision Note

## 位置づけ

この文書は `docs/AGENT_ASSESSMENT_INDIVIDUAL_TRADER_2026-06-20.md` の別紙です。

正本ではありません。repo の正本は `src/`, `tests/`, `schemas/`, `configs/`, `scripts/`, CLI help, runtime artifact です。この文書は、個人トレーダーが `marketlens-strike` を「利益を取りに行く道具」として見る時に、都合のいい物語を潰すための現場メモです。

README や `CURRENT_STATE.md` には混ぜません。公式説明ではなく、儲かった気になる前に止めるための判断メモです。

## 一行結論

`marketlens-strike` は利益を自動発見する装置ではありません。貪欲に利益を狙うなら、まずこの repo の PASS、paper filled、Sharpe、first slice 完了を疑い、ドル建ての必要利益と現実の摩擦で候補を切るべきです。

## 追加調査で見た現物

今回追加で確認した一次ソース:

- `data/research/strategy_backtest_metrics.json`
- `data/research/backtest_stress/strategy_backtest_stress.json`
- `data/research/backtest_pack/strategy_backtest_pack_validation.json`
- `data/research/strategy_lifecycle/paper_observation_status.json`
- `data/paper/observations/local-paper-20260617-200702/paper_observation_ledger.jsonl`
- `data/paper/observations/local-paper-20260617-200702/paper_observation_review_decision.json`
- `data/research/trial_ledger.jsonl`
- `configs/micro_live_policy.yaml`
- `scripts/seed_strategy_authoring_baseline_data.py`
- `src/sis/execution/live_order_policy.py`
- `src/sis/execution/micro_live_canary.py`
- `src/sis/strategy_micro_live_plan/service.py`
- `uv run sis --help`
- `uv run sis strategy-micro-live-plan --help`
- `uv run sis estimate-order --help`
- `uv run sis cancel-order --help`

## 利益から逆算した現実

現行の fixture backtest は次の状態です。

```text
signals_considered: 7
first_ts_signal: 2026-01-05 14:00:00+00:00
last_ts_signal: 2026-01-06 14:00:00+00:00
avg_signal_return: 0.0006647314658437868
total_signal_return: 0.0046531202609065075
cost_drag_bps: 7.0
backtest_passed: true
metrics[0].sharpe: 8300.156265556454
```

`configs/micro_live_policy.yaml` の現行上限は:

```text
enabled: false
max_notional_usd: 50
max_daily_loss_usd: 10
max_open_positions: 1
max_leverage: 2
```

ここからドル建てで見ると、かなり厳しいです。

```text
avg_return: 0.000664731466
$50 notional での期待 gross: 約 $0.033 / trade
$50 notional の 7 trade 合計 gross: 約 $0.233
月 $100 に必要な trade 数: 約 3009 trades
7 trade sequence で月 $100 に必要な回数: 約 430 sequences
```

この計算は fixture の数字をそのまま信じた場合です。現実には spread、slippage、手数料、約定拒否、待機時間、集中力、ミスが乗ります。つまり、現行の小額 policy と fixture edge の組み合わせは、利益装置としては桁が足りません。

## 摩擦で消える edge

`strategy_backtest_stress.json` はもっと重要です。

| scenario | 追加摩擦 | stressed avg signal return | stressed total return | positive rate |
|---|---:|---:|---:|---:|
| base | 0 bps | 0.0006647315 | 0.0046531203 | 1.0 |
| mild | 5 bps | 0.0001647315 | 0.0011531203 | 1.0 |
| moderate | 10 bps | -0.0003352685 | -0.0023468797 | 0.0 |
| severe | 25 bps | -0.0018352685 | -0.0128468797 | 0.0 |

泥臭い読み方:

- base の edge は約 6.6 bps。
- mild の 5 bps 追加でほぼ消える。
- moderate の 10 bps 追加で全 trade が負け側になる。
- つまり「少し上振れたら儲かる」ではなく、「少し摩擦が増えたら死ぬ」です。

利益を取りに行くなら、最初に見るのは `backtest_passed` ではなく、10 bps 追加摩擦後にまだ残るかです。残らない候補は、きれいなレポートを作る前に捨てる方がいいです。

## paper filled の弱さ

最新 normal paper は:

```text
normal_session_count: 8
fills: 20/20 met
trading_days: 1/10
latest_normal_decision: NEEDS_MORE_PAPER_OBSERVATION
credentials_used: false
external_api_used: false
live_conversion_allowed: false
permits_live_order: false
```

`local-paper-20260617-200702` の ledger を集計すると:

```text
entry_count: 20
status: paper_filled x 20
unique_intents: 1
unique_candidates: 1
created_at range: 2026-06-17T11:07:10Z to 2026-06-17T11:13:45Z
quote_ts: 2026-06-05T07:50:43Z 固定
quote_age_ms: 約 1,048,587,177 から 1,048,982,067
live_order_submitted: false
wallet_used: false
exchange_write_used: false
```

これは「20 回の独立した市場機会で勝った」ではありません。同じ candidate / intent を、同じ古い quote 文脈で、同日に paper filled として積んだものです。paper threshold 上も trading day は 1/10 で止まっています。

利益追求の読み方では、fills 20/20 は褒めません。見るべきは、異なる trading day、異なる quote、異なる市場状態で、net edge が残るかです。

## ご都合主義ナラティブを潰す

| 甘い物語 | 現物での潰し方 |
|---|---|
| 個人は小さいから有利 | 小さいことは容量制約を避けるだけ。edge は別問題。現行 $50 notional では $100/月に桁が足りない |
| backtest PASS だから候補 | PASS は配線確認。サンプル 7、実質 2 日、合成 fixture |
| Sharpe が高い | 7 trade の Sharpe 8300 は判断材料ではない |
| paper fills が 20 ある | unique candidate は 1、trading day は 1/10、quote は古い |
| stress しても mild はプラス | 5 bps でほぼ消え、10 bps で負ける。利益候補としては薄い |
| Workbench first slice 完了 | artifact / review / gate / observation / planning の配線完了。live ready ではない |
| optimizer ledger がある | `strategy-model-run-record` は実行済み trial の記録であり、optimizer 実行でも採用でもない |
| micro live まである | `enabled: false`。標準 CLI に `place-order` 相当は見えない。`micro_live_canary` の発注コードは policy gate の奥 |

## 貪欲に利益を追うなら、こう使う

安全に使う、では足りません。利益を追うなら、時間を食う候補を早く殺す必要があります。

1. 月次目標をドルで書く。
   例: `$100/month`。率ではなくドルで書きます。

2. 現行 notional で必要 trade 数を出す。
   `$50 notional` で 1 trade 約 `$0.033` なら、月 `$100` には約 `3009 trades` が必要です。この時点で、現行 fixture edge は利益目標に合いません。

3. 10 bps 追加摩擦で死ぬ候補は捨てる。
   「本当はもっと低コストで約定できるはず」は物語です。実測が出るまで採用しません。

4. paper filled ではなく、実質的に異なる機会数を見る。
   unique candidate、trading day、quote freshness、市場状態、net return を見ます。fill 数だけで進めません。

5. 勝ち候補より、捨て候補を増やす。
   個人が勝つには、当たりを探すより先に、時間を奪う外れを切る方が効きます。

6. live 導線がないことを前提にする。
   この repo は標準導線で新規 live 発注する場所ではありません。利益化の最後の 1 mile は別設計です。

7. それでも進める候補だけ、手動で paper を続ける。
   10 trading days 未満で勝った気にならない。同日 rerun や fill 水増しは、利益追求ではなく自己欺瞞です。

## 逆に、今やらない方がいいこと

- CLI 189 個を全部理解する。
- UI や viewer を先に磨く。
- model / optimizer の見栄えを増やす。
- artifact を増やして「進んだ感」を作る。
- `PASS` の数を KPI にする。
- fixture PnL を期待利益として語る。
- live permission なしに scale plan を読み替える。

## 次の実務アクション

利益目線で次にやるなら、追加機能ではなく、1 つの候補に対して次を手で作る方がいいです。

```text
strategy_id:
monthly_profit_target_usd:
capital_or_notional_limit_usd:
expected_net_bps_after_all_costs:
required_trade_count_per_month:
observed_trade_count_per_month:
stress_10bps_survives: true/false
paper_trading_days:
unique_market_days:
unique_candidate_count:
quote_freshness_ok: true/false
kill_decision: keep/kill/wait
```

この表で `required_trade_count_per_month` が現実的でない、または `stress_10bps_survives=false` なら、そこで殺します。レポートを厚くするより、その方が利益に近いです。

## 判断

この repo は「儲ける装置」ではありません。「儲かった気になる前に止める装置」です。

ただし、貪欲に利益を追う人にも価値はあります。価値は、夢を守ることではなく、薄い edge、古い quote、同日 paper 水増し、摩擦で死ぬ候補を早く捨てることです。

利益を狙うなら、この repo を信じるのではなく、この repo を使って自分の都合のいい物語を壊してください。
