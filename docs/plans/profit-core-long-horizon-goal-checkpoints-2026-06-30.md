<!--
作成日: 2026-06-30_21:26 JST
更新日: 2026-06-30_21:26 JST
-->

# Profit Core Long-Horizon Goal And Checkpoints

## 結論

考えうる先のゴールは、**候補を大量に作る repo** ではなく、**候補を広く作り、全探索を会計し、弱い候補を早く殺し、実行不能候補を止め、actual cash とそれ以外を混ぜず、必要な場合だけ明示承認つきで小さな実測へ進める Profit Core pipeline** にすること。

```text
Final shape =
  protocol-bound candidate generation
  -> multiplicity/accounting
  -> candidate-to-backtest bridge
  -> backtest kill gate
  -> local/mock virtual execution gate
  -> evidence packet + adversarial review
  -> human risk review
  -> explicit approval and tiny actual-cash measurement only when conditions are fixed
  -> actual cash report gate
  -> conservative promotion or kill
```

この最終像でも、profit proof と呼べる最初の層は `actual_cash` だけ。backtest、selection metrics、virtual execution、LLM review、risk review、paper/demo/testnet は証拠の種類が違う。

## 現在地

現在地は「CP1-CP3 の契約部品は実装済み。ただし既存候補 pipeline へまだ接続されていない」。

実装済み:

- `candidate_protocol_manifest.v1`
- `trial_multiplicity_account.v1`
- thin `backtest_kill_gate.v1`
- `edge-candidate-protocol-validate`
- 既存 `strategy_idea_candidates` の candidate set、search ledger、selection metrics、Perp estimate、C9 v0 Prep Watchdeck authoring bridge
- 既存 Crypto Perp の risk-taker review、actual cash report gate、tiny-live shadow 系 local artifacts

未接続:

- protocol manifest が candidate generation run をまだ支配していない。
- trial multiplicity account が既存 `search_ledger.jsonl` / selection metrics から生成されていない。
- backtest kill gate が C9 bridge / backtest pack output にまだ接続されていない。
- C9 v0 の `BRIDGED` が Profit Core 語彙の `BRIDGED_TECHNICAL_ONLY` とまだ分離されていない。
- `risk_taker_sprint` は mode enum として存在するが、隔離出力、再登録、promotion debt は未実装。
- `virtual_execution_gate.v1` は未実装。初期版は external venue ではなく local/mock lifecycle から始める。
- LLM adversarial review は Profit Core evidence packet 用としては未実装。最初は API 連携ではなく local/manual JSON diff checker でよい。
- actual cash report gate は既存 Crypto Perp 側にあるが、candidate lineage、protocol、multiplicity、kill gate、virtual gate、risk review を一本の promotion path として束ねていない。

## Must Not Break

- `actual_cash` と virtual / proxy / estimate / paper / demo / testnet を混ぜない。
- `NO_TRADE` を first-class outcome として扱う。
- `BRIDGED` / `BRIDGED_TECHNICAL_ONLY` を alpha proof、profit proof、paper permission、live readiness と読ませない。
- `AVAILABLE` を performance pass と読ませない。
- `NOT_ESTIMABLE` を failure ではなく正しい停止結果として扱う。
- `risk_taker_sprint` を本命成績に混ぜない。
- validation / holdout を見て修正した候補を同じ sealed holdout で再評価しない。
- LLM に official metric、PnL、actual_cash 判定、gate override、paper/live/tiny-live 許可をさせない。
- external venue docs、demo/testnet docs、API docs を legal clearance と読まない。
- wallet、signing、exchange write、live order、tiny-live measurement は明示承認なしに実行しない。

## Cross-Cutting Acceptance Gates

すべての checkpoint に共通する合格条件:

- narrative だけで進めない。schema validation、artifact hash、source refs、focused tests のいずれかで状態を確認できるようにする。
- candidate lineage を切らない。少なくとも candidate id、candidate set hash、protocol hash、multiplicity account hash、bridge / gate artifact refs の追跡先を残す。
- artifact ごとに evidence basis を明示する。例: `backtest`, `virtual_exchange`, `paper`, `demo`, `testnet`, `actual_cash`。
- permission field は明示 false を基本にする。未記載を許可として読ませない。
- 旧 artifact に field が無い場合は、黙って推測せず compatibility sidecar または migration note を出す。
- status 名は「何を許可しないか」を同じ artifact 内で読めるようにする。
- threshold や family policy を変えたら new protocol version と new multiplicity account にする。
- `AVAILABLE` / `READY_FOR_HUMAN_REVIEW` / `SHORTLIST_FOR_VIRTUAL` は pass ではなく、次の検査へ進める状態に限定する。

## Checkpoint Map

### P0: Current State Reconciliation

目的:

CP1-CP3 実装後の docs / code / branch / CLI catalog / final summary を current truth に揃える。

差分:

- `docs/profit_core_hybrid_modes/IMPLEMENTATION_CHECKPOINTS.md` は CP1-CP3 を future checkpoint として書いているが、現在 branch では実装済み。
- `docs/plans/profit-core-cp1-cp3-implementation-2026-06-30.md` は実装計画なので、完了後は final summary と code を正にする。

完了条件:

- current-state docs が「CP1-CP3 実装済み、未接続」と読める。
- `uv run python scripts/check_current_docs.py` と `uv run python scripts/check_cli_catalog.py` が通る。
- `.ai_memory/HANDOFF.md` が必要なら restart artifact として更新される。

止める条件:

- CP1-CP3 が実装済みなのか docs-only なのか曖昧なまま次へ進む。

### P1: Candidate Pipeline Attachment

目的:

既存 `strategy_idea_candidates` run が protocol manifest と multiplicity account を持てるようにする。

対象:

- `strategy_idea_candidate_set.v1`
- `search_ledger.jsonl`
- `selection_metrics.json`
- `candidate_protocol_manifest.v1`
- `trial_multiplicity_account.v1`

完了条件:

- candidate set または sidecar manifest に protocol ref / hash が残る。
- search ledger から `trial_multiplicity_account.v1` を生成できる。
- success-only reporting、sealed test selection、validation peek / rerank count を機械的に確認できる。
- `raw_p_value_count=0` なら BH/FDR は `NOT_ESTIMABLE`。
- PBO / DSR / White Reality Check は required inputs が無ければ `NOT_ESTIMABLE`。

止める条件:

- protocol が任意メモ扱いで、candidate generation を実際には拘束しない。
- multiplicity account が search ledger と一致しない。

### P2: Bridge Status Split

目的:

C9 v0 bridge の `BRIDGED` を Profit Core 語彙へ分解し、技術接続と経済的判定を混ぜない。

候補 status:

```text
BRIDGED_TECHNICAL_ONLY
BLOCKED_UNSUPPORTED_FAMILY
BLOCKED_MISSING_SOURCE
BLOCKED_BACKTEST_PACK
BLOCKED_ECONOMIC_GATE
BLOCKED_MULTIPLICITY_ACCOUNT
```

完了条件:

- 既存 `strategy_idea_candidate_authoring_bridge.v1` が `BRIDGED_TECHNICAL_ONLY` または互換 migration field を持つ。
- 旧 `BRIDGED` を alpha / profit / paper / live proof と読めない。
- candidate id、candidate set hash、ledger hash、protocol hash、multiplicity account hash が bridge manifest から追える。

止める条件:

- C9 bridge を Core 本体として固定する。
- backtest pack validation pass を economic pass と読める。

### P3: Backtest Kill Gate Integration

目的:

thin `backtest_kill_gate.v1` を C9 / Strategy Authoring / backtest pack output に接続する。

完了条件:

- `NO_TRADE` comparison が無い candidate は `INCONCLUSIVE_DATA`。
- family-specific event count policy を使う。
- after-cost / stress edge が `NO_TRADE` 以下なら `KILL`。
- source gap / unsupported execution candidate は `INCONCLUSIVE_DATA` または `RESEARCH_ONLY`。
- `SHORTLIST_FOR_VIRTUAL` は permission ではなく、次の local/mock virtual gate へ渡す状態。

止める条件:

- rare candidate を一律 event count だけで殺す。
- `SHORTLIST_FOR_VIRTUAL` を trade permission と読める。

### P4: Edge Candidate Factory V1

目的:

protocol-bound で candidate を作る。最初は `verification_throughput` の classical + limited grammar に限定する。

完了条件:

- protocol manifest なしでは run できない。
- 全候補、全棄却、全 parameter、全 family、全 source ref を保存する。
- best-only report を出さない。
- `unexecutable_reason_count` と `unexecutable_rate` を candidate factory KPI として出す。
- `risk_taker_sprint` 用の広い generator はまだ無効。

止める条件:

- generator が protocol 外の search space を勝手に広げる。
- LLM / GA / ML を先に入れる。

### P5: Virtual Execution Gate V1 Local/Mock

目的:

actual cash 前に order lifecycle と reconciliation を local/mock で検査する。PnL 判定はしない。

完了条件:

- `virtual_execution_gate.v1` が `actual_cash=false`、`cash_metric_basis=virtual_exchange`、`production_exchange_write_used=false`、`live_order_submitted=false`、`permits_live_order=false` を持つ。
- submit ack、partial fill、cancel、reject reason、duplicate prevention、flat reconciliation を local state machine で検査する。
- unknown state と reconcile mismatch は blocker。

止める条件:

- Bitget demo / Hyperliquid / GRVT を同時に入れる。
- virtual PnL を profit evidence と呼ぶ。

### P6: Evidence Packet And Claim Diff

目的:

候補の主張と machine-readable evidence を分け、overclaim を機械的に検出できる packet を作る。

完了条件:

- input は protocol、multiplicity account、candidate set、bridge manifest、kill gate、virtual gate、risk review source refs。
- human-facing claim と machine summary の差分を検査する。
- unsupported claim、missing comparison、basis mismatch、actual_cash overclaim を severity つきで出す。

止める条件:

- LLM API 連携を先に実装する。
- human prose を正本にする。

### P7: LLM Adversarial Review

目的:

LLM を許可者ではなく、evidence packet の adversarial reviewer に限定する。

完了条件:

- 出力は `ADVERSARIAL_FINDING`、`NEEDS_MORE_EVIDENCE`、`OVERCLAIM_FLAG`、`HUMAN_REVIEW_REQUIRED`、`NO_ADDITIONAL_BLOCKER_FOUND` などに限定。
- `NO_ADDITIONAL_BLOCKER_FOUND` は approval ではない。
- hard blocker は machine-checkable な欠落だけ。
- API 連携する場合は opt-in、redaction、artifact boundary、外部送信記録が必要。

止める条件:

- LLM に PnL、official metric、actual_cash 判定、gate override、strategy rewrite、paper/live/tiny-live permission をさせる。

### P8: Risk-Taker Sprint Isolation

目的:

攻撃モードを本命成績から隔離し、promotion debt を持たせる。

完了条件:

- `risk_taker_sprint` output は default aggregate に混ざらない。
- sprint candidate は `verification_throughput` へ再登録するまで actual cash へ進めない。
- sprint candidate は separate ledger / separate holdout / separate multiplicity account を持つ。
- GA / light ML を使うとしても ranking / no-trade filter に限定し、mainline promotion は conservative gate を通す。

止める条件:

- sprint winner がそのまま tiny-live / actual cash へ進む。
- sprint の positive result を本命 performance に混ぜる。

### P9: Actual Cash Readiness Packet

目的:

tiny actual-cash measurement を実行する前に、条件、上限、credential、jurisdiction、rollback、flat reconciliation、stop condition を固定する packet を作る。

完了条件:

- packet は実行許可そのものではなく、human approval の入力。
- max notional、max daily loss、isolated margin、withdrawal disabled、IP restriction、flat reconciliation、kill switch、stop condition が明示される。
- venue terms / jurisdiction は実行直前に current docs / official docs / user-provided account conditions で再確認する。
- external service write はこの checkpoint ではしない。

止める条件:

- demo/testnet docs を legal clearance と読む。
- approval なしに credentialed write / order submit へ進む。

### P10: External Virtual Venue Adapter

目的:

local/mock virtual gate を通った後、明示 opt-in の external demo/testnet / read-only venue adapter で lifecycle を検査する。

完了条件:

- 1 venue ずつ。Bitget / Hyperliquid / GRVT を同時実装しない。
- 実装前に公式 docs、rate limit、permission scope、terms、jurisdiction、credential handling を current verification する。
- external read/write boundary、network opt-in、redaction、recorded request/response artifact を固定する。
- demo/testnet result は actual cash ではない。

止める条件:

- public docs の古い記憶を根拠にする。
- credential / order / network side effect が曖昧。

### P11: Tiny Actual-Cash Measurement

目的:

human approval 済みの 1-2 candidate だけを、極小 notional と strict stop condition で actual cash sample に進める。

完了条件:

- approval artifact がある。
- all upstream refs が揃う。
- order intent、submitted order、fills、fees、funding、cash ledger、flat reconciliation が candidate lineage とつながる。
- `actual_cash_result_usd` は実 fill / fee / funding / ledger に基づく。
- `NO_TRADE` comparison が同一 event set で存在する。

止める条件:

- paper/demo/testnet/estimate を actual_cash として流用する。
- flat reconciliation なし。
- loss / venue / credential / legal stop condition が未定義。

### P12: Actual Cash Report Gate

目的:

actual cash sample を集計し、conservative promotion / wait / kill を決める。

完了条件:

- simulation / virtual / estimate / actual_cash が同じ report 内で明確に分離される。
- `actual_cash_edge_over_NO_TRADE` が無ければ promotion しない。
- sample size、event diversity、profit concentration、largest loss、operator burden、reconcile mismatch を出す。
- `promote` より `wait` / `kill` を first-class にする。

止める条件:

- 少数 positive fill を general profit proof と読む。
- `READY_FOR_HUMAN_RISK_REVIEW` を live readiness と読む。

### P13: Feedback And Threshold Calibration

目的:

失敗ログから generator、event_count_policy、unexecutable_rate、cost model、operator burden を更新する。

完了条件:

- killed candidates と actual execution failures が次 protocol の exclusion rules / family policy に反映される。
- threshold change は new protocol version と new trial account になる。
- holdout peek 後の修正は同一 family/version に戻さない。

止める条件:

- 良い結果だけを次回 protocol に反映する。
- threshold 変更が trial count / validation peek に記録されない。

## Better Revision

最初の素朴な long-horizon 案からの修正点:

1. `Virtual Execution Gate` を external venue から始めない。まず local/mock lifecycle。
2. `LLM adversarial review` の前に machine-readable evidence packet と claim diff を作る。
3. C9 bridge の `BRIDGED` は先に `BRIDGED_TECHNICAL_ONLY` へ分解する。ここを飛ばすと backtest success narrative が混ざる。
4. `risk_taker_sprint` は候補生成拡張より先に isolation / promotion debt を作る。
5. tiny actual-cash は checkpoint ではあるが、通常 goal で自動実行しない。明示承認、credential、external-state verification が必須。
6. external venue adapter は実装直前の公式 docs 再確認を checkpoint 条件にする。今の計画 doc に venue 仕様を固定しない。
7. final goal は「profit を出す」ではなく、「profit evidence を false-positive なしで作れる pipeline」に置く。利益そのものは市場と実測に依存する。

## Omission / Error-Risk Pass

見落としやすい点:

- CP1-CP3 は契約部品であり、pipeline 接続ではない。
- 既存 `strategy_idea_candidates` docs の `BRIDGED` と Profit Core docs の `BRIDGED_TECHNICAL_ONLY` は語彙衝突している。
- `trial_multiplicity_account.v1` は作っただけでは多重検定補正にならない。search ledger との一致が必要。
- backtest kill gate は薄い gate であり、full statistical engine ではない。
- `PBO` / `DSR` / `White Reality Check` の `NOT_ESTIMABLE` は正しい停止結果だが、永遠に未推定のままだと promotion bottleneck になる。
- actual cash report gate が存在しても、candidate lineage とつながらなければ Profit Core gate ではない。
- external venue docs、rate limits、jurisdiction、terms は変わる。実装直前に current verification が必要。
- live / tiny-live は repo 内の code surface があっても標準 operator CLI live execution permission ではない。
- `risk_taker_sprint` は心理的に「やってよい」方向へ誤読されやすい。名称より boundary と promotion debt を強制する。

## Suggested Goal Sequence

次の `/goal` は P1-P3 だけにするのが妥当。

```text
/goal Implement Profit Core pipeline attachment P1-P3 from docs/plans/profit-core-long-horizon-goal-checkpoints-2026-06-30.md: attach protocol and multiplicity refs to existing candidate artifacts, split C9 bridge status into technical-only vocabulary, and connect thin backtest_kill_gate decisions to candidate/backtest bridge outputs. Verify with focused edge_candidates and strategy_idea_candidates bridge tests, CLI catalog/current-doc checks if docs or command surface change, Ruff checks for changed Python, and git diff --check. Preserve actual_cash/no_actual_cash boundaries, NO_TRADE, NOT_ESTIMABLE, sealed holdout protection, and no paper/live/tiny-live/external venue/LLM/dependency scope. Stop with evidence plus blocker if any checkpoint cannot be completed defensibly.
```

P1-P3 が終わるまで、P4 以降の candidate factory expansion、virtual gate、LLM、risk-taker sprint は始めない。

P1-P3 でやらないこと:

- candidate generator の探索幅拡張。
- GA / ML / Optuna / tsfresh / 新規依存追加。
- external venue adapter、network access、credentials、order lifecycle 実行。
- LLM API 連携。
- actual cash、paper、demo、testnet、tiny-live 実行。
- economic threshold の実質変更。必要なら別 checkpoint と new protocol version に分ける。

## Readiness

仕様化 readiness: ready with assumptions.

Assumptions:

- Current branch state where CP1-CP3 are implemented is the planning baseline.
- The next implementation goal should not include external network, credentials, venue adapters, LLM API, or live/tiny-live execution.
- This doc is a roadmap and checkpoint contract, not an implementation claim.
