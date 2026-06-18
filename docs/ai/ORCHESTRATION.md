# Flexity AI Orchestration

## Purpose

This document defines how Cursor, Codex, MCP, Skills, and Subagents should work with Flexity and related projects.

The goal is to reduce manual coordination while preventing unsafe autonomous changes.

---

## Project map

### Flexity

Status:

    Main FastAPI multi-tenant ERP platform.
    New development.
    Industry templates/packages connect here.
    Kindergarten must be implemented here as tenant/template, not as a separate Flask project.

Allowed work:

- platform architecture;
- universal modules;
- industry templates;
- industry packages;
- tenant customization planning;
- controlled implementation after approved plan.

### Trailers

Status:

    Live client Flask project under Nginx.
    Legacy/reference project.
    Future industry_trailers package source.

Allowed work:

- read-only mapping;
- minimal hotfix after approval;
- documentation;
- migration map to Flexity.

Not allowed without explicit approval:

- broad rewrite;
- migrations;
- deploy;
- Nginx/systemd changes;
- destructive git commands.

### Consulting Flask

Status:

    Live Flask project under Nginx.
    Legacy/reference project.
    Future consulting_basic template source.

Allowed work:

- read-only mapping;
- minimal hotfix after approval;
- documentation;
- migration map to Flexity.

Not allowed:

- duplicate CRM/documents/payments outside Flexity when it belongs in core/universal modules;
- broad rewrite;
- deploy/migrations without approval.

### Clinic App Flask

Status:

    Live/reference Flask project.
    Future clinic_basic template source.

Allowed work:

- read-only mapping;
- minimal hotfix after approval;
- documentation;
- migration map to Flexity.

Not allowed:

- duplicate CRM/documents/payments outside Flexity when it belongs in core/universal modules;
- broad rewrite;
- deploy/migrations without approval;
- maintaining Clinic as a parallel long-term product line.

### Kindergarten

Status:

    New client.
    Must be connected inside Flexity as tenant/template.

Current approved future code direction after orchestration setup:

- edit only backend/app/modules/industry_templates/seed.py;
- improve kindergarten_basic document templates and fields;
- no migration;
- no frontend;
- no dependencies.

---

## Single product direction

Flexity is the **only target product**.

Clinic App Flask, Consulting Flask, Trailers Flask and Kindergarten are **reference systems and validation directions**.

They exist to:

- validate the universal Flexity model against real business processes;
- supply requirements for universal modules, industry templates and industry packages;
- support controlled live hotfixes where needed.

They must **not** become parallel CRM/ERP product lines.

### Reference project policy

- Read and map legacy/reference projects; do not copy Flask code directly.
- Extract entities, statuses, workflows, documents, finance rules and integrations as requirements.
- Implement in Flexity using existing universal modules first.
- Use `kindergarten_basic`, `consulting_basic`, `clinic_basic`, `trailers_basic` as **validation templates/packages** — not separate CRM systems.
- Tenant-specific branding, legal details, templates and workflow overrides belong to **tenant customization** (planned; requires explicit approval).

### Current W3 focus

**W3 Manager Operations** — universal manager workflow inside Flexity tenant workspace:

    client (party)
    -> work item
    -> activity / task
    -> stage transition
    -> document
    -> invoice / payment

W3 is **not** kindergarten-specific functionality.

Out of scope for W3 unless separately approved:

- child / group / attendance specifics;
- medical records and MedElement;
- VIN / production / warehouse depth;
- consulting-specific project accounting;
- tenant customization implementation.

---

## Architecture layers

    Flexity Core
    -> Universal modules
    -> Industry template / industry package
    -> Tenant customization

### Flexity Core

Core shared platform:

- tenants;
- auth;
- permissions;
- shared infrastructure;
- common API conventions;
- audit;
- billing/subscription foundation.

### Universal modules

Reusable modules across industries:

- CRM;
- documents;
- payments;
- tasks;
- files;
- notifications;
- comments;
- analytics;
- audit log.

### Industry template

Seed/config/default layer for a market segment.

Examples:

- kindergarten_basic;
- consulting_basic;
- clinic_basic;
- trailers_basic.

### Industry package

Deeper domain-specific logic.

Examples:

- industry_kindergarten;
- industry_trailers;
- industry_consulting;
- industry_clinic.

### Tenant customization

Client-specific layer above the industry layer.

Examples:

- logo;
- colors;
- legal details;
- client-specific document templates;
- custom fields;
- custom labels;
- workflow settings;
- notification settings;
- signature settings.

---

## Required task flow

Every task must follow this sequence:

1. Classify task.
2. Identify project.
3. Identify architecture layer.
4. Identify risk.
5. Identify files in scope.
6. Identify forbidden files.
7. Choose required skill:
   - research-brief;
   - implementation-plan;
   - change-request-triage;
   - live-hotfix-plan;
   - migration-map;
   - handoff;
   - qa-verification.
8. Create plan.
9. Get approval.
10. Implement only approved scope.
11. Run safe checks.
12. Summarize result.
13. Create handoff if needed.

---

## Cursor role

Cursor is the main IDE workflow.

Use Cursor for:

- short local tasks;
- small backend steps;
- documentation edits;
- controlled code changes;
- reviewing diffs;
- running local tests;
- Agents Window coordination.

Cursor must not:

- run destructive git commands without approval;
- deploy live projects;
- run migrations without approval;
- use Run Everything in live projects;
- let multiple agents edit the same files.

---

## Codex role

Codex is used for:

- isolated research;
- code review;
- PR review;
- mapping legacy projects;
- worktrees;
- isolated implementation tasks after plan;
- repeatable automations.

Codex must use separate branches/worktrees for parallel work.

Codex should not:

- touch live deploy;
- push without approval;
- run migrations without approval;
- edit the same files as Cursor at the same time.

---

## MCP Coordinator v0.1 role

MCP Coordinator is project memory and dispatcher.

It is not an autopilot.

Allowed:

- read project map;
- read architecture docs;
- read change requests;
- classify task;
- check forbidden zones;
- suggest next safe step;
- create markdown change request;
- create handoff.

Forbidden:

- deploy;
- run migrations;
- delete files;
- push to GitHub;
- change Nginx/systemd;
- perform destructive git actions.

---

## Run Mode / permissions

Target mode:

    Auto-review

Allowed auto-run commands:

- git status
- git status --short
- git diff
- git diff --stat
- git log --oneline -n 20
- python -m pytest
- python -m compileall
- ls
- pwd
- cat
- grep
- find

Commands requiring explicit approval:

- git reset
- git clean
- git push
- git pull
- git merge
- rm
- del
- flask db upgrade
- alembic upgrade
- pip install
- npm install
- docker compose down
- systemctl
- nginx
- ssh
- scp
- deploy scripts

---

## Cloud / Automations

Allowed cloud/automation work:

- nightly research;
- Trailers to Flexity mapping;
- Consulting to Flexity mapping;
- documentation update;
- PR review;
- architecture review;
- test report;
- handoff draft.

Not allowed yet:

- rewriting Trailers;
- deploying;
- running migrations;
- changing Nginx/systemd;
- fixing live projects without approval.

---

## Cursor + Codex parallel scheme

Safe patterns:

1. Cursor implements a small backend step, Codex reviews.
2. Codex creates research-map, Cursor implements later.
3. Cursor works on Flexity, Codex maps Trailers read-only.
4. Codex prepares PR, Cursor checks locally.
5. Codex reviews diff after Cursor finishes.

Rules:

- different branches;
- different worktrees;
- different tasks;
- no simultaneous edits to the same files;
- one agent writes, another verifies;
- live projects only through live-hotfix-plan.

---

## Session finish checklist

At the end of a session, record:

- current branch;
- git status;
- files changed;
- tests run;
- decisions made;
- next safe step;
- what must not be touched next.

Preferred location:

    docs/ai/handoffs/YYYY-MM-DD-session-handoff.md
