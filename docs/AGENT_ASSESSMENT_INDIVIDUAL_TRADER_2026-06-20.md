<!--
作成日: 2026-06-20_12:00 JST
更新日: 2026-06-21_21:41 JST
-->

# Agent Assessment: Individual Trader Lens

## この文書の位置づけ

Codex / Grok エージェントが `marketlens-strike` を調査した結果の**私見**。

正本ではない。優先順位:

1. `src/`, `tests/`, `schemas/`, `configs/`, `scripts/`, CLI help
2. `data/` の runtime artifact（存在する場合）
3. `docs/CURRENT_STATE.md` など repository 内 current doc
4. **この文書**

README と `CURRENT_STATE.md` には、正本ではない判断補助として掲載済み。実装判断では上の優先順位を守る。

---

## 一行結論

`marketlens-strike` は**月数百ドル規模の個人がアルファを自動発見する装置ではない**。**弱い候補を早く捨て、paper と backtest のズレを記録し、焦って本番相当に進まない**ための安全柵と反省日記である。重い。それでも「個人向け」と銘打っているのは、notional と損失上限の想定が小さいからで、操作が軽いからではない。

---

## 検証スナップショット

この文書は私見メモなので、固定のCLI数やpytest件数を投資判断の根拠にしない。現在値は必ず次で取り直す。

```bash
uv run python -V
uv run python scripts/check_cli_catalog.py
uv run python scripts/check_current_docs.py
./scripts/check
```

2026-06-21_20:58 JST の軽量再確認:

| チェック | 結果 |
|---------|------|
| Python | 3.13.7 |
| check_current_docs.py | pass（148 current docs） |
| check_cli_catalog.py | pass（205 public CLI commands） |

2026-06-20 再調査時点の古いスナップショット:

```bash
./scripts/check
```

結果:

| チェック | 結果 |
|---------|------|
| ruff check / format | pass |
| check_current_docs.py | pass |
| check_cli_catalog.py | pass（189 public CLI commands） |
| pyrefly | pass |
| ty | pass |
| pytest | **1340 passed** |

機械カウント（`src/sis/**/*.py`, `schemas/*.json`）:

| 項目 | 値 |
|------|-----|
| Python ソース行数 | 103,677 |
| JSON Schema | 121 |
| 公開 CLI | 189（当時値。現在は上の再確認結果を優先） |

Workbench first slice T0–T12b 完了は `docs/STRATEGY_OPERATIONS_WORKBENCH_COMPLETION_AUDIT_2026-06-19.md` の記述。**監査 doc の「完了」は first slice の契約完了であり、live 実戦完了ではない**。Crypto Perp についても、truth-cycle status、stage checklist、dogfood pack、Daily Brief / Workbench Viewer summary が増えたことは「読みやすくなった」という意味であり、live readinessではない。

---

## 初版からの修正（内省・誤謬リスクの洗い出し）

初版 `AGENT_ASSESSMENT` で不正確・不足だった点をここに固定する。

| 初版の書き方 | 問題 | 修正 |
|-------------|------|------|
| 「1 回あたり約 $0.66」だけ強調 | 総利益・PASS フラグ・データ出自を省略し、誤読を誘う | 下記「誤読しやすい数字」参照。fixture 合成データであることを明記 |
| 「標準 CLI から live 注文は出せない」 | 粗すぎる。`cancel-order` / `close-position` は公開 CLI にある | **新規発注の標準 operator surface はない**（`place-order` 系なし）。`micro_live_canary` はコード内に `place_limit_order` あり。`configs/micro_live_policy.yaml` は `enabled: false` |
| paper「8 session 回したのに足りない」 | ボトルネックが不明確 | **fills は 20/20 で充足**。詰まっているのは **trading_days 1/10 のみ** |
| 「観測入口が狭い」だけ | `ingest-research-data`（yfinance 等）の存在を落とした | 研究用価格取得経路はある。ただし **live 執行データではない**（readiness doc 記載） |
| `./scripts/check` 未実行 | 検証状態が古い | 本更新で再実行済み |
| `data/` の前提 | fresh checkout で空である点を書いていない | `.gitignore` で `data/` 除外。初回は seed / コマンド実行が必要 |

**まだ未検証（この文書の限界）:**

- `cancel-order` / `close-position` を credential ありで実際に叩いた結果
- `ingest-research-data` のネットワーク実行と生成 parquet の品質
- 全 README Read First 20 本の精読
- ユーザー口座サイズ・損失許容の個別適合

---

## 誤読しやすい数字（一次ソース付き）

### バックテスト例 `data/research/strategy_backtest_metrics.json`

| フィールド | 値 | 読み方 |
|-----------|-----|--------|
| `signals_considered` | 7 | 極小サンプル |
| `executed_signal_summary.first_ts_signal` / `last_ts_signal` | 2026-01-05 〜 2026-01-06 | **実質 2 日分** |
| `executed_signal_summary.avg_signal_return` | ≈ 0.000665 | $1000 notional なら **約 $0.66/回**（グロス） |
| `executed_signal_summary.total_signal_return` | ≈ 0.00465 | 7 回合計グロス ≈ **$4.65**（$7000 想定 notional 合計） |
| `aggregate_metrics.total_return` | ≈ 0.00466 | 約 **0.47%** |
| `aggregate_metrics.cost_drag_bps` | 7.0 | コストはあるが fixture では小さい |
| `summary.backtest_passed` | **true** | **危険な安心材料**。閾値 `max_drawdown` のみ pass 等、サンプルが小さすぎる |
| `metrics[0].sharpe` | **8300** | 7 トレードでは統計として無意味。見ない |

### この backtest が「儲かった」と言えない理由（データ出自）

`scripts/seed_strategy_authoring_baseline_data.py` が作る **deterministic fixture**:

- `trade_allowed: True` 固定
- `research_return_*` が単調増加
- spread **1 bps**、depth 十分、oracle/mark 完全一致
- cost matrix の notes: `"deterministic Strategy Authoring baseline fixture; not live venue evidence"`

つまり `backtest_passed: true` は**パイプライン接続テストの合格**であって、戦略優位の証明ではない。初版はこの点を薄くした。ここが最大の誤謬リスク。

### paper 観察 `data/research/strategy_lifecycle/paper_observation_status.json`

再取得: `2026-06-19T23:59:34Z`（`strategy-paper-observation-status` 実行）

| フィールド | 値 | 読み方 |
|-----------|-----|--------|
| `normal_session_count` | 8 | session を何度も切った |
| `latest_normal_requirement_gaps.fills` | 20/20 **met** | fill 数はもう足りている |
| `latest_normal_requirement_gaps.trading_days` | **1/10**（残り 9） | **ボトルネックはここだけ** |
| `latest_smoke_decision` | PASS | normal にはカウントしない |
| `credentials_used` / `external_api_used` | false | 外部口座つながっていない観測 |
| `live_conversion_allowed` / `permits_live_order` | false | 当然 |

泥臭い現実: **手順を回す労力と、カレンダーが進む速度が釣り合わない**。同日 rerun や fill 水増しは仕様上無効（`NEXT_DIRECTION_CURRENT.md` 明記）。

---

## リポジトリが実際に何か

### 公式の自己定位（doc 原文の要約）

`docs/TARGET_STRATEGY_OPERATIONS_WORKBENCH_2026-06-18.md`:

- 完全自動売買 bot ではない
- 個人システムトレーダー向け Human-in-the-loop Strategy Operations Workbench
- 「弱い候補を早く捨て、残った候補だけを小さく現実へ近づける運用装置」
- 実務評価で「方向性 80/100」「旧い入力定義 55/100」など自己採点あり

### 二重構造（doc と生成物の縫い目）

| 側 | 内容 |
|----|------|
| 宣言 | backtest-first / venue-neutral、OODA、反ナラティブ guard |
| 生成物 | Trade[XYZ] fixture、QQQ proxy、NDX 研究、paper session の trading day 待ち |

「個人向け」の実装は **口座サイズと損失上限の設定値** に現れ、`configs/micro_live_policy.yaml` は `max_notional_usd: 50`、`enabled: false`。一方で **検査の厳しさとコード量は機関寄り**。

### fresh checkout の現実

- `data/` は `.gitignore` 対象
- 初回は `uv run python scripts/seed_strategy_authoring_baseline_data.py` 等で fixture を作るか、各種 `sis` コマンドを回して生成する
- **この workspace には既に `data/` がある**ため、別環境では本書の JSON 数値は一致しない可能性がある

---

## live / execution について（粗い言い方の修正）

`docs/CURRENT_STATE.md` の正確な境界:

> `micro_live` 系 code は存在するが、**標準 operator CLI の live execution surface としては exposed していない**

コード上の事実:

| あるもの | ないもの / 止まるもの |
|---------|---------------------|
| 公開 CLI: `estimate-order`, `cancel-order`, `close-position`, `balance-status`, `fill-status` 等 | 公開 CLI に `place-order` 相当なし |
| `src/sis/execution/micro_live_canary.py` 内の `adapter.place_limit_order` | `micro_live_policy.enabled: false` が既定 |
| `paper-step`, `paper-from-intents`（紙上約定） | `permits_live_order: false` が artifact に埋め込まれる |

初版の「live 注文は出せない」は、**「標準 operator 導線から新規 live 発注に進めない」** と読み替えるのが正確。execution 系コマンドが存在することと、日常使いの live surface がないことは両立する。

---

## データ取得の経路（割愛していた部分）

| 経路 | 用途 | 限界 |
|------|------|------|
| `seed_strategy_authoring_baseline_data.py` | ローカル合成 fixture | live venue 証拠ではない |
| `ingest-research-data` | yfinance 等で研究用 OHLCV | research/backtest reference。live 執行データではない |
| `collect-trade-xyz-quotes` 等 | Trade[XYZ] read-only | network・設定が必要 |
| NDX Layer 2.2 `scope.yaml` | `external_api_allowed: false` | fixture-first 研究ゲート |

「入口が狭い」は **NDX 因果研究と paper 合格の現実観測** の話。価格 CSV を1本用意して backtest する道はあるが、**それを live 安全と混同しない**こと。

---

## 個人トレーダー向けと言えること / 言えないこと

### doc + data で裏が取れること

- backtest `PASS`、pack validation `PASS`、smoke `PASS` はいずれも **paper/live 許可ではない**（`strategy_backtest_pack_validation.json` で `permits_live_order: false`, `live_conversion_allowed: false` を機械検査）
- smoke と normal paper は分離
- NDX/QQQ 系は evidence 不足時 **paper path で fail closed**（`REPO_CAPABILITIES_PLAIN_JA`）
- Workbench T0–T12b first slice は実装済み（監査 doc）だが Svelte UI・production live・optimizer 自動実行は未完了

### 初版会話で外挿したもの（この文書でも採用しない）

- クオンツ文献名のリスト
- 「クジラと違うから勝てる」ナラティブ
- 「スプレッドシートの方がいい」断定
- 個人エッジの肯定 catalog

### 私見（外挿だが、repo 構造から言えること）

個人の強み（小さい・待てる・ニッチ）は**ありうる**が、**この repo がそれを発見する装置ではない**。発見するのはユーザーの仮説と市場。repo は **その仮説が早く死ぬ条件を記録する** 側。

---

## この repo で実際に得られるもの / 得られにくいもの

### 得られる（ドルではなく判断材料）

1. 仮説とデータ前提の固定（input contract / idea intake）
2. バックテスト物語の破綻条件（stress, regime, no-lookahead, pack validation）
3. paper と backtest のズレ記録（drift review, runtime observation）
4. 「なぜその日進んだか」の hash 付きログ（Strategy Review, stage decision）
5. **合成 fixture でもパイプライン全体が動くことの確認**

### 得られにくいもの

- 再現可能な月 $X の利益
- 少ないコマンド数での日常運用
- fresh clone ですぐ見える実戦成績（`data/` なし）
- UI（静的 HTML viewer のみ）

---

## 個人が最初に見るべき artifact（最小セット）

教科書的優先順位ではなく、**誤って安心するのを防ぐ順**:

```text
1. data/research/strategy_backtest_metrics.json
   → backtest_passed を信じる前に signals_considered とデータ出自を見る

2. data/research/backtest_pack/strategy_backtest_pack_validation.json
   → decision=PASS でも permits_live_order / live_conversion_allowed

3. data/research/strategy_lifecycle/paper_observation_status.json
   → latest_normal_requirement_gaps.trading_days（fills だけ見て満足しない）

4. data/research/strategy_authoring_baseline_* の生成元
   → scripts/seed_strategy_authoring_baseline_data.py（合成かどうか）

5. configs/micro_live_policy.yaml
   → enabled: false と上限額
```

---

## 最小の現実的コマンド列（個人・初回）

```bash
uv sync --dev --locked
uv run python scripts/seed_strategy_authoring_baseline_data.py
uv run sis strategy-author-validate --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml
uv run sis strategy-author-run --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml --through backtest
uv run sis strategy-backtest-pack-validate
uv run sis strategy-paper-observation-status --data-dir data --out data/research/strategy_lifecycle --reports-dir data/reports
```

ここまでで分かること: **配線は動く。数字の大きさや PASS は信用しない。paper は trading day で待たされる。**

---

## 公式 doc の縫い目（再掲・補足）

| 層 | ファイル | 注意 |
|----|---------|------|
| 完成形の設計 | `TARGET_STRATEGY_OPERATIONS_WORKBENCH_2026-06-18.md` | 現状証明ではない。自己採点あり |
| 実装 catalog | `IMPLEMENTED_SURFACES.md` | CLI の存在リスト |
| 境界 | `CURRENT_STATE.md` | できないこと |
| 運用の泥 | `NEXT_DIRECTION_CURRENT.md` | trading day・session 使い回し不可 |
| 監査スナップショット | `STRATEGY_OPERATIONS_WORKBENCH_COMPLETION_AUDIT_2026-06-19.md` | 日付固定。再実行で変わるものは pytest 件数等 |
| 実行結果 | `data/**` | 環境依存。最も具体的 |

---

## 使う / 使わない（私見・改訂）

### 使う価値がある

- 本番前に**何週間も**自分を検査したい人
- 「あのときなぜ進んだか」を後から追いたい人（artifact + hash）
- smoke と normal を混同して焦りたくない人
- **数百ドルが大きいから、$10 単位で計画だけ残したい人**（micro live plan）

### 向かない

- まず具体ルールで今月 $100 が欲しいだけの人
- CLI全体の多さで集中力が切れる人
- すでにブローカーで小さく live し学習中の人（この repo は前段の検査）

### 現実的な使い方（改訂）

1. 合成 fixture で動作確認（戦略優位の確認ではない）
2. 仮説を 1 本に絞り `strategy_idea` に書く
3. backtest で `backtest_passed` より `blocked_reason_counts` と `cost_drag_bps`
4. 自分の価格データに差し替えてから再度 backtest（`ingest-research-data` 等）
5. paper は勝敗より `trading_days` の増え方と drift
6. live は標準導線にない前提で、計画 artifact まで

---

## 調査で触った一次ソース

### ドキュメント

`AGENTS.md`, `README.md`, `docs/CURRENT_STATE.md`, `docs/REPO_CAPABILITIES_PLAIN_JA_2026-06-17.md`, `docs/IMPLEMENTED_SURFACES.md`, `docs/CODE_STATUS.md`, `docs/ARCHITECTURE_AND_PHASES.md`, `docs/NEXT_DIRECTION_CURRENT.md`, `docs/TARGET_STRATEGY_OPERATIONS_WORKBENCH_2026-06-18.md`, `docs/STRATEGY_OPERATIONS_WORKBENCH_COMPLETION_AUDIT_2026-06-19.md`, `docs/AI_AGENT_STRATEGY_BACKTEST_GUIDE.md`, `docs/strategy_research_lab/09_STRATEGY_AUTHOR_GUIDE.md`, `docs/strategy_micro_live_plan/README.md`

### コード・設定・データ

`scripts/seed_strategy_authoring_baseline_data.py`, `configs/micro_live_policy.yaml`, `configs/research_layer_2_2/ndx/scope.yaml`, `configs/research_layer_2_2/ndx/core_dag.yaml`, `src/sis/commands/execution.py`, `src/sis/execution/micro_live_canary.py`, `src/sis/execution/live_order_policy.py`, `data/research/strategy_backtest_metrics.json`, `data/research/strategy_lifecycle/paper_observation_status.json`, `data/research/backtest_pack/strategy_backtest_pack_validation.json`, `.gitignore`

### コマンド（初回調査 + 本更新）

`uv run sis --help`, `uv run sis implementation-status`, `uv run sis strategy-author-explain`, `uv run python scripts/check_cli_catalog.py`, `uv run pytest --collect-only`, `./scripts/check`, `uv run sis strategy-paper-observation-status`

---

## 会話経緯

1. リポジトリ全体の調査（正確だが百科事典的）
2. 深掘り（架构が長く泥が足りない）
3. 「教科書すぎる」→ 外挿を削り安全柵論に寄せた
4. 本更新 → 一次ソース再照合、初版の誤謬リスクを明示、数字の読み方を具体化

---

## 最後に

`marketlens-strike` は、個人の数百ドルを守る **安全柵と記録装置** として設計と実装が噛み合っている。アルファ工場ではない。

利益は repo の外——自分の仮説、差し替えた現実データ、増えた trading day、手動の判断——でしか生まれない。repo の価値は「儲ける約束」ではなく、**合成 fixture で PASS した気にならないこと**、**paper が backtest とズレたときに言い訳を残せないこと**、**$50 のミスを計画段階で書き留めること**にある。

それでも月 $100 を最優先するなら、この repo 全部より、先に **1 本のルール・1 つのコスト計算・1 つの実口座 or paper broker** の方が短い。両者は競合ではなく、repo は後から「自分を騙していなかったか」を検査する保険、と割り切るのが私見の落としどころである。
