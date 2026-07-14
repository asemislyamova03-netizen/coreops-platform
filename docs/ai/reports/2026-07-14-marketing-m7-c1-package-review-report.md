# Marketing M7-C1 — Package Review (pre-commit)

**Date:** 2026-07-14  
**Mode:** Review + staging plan only  
**Branch:** `feature/marketing-m6-package`  
**HEAD:** `4c6dd22` (`marketing: show topic context in pack detail`)  
**HQ:** no commit / push / deploy / stage yet

---

## Verdict

**READY TO STAGE (allow-list only)** after HQ approval to stage+commit.

Local M7-C1 backend is GREEN. Scope matches Preflight v2 backend-only. Dirty tree is large (~343 paths) — **must not** use `git add .`.

---

## 1. Dirty tree summary

| Item | Value |
|------|--------|
| Branch | `feature/marketing-m6-package` ↔ `origin/feature/marketing-m6-package` |
| Staged | **empty** ✅ |
| Dirty paths (approx) | ~343 (CRM, inbound, landing, publish, booking, `.ai_local`, …) |
| Alembic dirty | none |
| Frontend marketing Preflight tab | not changed |

Unrelated WIP must stay unstaged.

---

## 2. M7-C1 files confirmed

### Backend

| Path | Status | Role |
|------|--------|------|
| `backend/app/modules/marketing/service/preflight_rules.py` | **NEW** | Rule helpers |
| `backend/app/modules/marketing/service/approval.py` | modified | Wire v2 + report persist |
| `backend/app/modules/marketing/schemas.py` | modified (+11) | PreflightResponse v2 + pack detail `preflight_report_json` |
| `backend/app/modules/marketing/service/packs.py` | modified (+1) | Map `preflight_report_json` |
| `backend/tests/test_marketing_preflight_approval.py` | modified | Happy-path + M7-C1 cases |

### Docs

| Path | Status | Include? |
|------|--------|----------|
| `docs/ai/reports/2026-07-14-marketing-m7-c1-backend-preflight-report.md` | untracked | **yes** |
| `docs/ai/plans/2026-07-14-marketing-m7-c-implementation-plan.md` | untracked | **yes** (checklist + plan) |
| `docs/ai/plans/2026-07-14-marketing-m7-implementation-plan.md` | modified (+3) | **yes** (M7-C1 status) |
| `docs/ai/plans/2026-07-14-marketing-m7-c-preflight-v2-plan.md` | untracked | **yes** — product plan used for C1 |
| `docs/ai/reports/2026-07-14-marketing-m7-c-planning-report.md` | untracked | **yes** — planning report for C1 |
| `docs/ai/reports/2026-07-14-marketing-m7-c1-package-review-report.md` | this file | **yes** when staging |

### Extra / not in code step

No unexpected backend files.  
`platform-console/**` Preflight UI — **excluded** (M7-C2).

---

## 3. Scope review

| Gate | Result |
|------|--------|
| Frontend M7-C2 / Preflight tab | **PASS** — not in allow-list |
| Alembic / migration | **PASS** |
| env / secrets | **PASS** |
| production scripts / dist / node_modules | **PASS** |
| public inbound / landing | dirty elsewhere — **excluded** |
| CRM / booking / currency | dirty elsewhere — **excluded** |
| publish / export / Margosya | dirty scripts elsewhere — **excluded** from this package |

**Scope violations:** none in M7-C1 allow-list.

---

## 4. Backend behavior review

### Blockers (present)

- `topic_missing` (no linked topic)  
- `topic_not_approved`  
- `no_publishable_text`  
- `context_triple_missing` (audience + pain + CTA all empty)  
- `all_texts_too_short` (all non-empty social texts &lt; 20)  
- M6 preserved: `pack_metadata_incomplete`, `channel_text_missing`, `media_invalid_mime`

### Warnings (present)

- `insight_missing`, `source_ref_missing`  
- `cta_missing_for_funnel` for diagnosis / consultation / product_education / objection_handling  
- `media_missing`, `channel_text_short` (&lt; 40)  
- `notes_missing`, `topic_planned_date_missing`  
- M6 preserved: `insights_text_empty`, `telegram_text_too_long`, `media_not_1080`

### Approval semantics

- blockers → `preflight_status=failed` / pack `preflight_failed`  
- warnings only → `preflight_status=passed` / `ready_for_approval` → approve allowed  
- report `version=m7-c1`; keeps `errors`/`warnings`/`checks` + `blockers`/`checklist` aliases  
- pack detail now exposes `preflight_report_json` (additive)  
- tenant scoping unchanged (same repo getters)

---

## 5. Validation re-run (this review)

```bash
python -m pytest backend/tests/test_marketing_preflight_approval.py \
  backend/tests/test_marketing_packs.py \
  backend/tests/test_marketing_topics.py -q
```

**Result:** `52 passed` (~73–87s). Known SQLite FK DROP warnings only.

**Frontend/build:** not run — no FE files in M7-C1 package.

---

## 6. Proposed staging allow-list (do not stage until HQ asks)

```text
backend/app/modules/marketing/service/preflight_rules.py
backend/app/modules/marketing/service/approval.py
backend/app/modules/marketing/schemas.py
backend/app/modules/marketing/service/packs.py
backend/tests/test_marketing_preflight_approval.py
docs/ai/reports/2026-07-14-marketing-m7-c1-backend-preflight-report.md
docs/ai/reports/2026-07-14-marketing-m7-c1-package-review-report.md
docs/ai/plans/2026-07-14-marketing-m7-c-implementation-plan.md
docs/ai/plans/2026-07-14-marketing-m7-c-preflight-v2-plan.md
docs/ai/reports/2026-07-14-marketing-m7-c-planning-report.md
docs/ai/plans/2026-07-14-marketing-m7-implementation-plan.md
```

**Count:** 11 paths.

**Proposed commit message:**

```text
marketing: add preflight v2 backend rules
```

**Future staging commands (only after HQ asks):**

```bash
git add -- \
  backend/app/modules/marketing/service/preflight_rules.py \
  backend/app/modules/marketing/service/approval.py \
  backend/app/modules/marketing/schemas.py \
  backend/app/modules/marketing/service/packs.py \
  backend/tests/test_marketing_preflight_approval.py \
  docs/ai/reports/2026-07-14-marketing-m7-c1-backend-preflight-report.md \
  docs/ai/reports/2026-07-14-marketing-m7-c1-package-review-report.md \
  docs/ai/plans/2026-07-14-marketing-m7-c-implementation-plan.md \
  docs/ai/plans/2026-07-14-marketing-m7-c-preflight-v2-plan.md \
  docs/ai/reports/2026-07-14-marketing-m7-c-planning-report.md \
  docs/ai/plans/2026-07-14-marketing-m7-implementation-plan.md

git diff --cached --name-only
# must be exactly the 11 paths above
```

---

## 7. Explicitly excluded

- All CRM / parties / workflows / public inbound / landing / booking  
- `scripts/content/publish_*`  
- `platform-console/**` (M7-C2)  
- alembic, env, credentials, dist  
- M7-B commit report leftovers / unrelated marketing docs not required for C1

---

## 8. Risks

1. Dirty-tree contamination if broad `git add`.  
2. Deploy note later: packs without topic will fail preflight (intentional).  
3. Local HEAD is still M7-B commit `4c6dd22` on feature branch; C1 will be next local commit (main already has M7-B merge).

---

## 9. Recommendation

**Approve allow-list stage + commit** when HQ requests.  
No push/deploy in the same step without separate approval.

**Next safe step:** HQ says «stage + commit M7-C1 allow-list».

---

## Finish checklist

| Item | Value |
|------|--------|
| Code changes this review | none |
| Files added | this package-review report only |
| Tests | 52 passed |
| Migration | none |
| Publish/Margosya | none in scope |
| Handoff | optional after commit |
