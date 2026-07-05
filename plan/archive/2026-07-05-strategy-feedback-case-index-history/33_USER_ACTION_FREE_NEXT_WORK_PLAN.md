<!--
作成日: 2026-06-23_21:11 JST
更新日: 2026-06-23_21:19 JST
-->

# User-Action-Free Next Work Plan

## 結論

この文書は、ユーザー追加アクションなしで次の実装者が進められる作業だけを固定する実行計画です。

最初に進める範囲は local/offline docs と restart artifact の整理までです。schema、CLI、domain logic、DB、server UI、Svelte UI、runtime `data/` artifact の正本化、paper/live/account/wallet/signing/exchange-write/profit readiness は対象外です。

## 目的

1. 次の実装者が古い handoff や未承認の外部作業に引っ張られず、現行 repo から再開できるようにする。
2. 今すぐ進められる local/offline 作業と、ユーザー承認・外部 evidence・credential・accounting source が必要な作業を分ける。
3. `.ai_memory/HANDOFF.md` は tracked plan doc の代替にせず、restart artifact として扱う。

## 実装前に必ず確認すること

次の確認は read-only で行う。古い pass count、古い HEAD、古い generated artifact snapshot は根拠にしない。

```bash
git status --short --branch
git log -1 --oneline --decorate
uv run python scripts/check_current_docs.py
uv run python scripts/verify_restart_contract.py --print-current-contract
```

期待する読み方:

- `git status --short --branch` は current branch と dirty state の確認だけに使う。
- `git log -1 --oneline --decorate` はその時点の HEAD を確認するために使う。
- `scripts/check_current_docs.py` は current docs metadata、links、EOF、legacy roots、semantic drift、plan routing を確認するために使う。
- `.ai_memory/HANDOFF.md` は restart artifact として読み、code、tests、schemas、config、lockfiles、CI、CLI help、tracked plan docs より優先しない。

## 対象ファイル

必須:

- `plan/2026-06-22-strategy-feedback-case-index/33_USER_ACTION_FREE_NEXT_WORK_PLAN.md`
- `plan/2026-06-22-strategy-feedback-case-index/00_READ_ME_FIRST.md`
- `plan/README.md`

必要な場合のみ:

- `.ai_memory/HANDOFF.md`
- `scripts/verify_restart_contract.py`
- `tests/test_restart_contract_verifier.py`

optional low-risk cleanup:

- `tests/strategy_workbench_viewer/test_strategy_workbench_viewer.py`
- `tests/strategy_workbench_viewer/` 配下の分割先 test helper / test module

## 制約

- local/offline docs、restart artifact、必要な場合の test-only refactor だけを扱う。
- `data/` は読むだけなら可。ただし判断根拠は tracked summary に要約し、raw secret、account、statement、注文 ID、残高全文は扱わない。
- `PASS`、`READY_FOR_HUMAN_REVIEW`、`READ_ONLY_GO`、`PAPER_OBSERVATION_CANDIDATE` を readiness と読まない。
- `.ai_memory/HANDOFF.md` は `.gitignore` 対象なので、tracked plan doc の代わりにしない。
- HANDOFF を更新する場合は既存 helper を使う。直接手編集しない。
- helper 更新後に frontmatter の `restart_contract_json` だけでなく、本文の restart line、A2 expect、verified facts も古い HEAD を残していないことを確認する。
- test 分割は実装本体ではなく optional cleanup として別 step にする。

実行しない:

- network probe
- credential 利用
- paper order
- live order
- wallet
- signing
- exchange write
- tiny live
- production trading
- schema / CLI / domain logic / DB / UI の変更

## 実行順

### N1: `33` plan doc を作る

目的: ユーザー追加アクションなしで進められる作業を、tracked plan doc として残す。

完了条件:

- この文書が存在する。
- 目的、制約、対象ファイル、テスト方針、完了条件、実行順、除外範囲を含む。
- metadata header に作成時点の東京時刻がある。

### N2: active read order に導線を足す

対象:

- `plan/2026-06-22-strategy-feedback-case-index/00_READ_ME_FIRST.md`
- `plan/README.md`

完了条件:

- active folder の read order から `33_USER_ACTION_FREE_NEXT_WORK_PLAN.md` に辿れる。
- `plan/README.md` の Active implementation plan 節から `33` に辿れる。

### N3: current-docs check を通す

実行:

```bash
uv run python scripts/check_current_docs.py
git diff --stat
```

完了条件:

- current-docs check が通る。
- diff が docs routing とこの plan doc に限定されている。

### N4: HANDOFF を必要時だけ atomic refresh する

条件:

- `git log -1 --oneline --decorate` と `.ai_memory/HANDOFF.md` の restart contract が矛盾している。
- 次の再開者が古い HEAD に引っ張られるリスクがある。

実行:

```bash
uv run python scripts/verify_restart_contract.py --refresh-contract --verification-note "<latest verification result>"
uv run python scripts/verify_restart_contract.py
sed -n '1,120p' .ai_memory/HANDOFF.md
```

完了条件:

- helper で restart contract が更新される。
- full check などを再実行した場合、`--verification-note` で `[FACT verification]` も同時に更新する。
- helper の verify が通る。
- `.ai_memory/HANDOFF.md` の本文に古い HEAD / stale status / stale diff summary が残らない。
- `.ai_memory/HANDOFF.md` は restart artifact のままで、tracked docs の正本にはしない。

### N4A: HANDOFF helper を必要時だけ harden する

条件:

- helper が `restart_contract_json` だけを更新し、本文の `Restart-ready when`、A2 `Expect`、`[FACT git-log]` などに古い HEAD が残る。

対象:

- `scripts/verify_restart_contract.py`
- `tests/test_restart_contract_verifier.py`

完了条件:

- `--refresh-contract` が frontmatter と本文の主要 restart 文言を同じ atomic replace で更新する。
- `--verification-note` を指定した場合、本文の `[FACT verification]` も同じ helper で更新する。
- 古い本文が残らないことを focused test で確認する。
- 既存 verifier の dirty / untracked / mismatch 検出を壊さない。

### N5: optional test split を別 step として判断する

対象:

- `tests/strategy_workbench_viewer/test_strategy_workbench_viewer.py`

目的:

- 1264 行の viewer test を挙動変更なしで分割できるか確認する。

実施する場合の前提:

- helper import 依存を先に整理する。
- test-only refactor に限定する。
- schema、CLI、domain logic、viewer output contract は変えない。

検証:

```bash
uv run ruff check tests/strategy_workbench_viewer
uv run ruff format --check tests/strategy_workbench_viewer
uv run pytest tests/strategy_workbench_viewer -q
```

この optional cleanup は、N1-N4 の完了条件ではない。

## 除外範囲

今回の実装対象に入れない:

- D1 / D2: paper evidence。ユーザー承認と外部 evidence が必要。
- D6 / D7: credentialed read-only network probe。network / credential 許可が必要。
- D8-D13: order、live、secret、account side-effect work。明示承認が必要。
- D15 / D21: accounting source や operational source が必要な判断。
- D14 / D17 / D19 / D20: 今回は設計前メモ候補としてのみ扱う。実装対象にしない。

## テスト方針

docs only:

```bash
uv run python scripts/check_current_docs.py
git diff --stat
```

HANDOFF 更新を含む場合:

```bash
git status --short --branch
git log -1 --oneline --decorate
uv run python scripts/verify_restart_contract.py --refresh-contract --verification-note "<latest verification result>"
uv run python scripts/verify_restart_contract.py
sed -n '1,120p' .ai_memory/HANDOFF.md
```

HANDOFF helper hardening を含む場合:

```bash
uv run pytest tests/test_restart_contract_verifier.py -q
uv run ruff check scripts/verify_restart_contract.py tests/test_restart_contract_verifier.py
uv run ruff format --check scripts/verify_restart_contract.py tests/test_restart_contract_verifier.py
```

optional test split を実施する場合:

```bash
uv run ruff check tests/strategy_workbench_viewer
uv run ruff format --check tests/strategy_workbench_viewer
uv run pytest tests/strategy_workbench_viewer -q
```

final safety:

```bash
uv run python scripts/check_current_docs.py
```

`./scripts/check` は、docs-only 変更では必須にしない。test split や Python code 変更を含めた場合だけ必要性を再判断する。

## 完了条件

- `33_USER_ACTION_FREE_NEXT_WORK_PLAN.md` が存在し、目的、制約、対象ファイル、テスト方針、完了条件を含む。
- `00_READ_ME_FIRST.md` と `plan/README.md` から `33` に辿れる。
- plan 内で「今進める local/offline 作業」と「ユーザー承認・外部 evidence が必要な作業」が分離されている。
- current-docs check が通る。
- optional test split を実施した場合、Viewer 近接 tests が通る。
- paper/live/account/wallet/signing/exchange-write/profit readiness を新たに主張していない。
- HANDOFF 更新を実施した場合、helper の restart contract verify が通り、frontmatter と本文の主要 restart 文言が現 HEAD と矛盾しない。

## 残リスク

- `.ai_memory/HANDOFF.md` は git 管理外なので、tracked docs だけでは restart artifact の現物更新を保証できない。
- runtime `data/` artifact は時間とローカル環境で変わる。tracked docs には要約だけを残し、raw artifact の存在を current proof として固定しない。
- Viewer test 分割は低リスクだが、helper import の整理で想定より diff が広がる場合は中止して別計画にする。
