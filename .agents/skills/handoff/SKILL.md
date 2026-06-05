---
name: handoff
description: Use at the end of a session to create a concise continuation file with branch, status, changed files, checks, decisions, risks, and next safe step.
---

# Handoff Skill

## Use when

Use at the end of any substantial work session.

## Process

1. Run safe status commands:
   - git status --short;
   - git branch --show-current;
   - git diff --stat.

2. Summarize:
   - branch;
   - goal;
   - files changed;
   - tests/checks run;
   - decisions made;
   - risks;
   - next safe step;
   - forbidden next actions.

3. Create handoff file.

## Output path

    docs/ai/handoffs/YYYY-MM-DD-session-handoff.md

## Output structure

# Session Handoff: YYYY-MM-DD

## Branch

## Goal

## Status

## Files changed

## Checks run

## Decisions

## Risks

## Next safe step

## Do not do next
