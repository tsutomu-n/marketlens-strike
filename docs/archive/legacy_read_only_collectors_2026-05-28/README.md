# Legacy Read-Only Collectors Archive 2026-05-28

この directory は legacy `gtrade` / `ostium` read-only collector docs の archive です。current Trade[XYZ] operator path ではありません。

## Current Status

2026-05-28 時点の current path:

- Current venue: `trade_xyz`
- Current collector CLI: `uv run sis collect-trade-xyz-quotes`
- Current gate: `uv run sis phase-gate-review`
- Current docs:
  - `docs/CURRENT_STATE.md`
  - `docs/CODE_STATUS.md`
  - `docs/OPERATIONS_RUNBOOK.md`
  - `docs/FAILURE_MODE_RESPONSIBILITY_MAP_2026-05-28.md`
  - `docs/TRADE_XYZ_IMPLEMENTATION_STATUS_AUDIT_2026-05-28.md`
  - `docs/DOCUMENT_AUDIT_2026-05-28.md`

Do not use commands in this archive as current operator commands unless the legacy archive is intentionally restored.

## Archived Docs

| file | archived role |
|---|---|
| `LIVE_EVIDENCE_READ_ONLY_COLLECTORS.md` | legacy gTrade/Ostium collector operations |
| `READ_ONLY_COLLECTOR_IMPLEMENTATION_PLAN.md` | legacy collector implementation plan |
| `READ_ONLY_COLLECTOR_RISK_REVIEW.md` | legacy collector risk review and hardening backlog |

## Current Boundary

This archive is useful for historical reasoning about old failure modes:

- gTrade backend / pricing sidecar evidence
- Ostium constraint artifact evidence
- old Phase 2 read-only collector blockers
- legacy artifact digest / manifest hardening ideas

It is not evidence that current Trade[XYZ] read-only, P2, paper, or live readiness is blocked.
