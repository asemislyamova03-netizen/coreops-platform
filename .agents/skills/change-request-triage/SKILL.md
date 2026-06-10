---
name: change-request-triage
description: Use when a new idea, requirement, or scope change appears during work. Captures it as a Change Request instead of mixing it into the current task.
---

# Change Request Triage Skill

## Use when

Use when the user adds a new requirement while another task is in progress.

Examples:

- also add tenant customization;
- later add logo and client templates;
- maybe connect Bitrix;
- we need this for all industries.

## Process

1. Stop and classify whether the new requirement belongs to current scope.
2. If it is not part of the approved scope, do not implement it.
3. Add a Change Request entry to docs/ai/CHANGE_REQUESTS.md.
4. Include:
   - title;
   - status;
   - summary;
   - problem;
   - proposed direction;
   - out of scope;
   - next planning step.

## Output path

    docs/ai/CHANGE_REQUESTS.md

## Rule

A Change Request is not implementation approval.

Do not code from a Change Request until a separate implementation plan is approved.
