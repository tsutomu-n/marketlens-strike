<!--
作成日: 2026-06-22_19:34 JST
更新日: 2026-06-22_19:39 JST
-->

# User Inputs And Provision Guide

## 結論

次に進めるために、最初に必要なのは credential や live 承認ではない。まず必要なのは、どの lane を進めるかの指定と、その lane の根拠になる artifact / evidence である。

推奨する最初の進め方は、今回追加した local / offline surface を実 artifact で dogfood すること。つまり `Strategy Input Feedback`、`Strategy Case Index`、`Strategy Workbench Viewer` を実データで読み、次に direct apply、registry、UI、paper bridge のどれが本当に必要かを確認する。

secret、API key、口座情報、raw statement、実注文情報は chat や tracked file に貼らない。必要な場合は `.env`、shell environment、または `data/` / `.tmp/` の git-ignored path に置き、値ではなく path と masked summary だけを共有する。

## まず用意するもの

迷った場合は、まず次の3点だけでよい。

1. どの作業に進みたいか。
   - 例: `Local dogfood`
   - 平易な言い換え: 「まず手元の実データで、今回作った機能を試す」
2. 対象は何か。
   - 例: `strategy_id=ndx_example_001`
   - 平易な言い換え: 「どの戦略・ケース・銘柄について進めるか」
3. 根拠ファイルはどこにあるか。
   - 例: `data/user_inputs/2026-06-22/runtime_observation.json`
   - 平易な言い換え: 「判断材料になる JSON / YAML / report の場所」

最初から API key、口座情報、live 承認を出す必要はない。むしろ最初にそれらを出すと、作業範囲が危険側に膨らみやすい。

## 用語の言い換え

この文書では repo 内の用語を使う。初見で読みにくいものは、次の言い換えで読む。

| 用語 | 平易な言い換え | この文書での意味 |
|---|---|---|
| lane | 作業の種類 | 次に進める大分類。例: dogfood、paper evidence、read-only network |
| artifact | 証拠ファイル / 実行結果ファイル | CLI や手作業で作った JSON / YAML / Markdown / HTML |
| evidence | 根拠 / 観察証拠 | 判断に使える実データ、paper 結果、review 記録など |
| dogfood | 自分の実データで試すこと | 作った機能を、サンプルではなく実 artifact で読んで粗を出すこと |
| local / offline | 手元だけ / 外部接続なし | API、credential、注文、外部副作用を使わない作業 |
| credential | 認証情報 | API key、API secret、passphrase、token など |
| read-only | 読み取り専用 | 外部 API や artifact を読むだけで、注文・書き込み・変更をしない |
| no-write boundary | 書き込み禁止の線引き | exchange write、注文、DB 書き換えなどをしないと明示すること |
| permission boundary | 許可しない範囲 | paper order、live order、wallet、signing などを許可しない境界 |
| paper | 模擬取引 / paper trading | 実資金ではない検証用の取引・観察 |
| live | 実資金 / 本番取引 | 実口座・実注文・実損益を伴う状態 |
| direct apply | 自動反映 / 直接書き換え | proposal を元ファイルへ自動または半自動で反映すること |
| registry | 台帳 / 検索できる一覧 | 複数 case を DB や index として管理する仕組み |
| schema | データ形式の決まり | JSON の必須 field、型、禁止 flag などの契約 |
| fixture | テスト用の固定データ | 何度実行しても同じ結果になる検証用ファイル |
| redaction | 秘密情報の伏せ字化 | key、口座番号、注文 id、残高などを隠すこと |
| masked summary | 伏せ字つき要約 | `set` / `not set`、末尾4文字だけ、金額を丸めるなど |
| raw statement | 加工前の明細 | broker / exchange から出したそのままの明細 |
| tracked file | git で追跡されるファイル | `docs/`、`plan/`、`src/` など。secret や raw statement を置かない |
| git-ignored path | git に入れない置き場所 | `data/`、`.tmp/` など。raw artifact や private input の置き場所 |
| false readiness | 準備できたように見える誤判定 | 実際には paper / live / network の前提がないのに進めてしまうこと |

## 提供方法の基本ルール

### 1. chat には「値」ではなく「場所」を書く

よい例:

```text
artifact paths:
- data/user_inputs/2026-06-22/runtime_observation.json
- data/user_inputs/2026-06-22/case_lite_a.json
```

悪い例:

```text
API_SECRET=...
口座残高の明細全文=...
注文レスポンス全文=...
```

### 2. private input は git に入れない場所へ置く

推奨する置き場所:

```text
data/user_inputs/2026-06-22/
.tmp/user_inputs/2026-06-22/
data/private/
```

用途:

- `data/user_inputs/<date>/`: 次計画の材料にする raw artifact。
- `.tmp/user_inputs/<date>/`: 一時的に読むだけのファイル。
- `data/private/`: 明細や account 情報など、tracked docs に残さないもの。

避ける置き場所:

```text
docs/
plan/
src/
tests/
schemas/
```

理由:

- これらは git に入る可能性が高い。secret や private raw data を置かない。

### 3. secret は `.env` または shell environment に置く

よい例:

```text
credential status:
- BITGET_DEMO_API_KEY: set
- BITGET_DEMO_API_SECRET: set
- BITGET_DEMO_PASSPHRASE: set
- values pasted in chat: no
```

悪い例:

```text
BITGET_DEMO_API_SECRET=<actual secret>
```

### 4. 迷ったら redacted copy を作る

redacted copy（伏せ字版）にするもの:

- API key / secret
- account id
- wallet address が private 扱いの場合
- order id
- exact balance
- raw fills
- raw exchange response
- statement CSV

redaction の例:

```text
account_id: acct_********1234
api_key: set
balance_usd: rounded_to_nearest_100
order_id: redacted
```

## 必須・推奨・オプションの意味

- 必須: ないと次計画の対象、境界、完了条件が決まらない。
- 推奨: なくても開始できるが、あると計画の精度が上がる。
- オプション: UI、report、過去失敗など、判断の補助になるもの。

## 重要度ランキング

### 必須

#### 必須 1: 次に進める lane を1つだけ指定する

必要な理由:

- D1-D21 は依存関係が違う。複数 lane を同時に始めると、paper evidence、network、order、UI、DB が混ざり false readiness を作る。
- lane は「作業の種類」のこと。ここを1つに絞ると、必要なファイル、テスト、止める条件が決まる。

選べる lane:

1. Local dogfood（手元の実データで試す）: proposal / review / case index / viewer を実 artifact で読む。
2. Paper evidence（模擬取引の証拠確認）: paper bridge validation または normal paper observation continuation。
3. Credentialed read-only（認証あり・読み取り専用）: Bitget / Hyperliquid / Alpaca などの no-write network probe。
4. Demo order lifecycle（デモ口座の注文一連確認）: demo-only submit / cancel / close / reconcile。
5. Venue schema（取引所・ブローカー形式の追加）: target venue を1つに絞った schema / cost model 拡張。
6. Evaluation / accounting（評価・損益突合）: optimizer ではなく evaluation design、cash reconciliation、statement-derived summary。
7. Operations gate（運用前の安全確認）: freshness、ops drill、incident response、optional network CI。

判断の目安:

- 迷うなら `Local dogfood` を選ぶ。
- 新しい paper の結果があるなら `Paper evidence` を選ぶ。
- API key を使いたいだけなら、まだ `Credentialed read-only` までに止める。
- 実注文、tiny live、本番運用は、今の推奨では選ばない。

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
- target venue（対象取引所・ブローカー）や target symbol（対象銘柄）を増やすほど、テストと失敗時の切り分けが難しくなる。

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

書けない場合:

- `unknown` と書いてよい。
- ただし、次計画の最初の task は対象探索になる。
- `全部` や `よさそうなもの全部` は避ける。

#### 必須 3: 根拠 artifact の path を渡す

必要な理由:

- この repo は code / schema / CLI / artifact hash を正とする。説明だけでは次計画の acceptance に落とせない。
- artifact は「証拠ファイル」のこと。JSON / YAML / Markdown / HTML のどれでもよいが、まず path が必要。

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

足りない場合の書き方:

```text
missing:
- source contract: none
- runtime observation: unknown
- case lite: not yet generated
```

足りないものがあること自体は問題ではない。問題は、足りないものを「ある前提」で計画すること。

#### 必須 4: permission boundary を明示する

必要な理由:

- `READY_*`、`CANDIDATE`、`review`、`plan` は permission ではない。実務上の誤読を防ぐため、何を許可しないかを先に固定する。
- permission boundary は「何をしてはいけないかの線引き」のこと。

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

approval と扱わない例:

- 「Go」
- 「続けて」
- 「できるところまで」
- 「よさそうならやって」

approval として必要な例:

```text
explicit approval:
- scope: Bitget demo read-only probe only
- network: yes, demo read-only only
- order submit: no
- wallet / signing / exchange write: no
- expires: 2026-06-22 23:59 JST
```

#### 必須 5: secret / account / statement の渡し方を決める

必要な理由:

- secret や account raw data が tracked docs / logs / chat に残ると、実装より先に運用リスクになる。
- statement は「取引所やブローカーの明細」のこと。raw statement は加工前の明細なので、そのまま docs や plan に入れない。

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

読み方:

- 「あなたが用意するもの」は、ファイルや明示判断として渡すもの。
- 「こちらが確認すること」は、Codex が repo 内で read-only に検証すること。
- 「次に出せる成果物」は、その lane で現実的に作れるもの。

### Lane 1: Local Dogfood

平易な言い換え:

- 今回作った機能を、サンプルではなく実際のファイルで試す。
- API や注文は使わない。
- まずここから始めるのが一番安全。

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

あなたが用意するもの:

```text
lane: Local dogfood
strategy_id: <strategy_id>
source contract: <path or none>
runtime observation: <path or none>
learning event: <path or none>
case lite files:
- <path>
- <path>
permission boundary:
- no direct apply
- no paper order
- no live order
```

こちらが確認すること:

- file が存在するか。
- schema version が期待通りか。
- hash を取れるか。
- boundary flag が live / wallet / signing / exchange write を許可していないか。
- proposal / review / case index / viewer が実 artifact で読めるか。

次に出せる成果物:

- dogfood 実行メモ。
- proposal / review / case index / viewer の不足点。
- D3 direct apply、D4 registry、D5 UI のどれが本当に必要かの判断。

ここで進めないもの:

- Strategy Input Contract の自動編集。
- DB registry。
- Svelte / server UI。
- paper / live / network。

### Lane 2: Paper Evidence

平易な言い換え:

- 模擬取引や paper 観察の証拠を確認する。
- 「paper で次へ進めるか」を見るが、live 許可ではない。
- 新しい trading day の証拠がない場合、同じ日の再実行だけでは進まない。

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

あなたが用意するもの:

```text
lane: Paper evidence
strategy_id: <strategy_id>
authoring yaml: <path>
backtest result: <path>
backtest pack validation: <path>
strategy review record: <path>
stage decision: <path>
paper smoke plan: <path>
paper observation status: <path>
new trading day evidence: yes / no
same-day rerun only: yes / no
```

こちらが確認すること:

- `normal_thresholds_met` が true か false か。
- `latest_normal_requirement_gaps` に何が残っているか。
- smoke と normal を混同していないか。
- `live_conversion_allowed=false` と `permits_live_order=false` が維持されているか。
- same-day rerun を trading day 増加として扱っていないか。

次に出せる成果物:

- paper bridge validation report。
- normal paper observation continuation の次手。
- drift / learning へ戻すべきかの判断。

ここで進めないもの:

- paper order の自動実行。
- micro live plan への自動昇格。
- profit / alpha claim。

### Lane 3: Credentialed Read-only Network

平易な言い換え:

- API key などを使って、外部サービスを読むだけの確認をする。
- 読むだけで、注文や書き込みはしない。
- secret を扱うため、Local Dogfood より危険度が上がる。

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

あなたが用意するもの:

```text
lane: Credentialed read-only
target provider: <Bitget / Hyperliquid / Alpaca / other>
mode: demo / production / public / address-scoped / credentialed
env vars are set: yes / no
values pasted in chat: no
read-only only: yes
write/order permission: no
official docs checked: <url or not yet>
```

こちらが確認すること:

- command help と current docs が一致しているか。
- opt-in なしに network を叩かない設計か。
- secret が stdout、logs、artifact、tracked file に出ないか。
- no-write boundary が tests / schema / docs にあるか。
- normal CI に入らないか。

次に出せる成果物:

- read-only probe の別計画。
- redaction test 方針。
- network result を readiness と読まない report schema。

ここで進めないもの:

- order submit。
- cancel / close。
- wallet / signing / exchange write。
- production readiness claim。

### Lane 4: Demo Order Lifecycle

平易な言い換え:

- デモ口座で、注文を出して、取り消して、閉じて、最終的にポジションが残っていないか確認する。
- demo でも order path なので、read-only より危険。
- production へ向かわない guard が先に必要。

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

あなたが用意するもの:

```text
lane: Demo order lifecycle
account type: demo only
production endpoint blocked: yes
max notional: <amount>
max open positions: <number>
submit allowed: demo only
cancel / close / reconcile required: yes
failed path handling:
- failed submit: <policy>
- partial fill: <policy>
- cancel rejected: <policy>
- close rejected: <policy>
```

こちらが確認すること:

- demo endpoint と production endpoint が混ざらないか。
- order idempotency があるか。
- query-before-resubmit があるか。
- close / reconcile なしに成功扱いしていないか。
- failure path の fixture を作れるか。

次に出せる成果物:

- demo order lifecycle plan。
- dry-run / fixture-first tests。
- demo-only order lifecycle report schema。

ここで進めないもの:

- production order。
- real tiny live。
- write key の恒久運用。

### Lane 5: Tiny Live / Production Live

平易な言い換え:

- 実資金で小さく試す、または本番運用する。
- 今は推奨しない。
- ここは「実装できるか」よりも「事故時に止められるか」「損失と明細を突合できるか」が先。

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

あなたが用意するもの:

```text
lane: Tiny Live / Production Live
explicit approval: separate message required
account: isolated margin
withdrawal disabled: yes
IP restriction: yes
max notional: <= 25 USD
max open positions: 1
existing position: none
open order: none
reduce-only close: available
flat reconciliation: required
kill switch: documented
accounting boundary: documented
```

こちらが確認すること:

- approval scope が曖昧でないか。
- mock と real network を混同していないか。
- preflight、execution、close、reconcile、post-run audit が分かれているか。
- D13、D19、D20、D21 が満たされているか。
- secret や raw statement を tracked file に入れない設計か。

次に出せる成果物:

- 通常は「まだ進めない」という readiness report。
- 例外的に前提が全部そろった場合だけ、tiny live preflight plan。

ここで進めないもの:

- automatic trading daemon。
- position scale-up。
- production live trading。
- profit claim。

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
