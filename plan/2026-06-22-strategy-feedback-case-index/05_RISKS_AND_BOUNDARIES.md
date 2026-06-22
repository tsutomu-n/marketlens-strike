<!--
作成日: 2026-06-22_17:55 JST
更新日: 2026-06-22_18:36 JST
-->

# Risks And Boundaries

## 現実的なリスク

### R1: Strategy Input Contract を自動更新したくなる

この計画の目的は更新候補を作ることだけ。contract file を直接 patch しない。自動適用を入れると、artifact review と human decision の境界が崩れる。

対策:

- proposal / review schema に `auto_applied=false` と `direct_contract_edit_allowed=false` を入れる。
- service から contract writer を呼ばない。
- tests で true を拒否する。

### R2: Case Index が full registry に膨らむ

この計画の index は派生成果物であり、DB registry ではない。merge policy、conflict resolution、timeline editor、search DB は作らない。

対策:

- 入力は existing `strategy_case_lite.v1` artifact に限定する。
- 出力は再生成可能な JSON / Markdown に限定する。
- persistence は filesystem artifact のみ。

### R3: Viewer 改善が UI プロジェクト化する

既存の Static Workbench Viewer に summary を足すだけにする。Svelte UI、server、client-side state、interactive editor は別計画。

対策:

- `strategy-workbench-viewer-build` の既存 static HTML generation pattern を維持する。
- 追加は artifact summary と HTML section に限定する。

### R4: paper / live readiness を誤って主張する

Runtime Observation、Learning Event、Case Index、Viewer はどれも実行許可ではない。

対策:

- docs と schema boundary に `permits_live_order=false`、`permits_exchange_write=false` を明記する。
- `NEXT_DIRECTION_CURRENT.md` では paper bridge / network probe / schema widening を未実装のまま残す。

### R5: source artifact の provenance が弱い

更新候補がどの artifact 由来か追えないと、後からレビューできない。

対策:

- source path、sha256、schema version、artifact kind を必須にする。
- output Markdown にも source hash を表示する。

### R6: source contract なしの proposal が apply-ready に見える

`--source-contract` を optional にすると、観察結果だけで contract 更新が確定したように見えやすい。

対策:

- source contract なしの場合は `READY_FOR_HUMAN_REVIEW` ではなく、source contract context 不足の status にする。
- review artifact でも direct apply を許可しない。
- `--source-contract` がある場合は `StrategyInputContract` model validation を通す。
- contract 内の declared source hash / columns / timestamp 検査は既存 `strategy-input-contract-validate` の責務として分け、この計画では暗黙に再実装しない。

### R7: Case Index の data-dir scan が無関係 JSON を拾う

`data/` には viewer manifest、report summary、既存 index、他 domain artifact が混在する。拡張子だけで拾うと case count と strategy count が壊れる。

対策:

- `schema_version == "strategy_case_lite.v1"` の JSON だけを採用する。
- case-lite 0件は success にしない。
- explicit `--case` は case-lite 以外を fail にする。
- data-dir scan は schema_version が違う JSON を無視し、schema_version が `strategy_case_lite.v1` の壊れた JSON を fail にする。
- latest case selection は deterministic にする。

## 抜け漏れチェック

- Runtime Observation だけで動くか: 必須。
- Learning Event だけで動くか: 必須。
- source contract がない場合でも proposal を作れるか: 必須。
- source contract がない proposal を apply-ready にしないか: 必須。
- source contract がある場合に hash を残すか: 必須。
- source contract の内部 source validation をこの計画で再実装していないことを docs に明記したか: 必須。
- review で approve / reject / hold を表現できるか: 必須。
- review の approved_change_ids が proposal change ids と整合するか: 必須。
- direct apply をしないか: 必須。
- case-lite artifact が複数ある場合に index できるか: 必須。
- case-lite artifact が壊れている場合に黙って落とさないか: 必須。
- data-dir scan が case-lite 以外を混ぜないか: 必須。
- viewer に source hash が出るか: 必須。
- docs / CLI catalog から新規 command を辿れるか: 必須。

## 別計画に送るもの

- Paper vs backtest bridge validation
- credentialed venue read-only probe
- Bitget demo order lifecycle
- production venue schema widening
- micro live measurement
- live order preview command
- Svelte UI
- Strategy Case full registry
- Strategy Input Contract direct patch flow

## Better にした判断

当初候補にあった `Strategy Case registry` は、この計画では `Strategy Case Lite Index` に落とす。理由は、現行 code には `strategy_case_lite.v1` の artifact surface があり、DB registry や merge policy の前提はまだないため。

当初候補にあった `auto反映` は、この計画では `update proposal artifact` に落とす。理由は、現行 Strategy Operations が human-in-the-loop であり、Strategy Input Contract を直接編集する writer を増やすと境界が壊れるため。

当初候補にあった paper bridge と venue probe は、この計画から外す。理由は、承認、credential、network、副作用、venue-specific scope が混ざり、今回の local artifact workflow と検証粒度が違うため。
