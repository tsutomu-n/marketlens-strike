<!--
作成日: 2026-07-04_10:30 JST
更新日: 2026-07-04_10:47 JST
-->

# Final State Progress Assessment

## 結論

この repo は、研究、backtest、local artifact gate、review packet、Crypto Perp profit-readiness の土台としてはかなり進んでいる。

ただし、最終形を「実資金または実損益に接続した、利益判断可能な個人運用システム」と定義すると、現在地は **50%前後** と見る。理由は、local validation と before-cost / estimate / virtual / review artifact は厚いが、Reality Check の次 blocker が `ACTUAL_CASH_SOURCE_MISSING` であり、actual cash evidence がまだ入っていないため。

live trading / wallet / signing / exchange write / 自動売買まで含めた最終形としては、現行 operator path では未許可なので **30%未満** と見る。

90%に近づける具体的な大チャンクと順序は [PROGRESS_TO_90_ROADMAP_2026-07-04.md](PROGRESS_TO_90_ROADMAP_2026-07-04.md) を読む。

## この文書の評価対象

この文書は、次の3つを分けて評価する。

| 評価軸 | 意味 | 現在評価 |
|---|---|---:|
| Research / backtest / local artifact platform | 戦略作成、検証、schema、CLI、review、local gate が使える状態 | 75%前後 |
| Profit Core | 実利益判断に必要な event、outcome、source availability、actual cash source、rows、gate、review がつながる状態 | 50%前後 |
| Production live trading | credential、wallet/signing、exchange write、live order、flat reconciliation、運用停止条件まで含む状態 | 30%未満 |

この評価値は数学的な完成率ではない。repo 内の current docs、CLI、schema、tests、直近の handoff に基づく実務上の到達度である。

## 確認した現行正本

確認時点: `2026-07-04_10:30 JST`

- `./.ai_memory/HANDOFF.md`
- `docs/CURRENT_STATE.md`
- `docs/IMPLEMENTED_SURFACES.md`
- `docs/NEXT_DIRECTION_CURRENT.md`
- `docs/final-summary.md`
- `docs/plans/profit-event-outcome-inputs-2026-07-04.md`
- `uv run sis --help`
- `uv run python scripts/check_current_docs.py`
- `uv run python scripts/check_cli_catalog.py`
- `./scripts/check`
- `git status --short --branch --untracked-files=all`

文書作成開始時点で確認した restart baseline:

- `main` は `origin/main` と一致。
- HEAD は `18f3980a7e1cb73d660700c8e18c8fc016f79662 ai: add profit event outcome inputs`。
- tracked diff は unstaged / staged ともに空だった。
- `uv run python -V` は `Python 3.13.7`。
- `uv run python scripts/check_current_docs.py` は `checked 207 current docs`。
- `uv run python scripts/check_cli_catalog.py` は `checked 233 public CLI commands against Typer registration`。
- `./scripts/check` は `2873 passed` まで通過。
- `src/sis`、`tests`、`schemas` を含む実装・検証 surface は大きい。確認時点で `schemas/*.json` は 163 files、`tests/test_*.py` は 699 files。

## 進捗の詳細評価

| 領域 | 現在評価 | 根拠 | 未完了の核 |
|---|---:|---|---|
| Restart checkpoint | 100% | clean `main`、HEAD、diff empty を確認済み | なし |
| CLI / docs consistency | 90% | current docs checker、CLI catalog checker、`./scripts/check` が通過 | checks passing は利益証拠ではない |
| Strategy Lab / Strategy Authoring | 75% | Strategy Input Contract、Idea Intake、Authoring、backtest suite、review packet、stage decision、learning loop が public CLI と docs に存在 | 実損益 feedback による自動改善までは未接続 |
| Backtest / robustness | 75% | backtest pack、comparison、stress、regime split、rolling stability、benchmark relative、framework adapters が実装済み surface | backtest pass は alpha proof ではない |
| NDX local research gates | 65% | Layer 2.2-2.8 の local/manual gate が実装済み | alpha、paper readiness、live readiness は証明しない |
| Crypto Perp Truth-Cycle | 70% | probe audit、raw refresh、event、decision、outcome、tournament rows/report/gate、truth-cycle status が実装済み | real network measurement と actual cash basis が未完了 |
| Profit-readiness local automation | 60% | inventory、plan、run-local、source availability、replay、feature、edge、rows v2、bias guard、risk-taker review が実装済み | actual cash source がない |
| Profit Core Reality Check | 55% | deterministic blocker summary と `ACTUAL_CASH_SOURCE_MISSING` まで到達 | blocker 解消は未着手 |
| Actual cash evidence | 20% | actual cash ledger / rows / report gate surface はある | cash ledger plus explicit assignment、または live measurement artifact がない |
| Tiny-live / live readiness | 20%未満 | shadow / plan / review artifact はある | credentialed write、order lifecycle、wallet/signing、exchange write は未許可 |
| Production trading operations | 20%未満 | operations / audit / kill-switch / scheduling surface はある | 本番発注 path と実運用権限は現行 operator path にない |

## 50%前後と見る理由

50%前後という評価は、実装量ではなく「最終的に利益判断へ閉じる距離」で見ている。

到達済み:

- Strategy Lab から backtest、review、stage decision、paper smoke plan、runtime observation、drift review、learning、case index、daily brief、AI review packet まで、local artifact chain は広く実装済み。
- Crypto Perp では、event / decision / outcome / tournament / gate / truth-cycle status の MVP surface がある。
- Profit-readiness では、source availability、replay slice、feature pack、edge score、cost-aware rows、bias guard、risk review、Reality Check がある。
- 直近 commit で `market_window_v1` event と `crypto-perp-event-record`、`--settled-at` 付き outcome recording が入った。
- public candle CSV から real market observation window と matured before-cost outcome までは作れる。

未到達:

- `docs/final-summary.md` の直近 addendum では Reality Check の次 blocker が `ACTUAL_CASH_SOURCE_MISSING`。
- `crypto-perp-source-availability` は `can_compute_actual_cash=false`。
- `docs/IMPLEMENTED_SURFACES.md` は production live trading、wallet、signing、exchange write を現行 operator path で許可しないと明記している。
- `docs/CURRENT_STATE.md` は production live order smoke、signing / wallet / exchange write integration、Bitget credentialed read-only network smoke、Bitget demo order lifecycle、tiny live measurement を未証明としている。

つまり、検証の器はかなりできているが、器に入れる実損益 evidence がない。

## 75%ではなく50%に下げる理由

Research / backtest platform としてなら 75%前後でよい。理由は、public CLI、schema、docs、tests、review flow が揃っており、local-only の検証・記録・停止条件が多いから。

しかし Profit Core の目的を「利益があるかを現実に判断すること」と置くと、actual cash source がない時点で最後の判定へ進めない。before-cost proxy、cost-adjusted estimate、stress estimate、virtual exchange、dogfood、backtest、public candle-only outcome は、actual cash evidence ではない。

この repo はそれを誤って合格扱いしないように guard を置いている。その設計はよいが、進捗率としては actual cash blocker の重みが大きい。

## 30%未満になる条件

最終形を production live trading まで含めるなら、評価は 30%未満になる。

未証明または未許可のもの:

- production live order smoke
- signing / wallet / exchange write integration
- Bitget credentialed read-only network smoke
- Bitget demo order lifecycle
- live order preview / 注文候補生成の正式 command surface
- tiny live measurement 実行
- isolated margin / withdrawal disabled API key / IP restriction / max notional cap / flat reconciliation を満たした実運用

現行 repo には、それらを混同しないための shadow、plan、review、permission boundary はある。だが、それは live trading 実装完了ではない。

## 次に進めるなら何をするか

最短の次手は、actual cash source を安全に入れるための入力仕様を決めること。

優先順:

1. actual cash source を、manual cash ledger plus explicit assignment で入れるか、live measurement artifact で入れるかを決める。
2. credential / exchange write なしで済むなら、まず manual cash ledger plus explicit assignment を優先する。
3. `crypto-perp-actual-cash-rows-build` に渡せる最小サンプルを作る。
4. `crypto-perp-actual-cash-report-gate` で non-actual basis を拒否できることを確認する。
5. `profit-core-reality-check` の blocker が `ACTUAL_CASH_SOURCE_MISSING` から次へ進むか確認する。
6. その後に risk-taker review、tiny-live shadow、human review を読む。

この順序なら、credential、exchange write、live order を使わずに、現在の最大 blocker を一段だけ進められる。

## やらないこと

次はやらない。

- preview rows を actual cash として扱う。
- before-cost proxy を利益証拠として扱う。
- cost-adjusted estimate を実損益として扱う。
- backtest pass を alpha proof として扱う。
- public candle-only outcome を cash evidence として扱う。
- dogfood / status / viewer artifact を profit evidence として扱う。
- explicit approval なしに credential、external API、demo/testnet order lifecycle、exchange write、wallet/signing、live order、tiny-live execution を行う。

## 実務上の完了定義

この repo の「最終形」を段階別に定義すると、次のようになる。

### Stage 1: Local research platform

完了条件:

- Strategy Lab / Strategy Authoring / backtest / review / stage decision が current docs と CLI に沿って使える。
- schema validation と docs / CLI catalog check が通る。
- local artifact で next action と stop condition が分かる。

現在評価: ほぼ実用域。

### Stage 2: Profit evidence loop

完了条件:

- real event と matured outcome がある。
- actual cash source がある。
- actual cash rows が作れる。
- actual-cash report gate が通る、または失敗理由を出す。
- Reality Check が deterministic に次 blocker を出す。
- non-actual evidence が混入しない。

現在評価: event / outcome までは進んだ。actual cash source で停止中。

### Stage 3: Human risk review

完了条件:

- actual cash basis の tournament / risk review が読める。
- NO_TRADE を含む同一 event set 比較ができる。
- largest loss、profit concentration、operator time、bias guard が読める。
- human review が live permission ではなく、次の判断記録として残る。

現在評価: surface はある。actual cash basis の入力が足りない。

### Stage 4: Tiny-live preparation

完了条件:

- explicit approval がある。
- isolated margin、withdrawal disabled API key、IP restriction、max notional cap、flat reconciliation 条件が満たされる。
- tiny-live shadow が false permission のまま事前条件を検査する。
- order lifecycle 実行は別承認で扱う。

現在評価: planning / shadow surface はある。実行は未承認、未実行。

### Stage 5: Production operations

完了条件:

- credentialed read-only smoke、demo/testnet lifecycle、production write boundary、kill switch、monitoring、reconciliation、audit、rollback がつながる。
- live order と wallet/signing の責任境界が明示される。
- failure mode と stop condition が運用 runbook に閉じる。

現在評価: production trading としては未完成。

## 抜け、漏れ、誤謬リスク

- この文書は current repo の docs / CLI / git 状態からの評価であり、市場で勝てる確率を評価していない。
- `tests/test_*.py` や schema の file count は規模の補助情報であり、品質や利益の証明ではない。
- `./scripts/check` の full run は通過したが、これは品質ゲートであり、利益証拠ではない。
- `data/` は runtime / generated state であり、fresh checkout では存在しない artifact がある。
- historical docs や archive docs は current proof として扱わない。
- actual cash source をどう入れるかは未決。manual ledger で進める場合も、入力の出所、手数料、slippage、assignment の明示が必要。
