<!--
作成日: 2026-06-22_19:34 JST
更新日: 2026-06-22_19:34 JST
-->

# User Inputs And Provision Guide

## 結論

次に進めるために、最初に必要なのは credential や live 承認ではない。まず必要なのは、どの lane を進めるかの指定と、その lane の根拠になる artifact / evidence である。

推奨する最初の進め方は、今回追加した local / offline surface を実 artifact で dogfood すること。つまり `Strategy Input Feedback`、`Strategy Case Index`、`Strategy Workbench Viewer` を実データで読み、次に direct apply、registry、UI、paper bridge のどれが本当に必要かを確認する。

secret、API key、口座情報、raw statement、実注文情報は chat や tracked file に貼らない。必要な場合は `.env`、shell environment、または `data/` / `.tmp/` の git-ignored path に置き、値ではなく path と masked summary だけを共有する。

## 重要度ランキング

### 必須

#### 必須 1: 次に進める lane を1つだけ指定する

必要な理由:

- D1-D21 は依存関係が違う。複数 lane を同時に始めると、paper evidence、network、order、UI、DB が混ざり false readiness を作る。

選べる lane:

1. Local dogfood: proposal / review / case index / viewer を実 artifact で読む。
2. Paper evidence: paper bridge validation または normal paper observation continuation。
3. Credentialed read-only: Bitget / Hyperliquid / Alpaca などの no-write network probe。
4. Demo order lifecycle: demo-only submit / cancel / close / reconcile。
5. Venue schema: target venue を1つに絞った schema / cost model 拡張。
6. Evaluation / accounting: optimizer ではなく evaluation design、cash reconciliation、statement-derived summary。
7. Operations gate: freshness、ops drill、incident response、optional network CI。

提供方法:

- chat で次の形で指定する。

```text
次に進める lane: Local dogfood
対象 strategy: <strategy_id or unknown>
今回やらないこと: credential / network / live / wallet / signing / exchange write
```

#### 必須 2: 対象 strategy / case / venue を固定する

必要な理由:

- 対象が曖昧だと、artifact chain、test fixture、entry criteria、完了条件が決まらない。

提供するもの:

- `strategy_id`
- 関連 case id があれば `case_id`
- venue を扱う場合は target venue 1つだけ
- 期間を扱う場合は対象期間
- symbol を扱う場合は target symbol 1つから開始

提供方法:

```text
strategy_id: <id>
case_id: <id or none>
target venue: none / bitget_demo / bitget_futures / hyperliquid_perp / alpaca / trade_xyz
target symbol: <symbol or none>
対象期間: <YYYY-MM-DD to YYYY-MM-DD or none>
```

#### 必須 3: 根拠 artifact の path を渡す

必要な理由:

- この repo は code / schema / CLI / artifact hash を正とする。説明だけでは次計画の acceptance に落とせない。

Local dogfood で最低限あるとよい path:

- Strategy Input Contract
- Runtime Observation または Strategy Learning Event
- Strategy Input Feedback proposal / review
- Strategy Case Lite artifacts
- Strategy Case Index artifact
- Workbench Viewer manifest / HTML

Paper evidence で必要な path:

- Strategy Authoring YAML
- backtest result / backtest pack validation
- Strategy Review record
- Stage Decision
- Paper Smoke Plan
- paper observation status
- paper observation session / review artifact

提供方法:

- git-ignored の raw artifact は `data/user_inputs/<date>/` または `.tmp/user_inputs/<date>/` に置く。
- chat には値ではなく path を貼る。

```text
artifact package:
- data/user_inputs/2026-06-22/input_contract.json
- data/user_inputs/2026-06-22/runtime_observation.json
- data/user_inputs/2026-06-22/learning_event.json
- data/user_inputs/2026-06-22/case_lite_a.json
```

#### 必須 4: permission boundary を明示する

必要な理由:

- `READY_*`、`CANDIDATE`、`review`、`plan` は permission ではない。実務上の誤読を防ぐため、何を許可しないかを先に固定する。

提供方法:

```text
この依頼で許可しないこと:
- credentialed network: no
- paper order: no
- live order: no
- wallet / signing / exchange write: no
- production live trading: no
```

もし許可が必要な lane を選ぶ場合:

- approval は別メッセージで明示する。
- scope、venue、account type、max notional、max open positions、stop condition、期限を書く。
- `yes` や「進めて」だけでは approval と扱わない。

#### 必須 5: secret / account / statement の渡し方を決める

必要な理由:

- secret や account raw data が tracked docs / logs / chat に残ると、実装より先に運用リスクになる。

提供方法:

- API key / secret は chat に貼らない。
- `.env` または shell environment に設定する。
- raw statement は `data/private/`、`data/user_inputs/`、`.tmp/user_inputs/` のような git-ignored path に置く。
- chat では masked summary だけを伝える。

```text
credential status:
- BITGET_DEMO_API_KEY: set
- BITGET_DEMO_API_SECRET: set
- BITGET_DEMO_PASSPHRASE: set
- production key: not provided
- withdrawal permission: disabled
- IP restriction: enabled
```

### 推奨

#### 推奨 1: Dogfood 結果の short note を残す

必要な理由:

- `data/` は git-ignored なので、次計画の判断に使うには tracked summary が必要。

提供するもの:

- 実行した command
- input path
- output path
- 読みにくかった点
- 誤読しそうだった field
- 次に必要だと感じた変更

提供方法:

```text
dogfood note:
- command: uv run sis strategy-case-index-build ...
- input: data/user_inputs/2026-06-22/case_lite_*.json
- output: data/strategy_case_index/strategy_case_index.json
- pain: latest status は見えるが、blocked reason の原因 artifact に戻りにくい
- next need: viewer に source artifact deep link が必要
```

#### 推奨 2: 期待する成果物を1つに絞る

必要な理由:

- 「UIもDBもpaperもliveも」になると計画が破綻する。

提供方法:

```text
期待する成果物:
- D1 paper bridge validation report only
- または D3 manual patch proposal only
- または D5 viewer dogfood improvement note only
```

#### 推奨 3: 失敗例・保留例・却下例を用意する

必要な理由:

- successful artifact だけだと、boundary violation、missing source、hold / reject の設計が弱くなる。

提供するもの:

- missing source contract の proposal
- `HOLD` / `REJECT` / `NEEDS_FIX` の review
- stale source path
- no case-lite found
- normal paper threshold 未達の status

提供方法:

- raw artifact path と expected interpretation をセットで渡す。

```text
negative samples:
- data/user_inputs/2026-06-22/proposal_missing_source_contract.json
  expected: direct apply しない
- data/user_inputs/2026-06-22/paper_observation_status_not_met.json
  expected: live readiness と読まない
```

#### 推奨 4: 現時点でやらないことを明記する

必要な理由:

- 否定境界がないと、次計画で live、network、DB、UI が膨らみやすい。

提供方法:

```text
今回やらないこと:
- no DB registry
- no Svelte UI
- no network
- no order lifecycle
- no production venue schema widening
```

#### 推奨 5: 公式 docs 確認が必要な外部対象を明示する

必要な理由:

- exchange / broker / external API は仕様が変わる。記憶や過去ログで計画すると危険。

提供方法:

```text
external docs required:
- Bitget demo API docs: required / not yet checked
- Hyperliquid API docs: not in this scope
- Alpaca paper API docs: not in this scope
```

### オプション

#### オプション 1: スクリーンショットや HTML report

使いどころ:

- Viewer / report の読みにくさを伝える時。

提供方法:

- `.png` や `.html` を `data/user_inputs/<date>/` または `.tmp/user_inputs/<date>/` に置く。
- secret、account id、API key、残高、注文 id が写っている場合は redaction する。

#### オプション 2: 期待する UI / report の読み方メモ

使いどころ:

- Svelte UI や server UI へ進む前の、static viewer dogfood evidence にする時。

提供方法:

```text
viewer reading note:
- first thing I looked for: blocked reason
- hard to find: source artifact that caused the blocker
- not needed: server state
```

#### オプション 3: 過去の失敗ログ

使いどころ:

- operation drill、network probe、paper bridge の failure mode を設計する時。

提供方法:

- stack trace や error response は secret を redaction して渡す。
- raw API response 全文は tracked docs に入れない。

#### オプション 4: 優先しない候補の明示

使いどころ:

- 範囲を狭く保つため。

提供方法:

```text
優先しない:
- production live
- DB registry
- optimizer
- Svelte UI
```

## Lane 別の用意物

### Lane 1: Local Dogfood

必須:

1. `strategy_id`
2. Strategy Input Contract または「source contract なしで試す」という明示
3. Runtime Observation または Strategy Learning Event
4. Strategy Case Lite artifacts
5. 「direct apply しない」境界

推奨:

1. approved / rejected / hold / needs_fix の review sample
2. Case Index と Viewer の dogfood note
3. missing / stale / malformed sample

オプション:

1. Viewer screenshot
2. HTML report

### Lane 2: Paper Evidence

必須:

1. 対象 strategy
2. Strategy Authoring YAML
3. backtest result / backtest pack validation
4. Strategy Review record
5. Stage Decision
6. Paper Smoke Plan
7. paper observation status
8. new trading day を含む evidence があるかの明示

推奨:

1. `latest_normal_requirement_gaps`
2. normal / smoke の区別
3. same-day rerun ではないことの説明

オプション:

1. paper report screenshot
2. operator note

### Lane 3: Credentialed Read-only Network

必須:

1. target provider / venue 1つ
2. demo / production / public / address-scoped / credentialed の区別
3. opt-in 方針
4. no-write boundary
5. redaction 方針
6. credential は `.env` / shell environment にあるという masked confirmation

推奨:

1. withdrawal disabled
2. IP restriction
3. rate limit / timeout 方針
4. official docs 確認リンクまたは確認メモ

オプション:

1. sanitized failed response
2. sandbox / demo account note

### Lane 4: Demo Order Lifecycle

必須:

1. demo-only account
2. production endpoint に向かわない guard 方針
3. max notional
4. max open positions
5. submit / cancel / close / reconcile の stop condition
6. failed submit / partial fill / cancel rejected / close rejected の扱い

推奨:

1. idempotency / client order id 方針
2. query-before-resubmit 方針
3. flat reconciliation の expected output

オプション:

1. demo UI screenshot
2. sanitized demo order log

### Lane 5: Tiny Live / Production Live

必須:

1. 別メッセージでの explicit approval
2. isolated margin account
3. withdrawal disabled write key
4. IP restriction
5. max notional 25 USD 以下
6. max open positions 1
7. no existing position / open order confirmation
8. reduce-only close
9. flat reconciliation
10. kill switch
11. D13 secret management
12. D19 freshness gate
13. D20 operations drill
14. D21 accounting boundary

推奨:

1. monitoring owner
2. alert path
3. rollback / revoke procedure
4. post-run audit bundle path

オプション:

1. sanitized exchange statement summary
2. operator run note

注意:

- 今の推奨は、この lane に進まないこと。
- `crypto-perp-tiny-live-measurement --real-network` は、help 上も separate approval が必要であり、mock test を real measurement と読まない。

## 質問

回答があると次計画の精度が上がる。未回答でも、Local Dogfood からなら進められる。

1. 次に進める lane は `Local dogfood` でよいか。それとも `Paper evidence` を優先するか。
2. 対象にする `strategy_id` はどれか。
3. 実 artifact は既に `data/` にあるか。ある場合、path はどれか。
4. 新しい normal paper observation evidence はあるか。ある場合、same-day rerun ではなく新しい trading day を含むか。
5. credential / network / order / live は、今回も明示的に対象外でよいか。

## 提供テンプレート

最小テンプレート:

```text
次に進める lane: Local dogfood
strategy_id: <strategy_id>
case_id: <case_id or none>
artifact paths:
- <path>
- <path>
今回やらないこと:
- credentialed network
- paper order
- live order
- wallet / signing / exchange write
notes:
- <困っている点>
```

paper evidence テンプレート:

```text
次に進める lane: Paper evidence
strategy_id: <strategy_id>
new trading day evidence: yes / no
artifact paths:
- Strategy Authoring YAML: <path>
- backtest result: <path>
- review record: <path>
- stage decision: <path>
- paper smoke plan: <path>
- paper observation status: <path>
permission boundary:
- paper order approval: no / yes with separate message
- live order approval: no
```

network テンプレート:

```text
次に進める lane: Credentialed read-only
target provider: <provider>
mode: demo / production / public / address-scoped / credentialed
credentials:
- env vars are set: yes / no
- values pasted in chat: no
permission boundary:
- read-only only
- no order
- no wallet / signing / exchange write
official docs checked:
- <url or not yet>
```
