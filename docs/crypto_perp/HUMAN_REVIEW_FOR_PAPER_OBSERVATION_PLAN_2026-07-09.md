<!--
作成日: 2026-07-09_19:01 JST
更新日: 2026-07-11_18:35 JST
-->

# Human Review Plan For Crypto Perp Paper Observation Candidate

## 結論

現在のpacket判定は`BLOCKED_BY_BIAS_GUARD`、next actionは`FIX_REVIEW_PACKET_BLOCKERS`です。Paper Observationの計画レビューには進めません。

名目14 trades / 10 winsは捨てる数字ではありません。しかしguardはPBO標本条件でBLOCKED、PBO専用証跡はなく、最大6同時positionを資本へ反映していません。5 episode bootstrapは0を跨ぎ、single-position近似は負、selectorはalways-longを下回ります。

## Current Evidence

- bias guard: `BLOCKED`
- guard stop reason: `BIAS_GUARD_FAILED_sample_sufficient_for_pbo`
- guard warning: `BIAS_GUARD_WARNING_stress_cash_non_negative`
- PBO: `NOT_ESTIMABLE`
- fold count: `0`
- `pbo_computed` / `pbo_evidence_verified`: `false / false`
- candidate pack: `BACKTEST_REJECT`
- no-cash gate: `NO_CASH_BACKTEST_REJECT`
- kill report: `KILL_UPSTREAM_GATE_REJECTED`
- leaderboard: `KILL`
- human review packet: `BLOCKED_BY_BIAS_GUARD`
- next action: `FIX_REVIEW_PACKET_BLOCKERS`
- artifact lineage: `PASS`
- input contract: `crypto_perp_human_review_packet_inputs.v2`, strict 12 inputs
- event / outcome: `30 / 30`
- ticker / funding coverage: `30 / 30`、ticker eligibleに余裕なし
- selected simulated trades / wins: `14 / 10`
- backtest / stress: `3.042366783076564551621614274 / 2.762366783076564551621614274 USD`
- peak concurrent positions: `6`
- market episodes / wins: `5 / 3`
- single-position total: `-0.4618201695034107750204885438 USD`
- always-long total: `5.816219911337534249441041925 USD`
- signal score/result correlation: `-0.2902937515082110915592253119`
- short sleeve: `2 losses / -0.4939911498820537167728313263 USD`
- Paper、actual cash、wallet、signing、exchange write、live系flag: 全てfalse

## 現在の停止理由

### BIAS_GUARD_BLOCKED / PBO_NOT_ESTIMABLE

pack defaultの`fold_count=0`ではPBO入力条件を満たさず、guard errorになります。foldを2以上へ変えて`INPUT_THRESHOLD_MET`にしても、PBO値を計算したことにはなりません。`COMPUTED_PASS`文字列だけでも不十分で、専用PBO artifactとlineageを検証するproducerがない現在はREADY不能です。

### POSITION_OVERLAP_NOT_ACCOUNTED

14 tradesの最大同時保有は6です。5 market episodes / 3 winsへ圧縮され、単一position近似は負です。position limit、gross notional、資本拘束を入れないaggregate totalをPaper計画の根拠に使いません。

### INDEPENDENT_MARKET_EPISODE_SAMPLE_NOT_MET

最低10 episodeに対して5です。cutoffは約35時間15分、30件中27件が2026-07-09 UTCへ集中します。trade iid bootstrap 95%は`[+0.1069,+5.7882]`ですが、episode bootstrap 95%は`[-1.9182,+9.2413]`で0を跨ぎます。

### SELECTOR_DOES_NOT_BEAT_BEST_STATIC_ACTION

selector `3.042366783076564551621614274 USD`はalways-long `5.816219911337534249441041925 USD`を下回ります。同じ30 eventsでlong-onlyへ切り替えるのは後付け最適化なので、別期間のout-of-sampleで事前固定比較します。

### EXECUTION_EVIDENCE_THIN

raw491 windowsのうちstrict contractで467がeligible、24がrejectです。ticker-covered eligibleはちょうど30です。books/trades/replayがなく、slippage 50 bpsではtotalが`-3.67763 USD`へ落ちます。実約定摩擦へ強い証拠ではありません。

## Blockerを利益機会へ変える実装条件

1. PBOを実計算し、fold結果・PBO値・閾値・source refを専用artifactへ保存する。
2. 同時保有、gross notional、position limit、資本拘束をbacktest/stressへ反映する。
3. selector、always-long、NO_TRADEを別期間・複数regimeで事前固定比較する。
4. short sleeveを独立標本で再検証し、負け続けるなら事前ルールで切る。
5. episodeを最低10より十分多くし、日付・symbol・regime集中を薄める。
6. books/trades/replayまたはqueue、partial fill、latencyを表現する証拠を追加する。
7. 2/50 bps、notional、operator laborの感応度を継続し、break-even摩擦を監視する。
8. strict v2 12-input lineage、全安全flag、focused/full verificationを再確認する。

## Human Review開始条件

- guardが`PASS`である。
- PBO専用証跡が検証され、`pbo_computed=true`かつ`pbo_evidence_verified=true`である。
- candidate、gate、kill、leaderboardがHOLD chainとして整合する。
- position overlap反映後も利益/risk条件を満たす。
- 独立episode、期間、regime、symbolの外部妥当性がある。
- selectorの追加価値をout-of-sampleで示す。
- artifact lineageが`PASS`、安全flagが全てfalseである。
- branch全体diffと再生成artifactを人間が確認する。

## Non-Goals / Branch Status

Paper Observation開始、paper order、actual cash、wallet、signing、exchange write、live order、profit proofは対象外です。ブランチは未コミット差分を含みmerge不可です。commit、push、merge、cherry-pickは実施していません。
