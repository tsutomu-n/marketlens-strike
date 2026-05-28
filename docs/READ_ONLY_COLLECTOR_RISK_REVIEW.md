# Legacy Read-Only Collector Risk Review

> Current status: historical / legacy. This risk review describes the old gTrade/Ostium read-only collector path, not the current Trade[XYZ] quote collection path. Current Trade[XYZ] gate status is tracked in `docs/CURRENT_STATE.md` and `data/ops/phase_gate_review_summary.json`.

この文書は legacy `gtrade` / `ostium` read-only collector の実装に残る抜け、漏れ、誤謬リスク、改善余地を記録する。current Trade[XYZ] PR12 read-only gate のリスク一覧ではない。
実装計画とタスク一覧は `docs/READ_ONLY_COLLECTOR_IMPLEMENTATION_PLAN.md` を読む。
運用上の artifact contract は `docs/LIVE_EVIDENCE_READ_ONLY_COLLECTORS.md` を読む。

## Conclusion

legacy read-only 実データ取得の土台として使える。
ただし legacy collector chain の Phase gate を過信して Phase 2 へ進めるには早い。

Trade[XYZ] current path は別系統で、2026-05-28 時点の latest phase gate は `READ_ONLY_GO`、`phase2_entry_allowed=true`、`blockers=[]`。

主な理由は次のとおり。

- SDK read-only probe が「非空かつ期待 field を含む実データ」をまだ厳密検査していない
- Ostium top-level fetch failure が fail-closed summary として必ず残る設計ではない
- Phase gate が artifact ref の存在を主に見ており、path / digest / schema digest / 実ファイル存在まで検査していない
- docs と実装の Phase Gate 条件にズレが残りやすい
- live smoke が未実行で、外部 API の現時点 shape は artifact としてまだ固定されていない

## Confirmed Current State

実装済み:

- gTrade REST snapshot と backend WS event stream の保存
- gTrade pricing WS v4 の mark price / index price 分離
- gTrade flat array fallback の `mark_index_inferred_equal=true` 明示
- Ostium Builder API raw artifact 保存
- Ostium legacy metadata REST raw artifact 保存
- Ostium Python SDK の秘密鍵なし read-only probe status 保存
- Phase gate で read-only collector artifact 不足を blocker 化

未完了:

- live smoke artifact の取得
- SDK probe の payload quality validation
- top-level fetch failure の raw error summary 化
- Phase gate の artifact ref deep validation
- live artifact 由来の regression fixture 追加

## Findings

### F1. SDK read-only probe が空レスポンスでも pass し得る

Risk:

`ostium-python-sdk` の `get_latest_prices()` または `get_formatted_pairs_details()` が空配列、空 dict、期待 field 欠落 payload を返しても、例外でなければ `read_only_probe_passed` になり得る。

Why it matters:

SDK が import できるだけ、または空応答を返すだけでは「read-only 実データ取得に成功」とは言えない。

Better acceptance:

- `observed_count > 0`
- 少なくとも 1 row が `from` / `to` と price field を持つ
- price field は `mid`、`bid` / `ask`、または SDK pair detail の price 相当 field のいずれか

### F2. Ostium top-level fetch failure が summary を残さず例外終了し得る

Risk:

Builder API `GET /v1/prices` または legacy `latest-prices` が失敗すると、collector が summary を書く前に落ちる可能性がある。

Why it matters:

失敗時ほど raw error artifact と `constraint_status=failed` summary が必要。summary が無いと Phase gate 側では「missing artifact」になり、根因が追いにくい。

Better acceptance:

- top-level fetch failure も raw error artifact として保存する
- summary を必ず `data/ops/ostium_constraints_<run_id>.json` に書く
- failures に `builder_prices_fetch_failed` または `legacy_latest_prices_fetch_failed` を入れる

### F3. Phase gate の artifact ref 検査が浅い

Risk:

Phase gate は `builder_prices_artifact` や `legacy_latest_prices_artifact` の field 存在を見ているが、次を必ず検査しているわけではない。

- `path`
- `body_digest`
- `schema_digest`
- path が実在すること
- path 内の digest と summary の digest が一致すること

Why it matters:

壊れた summary、古い summary、手書き fixture でも gate を通す余地がある。

Better acceptance:

- artifact ref validator を共通化する
- summary 内 ref と実ファイル envelope を照合する
- digest mismatch は Phase 2 blocker にする

### F4. Asset-level trading-hours の二重防御が弱い

Risk:

Phase gate は asset row に `trading_hours_artifact` があることを主に見ている。`trading_hours_observed=true` や fetch error でないことは gate 側で十分に再確認していない。

Why it matters:

constraint summary の作成ロジックが将来壊れた場合、gate 側の二重防御が弱い。

Better acceptance:

- asset row ごとに `trading_hours_observed is True` を gate で確認する
- raw artifact が fetch error envelope の場合は blocker にする

### F5. Docs と実装の Phase Gate 条件がズレやすい

Risk:

運用 docs に書かれた Phase Gate 条件が実装より少ない、または古くなると、人間が誤って Phase 2 に進める可能性がある。

Better acceptance:

- `docs/LIVE_EVIDENCE_READ_ONLY_COLLECTORS.md` の Phase Gate 条件を code truth と同期する
- risk review doc への参照を runbook に残す
- future hardening が未実装であることを明示する

### F6. 古い fixture が new contract を十分に検査していない

Risk:

一部テスト fixture は古い Ostium summary shape のまま残っている可能性がある。

Why it matters:

新 contract を破っても、古い fixture が通ってしまうと regression detection が弱い。

Better acceptance:

- Phase gate 系 fixture は new contract shape に更新する
- quote evidence refs 系 fixture は「参照添付だけの test」と明記し、constraint correctness と混同しない
- live smoke artifact から regression fixture を追加する

## Better Backlog

優先順:

1. SDK probe pass 条件を `observed_count > 0` かつ expected fields ありに上げる
2. top-level fetch 失敗時も raw error artifact と summary を必ず書く
3. Phase gate で artifact ref の `path`、digest、schema digest、実ファイル存在を検査する
4. asset-level gate で `trading_hours_observed=true` と fetch error 非該当を確認する
5. old fixtures を new artifact contract に更新する
6. live smoke artifact から regression fixture を追加する

## Acceptance For Future Fix

将来この backlog を実装する場合の合格条件:

- `uv run sis ostium-constraint-artifact --run-id manual_smoke` が成功時も失敗時も summary を残す
- SDK empty payload は `read_only_probe_passed` にならない
- top-level Builder API failure は `builder_prices_fetch_failed` として summary に残る
- Phase gate は artifact ref の path / digest / schema digest / file existence を検査する
- Phase gate は asset-level `trading_hours_observed` を検査する
- docs の Phase Gate 条件が implementation と一致している
- targeted tests と full pytest が通る

## Do Not Do

- 本番発注しない
- private key を要求しない
- allowance を付与しない
- contract write しない
- live smoke 失敗を upstream workaround で隠さない
- `phase2_entry_allowed` を log だけで判断しない
- risk review doc の pending item を実装済みとして扱わない
