import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ApiError } from "../api/client";
import { applyTemplate, listTemplates } from "../api/industry-templates";
import { getTenantLabels } from "../api/labels";
import {
  disableModule,
  enableModule,
  listModuleRegistry,
  listTenantModules,
} from "../api/modules";
import {
  buildTenantModuleRows,
  disableBlockedMessage,
} from "./tenantModulesHelpers";
import { assignPlan, getSubscription, listPlans } from "../api/subscriptions";
import {
  addTenantMembership,
  createTenantUser,
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
import type { TenantModuleRow } from "../types/module";
import type { TenantMembership, TenantMembershipRole, TenantStatus, TenantUserCreateRole } from "../types/tenant";
import type { ApplyTemplateResponse } from "../types/template";
import {
  formatApiErrorMessage,
  formatCommonStatus,
  formatMembershipRole,
  formatModuleStatus,
  formatModuleMode,
  formatTenantStatus,
} from "../i18n/ruUi";

type TabId =
  | "info"
  | "users"
  | "modules"
  | "subscription"
  | "labels"
  | "apply-template";

const TABS: Array<{ id: TabId; label: string }> = [
  { id: "info", label: "Сведения" },
  { id: "users", label: "Пользователи" },
  { id: "modules", label: "Модули" },
  { id: "subscription", label: "Подписка" },
  { id: "labels", label: "Метки" },
  { id: "apply-template", label: "Применить шаблон" },
];

const STATUS_OPTIONS: Array<{ value: TenantStatus; label: string }> = [
  { value: "trial", label: formatTenantStatus("trial") },
  { value: "active", label: formatTenantStatus("active") },
  { value: "suspended", label: formatTenantStatus("suspended") },
  { value: "archived", label: formatTenantStatus("archived") },
];

const MEMBERSHIP_ROLE_OPTIONS: Array<{ value: TenantMembershipRole; label: string }> = [
  { value: "tenant_owner", label: formatMembershipRole("tenant_owner") },
  { value: "tenant_admin", label: formatMembershipRole("tenant_admin") },
  { value: "member", label: formatMembershipRole("member") },
];

const CREATE_USER_ROLE_OPTIONS: Array<{ value: TenantUserCreateRole; label: string }> = [
  { value: "tenant_owner", label: formatMembershipRole("tenant_owner") },
  { value: "tenant_admin", label: formatMembershipRole("tenant_admin") },
  { value: "member", label: formatMembershipRole("member") },
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
  const [showCreateUserModal, setShowCreateUserModal] = useState(false);
  const [createUserEmail, setCreateUserEmail] = useState("");
  const [createUserFullName, setCreateUserFullName] = useState("");
  const [createUserTempPassword, setCreateUserTempPassword] = useState("");
  const [createUserRole, setCreateUserRole] = useState<TenantUserCreateRole>("member");
  const [createUserFormError, setCreateUserFormError] = useState<string | null>(null);
  const [createUserSuccess, setCreateUserSuccess] = useState<{
    email: string;
    temporaryPassword: string;
  } | null>(null);

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

  const registryQuery = useQuery({
    queryKey: ["module-registry"],
    queryFn: listModuleRegistry,
    enabled: activeTab === "modules",
  });

  const moduleRows = buildTenantModuleRows(
    modulesQuery.data ?? [],
    registryQuery.data ?? [],
  );

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
    onSuccess: (_data, variables) => {
      setActionSuccess(
        variables.action === "enable" ? "Модуль включён" : "Модуль отключён",
      );
      setActionError(null);
      void queryClient.invalidateQueries({ queryKey: ["tenant-modules", tenantId] });
    },
    onError: (err: unknown) => {
      setActionSuccess(null);
      setActionError(err instanceof ApiError ? formatApiErrorMessage(err.message) : "Ошибка модуля");
    },
  });

  const requestDisableModule = (row: TenantModuleRow) => {
    if (row.active_dependents.length > 0) {
      setActionSuccess(null);
      setActionError(disableBlockedMessage(row.module_code, row.active_dependents));
      return;
    }
    const confirmed = window.confirm(
      `Отключить модуль «${row.name}» (${row.module_code})?\n` +
        "Данные tenant не удаляются — отключается только доступ к модулю.",
    );
    if (!confirmed) {
      return;
    }
    moduleMutation.mutate({ code: row.module_code, action: "disable" });
  };

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
      setActionSuccess("Пользователь добавлен в организацию");
      setActionError(null);
      setNewMemberEmail("");
      void queryClient.invalidateQueries({ queryKey: ["tenant-memberships", tenantId] });
    },
    onError: (err: unknown) => {
      setActionSuccess(null);
      setActionError(err instanceof ApiError ? formatApiErrorMessage(err.message) : "Ошибка добавления пользователя");
    },
  });

  const resetCreateUserModal = () => {
    setShowCreateUserModal(false);
    setCreateUserEmail("");
    setCreateUserFullName("");
    setCreateUserTempPassword("");
    setCreateUserRole("member");
    setCreateUserFormError(null);
    setCreateUserSuccess(null);
  };

  const createUserMutation = useMutation({
    mutationFn: () =>
      createTenantUser(tenantId, {
        email: createUserEmail.trim(),
        full_name: createUserFullName.trim(),
        temporary_password: createUserTempPassword,
        role: createUserRole,
      }),
    onSuccess: () => {
      setCreateUserSuccess({
        email: createUserEmail.trim(),
        temporaryPassword: createUserTempPassword,
      });
      setCreateUserTempPassword("");
      setCreateUserFormError(null);
      setActionError(null);
      void queryClient.invalidateQueries({ queryKey: ["tenant-memberships", tenantId] });
    },
    onError: (err: unknown) => {
      setCreateUserSuccess(null);
      setCreateUserFormError(
        err instanceof ApiError
          ? formatApiErrorMessage(err.message)
          : "Не удалось создать пользователя",
      );
    },
  });

  if (tenantQuery.isLoading) return <Loading />;
  if (tenantQuery.error || !tenantQuery.data) {
    return <Alert variant="error">Организация не найдена или ошибка загрузки</Alert>;
  }

  const tenant = tenantQuery.data;

  const handleApplyTemplate = (templateId: string, templateName: string) => {
    const confirmed = window.confirm(
      `Применить шаблон «${templateName}» к организации «${tenant.name}»?\n\nПовторное применение может создать дубликаты данных.`,
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
            <span className={`badge badge-${tenant.status}`}>
              {formatTenantStatus(tenant.status)}
            </span>
          </p>
        </div>
        <div className="actions-row">
          <Link to={`/workspace/${tenant.slug}/dashboard`}>
            <Button>Открыть рабочее место</Button>
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
            <dt>Компания провайдера</dt>
            <dd><code>{tenant.provider_company_id}</code></dd>
            <dt>ID отраслевого шаблона</dt>
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
          {modulesQuery.isLoading || registryQuery.isLoading ? (
            <Loading />
          ) : modulesQuery.error || registryQuery.error ? (
            <Alert variant="error">Не удалось загрузить модули</Alert>
          ) : (
            <>
              <p className="muted" style={{ marginBottom: "0.75rem" }}>
                Каталог модулей общий для всех tenant. Отключение не удаляет данные.
                Сначала отключайте зависимые модули, затем их зависимости.
              </p>
              <Table<TenantModuleRow>
                data={moduleRows}
                rowKey={(row) => row.id}
                emptyText="Модули не найдены"
                columns={[
                  {
                    key: "name",
                    header: "Модуль",
                    render: (row) => (
                      <div>
                        <div>{row.name}</div>
                        <div className="muted" style={{ fontSize: "0.85em" }}>
                          {row.module_code}
                          {row.description ? ` — ${row.description}` : ""}
                        </div>
                      </div>
                    ),
                  },
                  {
                    key: "status",
                    header: "Статус",
                    render: (row) => formatModuleStatus(row.status),
                  },
                  {
                    key: "mode",
                    header: "Режим",
                    render: (row) => formatModuleMode(row.mode),
                  },
                  {
                    key: "deps",
                    header: "Зависимости",
                    render: (row) =>
                      row.required_dependencies.length > 0
                        ? row.required_dependencies.join(", ")
                        : "—",
                  },
                  {
                    key: "dependents",
                    header: "Требуется для",
                    render: (row) =>
                      row.active_dependents.length > 0
                        ? row.active_dependents.join(", ")
                        : "—",
                  },
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
                              moduleMutation.mutate({
                                code: row.module_code,
                                action: "enable",
                              })
                            }
                          >
                            Включить
                          </Button>
                        )}
                        {row.status !== "disabled" && (
                          <Button
                            variant="danger"
                            disabled={moduleMutation.isPending}
                            onClick={() => requestDisableModule(row)}
                          >
                            Отключить
                          </Button>
                        )}
                      </div>
                    ),
                  },
                ]}
              />
            </>
          )}
        </div>
      )}

      {activeTab === "users" && (
        <div className="panel">
          <div className="form-inline tenant-users-actions">
            <Button variant="secondary" onClick={() => setShowCreateUserModal(true)}>
              Создать пользователя
            </Button>
          </div>
          <div className="form-inline">
            <Input
              label="Email пользователя"
              name="membership_user_email"
              type="email"
              value={newMemberEmail}
              onChange={(e) => setNewMemberEmail(e.target.value)}
              placeholder="user@example.com"
            />
            <Select
              label="Роль"
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
              Добавить существующего пользователя
            </Button>
          </div>
          {membershipsQuery.isLoading ? (
            <Loading />
          ) : membershipsQuery.error ? (
            <Alert variant="error">Не удалось загрузить пользователей</Alert>
          ) : (
            <Table<TenantMembership>
              data={membershipsQuery.data ?? []}
              rowKey={(row) => row.membership_id}
              emptyText="Пользователи организации не найдены"
              columns={[
                { key: "email", header: "Email", render: (row) => row.email },
                { key: "full_name", header: "Имя", render: (row) => row.full_name },
                {
                  key: "user_status",
                  header: "Статус пользователя",
                  render: (row) =>
                    formatCommonStatus(row.user_is_active ? "active" : "inactive"),
                },
                {
                  key: "role",
                  header: "Роль в организации",
                  render: (row) => formatMembershipRole(row.role),
                },
                {
                  key: "membership_status",
                  header: "Статус участия",
                  render: (row) =>
                    formatCommonStatus(row.membership_is_active ? "active" : "inactive"),
                },
                {
                  key: "created_at",
                  header: "Добавлен",
                  render: (row) => dateFormatter.format(new Date(row.created_at)),
                },
              ]}
            />
          )}
        </div>
      )}

      {showCreateUserModal && (
        <div
          className="workspace-modal-overlay"
          role="presentation"
          onClick={resetCreateUserModal}
          onKeyDown={(event) => {
            if (event.key === "Escape") resetCreateUserModal();
          }}
        >
          <div
            className="workspace-modal panel"
            role="dialog"
            aria-modal="true"
            aria-labelledby="create-tenant-user-title"
            onClick={(event) => event.stopPropagation()}
          >
            <header className="workspace-modal-header">
              <h2 id="create-tenant-user-title">Создать пользователя</h2>
              <button type="button" className="btn btn-secondary" onClick={resetCreateUserModal}>
                Закрыть
              </button>
            </header>
            <div className="workspace-modal-body">
              {createUserSuccess ? (
                <Alert variant="success">
                  <p>
                    Пользователь создан и добавлен в организацию. Передайте клиенту email и
                    временный пароль вручную.
                  </p>
                  <dl className="detail-list tenant-user-credentials">
                    <dt>Email</dt>
                    <dd>{createUserSuccess.email}</dd>
                    <dt>Временный пароль</dt>
                    <dd>
                      <code>{createUserSuccess.temporaryPassword}</code>
                    </dd>
                  </dl>
                  <div className="actions-row">
                    <Button onClick={resetCreateUserModal}>Готово</Button>
                  </div>
                </Alert>
              ) : (
                <form
                  className="workspace-form"
                  onSubmit={(event) => {
                    event.preventDefault();
                    if (
                      !createUserEmail.trim() ||
                      !createUserFullName.trim() ||
                      createUserTempPassword.length < 8
                    ) {
                      setCreateUserFormError(
                        "Заполните email, имя и временный пароль (минимум 8 символов).",
                      );
                      return;
                    }
                    setCreateUserFormError(null);
                    createUserMutation.mutate();
                  }}
                >
                  <Input
                    label="Email"
                    name="create_user_email"
                    type="email"
                    required
                    value={createUserEmail}
                    onChange={(e) => setCreateUserEmail(e.target.value)}
                  />
                  <Input
                    label="Имя"
                    name="create_user_full_name"
                    required
                    value={createUserFullName}
                    onChange={(e) => setCreateUserFullName(e.target.value)}
                  />
                  <Input
                    label="Временный пароль"
                    name="create_user_temp_password"
                    type="password"
                    required
                    minLength={8}
                    autoComplete="new-password"
                    value={createUserTempPassword}
                    onChange={(e) => setCreateUserTempPassword(e.target.value)}
                  />
                  <Select
                    label="Роль в организации"
                    name="create_user_role"
                    value={createUserRole}
                    options={CREATE_USER_ROLE_OPTIONS}
                    onChange={(e) => setCreateUserRole(e.target.value as TenantUserCreateRole)}
                  />
                  {createUserFormError && <Alert variant="error">{createUserFormError}</Alert>}
                  <div className="actions-row workspace-form-actions">
                    <Button type="button" variant="secondary" onClick={resetCreateUserModal}>
                      Отмена
                    </Button>
                    <Button type="submit" disabled={createUserMutation.isPending}>
                      {createUserMutation.isPending ? "Создание..." : "Создать"}
                    </Button>
                  </div>
                </form>
              )}
            </div>
          </div>
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
                    {subscriptionQuery.data.plan_code}) —{" "}
                    {formatCommonStatus(subscriptionQuery.data.status)}
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
            <Alert variant="error">Не удалось загрузить метки</Alert>
          ) : (
            <>
              <Alert variant="info">
                Редактирование меток будет доступно в Track A (PATCH endpoint).
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
                Применение шаблона настраивает модули, метки, воронки и другие сущности
                организации.
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
