<!--
作成日: 2026-06-27_20:08 JST
更新日: 2026-06-27_20:08 JST
-->

# Crypto Perp Profit-Readiness Evidence Run Plan

## 結論

現時点の `data/crypto_perp` だけでは profit-readiness 判定へ進まない。local inventory で実 `event`、実 `outcome`、`source_availability`、`tournament_rows_v2`、cash ledger、live measurement artifact が見つからないため、今回の evidence run は `BLOCKED_MISSING_EVENT_OR_OUTCOME` で止める。

既存の `truth_cycle_*_check` artifact は dogfood / status / viewer flow の確認であり、利益証拠ではない。これらを `actual_cash_result_usd`、実 cash evidence、または tiny-live 測定済み evidence として扱わない。

## 現物確認

2026-06-27_20:08 JST 時点で確認した repo 状態:

- branch: `ai/crypto-perp-profit-readiness-20260627-1901`
- `git status --short --branch`: clean, `origin/main` と同一
- HEAD: `0f2066c docs: update current state and runbooks with profit-readiness evidence layer references`
- `.ai_memory/HANDOFF.md`: 別作業 `ai/strategy-ai-review-structured-findings-20260627-1822` の restart artifact なので、今回の Crypto Perp 判定の正本にしない

確認した local artifact 状態:

- あるもの: `data/crypto_perp/truth_cycle_*_check/` 配下の `dogfood_pack.md`、`truth_cycle_status.json`、`truth_cycle_status.md`、Daily Brief、Workbench Viewer artifact
- 見つからないもの: 実 `crypto_perp_event.v1`、実 `crypto_perp_outcome.v1`、`crypto_perp_source_availability.v1`、`crypto_perp_tournament_rows.v2`、cash ledger、live measurement artifact
- `find data/crypto_perp ... '*event*.json' '*outcome*.json' '*rows*v2*.json' '*cash*ledger*.json' '*live*measurement*.json' '*source*availability*.json' '*probe*audit*.json' '*raw*refresh*.json'` は該当なし

確認した CLI surface:

- `crypto-perp-truth-cycle-status`
- `crypto-perp-source-availability`
- `crypto-perp-replay-slice`
- `crypto-perp-feature-pack`
- `crypto-perp-edge-score`
- `crypto-perp-tournament-rows-v2`
- `crypto-perp-bias-guard`

## 目的

次の問いを、local artifact に基づいて判定できる状態まで進める。

```text
同じ event set で REVERSAL_SHORT / CONTINUATION_LONG / NO_TRADE を比較し、
fee / funding / slippage / operator time / data gap を含めても、
NO_TRADE を上回る行動候補が残るか。
```

ただし、実 event または実 outcome が無い場合は、利益判断へ進まず `BLOCKED_MISSING_EVENT_OR_OUTCOME` として止める。

## 制約

- 全ブランチをマージしない。
- `cascade/*` は混ぜない。
- 旧 M00-M11 plan package は historical implementation contract として扱う。
- 新 surface は追加しない。既存 CLI / schema / tests / docs を使う。
- 手入力 outcome は dry-run / proxy として扱い、profit evidence や actual cash evidence にしない。
- `actual_cash_result_usd` は cash ledger または live measurement artifact がある時だけ使う。
- 通常の replay / preview / simulation は `cost_adjusted_cash_estimate_usd`、`stress_cash_estimate_usd`、`evidence_level` で読む。
- 欠損 source は 0 埋めせず、`known_gaps` として残す。
- `NO_TRADE` は失敗ではなく正式 action として比較する。
- event 数不足時は `pbo_status=NOT_ESTIMABLE` とする。
- public network、credentialed read-only、exchange write、live order、自動売買は対象外。
- public Bitget probe は、別途明示承認と `SIS_ALLOW_PUBLIC_NETWORK=1` がある時だけ別作業で扱う。
- tiny-live shadow は非発注 preflight だけ。PASS しても live permission ではない。

## 正本

- `docs/NEXT_DIRECTION_CURRENT.md`
- `docs/runbooks/CRYPTO_PERP_TRUTH_CYCLE_RUNBOOK.md`
- `docs/crypto_perp/PROFIT_READINESS_EVIDENCE_PLAN_2026-06-27.md`
- `docs/crypto_perp/PROFIT_READINESS_ACCEPTANCE_VOCABULARY.md`
- `src/sis/commands/crypto_perp_profit_readiness.py`
- `src/sis/commands/crypto_perp_truth_cycle.py`
- `src/sis/crypto_perp/`
- `schemas/crypto_perp_*.schema.json`
- `tests/crypto_perp/`
- `uv run sis --help`

## 対象 artifact

生成候補:

- `data/crypto_perp/artifact_inventory/latest/`
- `data/crypto_perp/truth_cycle_status/latest/`
- `data/crypto_perp/source_availability/<event-id>/`
- `data/crypto_perp/replay_slice/<event-id>/`
- `data/crypto_perp/feature_pack/<event-id>/`
- `data/crypto_perp/edge_score/<event-id>/`
- `data/crypto_perp/tournament_rows_v2/<event-id>/`
- `data/crypto_perp/bias_guard/<event-id>/`

現在は実 event / outcome が見つからないため、`source_availability` 以降の artifact 生成に進まない。

## 実行順

### C00: repo 状態を固定確認する

実行する:

```bash
git status --short --branch
git log --oneline --decorate -5
```

dirty がある場合は今回対象かどうかを確認し、無関係なら触らない。

### C01: artifact inventory を作る

`data/crypto_perp` 配下から次を一覧化する。

- event
- outcome
- probe audit
- raw refresh
- rows-v2
- source availability
- cash ledger
- live measurement

実 event または実 outcome が無い場合は、以後の profit-readiness 判定を停止する。dogfood / status artifact は UI / flow 確認であり、profit evidence として扱わない。

### C02: 既存 artifact だけで truth-cycle status を作る

`crypto-perp-truth-cycle-status` には実在 path だけを渡す。

`path_not_found`、`MISSING_PROBE_AUDIT`、`NEEDS_ACTUAL_CASH` が出たら次 stage に進まない。`recommended_next_command` は許可ではなく、次に欠けている local step として読む。

現在は実 event / outcome が見つからないため、この段階で `BLOCKED_MISSING_EVENT_OR_OUTCOME` として止める。

### C03: 実 event がある場合だけ local evidence chain を作る

実 event artifact がある時だけ次へ進む。

```bash
uv run sis crypto-perp-source-availability --help
uv run sis crypto-perp-replay-slice --help
uv run sis crypto-perp-feature-pack --help
uv run sis crypto-perp-edge-score --help
```

books / trades / depth の欠損は optional feature 欠損として `known_gaps` に残す。0 埋めしない。

### C04: 実 outcome がある場合だけ rows-v2 を作る

実 outcome artifact がある時だけ次へ進む。

```bash
uv run sis crypto-perp-tournament-rows-v2 --help
```

`REVERSAL_SHORT`、`CONTINUATION_LONG`、`NO_TRADE` が同一 event set で 3 rows 揃うことを確認する。手入力価格だけで作った outcome は dry-run / proxy 扱いにし、actual cash evidence として扱わない。

### C05: bias guard を通す

```bash
uv run sis crypto-perp-bias-guard --help
```

event 数不足なら `pbo_status=NOT_ESTIMABLE` を正式結果として採用する。stress loss、profit concentration、operator time cost が悪い場合は停止する。

### C06: 判定を出す

`cost_adjusted_cash_estimate_usd` と `stress_cash_estimate_usd` で `NO_TRADE` を上回る action が残るかを見る。known gaps が判断を左右する場合は `INCONCLUSIVE_DATA` とする。

`actual_cash_result_usd` が無い場合は、実利益証明とは書かない。

### C07: public probe / tiny-live は別承認に切り出す

probe audit 不足なら、次 action は public probe 承認判断で止める。`READY_FOR_HUMAN_TINY_LIVE_REVIEW` が出ても、live order permission ではなく承認準備として止める。

## テスト方針

文書作成だけの場合:

```bash
uv run python scripts/check_current_docs.py
git diff --check
```

CLI catalog や runbook に触った場合:

```bash
uv run python scripts/check_cli_catalog.py
uv run python scripts/check_current_docs.py
git diff --check
```

Crypto Perp 実装に触った場合:

```bash
uv run pytest tests/crypto_perp -q
uv run python scripts/check_cli_catalog.py
uv run python scripts/check_current_docs.py
./scripts/check
git diff --check
```

## 完了条件

- この文書が `docs/crypto_perp/PROFIT_READINESS_EVIDENCE_RUN_PLAN_2026-06-27.md` に保存されている。
- timestamp header が repo rule 通りに入っている。
- 現在 `data/crypto_perp` に実 event / outcome が無いことを隠していない。
- dogfood / status artifact を profit evidence と誤表示していない。
- 手入力 outcome を actual cash evidence と誤表示しない。
- `actual_cash_result_usd` と estimate / proxy の境界が明記されている。
- `NO_TRADE` が正式 action として扱われている。
- source 欠損を 0 埋めしないことが明記されている。
- public network / credential / exchange write / live order / 自動売買が対象外である。
- PBO 不足時に `NOT_ESTIMABLE` とすることが明記されている。
- tiny-live shadow が live permission ではないことが明記されている。
- `uv run python scripts/check_current_docs.py` が通る。
- `git diff --check` が通る。

## 停止条件

- 実 event または実 outcome が存在しない。
- dogfood artifact だけで profit-readiness 判定を進めようとしている。
- 手入力価格だけの outcome を実データ証拠として扱っている。
- source availability が不明。
- books / trades 欠損を 0 として扱っている。
- before-cost proxy を actual cash と表示している。
- `NO_TRADE` row が欠けている。
- event set が action 間で一致しない。
- lookahead violation または recursive warmup violation がある。
- sample insufficient を隠して PBO を推定済みにしている。
- `stress_cash_estimate_usd < 0` の行動候補を先へ進めている。
- profit concentration が高すぎる。
- operator time cost が利益候補を上回る。
- public network 承認なしに probe を実行しようとしている。
- secret / credential が artifact に混ざる。
- exchange write または live order 呼び出しが発生する。

## 今回の停止判定

状態: `BLOCKED_MISSING_EVENT_OR_OUTCOME`

理由:

- 実 event artifact が見つからない。
- 実 outcome artifact が見つからない。
- dogfood / status artifact だけでは同一 event set の action 比較ができない。
- cash ledger または live measurement artifact がないため、`actual_cash_result_usd` を使えない。

次に必要な人間判断:

- public Bitget probe を別作業として承認するか。
- 承認する場合でも `SIS_ALLOW_PUBLIC_NETWORK=1` を明示した public network probe だけに限定し、credentialed read-only、exchange write、live order、自動売買へは進めない。
