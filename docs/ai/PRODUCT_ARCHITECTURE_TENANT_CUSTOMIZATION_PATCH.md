# Product Architecture Patch: Tenant Customization Layer

Use this section to update docs/ai/PRODUCT_ARCHITECTURE.md.

Suggested location: after the current description of Flexity platform layers or industry templates.

---

## Tenant Customization Layer

Flexity must support a separate tenant customization layer above industry templates and industry packages.

Target architecture:

    Flexity Core
    -> Universal modules
    -> Industry template / industry package
    -> Tenant customization

### Purpose

Tenant customization stores client-specific configuration that should not be hardcoded into Flexity Core, universal modules, or industry packages.

Industry templates/packages define reusable defaults for a business segment.

Tenant customization defines overrides for a specific client.

### Examples

Tenant customization may include:

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
- pipeline settings;
- notification settings;
- signature settings.

### Resolution order

For configurable templates, Flexity should eventually resolve configuration in this order:

    tenant customization
    -> industry template/package default
    -> universal module default
    -> platform fallback

For document templates, the preferred resolution order is:

    tenant custom template
    -> industry template default
    -> universal document default

### Product rule

Client-specific settings must not be hardcoded into:

- Flexity Core;
- universal modules;
- industry templates;
- industry packages.

Tenant customization is not an industry module.

It is a client-specific layer above industry behavior.

### Current status

This layer is a proposed Change Request and roadmap item.

Do not implement it in code until a separate research brief and implementation plan are approved.
