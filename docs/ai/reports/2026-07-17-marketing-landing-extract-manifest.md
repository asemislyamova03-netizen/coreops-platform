# Marketing landing extract manifest

**Date:** 2026-07-17 (session 2026-07-18 local)  
**Source (READ/COPY ONLY):** dirty root `C:/Users/АДМИН/OneDrive/Documents/Flexity`  
- branch `feature/marketing-m8-publish-bridge` @ `9658a82`  
- dirty `git diff --cached` staged count: **0** (verified before/after; root not modified)

**Target worktree:** `C:/Users/АДМИН/OneDrive/Documents/Flexity/.worktrees/marketing-landing-reconcile`  
**Branch:** `feature/marketing-landing-reconcile` FROM `origin/main` @ `abbde60`

**No push / no merge / no deploy.**

---

## Task classification

1. **Project:** Flexity  
2. **Category:** documentation_only + content extract (static marketing landing)  
3. **Risk:** low  
4. **Intended scope:** `landing/www/**` remainder + related article/handoff/report  
5. **Forbidden:** M8-D publish ops, credentials, `.ai_local`/`.worktrees`/dumps, wholesale shared files, C1c/Booking/E1/M8 core duplicates  
6. **Plan type:** documentation-only change + static content copy onto clean branch

---

## Inventory: dirty vs `origin/main`

| Bucket | Dirty only (not on main) | Content differs vs main | Decision |
|--------|--------------------------|-------------------------|----------|
| `landing/www` pages/assets | privacy, terms, `insights/ai-vs-kod.html`, 3 logo PNGs, 6 TikTok site-verification `.txt` | `insights/index.html` | **TRANSFER** |
| `landing/content/articles` | `2026-07-03-ai-vs-kod.md` | (other articles missing on dirty disk / pack diffs elsewhere) | **TRANSFER** article only |
| `landing/content/content-packs` | `2026-06-23-process-before-ai/*` | stoimost / 1s-erp pack files | **EXCLUDE** (publish/content-ops, not landing pages) |
| docs | `docs/ai/handoffs/2026-07-02-landing-live-deploy-handoff.md` | — | **TRANSFER** (landing deploy handoff) |
| M8-D publish ops | already on `feature/marketing-publish-ops-m8d-prep` | — | **FORBIDDEN / skip** |

`origin/main` already had most of `landing/www` (41 files) and content-packs/articles (168 landing paths). Remaining untransferred landing surface was small.

---

## Frontend target

**Static landing** under `landing/www/` (HTML + `assets/site.css` + Bootstrap CDN).  
**Not** the npm Platform Console (`platform-console/`). No `landing/package.json`. No lockfile changes.

Deploy path (docs): `/var/www/flexity-landing/` ← `landing/www/`.

---

## Files transferred (copy from dirty → worktree)

### Included

| Path | Why |
|------|-----|
| `landing/www/insights/ai-vs-kod.html` | New insight page |
| `landing/www/insights/index.html` | Lists ai-vs-kod; CTA → `/demo/` |
| `landing/www/privacy/index.html` | Legal page (Publisher / TikTok OAuth privacy) |
| `landing/www/terms/index.html` | Legal page (Publisher terms) |
| `landing/www/assets/flexity-logo-1024-from-svg.png` | Landing asset |
| `landing/www/assets/flexity-logo-from-favicon-1024.png` | Landing asset |
| `landing/www/assets/flexity-logo-from-favicon-512.png` | Landing asset |
| `landing/www/tiktok*.txt` (6 files) | Public TikTok *site verification* files (not API credentials) |
| `landing/content/articles/2026-07-03-ai-vs-kod.md` | Source article for insight |
| `docs/ai/handoffs/2026-07-02-landing-live-deploy-handoff.md` | Landing-only deploy handoff |
| `docs/ai/reports/2026-07-17-marketing-landing-extract-manifest.md` | This manifest |
| `landing/README.md` | Minimal route list update for privacy/terms/ai-vs-kod |

### Explicitly excluded

- `landing/content/content-packs/2026-06-23-process-before-ai/**` — content/publish pack
- Dirty content-pack diffs (`stoimost-*`, `1s-erp-*`, etc.) — not landing pages
- M8-D scripts/docs (already extracted on `feature/marketing-publish-ops-m8d-prep`)
- `backend/**`, `platform-console/**`, booking/C1c/E1, credentials (`.local-dev-credentials`, `.env`), `.ai_local/**`

---

## Checks

| Check | Result |
|-------|--------|
| Static presence + HTML doctype for key pages | **PASS** |
| npm build / typecheck / lint | **N/A** (static site; no landing package; did not touch lockfiles) |
| Hardcoded secrets / API keys | **None found** in transferred HTML |
| Production URLs | Canonical/OG use `https://www.flexity.asia/...`; console login `https://flexity.asia/console/login` (existing site pattern) |
| Responsive | viewport meta present on transferred HTML pages |
| CTA / positioning | Insights index + ai-vs-kod primary CTA → `/demo/` («Запросить демо»); secondary login → console; privacy/terms are legal-only (no demo CTA) |
| Dirty root staged | **0** |
| Push | **not done** |

---

## Residual valuable dirty-root buckets (after this extract)

Still left on dirty root (valuable, **not** in this branch):

1. **Backend / consulting import / C1c** — `backend/app/modules/**`, import dry-run, staging scripts, related tests  
2. **Booking MVP domain** — `backend/app/modules/booking/**` + booking tests/docs (may already have a separate worktree)  
3. **Platform Console WIP** — `platform-console/src/**`  
4. **Process overlay / E1 docs & code** — docs + any remaining backend overlays  
5. **Marketing M8 core / cabinet / publish bridge** — remaining marketing module code not in landing www (M8-D already branched)  
6. **Content-ops packs diffs** — e.g. `process-before-ai`, dirty vs main pack file diffs  
7. **Large docs/ai backlog** — plans, handoffs, research, CR notes (~200+ under `docs/ai`)  
8. **Industry/reference docs** — clinic/trailers/booking audit plans at `docs/FLEXITY_*`  
9. **Local-only / forbidden** — `.ai_local`, credentials, dumps, worktrees themselves  

---

## Commit intent

Local-only commit message:

`feat(marketing): reconcile remaining landing content onto main`
