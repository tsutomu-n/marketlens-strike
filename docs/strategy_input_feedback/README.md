<!--
作成日: 2026-06-22_18:55 JST
更新日: 2026-06-22_20:24 JST
-->

# Strategy Input Feedback

## 結論

Strategy Input Feedback は、Runtime Observation と Learning Event を読み、Strategy Input Contract 更新候補と人間レビュー artifact を作る local/offline surface です。

これは自動反映ではありません。Strategy Input Contract を直接編集せず、`auto_applied=false` と `direct_contract_edit_allowed=false` を維持します。paper 実行、live 実行、wallet、signing、exchange write も許可しません。

backtest-only artifact は、この command の proposal 入力ではありません。`strategy-case-lite-update --artifact` で backtest result、backtest pack、review manifest を Case Lite / Case Index に入れることはできますが、それだけでは Strategy Input Feedback proposal は作れません。

## CLI

proposal を作る:

```bash
uv run sis strategy-input-feedback-proposal-build \
  --strategy-id ndx-breakout-001 \
  --runtime-observation data/runtime_observations/ndx-breakout-001/smoke-001/strategy_runtime_observation_manifest.json \
  --learning-event data/strategy_learning/ndx-breakout-001/learn-001.json \
  --source-contract data/strategy_inputs/ndx-breakout-inputs-001.json \
  --out data/strategy_input_feedback
```

`--runtime-observation` と `--learning-event` は複数指定できます。少なくとも一方が必要です。

`--source-contract` がない場合、proposal は `NEEDS_SOURCE_CONTRACT_CONTEXT` になります。これは更新候補の文脈が足りない review-only proposal であり、apply-ready ではありません。

`--source-contract` だけを渡しても proposal は作れません。現行CLIは次で止まります。

```text
status=fail
error=at least one --runtime-observation or --learning-event is required
```

つまり、Strategy Input Contract は proposal の文脈であり、proposal の発火源ではありません。発火源は Runtime Observation または Learning Event です。

review を作る:

```bash
uv run sis strategy-input-feedback-proposal-review \
  --proposal data/strategy_input_feedback/ndx-breakout-001/<proposal-id>.json \
  --decision APPROVE_FOR_MANUAL_CONTRACT_UPDATE \
  --reviewer operator-a \
  --rationale "Manual contract update input only." \
  --approved-change-id runtime-001
```

`APPROVE_FOR_MANUAL_CONTRACT_UPDATE` は手動更新の入力として承認するだけです。ファイル patch や自動適用は行いません。`NEEDS_FIX` は `--required-action` が必要です。`REJECT` と `HOLD` は `--approved-change-id` を受け付けません。

## Artifacts

- `strategy_input_contract_update_proposal.v1`
- `strategy_input_contract_update_review.v1`

proposal は source artifact の path、sha256、schema_version、artifact_kind を保持します。source artifact は既存 Pydantic model で検証します。ただし boundary true が混入した source は ready proposal ではなく `BLOCKED_BOUNDARY_VIOLATION` として止めます。

`--source-contract` は `StrategyInputContract` model validation を行います。contract 内の各 source file の存在、declared sha256、column、timestamp 検査は既存 `strategy-input-contract-validate` の責務です。この command 内では再実装しません。

## 境界

- Strategy Input Contract を直接編集しない。
- patch file を生成しない。
- automatic apply をしない。
- paper / live execution permission ではない。
- wallet、signing、exchange write を使わない。
- source contract validation artifact を proposal に接続する flow は別計画。
- backtest-only Case Lite / Case Index は Input Feedback proposal の入力ではない。

## 検証

```bash
uv run pytest tests/strategy_input_feedback
uv run sis strategy-input-feedback-proposal-build --help
uv run sis strategy-input-feedback-proposal-review --help
uv run python scripts/check_current_docs.py
```
