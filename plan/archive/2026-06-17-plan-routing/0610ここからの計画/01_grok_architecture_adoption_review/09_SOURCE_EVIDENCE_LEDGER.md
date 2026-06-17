<!--
作成日: 2026-06-10_11:31 JST
更新日: 2026-06-10_11:31 JST
-->

# Source Evidence Ledger

This ledger records the concrete evidence used by the adoption review. It
prevents the review from relying on the Grok transcript or on a clean
architecture narrative.

## Local Evidence

Commands run:

```bash
codex --version
uv run sis --help
find src/sis -maxdepth 3 -type d | sort
find . -path './.git' -prune -o -path './.venv' -prune -o -path './data' -prune -o -path './logs' -prune -o -name '*.ipynb' -print
git diff -- src schemas pyproject.toml uv.lock tests
uv run python scripts/check_current_docs.py
./scripts/check
```

Observed facts:

- local Codex CLI reported `codex-cli 0.135.0`
- package root is `src/sis`
- `pyproject.toml` builds `packages = ["src/sis"]`
- no `.ipynb` files were found in the current checkout
- `git diff -- src schemas pyproject.toml uv.lock tests` had no output after
  the review-package change
- `uv run python scripts/check_current_docs.py` passed with 102 current docs
- `./scripts/check` passed with Python 3.13.7 and 955 pytest tests

## Repo Source Files

Use these local files before accepting architecture claims:

- `README.md`
- `docs/CURRENT_STATE.md`
- `docs/CODE_STATUS.md`
- `docs/ARCHITECTURE_AND_PHASES.md`
- `docs/research/ndx/README.md`
- `docs/backtest/README.md`
- `docs/strategy_research_lab/README.md`
- `pyproject.toml`
- `src/sis/cli.py`
- `src/sis/research/strategy_lab/`
- `src/sis/research/ndx/`
- `src/sis/backtest/`

## External Primary Sources Checked

- OpenAI Codex manual local cache:
  - `/tmp/openai-docs-cache/codex-manual.md`
  - `https://developers.openai.com/codex/codex-manual.md`
  - relevant topics: prompting, plan-first guidance, AGENTS.md, model selection
- Python Packaging User Guide:
  - `https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/`
- Numerai docs:
  - `https://docs.numer.ai/numerai-tournament/scoring`
  - `https://docs.numer.ai/numerai-tournament/submissions`
- Backtest overfitting and multiple-testing references:
  - `https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253`
  - `https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551`
  - `https://www.nber.org/papers/w20592`
- VectorBT docs:
  - `https://vectorbt.dev/`

## Evidence Limits

- The external sources support narrow ideas only: plan-first prompting,
  `src` layout concept, Numerai scoring vocabulary, backtest overfitting risk,
  and VectorBT's general purpose.
- They do not authorize adding VectorBT, renaming the package, changing schemas,
  or creating paper/live execution paths.
- The OpenAI Codex manual supports Codex workflow guidance. It does not make the
  Grok transcript a repo-specific architecture source.
