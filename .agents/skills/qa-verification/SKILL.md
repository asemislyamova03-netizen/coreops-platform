---
name: qa-verification
description: Use after changes to verify diff, scope drift, tests, architecture violations, and forbidden file changes.
---

# QA Verification Skill

## Use when

Use after any implementation or documentation setup.

## Process

1. Run:
   - git status --short;
   - git diff --stat;
   - git diff.

2. Check scope:
   - Did the task modify only approved files?
   - Did it avoid forbidden files?
   - Did it introduce dependencies?
   - Did it create migrations?
   - Did it touch live project files?

3. Check architecture:
   - Does the change respect Flexity Core to Universal modules to Industry to Tenant customization?
   - Are client-specific settings kept out of core?
   - Are legacy/live projects protected?

4. Run relevant safe checks:
   - python -m compileall changed Python folders;
   - python -m pytest, if appropriate and available.

5. Produce QA result.

## Output structure

# QA Verification

## Scope check

## Architecture check

## Diff summary

## Tests/checks

## Issues found

## Recommendation

- approve;
- revise;
- revert.

## Rules

- Do not fix issues unless explicitly asked.
- Verification is read-only unless approval is given.
