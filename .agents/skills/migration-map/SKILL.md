---
name: migration-map
description: Use for read-only mapping from legacy/live projects like Trailers or Consulting into future Flexity modules, templates, or packages.
---

# Migration Map Skill

## Use when

Use when analyzing how legacy/reference systems should be moved into Flexity.

Examples:

- Trailers to industry_trailers package;
- Consulting Flask to consulting_basic template;
- CRM duplication analysis;
- document/payment/order mapping.

## Process

1. Identify source project.
2. Identify target Flexity layer:
   - universal_module;
   - industry_template;
   - industry_package;
   - tenant_customization.

3. Read source project read-only.
4. Identify entities, workflows, roles, reports, documents.
5. Separate universal features from industry-specific features.
6. Identify what must not be duplicated because it belongs to Flexity core/universal modules.
7. Produce mapping.

## Output path

    docs/ai/research/YYYY-MM-DD-source-to-flexity-migration-map.md

## Output structure

# Migration Map: source to Flexity

## Source project

## Target Flexity layer

## Entities

## Workflows

## Roles

## Documents

## Payments

## Reports

## Universal modules

## Industry-specific package

## Tenant customization candidates

## Do not duplicate

## Recommended phases

## Rules

- Read-only unless separately approved.
- Do not modify legacy/live project.
- Do not create new code.
