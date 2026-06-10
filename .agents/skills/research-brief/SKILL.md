---
name: research-brief
description: Use before new Flexity architecture, product, module, integration, or unclear implementation tasks. Produces read-only research brief without editing code.
---

# Research Brief Skill

## Use when

Use this skill when the task is new, unclear, architectural, cross-project, or may affect Flexity product direction.

Examples:

- study how kindergarten should fit into Flexity;
- analyze Trailers for future migration;
- research MCP coordinator;
- understand current architecture before code.

## Do not use when

- The task is already approved and only needs implementation.
- The user asked for a small known edit with an approved plan.
- The task is a live hotfix; use live-hotfix-plan first.

## Process

1. Identify the project:
   - Flexity;
   - Trailers;
   - Consulting Flask;
   - other.

2. Identify the architecture layer:
   - platform_core;
   - universal_module;
   - industry_template;
   - industry_package;
   - tenant_customization;
   - migration_map;
   - documentation_only;
   - research_only.

3. Read relevant docs first:
   - docs/ai/PRODUCT_ARCHITECTURE.md;
   - docs/ai/ORCHESTRATION.md;
   - docs/ai/CHANGE_REQUESTS.md;
   - existing plans/research under docs/ai/.

4. Inspect code read-only if needed.

5. Produce a markdown brief with:
   - context;
   - current state;
   - relevant files;
   - architectural risks;
   - open questions;
   - recommended next step;
   - what not to touch.

## Output path

    docs/ai/research/YYYY-MM-DD-topic-research-brief.md

## Output structure

# Research Brief: topic

## Context

## Current state

## Relevant files

## Architecture classification

## Risks

## Constraints

## Recommendation

## Do not touch

## Next safe step

## Final checks

- No code changes.
- No migrations.
- No deploy.
- No destructive commands.
