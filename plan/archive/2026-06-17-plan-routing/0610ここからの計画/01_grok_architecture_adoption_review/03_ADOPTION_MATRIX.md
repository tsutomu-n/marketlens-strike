<!--
作成日: 2026-06-10_11:21 JST
更新日: 2026-06-10_11:21 JST
-->

# Adoption Matrix

| Proposal | Decision | Repo-specific handling |
| --- | --- | --- |
| Have Codex inspect the repo before planning | adopt | Require code/docs/CLI inspection before architecture plans. |
| Use explicit goal, constraints, and done conditions | adopt | Keep using plan packages with acceptance and stop conditions. |
| Ask for risk and impact before major edits | adopt | Apply to schema, storage, execution, and venue-boundary work. |
| Use AGENTS.md for durable guidance | adopt | Keep repo-local AGENTS concise and stable. |
| Use `src` layout | adapt | Already implemented as `src/sis`; do not create `src/strat_tool`. |
| Split practical code and research code | adapt | Preserve existing `src/sis/research/*`, `src/sis/backtest/*`, and Strategy Lab boundaries. |
| Add `typing.Protocol` for strategies | adapt | Only add if a concrete implementation seam needs it; do not add an abstract strategy layer speculatively. |
| Create `strategy/active` and `strategy/archive` | reject for this repo slice | Current Strategy Lab flow uses artifacts and schemas, not active/archive directories. |
| Make VectorBT the main backtester | reject for this repo slice | Not a dependency and not current backtest contract. Requires separate dependency decision. |
| Move notebooks to `research/experiments` | reject for current checkout | No `.ipynb` files were found in the repo scan. |
| Define phase goals and completion states | adapt | Use repo-specific phases tied to current gates and artifacts, not generic refactor phases. |
| Keep implementation incremental | adopt | Prefer narrow, verifiable slices over broad package migration. |
| Apply Numerai-style validation concepts | adapt | Use era metrics, neutralization, feature exposure, and multiple-testing controls only where they map to current Strategy Lab or NDX gates. |

## Unknown Or Unaccepted Claims

- Grok transcript claims about Codex CLI version history are not accepted unless
  verified against official OpenAI Codex documentation or the local CLI.
- GPT-5.5 capability claims are not implementation requirements.
- Any claim that depends on unlisted dependencies, external services, or
  credentials remains out of scope.

