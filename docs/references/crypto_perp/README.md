<!--
作成日: 2026-06-22_14:47 JST
更新日: 2026-06-22_14:47 JST
-->

# Crypto Perp References

この directory は、Crypto Perp Truth-Cycle MVP の実装時に確認した外部OSS / competition protocol reference を置く場所です。

## 位置づけ

正本ではありません。正本は次です。

- `src/sis/crypto_perp/`
- `src/sis/commands/crypto_perp*.py`
- `schemas/crypto_perp_*.schema.json`
- `tests/crypto_perp/`
- `uv run sis --help`
- [../../runbooks/CRYPTO_PERP_TRUTH_CYCLE_RUNBOOK.md](../../runbooks/CRYPTO_PERP_TRUTH_CYCLE_RUNBOOK.md)

外部ページは更新される可能性があります。実装判断で使う場合は、公式 docs と現在のコードを再確認します。

## Documents

- [COMPETITION_PROTOCOL.md](COMPETITION_PROTOCOL.md): hypothesis tournament の比較原則。
- [OSS_ADOPTION_DECISIONS.md](OSS_ADOPTION_DECISIONS.md): Tardis / pybotters / Freqtrade / Hummingbot などの採否境界。
- [HUMMINGBOT_BITGET_CONNECTOR_NOTES.md](HUMMINGBOT_BITGET_CONNECTOR_NOTES.md): Hummingbot Bitget connector の参考メモ。

これらは validation accelerator / design reference です。live execution、wallet、signing、exchange write、production Bitget readiness を許可しません。
