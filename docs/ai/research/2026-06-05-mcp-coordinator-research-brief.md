# Research Brief: MCP Coordinator v0.1

## Context

Flexity needs a local MCP Coordinator to reduce manual project coordination across Cursor, Codex, Skills, and Subagents.

The MCP Coordinator must act as project memory and dispatcher, not as an autopilot.

MCP Coordinator v0.1 must be intentionally low-risk.

## Goal

Design a local MCP server:

    tools/mcp_coordinator/server.py

The server should help agents:

- understand the project map;
- classify tasks;
- read architecture docs;
- read change requests;
- detect forbidden zones;
- suggest the next safe step;
- create markdown change requests;
- create handoff files.

## Non-goal

MCP Coordinator v0.1 must not:

- deploy;
- run migrations;
- delete files;
- push to GitHub;
- pull/merge/reset/clean;
- edit production config;
- change Nginx/systemd;
- run ssh/scp;
- install dependencies.

## Proposed tools

### get_project_map

Returns structured map:

- Flexity;
- Trailers;
- Consulting Flask;
- Kindergarten inside Flexity.

### get_active_project_rules

Reads:

- docs/ai/PRODUCT_ARCHITECTURE.md;
- docs/ai/ORCHESTRATION.md;
- docs/ai/CHANGE_REQUESTS.md;
- .cursor/rules/90-coordinator.mdc;
- AGENTS.md.

### classify_task

Input:

- task text.

Output:

- project;
- category;
- risk level;
- required skill;
- likely scope;
- forbidden scope.

Categories:

- platform_core;
- universal_module;
- industry_template;
- industry_package;
- tenant_customization;
- live_client_hotfix;
- migration_map;
- documentation_only;
- research_only.

### check_forbidden_zones

Input:

- proposed files;
- command;
- project;
- category.

Output:

- allowed: true or false;
- reason;
- approval required: true or false.

### get_next_safe_step

Input:

- task text;
- current branch;
- git status summary.

Output:

- next safe action;
- required file;
- required skill;
- whether approval is needed.

### create_change_request

Input:

- title;
- summary;
- reason;
- examples;
- out_of_scope.

Output:

- markdown entry appended or proposed for docs/ai/CHANGE_REQUESTS.md.

### create_session_handoff

Input:

- branch;
- status;
- changed files;
- checks;
- decisions;
- next step.

Output:

- markdown file under docs/ai/handoffs/.

## Data sources

Local files only.

No external API in v0.1.

## Safety design

The MCP server should expose only read and markdown-writing tools.

Even markdown-writing tools should write only under:

    docs/ai/

Allowed write paths:

- docs/ai/CHANGE_REQUESTS.md;
- docs/ai/handoffs/;
- docs/ai/research/;
- docs/ai/plans/.

Forbidden write paths:

- backend/;
- frontend/;
- migrations/;
- alembic/;
- deploy/;
- nginx/;
- systemd/;
- .env;
- production config files.

## Recommendation

Build MCP Coordinator in two steps:

1. Implementation plan only.
2. Code after approval.

## Next safe step

Create:

    docs/ai/plans/2026-06-05-mcp-coordinator-v0.1-implementation-plan.md
