import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ApiError } from "../api/client";
import { applyTemplate, listTemplates } from "../api/industry-templates";
import { getTenantLabels } from "../api/labels";
import { disableModule, enableModule, listTenantModules } from "../api/modules";
import { assignPlan, getSubscription, listPlans } from "../api/subscriptions";
import {
  addTenantMembership,
  getTenant,
  listTenantMemberships,
  patchTenant,
} from "../api/tenants";
import { Alert } from "../components/ui/Alert";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { Loading } from "../components/ui/Loading";
import { Select } from "../components/ui/Select";
import { Table } from "../components/ui/Table";
import type { TenantModule } from "../types/module";
import type { TenantMembership, TenantMembershipRole, TenantStatus } from "../types/tenant";
import type { ApplyTemplateResponse } from "../types/template";

type TabId =
  | "info"
  | "users"
  | "modules"
  | "subscription"
  | "labels"
  | "apply-template";

const TABS: Array<{ id: TabId; label: string }> = [
  { id: "info", label: "Info" },
  { id: "users", label: "Users" },
  { id: "modules", label: "Modules" },
  { id: "subscription", label: "Subscription" },
  { id: "labels", label: "Labels" },
  { id: "apply-template", label: "Apply Template" },
];

const STATUS_OPTIONS: Array<{ value: TenantStatus; label: string }> = [
  { value: "trial", label: "trial" },
  { value: "active", label: "active" },
  { value: "suspended", label: "suspended" },
  { value: "archived", label: "archived" },
];

const MEMBERSHIP_ROLE_OPTIONS: Array<{ value: TenantMembershipRole; label: string }> = [
  { value: "tenant_owner", label: "tenant_owner" },
  { value: "tenant_admin", label: "tenant_admin" },
  { value: "member", label: "member" },
];

const dateFormatter = new Intl.DateTimeFormat("ru-RU", {
  dateStyle: "medium",
  timeStyle: "short",
});

export function TenantDetailPage() {
  const { tenantId = "" } = useParams();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<TabId>("info");
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [selectedPlan, setSelectedPlan] = useState("");
  const [newMemberEmail, setNewMemberEmail] = useState("");
  const [newMemberRole, setNewMemberRole] = useState<TenantMembershipRole>("member");
  const [applyResult, setApplyResult] = useState<ApplyTemplateResponse | null>(null);

  const tenantQuery = useQuery({
    queryKey: ["tenant", tenantId],
    queryFn: () => getTenant(tenantId),
    enabled: Boolean(tenantId),
  });

  const modulesQuery = useQuery({
    queryKey: ["tenant-modules", tenantId],
    queryFn: () => listTenantModules(tenantId),
    enabled: Boolean(tenantId) && activeTab === "modules",
  });

  const membershipsQuery = useQuery({
    queryKey: ["tenant-memberships", tenantId],
    queryFn: () => listTenantMemberships(tenantId),
    enabled: Boolean(tenantId) && activeTab === "users",
  });

  const subscriptionQuery = useQuery({
    queryKey: ["tenant-subscription", tenantId],
    queryFn: () => getSubscription(tenantId),
    enabled: Boolean(tenantId) && activeTab === "subscription",
  });

  const plansQuery = useQuery({
    queryKey: ["plans"],
    queryFn: listPlans,
    enabled: activeTab === "subscription",
  });

  const labelsQuery = useQuery({
    queryKey: ["tenant-labels", tenantId],
    queryFn: () => getTenantLabels(tenantId),
    enabled: Boolean(tenantId) && activeTab === "labels",
  });

  const templatesQuery = useQuery({
    queryKey: ["industry-templates"],
    queryFn: listTemplates,
    enabled: activeTab === "apply-template",
  });

  const invalidateTenant = () => {
    void queryClient.invalidateQueries({ queryKey: ["tenant", tenantId] });
    void queryClient.invalidateQueries({ queryKey: ["tenants"] });
  };

  const statusMutation = useMutation({
    mutationFn: (status: TenantStatus) => patchTenant(tenantId, { status }),
    onSuccess: () => {
      setActionSuccess("Статус обновлён");
      setActionError(null);
      invalidateTenant();
    },
    onError: (err: unknown) => {
      setActionSuccess(null);
      setActionError(err instanceof ApiError ? err.message : "Ошибка обновления статуса");
    },
  });

  const moduleMutation = useMutation({
    mutationFn: ({ code, action }: { code: string; action: "enable" | "disable" }) =>
      action === "enable" ? enableModule(tenantId, code) : disableModule(tenantId, code),
    onSuccess: () => {
      setActionSuccess("Модуль обновлён");
      setActionError(null);
      void queryClient.invalidateQueries({ queryKey: ["tenant-modules", tenantId] });
    },
    onError: (err: unknown) => {
      setActionSuccess(null);
      setActionError(err instanceof ApiError ? err.message : "Ошибка модуля");
    },
  });

  const assignPlanMutation = useMutation({
    mutationFn: (planCode: string) => assignPlan(tenantId, planCode),
    onSuccess: () => {
      setActionSuccess("Подписка назначена");
      setActionError(null);
      void queryClient.invalidateQueries({ queryKey: ["tenant-subscription", tenantId] });
    },
    onError: (err: unknown) => {
      setActionSuccess(null);
      setActionError(err instanceof ApiError ? err.message : "Ошибка подписки");
    },
  });

  const applyTemplateMutation = useMutation({
    mutationFn: (templateId: string) => applyTemplate(tenantId, templateId),
    onSuccess: (result) => {
      setApplyResult(result);
      setActionSuccess(`Шаблон ${result.template_code} применён`);
      setActionError(null);
      invalidateTenant();
      void queryClient.invalidateQueries({ queryKey: ["tenant-modules", tenantId] });
      void queryClient.invalidateQueries({ queryKey: ["tenant-labels", tenantId] });
    },
    onError: (err: unknown) => {
      setActionSuccess(null);
      setApplyResult(null);
      setActionError(err instanceof ApiError ? err.message : "Ошибка применения шаблона");
    },
  });

  const addMembershipMutation = useMutation({
    mutationFn: ({ email, role }: { email: string; role: TenantMembershipRole }) =>
      addTenantMembership(tenantId, { user_email: email, role }),
    onSuccess: () => {
      setActionSuccess("Пользователь добавлен в tenant");
      setActionError(null);
      setNewMemberEmail("");
      void queryClient.invalidateQueries({ queryKey: ["tenant-memberships", tenantId] });
    },
    onError: (err: unknown) => {
      setActionSuccess(null);
      setActionError(err instanceof ApiError ? err.message : "Ошибка добавления пользователя");
    },
  });

  if (tenantQuery.isLoading) return <Loading />;
  if (tenantQuery.error || !tenantQuery.data) {
    return <Alert variant="error">Tenant не найден или ошибка загрузки</Alert>;
  }

  const tenant = tenantQuery.data;

  const handleApplyTemplate = (templateId: string, templateName: string) => {
    const confirmed = window.confirm(
      `Применить шаблон «${templateName}» к tenant «${tenant.name}»?\n\nПовторное применение может создать дубликаты данных.`,
    );
    if (!confirmed) return;
    setActionError(null);
    setActionSuccess(null);
    applyTemplateMutation.mutate(templateId);
  };

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>{tenant.name}</h1>
          <p className="muted">
            <code>{tenant.slug}</code> ·{" "}
            <span className={`badge badge-${tenant.status}`}>{tenant.status}</span>
          </p>
        </div>
        <div className="actions-row">
          <Link to={`/workspace/${tenant.slug}/dashboard`}>
            <Button>Open workspace</Button>
          </Link>
          <Link to="/tenants">
            <Button variant="secondary">К списку</Button>
          </Link>
        </div>
      </div>

      <div className="tabs">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            className={activeTab === tab.id ? "tab active" : "tab"}
            onClick={() => {
              setActiveTab(tab.id);
              setActionError(null);
              setActionSuccess(null);
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {actionError && <Alert variant="error">{actionError}</Alert>}
      {actionSuccess && <Alert variant="success">{actionSuccess}</Alert>}

      {activeTab === "info" && (
        <div className="panel">
          <dl className="detail-list">
            <dt>ID</dt>
            <dd><code>{tenant.id}</code></dd>
            <dt>Provider company</dt>
            <dd><code>{tenant.provider_company_id}</code></dd>
            <dt>Industry template ID</dt>
            <dd>
              {tenant.industry_template_id ? (
                <code>{tenant.industry_template_id}</code>
              ) : (
                <span className="muted">не назначен</span>
              )}
            </dd>
            <dt>Создан</dt>
            <dd>{dateFormatter.format(new Date(tenant.created_at))}</dd>
            <dt>Обновлён</dt>
            <dd>{dateFormatter.format(new Date(tenant.updated_at))}</dd>
          </dl>
          <div className="form-inline">
            <Select
              label="Статус"
              name="status"
              value={tenant.status}
              options={STATUS_OPTIONS}
              onChange={(e) => statusMutation.mutate(e.target.value as TenantStatus)}
            />
          </div>
        </div>
      )}

      {activeTab === "modules" && (
        <div className="panel">
          {modulesQuery.isLoading ? (
            <Loading />
          ) : modulesQuery.error ? (
            <Alert variant="error">Не удалось загрузить модули</Alert>
          ) : (
            <Table<TenantModule>
              data={modulesQuery.data ?? []}
              rowKey={(row) => row.id}
              emptyText="Модули не найдены"
              columns={[
                { key: "code", header: "Модуль", render: (row) => row.module_code },
                { key: "status", header: "Статус", render: (row) => row.status },
                { key: "mode", header: "Режим", render: (row) => row.mode },
                {
                  key: "actions",
                  header: "Действия",
                  render: (row) => (
                    <div className="actions-row compact">
                      {row.status !== "enabled" && (
                        <Button
                          variant="secondary"
                          disabled={moduleMutation.isPending}
                          onClick={() =>
                            moduleMutation.mutate({ code: row.module_code, action: "enable" })
                          }
                        >
                          Enable
                        </Button>
                      )}
                      {row.status !== "disabled" && (
                        <Button
                          variant="danger"
                          disabled={moduleMutation.isPending}
                          onClick={() =>
                            moduleMutation.mutate({ code: row.module_code, action: "disable" })
                          }
                        >
                          Disable
                        </Button>
                      )}
                    </div>
                  ),
                },
              ]}
            />
          )}
        </div>
      )}

      {activeTab === "users" && (
        <div className="panel">
          <div className="form-inline">
            <Input
              label="User email"
              name="membership_user_email"
              type="email"
              value={newMemberEmail}
              onChange={(e) => setNewMemberEmail(e.target.value)}
              placeholder="user@example.com"
            />
            <Select
              label="Role"
              name="membership_role"
              value={newMemberRole}
              options={MEMBERSHIP_ROLE_OPTIONS}
              onChange={(e) => setNewMemberRole(e.target.value as TenantMembershipRole)}
            />
            <Button
              disabled={!newMemberEmail.trim() || addMembershipMutation.isPending}
              onClick={() =>
                addMembershipMutation.mutate({
                  email: newMemberEmail.trim(),
                  role: newMemberRole,
                })
              }
            >
              Add existing user
            </Button>
          </div>
          {membershipsQuery.isLoading ? (
            <Loading />
          ) : membershipsQuery.error ? (
            <Alert variant="error">Не удалось загрузить memberships</Alert>
          ) : (
            <Table<TenantMembership>
              data={membershipsQuery.data ?? []}
              rowKey={(row) => row.membership_id}
              emptyText="Пользователи tenant не найдены"
              columns={[
                { key: "email", header: "Email", render: (row) => row.email },
                { key: "full_name", header: "Имя", render: (row) => row.full_name },
                {
                  key: "user_status",
                  header: "User status",
                  render: (row) => (row.user_is_active ? "active" : "inactive"),
                },
                { key: "role", header: "Tenant role", render: (row) => row.role },
                {
                  key: "membership_status",
                  header: "Membership status",
                  render: (row) => (row.membership_is_active ? "active" : "inactive"),
                },
                {
                  key: "created_at",
                  header: "Added at",
                  render: (row) => dateFormatter.format(new Date(row.created_at)),
                },
              ]}
            />
          )}
        </div>
      )}

      {activeTab === "subscription" && (
        <div className="panel">
          {subscriptionQuery.isLoading || plansQuery.isLoading ? (
            <Loading />
          ) : (
            <>
              <div className="detail-block">
                <h3>Текущая подписка</h3>
                {subscriptionQuery.data ? (
                  <p>
                    <strong>{subscriptionQuery.data.plan_name}</strong> (
                    {subscriptionQuery.data.plan_code}) — {subscriptionQuery.data.status}
                  </p>
                ) : (
                  <p className="muted">Подписка не назначена</p>
                )}
              </div>
              <div className="form-inline">
                <Select
                  label="Назначить план"
                  name="assign_plan"
                  emptyLabel="выберите план"
                  value={selectedPlan}
                  onChange={(e) => setSelectedPlan(e.target.value)}
                  options={(plansQuery.data ?? []).map((plan) => ({
                    value: plan.code,
                    label: `${plan.name} (${plan.code})`,
                  }))}
                />
                <Button
                  disabled={!selectedPlan || assignPlanMutation.isPending}
                  onClick={() => assignPlanMutation.mutate(selectedPlan)}
                >
                  Назначить
                </Button>
              </div>
            </>
          )}
        </div>
      )}

      {activeTab === "labels" && (
        <div className="panel">
          {labelsQuery.isLoading ? (
            <Loading />
          ) : labelsQuery.error ? (
            <Alert variant="error">Не удалось загрузить labels</Alert>
          ) : (
            <>
              <Alert variant="info">
                Редактирование labels будет доступно в Track A (PATCH endpoint).
              </Alert>
              <pre className="json-block">
                {JSON.stringify(labelsQuery.data ?? {}, null, 2)}
              </pre>
            </>
          )}
        </div>
      )}

      {activeTab === "apply-template" && (
        <div className="panel">
          {templatesQuery.isLoading ? (
            <Loading />
          ) : (
            <>
              <Alert variant="info">
                Применение шаблона настраивает модули, labels, pipelines и другие сущности tenant.
              </Alert>
              <div className="template-list">
                {(templatesQuery.data ?? [])
                  .filter((t) => t.is_active)
                  .map((template) => (
                    <div key={template.id} className="template-card">
                      <div>
                        <strong>{template.name}</strong>
                        <div className="muted">
                          <code>{template.code}</code>
                        </div>
                        {template.description && (
                          <p className="muted">{template.description}</p>
                        )}
                      </div>
                      <Button
                        disabled={applyTemplateMutation.isPending}
                        onClick={() => handleApplyTemplate(template.id, template.name)}
                      >
                        Применить
                      </Button>
                    </div>
                  ))}
              </div>
              {applyResult && (
                <div className="detail-block">
                  <h3>Результат применения</h3>
                  <pre className="json-block">{JSON.stringify(applyResult, null, 2)}</pre>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
