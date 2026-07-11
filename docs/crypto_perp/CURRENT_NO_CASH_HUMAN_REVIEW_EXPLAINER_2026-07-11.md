<!--
作成日: 2026-07-11_12:13 JST
更新日: 2026-07-11_20:38 JST
-->

# Crypto Perp No-Cash判定チェーンの現在地

## 結論

現在の30-event artifactは、人間レビュー計画へ進める状態ではありません。名目損益とtrade単位の統計には追う価値がある一方、guardはPBO標本条件でBLOCKED、独立性に近い5 episodeの損益分布は0を跨ぎ、position overlapを除くと損益は負です。攻めるべき仮説は残っていますが、今ここで昇格させるのは利益追求ではなく、薄い証拠への過払いです。

```text
bias guard         = BLOCKED
guard stop reason  = BIAS_GUARD_FAILED_sample_sufficient_for_pbo
warning            = BIAS_GUARD_WARNING_stress_cash_non_negative
pbo status         = NOT_ESTIMABLE
pbo computed       = false
candidate pack     = BACKTEST_REJECT
candidate reasons  = BIAS_GUARD_BLOCKED,
                     BIAS_GUARD_FAILED_sample_sufficient_for_pbo,
                     POSITION_OVERLAP_NOT_ACCOUNTED,
                     INDEPENDENT_MARKET_EPISODE_SAMPLE_NOT_MET,
                     SELECTOR_DOES_NOT_BEAT_BEST_STATIC_ACTION
no-cash gate       = NO_CASH_BACKTEST_REJECT
kill report        = KILL_UPSTREAM_GATE_REJECTED
leaderboard        = KILL
human review packet= BLOCKED_BY_BIAS_GUARD
next action        = FIX_REVIEW_PACKET_BLOCKERS
artifact lineage   = PASS
```

pack defaultは`fold_count=0`です。eventが30あってもPBO入力条件を満たさず、`pbo_status=NOT_ESTIMABLE`になります。さらに`COMPUTED_PASS`という文字列だけでは不十分で、専用PBO計算証跡とlineageを検証するproducerがない現在は`pbo_evidence_verified=false`です。READYは到達不能です。

Paper Observation、paper order、actual cash、wallet、signing、exchange write、live orderの関連flagはすべてfalseです。

## Repo全体における位置づけ

`marketlens-strike`はPython 3.13 / Typerベースのresearch、read-only evidence、backtest、paper safety gateを扱うCLI workspaceです。今回の対象はCrypto Perpのno-cash laneだけで、venueへの発注、実口座の約定実績、利益証明を作る作業ではありません。

```text
公開市場データ
  -> timestamp-safe event / outcome / source evidence
  -> tournament rowsとbias guard
  -> Backtest Candidate Pack
  -> No-Cash Backtest Gate
  -> NO_TRADE Kill Report
  -> Candidate Leaderboard
  -> Human Review Packet
```

後段は上流artifactのschema、raw SHA、event/outcome pair、execution window、decision、boundaryを再検査します。新規packetはstrict v2 input contractで12入力を固定し、古いartifactや矛盾した入力を混ぜて停止判定を昇格させる経路を閉じています。

Candidate Packも全`market_window_v1`をmutable labelに関係なくraw candleへ戻して検証します。dogfood fixtureとraw provenanceを再構築できない非market eventはCOLLECTで、ticker/funding availableの自己申告もraw status不一致なら拒否します。

## 利益を取りに行くうえでの実測

### 1. trade単位の見た目は改善したが、独立利益の証明ではない

14 trades中10 wins、nominal totalは`+3.042366783076564551621614274 USD`です。naive iid t=`2.0179`、one-sided sign p=`0.0898`、trade iid bootstrap total 95% interval=`[+0.1069,+5.7882]`なので、仮説を捨てる数字ではありません。

ただし60分holdingに対してsignalが重なり、最大同時保有は6です。時間重複をまとめると5 market episodes / 3 winsにしかならず、episode bootstrap total 95% intervalは`[-1.9182,+9.2413]`で0を跨ぎます。単一position近似は`-0.4618201695034107750204885438 USD`です。tradeを14個のiid賭けとして扱うと、資本拘束と共通市場ショックを無視して確信度を水増しします。

正利益episodeの集中も高く、largest shareは約`0.716`、top-2 shareは約`0.997`です。Kill Reportのepisode閾値`0.60 / 0.80`を超えますが、現在は上流gate rejectが先に効くため最終chainはKILLのままです。

Kill Reportはこのepisode totalsを自己申告値として信頼せず、pack-local execution windowsとbacktest resultsから再計算し、reported totalsと完全一致する場合だけ集中判定へ使います。

### 2. 標本は約35時間15分、実質1日に集中している

30 eventsはBTCUSDT単一symbolです。cutoff spanは`2026-07-07T21:35Z`から`2026-07-09T08:50Z`まで約35時間15分ですが、日付別は2026-07-07が3件、2026-07-09が27件です。複数regime・複数週・複数symbolの証拠ではありません。

### 3. selectorは単純always-longに負けている

selector total `3.042366783076564551621614274 USD`に対し、同じrowsの`CONTINUATION_LONG`固定は`5.816219911337534249441041925 USD`です。score/result correlationも`-0.2902937515082110915592253119`です。複雑さが追加利益を生んでおらず、`SELECTOR_DOES_NOT_BEAT_BEST_STATIC_ACTION`を停止理由に残します。

### 4. short sleeveは全敗している

`REVERSAL_SHORT`は2 trades、2 losses、合計`-0.4939911498820537167728313263 USD`です。shortを今すぐ削るのも同一標本への後付け最適化です。別期間で事前固定したlong-only / selector / NO_TRADEを競わせ、負ける袖を切るのが実務的です。

### 5. cost感応度は直った

Candidate Packは既存derived rowsを一切信用せず、matured outcomesから常時再計算します。同一eventの複数outcome/duplicate event IDはexit code 2です。

同じselected sampleで、slippage 2 bps / notional 100 USDは`+3.04237 USD`、slippage 50 bpsは`-3.67763 USD`、notional 1000 USDは`+30.42367 USD`です。3ケースの`tournament_rows_v2.json` SHA-256はすべて異なります。cost変更を無視して旧rowsを再利用するbugは閉じました。

これは重要な前進ですが、50 bpsで負へ落ちることは実約定摩擦への感応度が高いことも示します。operator laborは0のままで、運用コスト未計上です。

## Source selectionの現実

source candleからのraw candidateは491です。strict timestamp/window検査後のeligibleは467、rejectは24です。

- `ENTRY_NOT_NEXT_COMPLETE_BAR`: 2
- `FULL_HORIZON_CANDLES_NOT_CONTIGUOUS`: 11
- `LOOKBACK_CANDLES_NOT_CONTIGUOUS`: 11

input CSV / source rowsはtimestampがuniqueかつstrict increasing、`available_at >= ts + interval`、連続lookback、entryがcutoff+5分の最初の完全bar、60分full horizonが連続していることを要求します。ticker-covered eligibleはtargetと同じ30件だけで、予備の31件目がありません。1件壊れればsample再生成が停止する薄い供給です。

さらにOHLCは有限かつ正で、high/lowがopen/closeを包含し、base/quote volumeは負でないことを要求します。timestampだけ正しい壊れたbarでevent/outcomeを再構築しません。

## 現在の30-event evidence

| 項目 | 現在値 | 実務上の読み方 |
|---|---:|---|
| event / outcome | 30 / 30 | 同一symbol、短期間、27件が同一UTC日 |
| selected simulated trades / wins | 14 / 10 | iid前提では見栄えが良いが依存あり |
| backtest total | 3.042366783076564551621614274 USD | 同時保有を許したlocal estimate |
| stress total | 2.762366783076564551621614274 USD | selected-policyのlocal stress estimate |
| peak concurrent positions | 6 | position overlapを損益判定へ未反映 |
| market episodes / wins | 5 / 3 | episode bootstrapは0を跨ぐ |
| single-position total | -0.4618201695034107750204885438 USD | 重複を排した近似は負 |
| always-long total | 5.816219911337534249441041925 USD | selectorが単純基準を下回る |
| score / result correlation | -0.2902937515082110915592253119 | ranking signalを支持しない |
| short sleeve | 2 losses / -0.4939911498820537167728313263 USD | short edgeを支持しない |
| trade iid bootstrap 95% | +0.1069 to +5.7882 USD | dependenceを無視した参考値 |
| episode bootstrap 95% | -1.9182 to +9.2413 USD | 0を跨ぎ不確実 |
| PBO | NOT_ESTIMABLE / computed=false | fold_count=0、専用証跡なし |
| operator labor | 0 USD | 労務費を未計上 |
| artifact lineage | PASS | 同一run整合。経済妥当性ではない |

## Bias GuardとPBOの読み方

現在のguardは`BLOCKED`です。error stop reasonは`BIAS_GUARD_FAILED_sample_sufficient_for_pbo`、診断warningは`BIAS_GUARD_WARNING_stress_cash_non_negative`です。後者は選択されなかった反実仮想actionを含む非`NO_TRADE` rowに負のstress値があることを示します。

fold数を増やして`INPUT_THRESHOLD_MET`へ変えてもPBOは計算されません。`COMPUTED_PASS`文字列の偽装も、専用証跡を検証できないためPacketで止まります。必要なのは実際のPBO計算、fold結果、閾値、source refを持つproducerです。

## Artifact lineage

packet lineageは`PASS`です。pack-local rows/guard、12入力のraw SHA、schema、event/outcome pair、entry/horizon、decision chainを照合しています。出力は`input_contract_version=crypto_perp_human_review_packet_inputs.v2`です。fieldがない旧v1はread-compatibleですが、新規v2と同じ強度の証拠とは扱いません。

lineage PASSは同じrunがつながっている証明であり、外部妥当性、PBO、執行可能性、将来利益の証明ではありません。

## 残リスク

- 30 events、5 episodes、ticker eligibleちょうど30は小標本で余裕がありません。
- 同一symbol、約35時間、27/30が同一UTC日です。
- books、trades、replayがありません。
- candle local simulationはqueue、spread変動、partial fill、latency、liquidation条件を再現しません。
- 50 bps摩擦で損益が負になります。
- 正利益の約99.7%が上位2 market episodesへ集中しています。
- operator labor costは0です。
- 反実仮想actionに負のstress rowがあります。
- rolling stability完走は複数regimeの安定性ではありません。
- raw candle/ticker/funding再構築はlocal JSON改変を検出しますが、取引所配信の完全性、欠落の不存在、上流sourceの真正性までは証明しません。

## 安全境界とMerge判断

`paper_permission_granted`、`permits_paper_order`、`permits_live_order`、`actual_cash_used`、`profit_proven`、`wallet_used`、`signing_used`、`exchange_write_used`、`live_order_submitted`はすべてfalseです。

focused contract listはcount=249 / 11.80s、targeted hostile re-reviewはcount=44 / 2.56s、最終local `./scripts/check`はPytest count=3134 / 89.06sでPASSしました。hostile 3 findingsは解消し、新規blockerはありません。runtime validator、lineage/safety、diff reviewもPASSし、判定chainは不変です。ブランチ全体はPR #42としてcommit・pushされ、`main`へsquash merge済みです。merge commitは`a184915`で、PR headのCI 2本とmerge後の`main` CIはいずれも成功しました。`9c8de64`だけのcherry-pickは行っていません。runtime `data/`、`.tmp/`、`.ai-work/`はGitへ含めていません。
