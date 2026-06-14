<!--
作成日: 2026-06-13_20:51 JST
更新日: 2026-06-14_11:00 JST
-->

# vectorbt License Decision Memo

## 結論

`vectorbt` は repo optional extra として正式採用する。`pyproject.toml` / `uv.lock` へ `vectorbt==1.0.0` を追加済みである。

公式 license が `Apache 2.0 with Commons Clause` であり、通常の Apache-2.0 単体ではない点は変わらない。2026-06-14_11:00 JST に owner から「懸念事項はすべて解決しているため正式採用する」と明示されたため、この repo では owner approval 済みとして optional extra 採用に進める。

技術面では `vectorbt 1.0.0` は Python `>=3.10` と Python 3.13 classifier を持ち、一時 `uv --with vectorbt` import と `strategy-backtest-external-run` smoke は成立している。したがって blocker は主に license / adoption policy であり、adapter 技術検証ではない。

## 決定

| Item | Decision |
|---|---|
| repo dependency | 通常 dependency にはしない |
| optional extra | `vectorbt = ["vectorbt==1.0.0"]` を追加 |
| lockfile | `uv.lock` に `vectorbt==1.0.0` と transitive dependency を追加 |
| temporary smoke | `uv run --extra vectorbt ...` に置き換え |
| `vectorbt[full]` / `vectorbt[rust]` / `vectorbt[all]` | 採用しない |
| production / live path | 接続しない |
| 採用根拠 | 2026-06-14_11:00 JST の owner approval |

## 確認した一次情報

### Official license

公式 license page と GitHub license file は、`vectorbt` の license を `Apache 2.0 with Commons Clause` としている。Commons Clause は、元の license に対して `Sell` に関する追加制限を載せる条件である。

参照:

- https://vectorbt.dev/terms/license/
- https://github.com/polakowo/vectorbt/blob/master/LICENSE.md

### GitHub repository metadata

GitHub API で確認した repository metadata:

- default branch: `master`
- repository license key: `other`
- repository license SPDX: `NOASSERTION`
- license file path: `LICENSE.md`
- license file URL: `https://github.com/polakowo/vectorbt/blob/master/LICENSE.md`

このため、`Apache-2.0` として自動分類できる dependency ではなく、repo 側では制限付き license として扱う。

### PyPI package metadata

PyPI JSON と installed metadata で確認した `vectorbt 1.0.0` metadata:

- version: `1.0.0`
- `Requires-Python`: `>=3.10`
- Python 3.13 classifier: あり
- `License`: `None`
- `License-Expression`: `None`
- extras: `rust`, `full-no-talib`, `full`, `test`, `test-rust`, `docs`, `all`

PyPI page は Python 3.13 対応を示す一方、machine-readable license metadata は空である。license 判断は PyPI metadata だけでは完結せず、公式 license page / GitHub license file を優先する。

参照:

- https://pypi.org/project/vectorbt/
- https://pypi.org/pypi/vectorbt/json

## Repo への適用判断

この repo は backtest-first / venue-neutral の研究・paper operation workspace であり、将来的に report / operator workflow / hosted artifact / consulting-like handoff へ広がる可能性がある。Commons Clause の `Sell` 制限は、その将来利用と衝突する余地がある。

したがって、現時点の repo policy としては次を採る。

- `vectorbt` は `vectorbt` optional extra として採用する。
- `src/sis/backtest/vectorbt_adapter.py` は残してよい。
- `strategy-backtest-external-run` は `uv run --extra vectorbt` 環境で `vectorbt.Portfolio.from_signals` を実行してよい。
- `strategy-backtest-compare` は `vectorbt` result を optional external result として取り込んでよい。
- ただし、通常 dependency / dev dependency / 標準 engine にはしない。

## 採用後も変更してはいけないこと

次を行わない。

- `vectorbt[full]`, `vectorbt[rust]`, `vectorbt[all]` を採用する。
- `vectorbt` を標準 engine にする。
- `strategy_authoring_native` の完成線を `vectorbt` 前提へ変える。
- `vectorbt` result から alpha / paper / live readiness を主張する。
- live order、wallet、signing、exchange write に接続する。

## 採用時の条件

`vectorbt` 採用では、次を満たす。

1. owner approval を docs か issue / decision record に残す。
2. Commons Clause が repo の利用形態に許容される理由を明記する。
3. `vectorbt` base extra だけを対象にし、`full`, `rust`, `all` は別 review にする。
4. `uv sync --dev --extra vectorbt --locked` が安定することを確認する。
5. transitive dependency の license と optional native build risk を確認する。
6. `strategy_backtest_external_result.v1` の source path / source hash / runner mode / dependency source を維持する。
7. `strategy-backtest-pack` の標準完成線を `complete_without_locked_external_dependency` から不用意に変えない。
8. 全 artifact で `permits_live_order=false`, `wallet_used=false`, `exchange_write_used=false` を維持する。

## 現時点で使えるコマンド

optional extra 環境で `vectorbt` を使う場合:

```bash
uv run --extra vectorbt python -c 'import vectorbt; print(vectorbt.__version__)'
uv run --extra vectorbt sis strategy-backtest-external-run
uv run --extra vectorbt sis strategy-backtest-framework-run --framework vectorbt
uv run sis strategy-backtest-compare
```

通常 repo の標準 pack は引き続き native-primary として実行する。

```bash
uv run sis strategy-backtest-pack
uv run sis strategy-backtest-pack-validate
```

## 抜け・漏れ・誤謬リスク

- この memo は engineering adoption decision であり、法務助言ではない。
- package metadata は変わり得る。採用を再検討する時点で PyPI / GitHub / 公式 docs を再確認する。
- ここでは transitive dependency license を全件棚卸ししていない。採用時は `uv tree` と wheel metadata の確認が必要である。
- `vectorbt 1.0.0` は 2026-04-22 release であり、0.x 系の過去 metadata と差がある。古い blog / docs の license 記述を正本にしない。
- GitHub / PyPI metadata と公式 license text の表示粒度が違うため、機械的な SPDX 判定だけで採用可とは扱わない。
