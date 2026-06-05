# Flexity Change Requests

This file records product and architecture changes that must be evaluated before implementation.

---

## CR-2026-06-05-001: Tenant Customization Layer

### Status

Proposed. Do not implement yet.

### Type

Architecture / Product layer.

### Summary

Flexity needs a separate tenant customization layer on top of industry templates and industry packages.

Target architecture:

    Flexity Core
    -> Universal modules
    -> Industry template / industry package
    -> Tenant customization

### Problem

Industry templates/packages define reusable business logic for a market segment.

But individual clients need their own configuration without creating a new industry module every time.

Examples:

- client logo;
- brand colors;
- company/legal details;
- document package;
- custom contract template;
- custom invoice template;
- custom act template;
- custom application template;
- custom fields;
- custom entity labels;
- custom pipeline settings;
- notification settings;
- signature settings.

These are tenant-specific settings, not industry-level features.

### Product rule

Do not hardcode client-specific settings into:

- Flexity Core;
- universal modules;
- industry templates;
- industry packages.

Client-specific settings must live in tenant customization.

### Initial scope

The tenant customization layer should eventually support:

1. Branding:
   - logo;
   - primary color;
   - secondary color;
   - document header/footer.

2. Legal profile:
   - client legal name;
   - BIN/IIN or equivalent;
   - address;
   - bank details;
   - signatory name and position.

3. Document customization:
   - enabled document types;
   - custom document templates;
   - custom placeholders;
   - custom numbering rules.

4. Field customization:
   - additional fields;
   - labels;
   - required/optional settings;
   - visibility per role.

5. Workflow customization:
   - pipeline names;
   - statuses;
   - notifications;
   - signature flow.

### Out of scope for now

Do not implement code yet.

Do not add migrations yet.

Do not change kindergarten code yet.

Do not change universal modules yet.

### Next required step

Create a research brief and implementation plan before code.

Recommended first planning file:

    docs/ai/plans/YYYY-MM-DD-tenant-customization-layer-plan.md

### Acceptance criteria for future implementation

- Tenant customization is clearly separated from industry templates/packages.
- Default industry behavior works without customization.
- Tenant settings override only approved configurable areas.
- No client-specific logic leaks into core.
- Document templates can be resolved in this order:

    tenant custom template
    -> industry template default
    -> universal document default
