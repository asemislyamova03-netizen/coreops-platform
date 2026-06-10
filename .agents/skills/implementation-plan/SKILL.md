---
name: implementation-plan
description: Use before writing code in Flexity. Creates a small approved implementation plan with exact files, scope, tests, and rollback notes.
---

# Implementation Plan Skill

## Use when

Use this skill before any code change.

Examples:

- add fields to kindergarten_basic seed;
- add a new endpoint;
- change a module;
- modify template/package behavior.

## Required inputs

- Task description.
- Target project.
- Current branch.
- Relevant research brief if available.
- Exact constraints from user.

## Process

1. Classify task:
   - platform_core;
   - universal_module;
   - industry_template;
   - industry_package;
   - tenant_customization;
   - live_client_hotfix;
   - migration_map;
   - documentation_only;
   - research_only.

2. Identify exact files to modify.

3. Identify forbidden files.

4. Define implementation steps.

5. Define checks/tests.

6. Define rollback plan.

7. Wait for approval before code.

## Output path

    docs/ai/plans/YYYY-MM-DD-topic-implementation-plan.md

## Output structure

# Implementation Plan: topic

## Goal

## Classification

## Scope

### Files to modify

### Files not to touch

## Steps

## Tests/checks

## Risks

## Rollback

## Approval

Status: waiting for approval

## Rules

- Keep scope small.
- Do not mix unrelated changes.
- Do not add dependencies unless explicitly approved.
- Do not run migrations unless explicitly approved.
- Do not push unless explicitly approved.
