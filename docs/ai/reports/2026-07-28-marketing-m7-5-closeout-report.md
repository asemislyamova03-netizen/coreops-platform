# Report: Marketing M7.5 Formal Closeout

**Date:** 2026-07-28  
**Category:** `documentation_only`  
**Baseline / `origin/main`:** `438e39c` (`fix(marketing): align m7.5 timestamp defaults`)  
**Final verdict:** **M7.5 COMPLETE / STAGE DOGFOOD GREEN**  
**Status:** **CLOSED**

HQ decision: M7.5 is complete after implementation A–D, timestamp fix, stage deploy, API dogfood, and Browser A–H. This document is the **canonical** formal closeout. Code, runtime, and production were not changed by this documentation step.

---

## Task Classification

| Field | Value |
|---|---|
| Project | Flexity |
| Category | `documentation_only` |
| Risk | low |
| Intended scope | this report + minimal status pointers in existing M7.5 docs |
| Forbidden | product code, migrations, tests, deploy, prod, dirty M8 worktree, M8-D3 |

---

## Code and deployment

| Layer | Value |
|---|---|
| `origin/main` | `438e39c` |
| Stage backend | `438e39c` |
| Stage DB (alembic) | `0029_mkt_timestamp_defaults` |
| Stage hostname | `stage.flexity.kz` |
| Stage console alias (dogfood) | `dist-298bac4/` (UI from M7.5-D; timestamp hotfix was backend-only) |
| Production backend | `c90e482` |
| Production DB (alembic) | `0026_mkt_publish_destinations` |
| Production M7.5 deploy | **not performed** |

---

## Functional chain (validated)

```text
Guide → Rubrics → Prompt → Import → Plan → Approve → Topic → Take → Pack
```

Publish Bridge / live publish / M8-D3 were **not** part of M7.5 closeout.

---

## Evidence summary

### Implementation A–D + timestamp

| Slice | Role | Key SHA / note |
|---|---|---|
| A | Guide + Rubrics | on path to `298bac4` / merged main lineage |
| B | Content plans | on path to `298bac4` |
| C | Prompt export + import | on path to `298bac4` |
| D | Dogfood UI + create-topic | `298bac4` |
| Timestamp hotfix | migration `0029` + rubric IntegrityError narrowing | squash on `origin/main`: **`438e39c`** |

Related on-main implementation reports (non-canonical vs this closeout):

- `docs/ai/reports/2026-07-27-marketing-m7-5-a-guide-rubrics-implementation-report.md`
- `docs/ai/reports/2026-07-27-marketing-m7-5-b-content-plans-implementation-report.md`
- `docs/ai/reports/2026-07-27-marketing-m7-5-c-plan-import-implementation-report.md`
- `docs/ai/reports/2026-07-27-marketing-m7-5-d-dogfood-ui-implementation-report.md`
- `docs/ai/reports/2026-07-28-m7-5-timestamp-defaults-implementation-report.md`
- Plan: `docs/ai/plans/2026-07-27-marketing-m7-5-upstream-guide-rubrics-content-plan-implementation-plan.md`

### API dogfood (stage) — GREEN

| Entity | ID |
|---|---|
| Plan | `61123b33-786c-419b-af65-fe97c32ae42b` |
| Topic | `af4ebd80-83ea-4f5c-a88d-b7d732d945e1` |
| Pack | `188c2cf3-e7d7-4135-906a-d6b5fd9896e9` |
| Marker | `m75-closeout-1785186592` |
| Tenant | `stage-synth-t-g3a03` |

Negatives (unknown rubric, preview no writes, create-topic before approve, tenant isolation) passed. Publish not called. Production unchanged during dogfood.

### Browser A–H (stage) — GREEN

| Field | Value |
|---|---|
| Marker | `browser-m75-20260728-1785228329271` |
| Tenant | `stage-synth-t-g3a03` |
| Plan | `ea4a94c7-055a-44c4-bf26-1cbbd6e2b45a` (`approved`) |
| Topic | `9002ec03-e79c-4c63-9e0e-114b8233c4b1` (`approved`, `source=content_plan`) |
| Pack | `a3019c37-42e7-4b43-a9ab-bada9cfe19e2` (`draft`) |
| Final URL | stage pack detail under `stage.flexity.kz` / workspace marketing packs |
| Publish | **not invoked** |
| Steps A–H | all **PASS** |
| Critical console errors | none |

Local evidence path (ops machine, not in git):  
`%LOCALAPPDATA%\Temp\m75_browser_ah\evidence\` (`evidence.json`, `verdict.txt`, screenshots A–H).

---

## Access clarification

- `asem-stage` and `asem-prod` are **nginx Basic Auth users**, not environments, tenants, or cabinets.
- Stage and production are **two isolated runtimes** on host `cloud-001` (stage `:8015` / `coreops_stage` vs prod `:8005` / `coreops`).
- Stage Basic Auth was restored **stage-only**; **production was not modified**.
- Credential values and secret file contents are intentionally omitted from this closeout.

---

## Non-blocking noise

During Browser A–H navigation, one aborted request:

- `GET .../labels` → `net::ERR_ABORTED`
- No critical console errors
- Not registered as a product bug
- Does **not** block M7.5 closeout

---

## Explicit exclusions

- No production deploy of M7.5
- No publishing / live adapters
- No M8-D3
- No product code changes in this documentation closeout
- Dirty worktree `feature/marketing-m8-publish-bridge` @ `860d904` **untouched**

---

## Next-state boundary

| Item | State |
|---|---|
| M7.5 | **CLOSED** (stage dogfood GREEN) |
| Stage test objects (API + browser IDs above) | remain as **audit evidence** |
| Production promotion of M7.5 | requires **separate HQ decision** — not declared done |
| M8-D3 | remains **PAUSED** until HQ chooses the next stage |

Do **not** treat M7.5 as deployed to production.

---

## Validation notes (documentation closeout session)

- Temporary worktree from `origin/main` @ `438e39c` (0 commits ahead of baseline).
- No commit / push / merge / deploy in this session.
- Dirty M8 root worktree left unchanged.
