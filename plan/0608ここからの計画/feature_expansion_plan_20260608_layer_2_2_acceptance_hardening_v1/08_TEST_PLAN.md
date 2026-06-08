<!--
作成日: 2026-06-08_19:23 JST
更新日: 2026-06-08_19:23 JST
-->

# 08_TEST_PLAN

## 方針

外部APIなし、credentialsなし、fixtureベースで検証する。

## 重点テスト

### exit gate semantics

```text
- clean approve -> APPROVE_2_3 / second_review_required=false / freezeあり
- blocker -> REVISE_2_2 / freezeなし
- unresolved human decision -> REVISE_2_2 / freezeなし
- high unresolved -> REVISE_2_2 / freezeなし
- high resolved -> APPROVE_2_3可 / second_review_required=false / freezeあり
- reject_seed without confirmation -> REVISE_2_2
- reject_seed with causal/temporal confirmation -> REJECT_SEED / freezeなし
- pack_hash mismatch -> input error
- current artifact pack_hash mismatch -> input error
```

## 最小対象テスト

```bash
uv run pytest -q tests/research/test_layer22_exit_gate.py
uv run pytest -q tests/research/test_llm_review_import.py
uv run pytest -q tests/research/test_llm_review_schema.py
uv run pytest -q tests/research/test_research_layer22_review_commands.py
```

## full research test

```bash
uv run pytest -q tests/research
```

## full repo gate

```bash
uv run python scripts/check_current_docs.py
./scripts/check
```

## テストで禁止すること

```text
- external LLM API call
- network fixture
- credentials read
- yfinance/FRED/Alpaca/Bitget/Trade[XYZ] API call
- strategy_signals.parquet生成
- feature panel生成
```
