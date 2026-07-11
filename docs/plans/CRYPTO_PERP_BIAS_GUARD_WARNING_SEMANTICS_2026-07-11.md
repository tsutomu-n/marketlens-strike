<!--
作成日: 2026-07-11_14:09 JST
更新日: 2026-07-11_18:53 JST
-->

# Crypto Perp Bias Guard Warning Semantics Plan

> **Status: SUPERSEDED / HISTORICAL.** この文書はwarning semanticsを導入した時点の計画・検証記録です。末尾のREADY chainは当時の再現結果であり、現行判定ではありません。
>
> 後続hardeningでderived rows常時再計算、strict candle contract、strict v2 12-input packet、PBO専用証跡条件、position診断を追加しました。現在はguard `BLOCKED` / PBO `NOT_ESTIMABLE` / packet `BLOCKED_BY_BIAS_GUARD`です。
>
> 現行計画: [CRYPTO_PERP_PROFIT_EVIDENCE_HARDENING_2026-07-11.md](CRYPTO_PERP_PROFIT_EVIDENCE_HARDENING_2026-07-11.md)

## Checkpoint ID

`BG-WARNING-20260711`

## 目的

全反実仮想アクションの最小stress値を要求する`stress_cash_non_negative`だけを警告へ変更し、実際に選択された方針の収益・stress・drawdown・最大損失・集中リスクは既存の後段gateで引き続き拒否できるようにする。警告はHuman Review Packetまで失わず伝播する。

## 現状

`BiasGuardCheck.severity`は`error`と`warning`を表現できるが、guard構築処理はseverityを設定せず、すべての失敗checkをstop reasonへ変換している。現在の30-event artifactは`stress_cash_non_negative`だけが失敗し、判定チェーン全体が正しくfail-closedで停止している。

## 制約

- 真のerror、guard missing、`NOT_RUN`、未知statusのfail-closed挙動を変えない。
- bias guardの他のcheck、閾値、PBO条件を変えない。
- 選択方針に対する後段の収益・stress・drawdown・最大損失・集中リスク判定を弱めない。
- Paper Observation、paper order、actual cash、wallet、signing、exchange write、live executionを許可しない。
- 現ブランチを継続し、commit、push、merge、cherry-pickを行わない。

## 対象ファイル

- `src/sis/crypto_perp/bias_guards.py`
- `src/sis/crypto_perp/backtest_candidate_pack.py`
- `src/sis/crypto_perp/no_cash_backtest_gate.py`
- `src/sis/crypto_perp/human_review_packet.py`
- `schemas/crypto_perp_human_review_packet.v1.schema.json`
- 対応する`tests/crypto_perp/`のfocused tests
- 現行仕様、第三者向け説明、final summary

## 実装方針

1. `stress_cash_non_negative`だけを`warning` severityにする。
2. failed errorだけを`BIAS_GUARD_FAILED_*` stop reasonにし、failed warningは`BIAS_GUARD_WARNING_*` known gapにする。
3. summaryには全失敗数、error失敗数、warning失敗数を分離して残す。
4. Candidate Pack、No-Cash Gate、Human Review Packetにwarning codeをadditiveに伝播する。
5. guardがwarningのみで`PASS`の場合だけ、既存の選択方針リスク判定へ進める。

## Red-Green手順

1. RED: warning失敗がguardをBLOCKEDにせず、warning codeが残る契約テストを追加する。
2. RED: error失敗は従来どおりBLOCKEDとなる回帰テストを固定する。
3. RED: warning codeがcandidate、gate、packetまで残る統合テストを追加する。
4. GREEN: severity別集計と警告伝播を最小実装する。
5. REFACTOR: 重複抽出を局所helperに限定し、公開schema変更をadditiveに保つ。

## テスト方針

- focused: bias guard、candidate pack、no-cash gate、human review packet。
- 回帰: BLOCKED、missing、unknownがHOLD/READYへ進まないこと。
- artifact: 既存30-event inputを再利用して全段を再生成する。
- safety: 全artifactのpaper、cash、wallet、signing、exchange write、live flagがfalseであること。
- full: docs、CLI catalog、diff check、CLI help、`./scripts/check`。

## 完了条件

- warning-only guardは`PASS`だが警告がpacketまで追跡できる。
- error guardとstatus不明は引き続き停止する。
- 現30-event artifactの実判定が既存の選択方針gateを通過する場合のみREADYとなる。
- 全安全flagがfalseで、focused/full checksが成功する。

## 失敗条件

- warningが後段artifactから消える。
- error failureがPASSになる。
- gateの選択方針stressまたは損失判定が弱まる。
- READYがPaper Observationや注文許可と誤解できる出力になる。

## 影響範囲と移行

既存reader互換を維持するadditive fieldのみ追加する。新規生成物はwarning codeを必ず出力する。古いartifactにfieldがない場合は空配列として扱う。

## ロールバック

本checkpointの差分だけを手動で戻し、既存artifactを再生成すれば、現在のerror扱いと停止チェーンへ戻せる。破壊的git操作は使わない。

## 代替案と却下理由

- check削除: 診断情報が消えるため却下。
- 全stress判定を削除: 選択方針の下流リスク防御まで弱めるため却下。
- 現状維持: 非選択反実仮想の単一損失で現実的候補を恒久停止するため却下。

## 未解決事項

この変更は現在の30-event標本の独立性、単一regime、日付集中、収益再現性を解決しない。これらはHuman Reviewで明示し、Paper/cash許可とは分離する。

## Implementation Result

- RED: warning semantics、error回帰、candidate/gate/packet伝播の5 failureを確認した。
- GREEN: `stress_cash_non_negative`だけをwarningにし、error stop reasonとwarning known gapを分離した。
- Migration: 同じevent setとSHAでも旧`severity=error` contractのguardは再利用せず、再計算する回帰テストを追加した。
- Reproduction: Candidate Pack再生成では`--fold-count 2`を明示し、PBOを`ESTIMATED`として再現した。省略時の既定値0は安全側の`NOT_ESTIMABLE`となる。
- Current chain: `PASS` + warning -> `BACKTEST_CANDIDATE_HOLD` -> `NO_CASH_BACKTEST_HOLD` -> `HOLD_FOR_LEADERBOARD` -> `HOLD_FOR_HUMAN_REVIEW` -> `READY_FOR_HUMAN_REVIEW_PLANNING`。
- Warning: `BIAS_GUARD_WARNING_stress_cash_non_negative`はCandidate Pack、Gate、Human Review Packetへ伝播する。
- Safety: Paper、actual cash、wallet、signing、exchange write、live orderの全flagはfalse。
- Focused verification: 60 tests passed。
- Full verification: Ruff、format、current docs 160、CLI catalog 241、Pyrefly、ty、Pytest 2974が成功した。
- Git: commit、push、merge、cherry-pickは未実施。branch全体のmerge holdを維持する。
