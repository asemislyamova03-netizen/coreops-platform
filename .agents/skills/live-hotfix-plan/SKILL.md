---
name: live-hotfix-plan
description: Use before touching live Flask/Nginx projects such as Trailers or Consulting. Produces minimal-risk hotfix plan and forbids broad rewrites/deploy without approval.
---

# Live Hotfix Plan Skill

## Use when

Use before any change to live/reference projects:

- Trailers;
- Consulting Flask;
- any project under Nginx;
- any project with production users/data.

## Process

1. Confirm project is live/reference.
2. Define the exact bug or support issue.
3. Identify minimal files to inspect.
4. Inspect read-only first.
5. Propose the smallest safe patch.
6. Define how to test locally.
7. Define production risk.
8. Wait for approval.

## Forbidden without explicit approval

- deploy;
- migrations;
- Nginx/systemd changes;
- git push;
- git reset;
- git clean;
- deleting files;
- broad refactor;
- architecture rewrite.

## Output structure

# Live Hotfix Plan: issue

## Project

## Problem

## Risk level

## Files to inspect

## Proposed minimal change

## Files not to touch

## Test plan

## Rollback

## Approval

Status: waiting for approval
