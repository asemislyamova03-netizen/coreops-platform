# Public Inbound Leads MVP Runbook

## Scope

The MVP exposes `POST /api/v1/public/leads` for the public website demo/contact flow.
It is disabled by default and writes into existing parties and CRM workflow tables.

## Required Runtime Configuration

```env
PUBLIC_LEADS_ENABLED=false
PUBLIC_LEADS_TARGET_TENANT_ID=
PUBLIC_LEADS_PIPELINE_ID=
PUBLIC_LEADS_STAGE_ID=
PUBLIC_LEADS_CREATED_BY_USER_ID=
PUBLIC_LEADS_ALLOWED_ORIGINS=https://www.flexity.asia
PUBLIC_LEADS_TELEGRAM_BOT_TOKEN=
PUBLIC_LEADS_TELEGRAM_CHAT_ID=
```

Telegram settings are optional. If they are missing, the lead is still created and no
notification is sent.

## Safety Rules

- Keep `PUBLIC_LEADS_ENABLED=false` until runtime tenant, pipeline, stage and user IDs
  are verified.
- Do not use wildcard origins.
- Do not store Telegram credentials in the repository.
- Do not enable the endpoint for tenants without active `parties` and `crm` modules and
  `crm.work_items.create` entitlement.
- Notification failures must be reviewed in backend logs; they do not roll back created
  Party or WorkItem records.
