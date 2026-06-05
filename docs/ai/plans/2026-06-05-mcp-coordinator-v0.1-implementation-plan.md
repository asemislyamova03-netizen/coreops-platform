# Implementation Plan: MCP Coordinator v0.1

## Goal

Create a local MCP Coordinator server as project memory and dispatcher for Flexity ecosystem work.

Target file:

    tools/mcp_coordinator/server.py

## Classification

Category:

    platform_core / tooling

Risk:

    medium

Reason:

MCP tools can influence agent behavior and may create files.

## Scope

### Files to create later

    tools/mcp_coordinator/server.py

### Files to create only after server works

    .cursor/mcp.json

### Files allowed for read access

    docs/ai/PRODUCT_ARCHITECTURE.md
    docs/ai/ORCHESTRATION.md
    docs/ai/CHANGE_REQUESTS.md
    .cursor/rules/90-coordinator.mdc
    AGENTS.md

### Files allowed for write access

    docs/ai/CHANGE_REQUESTS.md
    docs/ai/handoffs/
    docs/ai/research/
    docs/ai/plans/

### Forbidden write access

    backend/
    frontend/
    migrations/
    alembic/
    deploy/
    nginx/
    systemd/
    .env
    production config files

## Proposed tools

1. get_project_map
2. get_active_project_rules
3. classify_task
4. check_forbidden_zones
5. get_next_safe_step
6. create_change_request
7. create_session_handoff

## Implementation approach

Use Python MCP SDK / FastMCP only if the dependency is already available in the project environment.

If the dependency is not available, do not run pip install without approval.

Recommended first code version:

- no network;
- no shell command execution;
- no git command execution;
- no deploy;
- no migration;
- only filesystem reads;
- only markdown writes under docs/ai.

## Safety checks

Before connecting to Cursor:

    python -m compileall tools/mcp_coordinator

Manual test through MCP inspector or direct Python call only after approval.

## Cursor connection later

Only after code is reviewed, add:

    .cursor/mcp.json

Potential config:

    {
      "mcpServers": {
        "flexity-coordinator": {
          "command": "python",
          "args": ["tools/mcp_coordinator/server.py"]
        }
      }
    }

Do not add this file until server.py is approved.

## Rollback

Delete:

    tools/mcp_coordinator/server.py
    .cursor/mcp.json

No app code should be affected.

## Approval

Status: waiting for approval before code.
