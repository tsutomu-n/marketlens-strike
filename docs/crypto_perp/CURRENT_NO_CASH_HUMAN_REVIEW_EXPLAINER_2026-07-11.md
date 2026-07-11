<!--
作成日: 2026-07-11_11:41 JST
更新日: 2026-07-11_11:48 JST
-->

# Crypto Perp No-Cash 検証と人間レビューの現在地

## 結論

現在行っているのは、`marketlens-strike` の Crypto Perp 研究経路で、実資金も注文も使わず、公開市場データから作った局所シミュレーション候補を人間レビューに掛ける作業である。

30イベント分の ticker・funding を含む入力、13件のシミュレーション取引、コスト・stress・損失集中・`NO_TRADE` 比較まで生成され、表面的な後段 artifact は次を返している。

- candidate pack: `BACKTEST_CANDIDATE_HOLD`
- no-cash gate: `NO_CASH_BACKTEST_HOLD`
- human review packet: `READY_FOR_HUMAN_REVIEW_PLANNING`

しかし、上流の bias guard は `guard_status=BLOCKED` を返している。停止理由は `BIAS_GUARD_FAILED_stress_cash_non_negative` で、分割評価における最小 stress cash estimate は `-0.9466849592582005517888171228 USD` である。

現行の no-cash gate は `pbo_status` を読む一方、`bias_guard_status` を停止判定に使っていない。このため、現在の HOLD / READY は一連の証拠が整合した承認判定ではない。人間レビューの現時点の結論は次のとおりである。

> ローカル検証結果の分析と修正計画には使えるが、Paper Observation の実施計画、paper order、実資金、ライブ運用へ進む根拠には使えない。先に bias guard を後段ゲートへ fail-closed で接続し、artifact を再生成して再判定する必要がある。

## この文書の対象読者

Repo が市場調査、backtest、paper workflow、安全ゲートを持つ Python CLI workspace であることだけを知り、今回のセッション履歴や Crypto Perp artifact の詳細を知らない第三者を対象とする。

この文書は次を説明する。

1. Repo 全体の中で今回の作業がどこに位置するか。
2. どのデータを使い、どの順に artifact を作ったか。
3. 何が確認でき、何が確認できていないか。
4. なぜ自動 artifact の HOLD をそのまま採用できないか。
5. 次に何を直し、どの条件で人間レビューをやり直すか。

## Repo の概要と今回の位置づけ

`marketlens-strike` は Python 3.13 / Typer ベースの CLI workspace である。主な責任範囲は次のとおりである。

| 領域 | 役割 | 今回との関係 |
|---|---|---|
| research / Strategy Lab | 仮説、特徴量、候補、研究 artifact を扱う | 背景となる研究基盤 |
| backtest | 履歴・局所データ上で候補挙動を評価する | 今回の中心 |
| paper | 実注文ではない観測・記録 workflow | 将来候補。現在は未許可 |
| execution / risk | 注文・リスク境界を扱う | 今回は使用禁止 |
| tracking / validation | artifact lineage、schema、状態を検証する | 今回の証拠管理に関係 |
| venues | venue 固有の読取・接続処理 | 今回は Bitget 公開データの読取だけ |

Repo のデフォルト軸は research/backtest-first であり、Trade[XYZ] やライブ注文は今回の主題ではない。今回の作業は Crypto Perp の no-cash lane に限定される。

## 用語

| 用語 | この文書での意味 | 意味しないもの |
|---|---|---|
| no-cash | 実資金、cash ledger、wallet、signing、exchange write を使わない検証 | 無リスク、利益確定、実運用可能 |
| real-market | 公開市場データを入力に使った | 実約定、実注文、板再現、ライブ実績 |
| local simulation | ローカルで価格 proxy とコスト仮定から損益を再計算した | 取引所での fill 再現 |
| HOLD | 候補を即時 reject せず、人間判断まで保持する内部判定 | Paper Observation permission |
| Paper Observation | 実資金を使わず、将来時点のシグナルや想定挙動を観測・記録する段階 | paper order permission や発注 |
| paper order | paper 環境への注文操作 | 単なる観測 |
| bias guard | lookahead、標本量、stress、利益集中などの偏り・脆弱性を検査する artifact | 全リスクを保証する証明 |
| PBO | overfitting の可能性に関する推定状態 | bias guard 全体の PASS |
| `NO_TRADE` | 取引しない場合のゼロ exposure baseline | リスクなしの実現損益 |
| fail-closed | 必須入力が失敗・不明・矛盾なら、先へ進めず停止する | 失敗を known gap として通過させること |

## 許可境界

現 artifact による許可状態は次のとおりである。

| 操作・主張 | 現在の状態 | 根拠 |
|---|---|---|
| ローカル artifact の閲覧・再計算 | 可 | no-cash の範囲内 |
| 人間による証拠レビュー | 可 | `required_human_review=true` |
| 修正計画の作成 | 可 | 外部副作用なし |
| Paper Observation の開始 | 不可 | 明示的 permission artifact がない |
| paper order | 不可 | `permits_paper_order=false` |
| live order | 不可 | `permits_live_order=false` |
| 実資金使用 | 不可・未実施 | `actual_cash_used=false` |
| wallet / signing | 不可・未実施 | 各 boundary flag が false |
| exchange write | 不可・未実施 | `exchange_write_used=false` |
| 利益証明 | 不可 | `profit_proven=false` |
| ライブ準備完了の主張 | 不可 | `NOT_LIVE_READINESS` |

`READY_FOR_HUMAN_REVIEW_PLANNING` はレビュー資料が揃ったという packet の状態であり、Paper Observation を許可する状態ではない。

## 実施した処理

### 1. 公開データの収集と時点整合

Bitget の公開 source から BTCUSDT の candle、ticker snapshot、funding を収集した。外部への注文、秘密情報、wallet、signing は使っていない。

ticker は過去へ遡って完全復元できないため、forward-only で snapshot を蓄積し、各イベント時点で利用可能だった ticker を要求した。30イベント分の ticker coverage が成熟するまで待ち、未来情報を信号へ混ぜない条件で sample を選んだ。

### 2. ticker-required sample の生成

入力の入口は `data/crypto_perp/real_market_no_cash/ticker_required/selection_manifest.json` である。

確認された値:

- symbol: `BTCUSDT`
- event count: `30`
- outcome count: `30`
- ticker available: `30 / 30`
- funding available: `30 / 30`
- selection policy: `time_evenly_spaced_before_outcome; no outcome-favorable filtering; require_ticker_coverage=true`
- ticker maximum staleness: `900` 秒

この sample は outcome を信号生成後に評価する構造を持つが、公開 candle だけを使う局所 sample であり、板・個別約定・replay は含まない。

### 3. Backtest Candidate Pack の生成

`crypto-perp-backtest-candidate-pack` が、イベントごとの source availability、最小 feature、edge score、signal、execution assumptions、backtest、stress、regime split、rolling stability を生成した。

主な実行仮定:

- position size: `100 USD`
- entry proxy: signal 後の次の 5 分足 open
- exit proxy: matured outcome の最初の horizon close
- maximum holding: `60` 分
- taker fee rate: `0.0004`
- funding rate assumption: `0.0001`
- slippage: `2 bps`
- zero cost: 禁止

feature pack と edge score は各30件、合計60 artifact が `recomputed_minimal` である。したがって、証拠 grade は `local_simulation_with_recomputed_minimal_artifacts`、最強の証拠レベルは `recomputed_minimal_simulated_estimate` に留まる。

### 4. No-Cash Backtest Gate

no-cash gate は、最低イベント数、最低取引数、critical source、未来情報、rolling stability、PBO status、総損益、stress 損益、drawdown、最大損失比率を検査する。

現 artifact は次を返した。

- `gate_decision=NO_CASH_BACKTEST_HOLD`
- `blocker_count=0`
- `permits_paper_order=false`
- `permits_live_order=false`
- `actual_cash_used=false`
- `profit_proven=false`

ただし後述のとおり、bias guard 全体の status を入力として停止判定していない。

### 5. NO_TRADE Kill Report

`NO_TRADE` と比べて、取引候補がコスト控除後、stress 後、損失集中・利益集中の閾値後にも残るかを検査した。

現判定は `HOLD_FOR_LEADERBOARD` である。これは「即時 kill 条件に該当しなかった」という意味であり、独立標本、再現可能な fill、将来利益を保証しない。

### 6. Candidate Leaderboard と Human Review Packet

候補は1件だけで、leaderboard は `HOLD_FOR_HUMAN_REVIEW` を返した。複数候補間の強い比較ではなく、単一候補を次の判断へ送る形式である。

human review packet は7つの入力 artifact と既知 gap、レビュー質問、安全境界を束ね、`READY_FOR_HUMAN_REVIEW_PLANNING` を返した。

## Artifact の流れ

| 段階 | 主な入力 | 主な出力 | 現在値 |
|---|---|---|---|
| sample selection | public candles、ticker、funding | `selection_manifest.json` | 30件 coverage 完了 |
| tournament / bias check | event outcomes と3 action rows | `tournament_rows_v2.json`、`bias_guard.json` | bias guard `BLOCKED` |
| candidate pack | event / outcome / source artifacts | `decision.json`、backtest、stress 等 | `BACKTEST_CANDIDATE_HOLD` |
| no-cash gate | candidate pack 一式 | `no_cash_backtest_gate.json` | `NO_CASH_BACKTEST_HOLD` |
| kill report | signal、backtest、stress、tournament | `no_trade_kill_report.json` | `HOLD_FOR_LEADERBOARD` |
| leaderboard | decision、results、kill report、gate | `candidate_leaderboard.json` | `HOLD_FOR_HUMAN_REVIEW` |
| review packet | 上記の束 | `human_review_packet.json` | `READY_FOR_HUMAN_REVIEW_PLANNING` |

## Artifact の保存・hash・再現性

現評価に使った `data/crypto_perp/real_market_no_cash/` 以下は `.gitignore` の `data/` 規則に該当し、Git 管理されていない。したがって、branch `ai/human-review-packet-20260709-2200` や commit `496fec5` だけを取得しても、ここに記載した runtime artifact が自動的に付属するとは限らない。

human review packet は7つの入力 path と hash を `source_refs` に保持する。2026-07-11 の二次確認では、producer と同じ計算方法で7入力すべてが一致した。

ただし `source_refs[].sha256` の値は、一般的な raw file bytes の `sha256sum` ではない。実装は file text を一要素の list に入れ、canonical JSON 化した値へ SHA-256 を適用する `stable_hash([file_text])` 方式である。このため通常の `sha256sum <file>` とは一致しない。検証時は producer と同じ実装を使う必要がある。

この命名は誤読余地がある。今回の scope では schema や hash 方式を変更していないが、将来は次のいずれかを契約として明示すべきである。

- field 名どおり raw file SHA-256 に統一する。
- 現方式を維持し、algorithm / canonicalization を schema と docs に明示する。

また、Git 管理外 artifact を第三者へ渡す場合は、artifact bundle、manifest、producer version、source-ref verification command を一緒に保存しなければ、commit だけから同一判断を監査できない。

## 定量結果

### 標本と行動

| 指標 | 値 |
|---|---:|
| event | 30 |
| simulated trade | 13 |
| `NO_TRADE` | 17 |
| `CONTINUATION_LONG` | 11 |
| `REVERSAL_SHORT` | 2 |
| unknown | 0 |
| critical missing | 0 |
| future signal source | 0 |

13取引中、long が11件、short が2件である。short 2件はいずれも損失だった。方向別の頑健性を判断できる標本ではない。

### 損益とリスク

| 指標 | 通常 | stress |
|---|---:|---:|
| total result | `2.4579533230 USD` | `2.1979533230 USD` |
| average per event | `0.0819317774 USD` | `0.0732651108 USD` |
| simulated-trade win rate | `69.2307%` | `69.2307%` |
| max drawdown | `-0.9032395041 USD` | `-0.9432395041 USD` |

通常結果に対する最大 drawdown の絶対値は約 `36.75%` である。no-cash gate の閾値 `100%` 以内だが、標本が小さく集中しているため、この比率を安定したリスク特性とは扱えない。

### コスト

| 項目 | 値 |
|---|---:|
| fee drag | `1.04 USD` |
| funding drag | `0.01625 USD` |
| slippage drag | `0.26 USD` |
| total modeled drag | `1.31625 USD` |
| net total result | `2.4579533230 USD` |
| cost-before-drag 相当 | `3.7742033230 USD` |

modeled cost は cost-before-drag 相当額の約 `34.9%` を占める。aggregate stress 後も正だが、コストへの感応度は小さくない。books / trades / replay がないため、2 bps slippage や next-open proxy が実際の fill を十分に近似するかは確認できない。

### 集中度

- largest win concentration: 約 `18.57%`
- top-2 win concentration: 約 `35.98%`
- largest loss concentration: 約 `33.34%`
- largest loss / total result: 約 `19.55%`
- total loss: `1.4414974383 USD`

設定済み kill threshold 内には収まる。ただし threshold pass は標本独立性や外部妥当性を保証しない。

## 標本の独立性と代表性

30件という件数だけでは、30の独立した市場局面を意味しない。

確認済みの集中:

- 全30件が `BTCUSDT`。
- 30件中27件が `2026-07-09 UTC`、残り3件が `2026-07-07 UTC`。
- `2026-07-09` の27件は `03:55Z` から `08:50Z` の約5時間に集中。
- regime split は `market_window_v1` の1種類だけ。
- 13取引中11件が long。
- 複数の取引信号が5分間隔で並ぶ一方、outcome horizon / maximum holding は60分。

このため、隣接イベントが同じ将来60分の価格変動を共有し得る。event row は別でも、損益観測は統計的に強く相関している可能性がある。現 artifact には effective independent sample size、block bootstrap、日別 out-of-sample、複数 regime、複数銘柄による検証がない。

したがって `event_count=30`、`rolling_stability_status=complete`、`pbo_status=ESTIMATED` を、十分な期間・局面での頑健性と読み替えてはならない。

## 重大なゲート矛盾

### 確認された事実

`data/crypto_perp/real_market_no_cash/ticker_required/aggregate/bias_guard.json` は次を持つ。

- `guard_status=BLOCKED`
- `pbo_status=ESTIMATED`
- failed check: `stress_cash_non_negative`
- observed minimum: `-0.9466849592582005517888171228`
- stop reason: `BIAS_GUARD_FAILED_stress_cash_non_negative`

candidate pack の summary は同じ `bias_guard_status=BLOCKED` と `pbo_status=ESTIMATED` を記録する。それにもかかわらず candidate decision は `BACKTEST_CANDIDATE_HOLD` である。

no-cash gate 実装は candidate summary から `pbo_status` を読み、`ESTIMATED` を通過状態として扱う。しかし `bias_guard_status` を読み取って blocker に変換していない。その結果、上流の停止理由が後段で失われ、`blocker_count=0` と `NO_CASH_BACKTEST_HOLD` が生成された。

### 誤解してはいけない点

aggregate stress total が `+2.1979533230 USD` で、bias guard の minimum stress cash が負であること自体は、直ちに計算矛盾とは限らない。前者は選択された取引全体の集計、後者は bias guard 内の分割・action 評価の最小値であり、集計単位が異なる。

問題は、より細かい評価で `BLOCKED` が出たにもかかわらず、後段 gate がその status を契約上消費せず HOLD を返したことである。

### テストの抜け

関連 focused tests 36件は通過した。しかし no-cash gate の test fixture は `bias_guard_status=PASS` を設定し、`BLOCKED` の時に gate が停止する回帰ケースを持たない。テスト green は現契約の整合性を証明していない。

## 追加の実装リスク

### Bias guard artifact の lineage 照合

candidate pack は tournament rows を event ID set の一致で再利用する。一方、既存 bias guard は現在、`event_count` の一致だけで探索・再利用する。

現 artifact が実際に別 event set のものだと断定する証拠はない。しかし同じ件数の異なる event set が data tree に存在した場合、誤った bias guard を再利用できる設計余地がある。次の修正では、bias guard の `source_refs` または tournament rows artifact ID / hash と現在入力を照合すべきである。

### Recomputed minimal artifacts

feature pack と edge score は各イベントについて minimal 再計算されている。既存の豊富な feature artifact を評価したのではない。これは再現可能な局所計算には有用だが、実運用シグナルの完全性を示さない。

### Optional source の扱い

books、trades、replay は現ゲート設定で optional であり、欠落は blocker ではなく known gap に送られる。この判断は no-cash の初期候補選別としては説明可能だが、fill 品質や短期価格衝撃を評価する段階では不足する。

## 人間レビュー質問への回答

| 質問 | 現時点の回答 | 理由 |
|---|---|---|
| books / trades / replay 不足を許容できるか | 修正計画の議論には可。Paper Observation 実施判断には未確定 | fill / slippage / replay fidelity が未検証 |
| `NO_TRADE` 比較は計画に十分か | 単独では不十分 | 小標本・時間集中・方向集中がある |
| kill report は候補を残すか | 設定済み閾値上は残す | ただし bias guard BLOCKED が優先 |
| leaderboard は候補を残すか | artifact 上は残す | 候補1件で、上流停止を継承していない |
| permission flags は安全か | false のまま | 境界 flag 自体は維持されている |
| drawdown / loss concentration は許容か | kill threshold 内だが、十分な証拠ではない | 13取引、相関標本、1 regime |
| cost assumptions は許容か | 局所感応度試験には可 | 実 fill の根拠には不可 |
| 追加 source coverage が必要か | gate 修正後に再判定。Paper Observation 実施前には必要性を仕様化すべき | 現仕様に最低要件がない |

## 現在の判断

### 続行してよい作業

- artifact とコードの read-only 調査
- bias guard / gate 契約の修正計画
- fail-closed regression test の追加
- lineage 照合の強化
- 同じ no-cash 入力からの artifact 再生成
- 修正後の人間レビュー

### 現在停止すべき作業

- Paper Observation session の開始
- paper order の作成・送信
- actual cash ledger の作成を前提にした昇格
- wallet / signing / exchange write の利用
- live order、tiny-live、production live の計画・実行
- 利益、再現性、ライブ準備完了の対外的主張

## 次の修正

優先順位は次のとおりである。

1. `bias_guard_status` が `PASS` 系以外なら candidate pack または no-cash gate が必ず停止する契約を決める。
2. `BLOCKED`、missing、unknown status を fail-closed にする回帰テストを先に追加する。
3. candidate decision、no-cash gate、kill report、leaderboard、human review packet に停止理由を伝播する。
4. bias guard の再利用を event count だけでなく、対応する tournament rows / source hash で検証する。
5. current no-cash input から全後段 artifact を再生成する。
6. source ref hash、decision、reason code、安全 flag を再照合する。
7. focused tests、docs check、CLI catalog、full `./scripts/check` を実行する。
8. 修正後 artifact に基づき、人間レビューを最初からやり直す。

修正後も自動的に Paper Observation permission は出さない。まず「Paper Observation を計画するために必要な観測期間、独立局面、方向別取引数、source coverage、停止閾値」を別仕様として決める必要がある。

## 修正の完了条件

- `bias_guard_status=BLOCKED` の fixture で後段が HOLD / READY を返さない。
- `bias_guard_status` missing / unknown も通過しない。
- stop reason が human review packet まで欠落せず伝播する。
- bias guard の lineage が現在の tournament rows と一致する。
- permission / actual-cash / live boundary flag はすべて false のまま。
- regenerated artifact の source refs と hashes が現入力に一致する。
- current docs と CLI catalog checker が通る。
- full test の実行結果と未実行項目が記録される。

## 現時点で未定義・未確認の事項

次は現 artifact からは答えられず、完了した事実として扱えない。

- Paper Observation 計画に必要な最低暦日数。
- 重複しない独立 horizon の最低数。
- long / short 方向別の最低取引数。
- 複数 volatility / trend regime の最低 coverage。
- books、trades、replay のうち、どれを Paper Observation 前の必須 source とするか。
- slippage 2 bps の実測妥当性。
- next-5m-open proxy と実際の fill の乖離。
- funding rate assumption と保有時刻の実際の課金整合。
- latency、partial fill、queue position、market impact、liquidation、margin の再現性。
- out-of-sample 期間、walk-forward、block-aware resampling の合格条件。
- 単一候補 leaderboard を比較評価と呼べる最低候補数。
- Paper Observation を開始・停止・昇格する人間責任者と承認 artifact。

これらは今回割愛したのではなく、現在の Repo 契約または artifact で未定義・未証明の項目である。

## 検証済み事項と未実行事項

2026-07-11 の read-only review で確認した事項:

- Git branch: `ai/human-review-packet-20260709-2200`
- HEAD: `496fec5`
- upstream divergence: `0 / 0`
- review 開始時 worktree: clean
- relevant focused tests: `36 passed`
- current docs checker: `160` docs passed
- CLI catalog checker: `241` commands passed
- full `./scripts/check`: `2953 passed`。Ruff、format check、current docs、CLI catalog、Pyrefly、ty を含めて成功
- bias guard、candidate pack、gate、kill report、leaderboard、human review packet の current artifact 内容
- gate と candidate pack の関連コード
- human review packet の7 source refs が producer の `stable_hash([file_text])` 方式で current input と一致すること
- current runtime artifact が Git ignore 対象であること

このレビュー時点で未実行:

- artifact の再生成
- fail-closed 修正
- Paper Observation
- paper / live / actual-cash 操作

固定 pass count は将来変わり得るため、現在確認にはコマンドを再実行する。

## 正本と入口

実装上の正本:

- `src/sis/crypto_perp/backtest_candidate_pack.py`
- `src/sis/crypto_perp/no_cash_backtest_gate.py`
- `src/sis/crypto_perp/no_trade_kill_report.py`
- `src/sis/crypto_perp/candidate_leaderboard.py`
- `src/sis/crypto_perp/human_review_packet.py`
- `tests/crypto_perp/`
- `schemas/`
- `configs/cost_models/crypto_perp_bitget_usdt_futures.yaml`

current artifact:

- `data/crypto_perp/real_market_no_cash/ticker_required/selection_manifest.json`
- `data/crypto_perp/real_market_no_cash/ticker_required/aggregate/bias_guard.json`
- `data/crypto_perp/real_market_no_cash/backtest_candidate_pack/latest/decision.json`
- `data/crypto_perp/real_market_no_cash/backtest_candidate_pack/latest/backtest_result.json`
- `data/crypto_perp/real_market_no_cash/backtest_candidate_pack/latest/stress_result.json`
- `data/crypto_perp/real_market_no_cash/no_cash_backtest_gate/latest/no_cash_backtest_gate.json`
- `data/crypto_perp/real_market_no_cash/no_trade_kill_report/latest/no_trade_kill_report.json`
- `data/crypto_perp/real_market_no_cash/candidate_leaderboard/latest/candidate_leaderboard.json`
- `data/crypto_perp/real_market_no_cash/human_review_packet/latest/human_review_packet.json`

補助文書:

- [Backtest Candidate Pack v1](BACKTEST_CANDIDATE_PACK_V1.md)
- [No-Cash Backtest Gate v1](NO_CASH_BACKTEST_GATE_V1.md)
- [Human Review Plan](HUMAN_REVIEW_FOR_PAPER_OBSERVATION_PLAN_2026-07-09.md)
- [Human Review Packet v1](HUMAN_REVIEW_PACKET_V1.md)
- [NO_TRADE Kill Report v1](NO_TRADE_KILL_REPORT_V1.md)
- [Candidate Leaderboard v1](CANDIDATE_LEADERBOARD_V1.md)

## 再開時の最短手順

1. この文書で現在の停止理由を確認する。
2. `git status --short --branch --untracked-files=all` で差分を確認する。
3. current bias guard と後段 decision artifact を再確認する。
4. fail-closed 修正計画と tests を確認する。
5. 修正・再生成・全検証後にだけ、人間レビューを再開する。

現時点の次の技術作業は Paper Observation ではなく、bias guard の停止判定を後段へ正しく伝播させる修正である。
