const tenantStatusRu: Record<string, string> = {
  trial: "Тестовый период",
  active: "Активен",
  suspended: "Приостановлен",
  archived: "Архив",
};

const membershipRoleRu: Record<string, string> = {
  provider_owner: "Владелец платформы",
  tenant_owner: "Владелец организации",
  tenant_admin: "Администратор организации",
  member: "Сотрудник",
  tenant_member: "Сотрудник",
};

const partyTypeRu: Record<string, string> = {
  person: "Физическое лицо",
  organization: "Организация",
  sole_proprietor: "ИП",
};

const partyRoleRu: Record<string, string> = {
  client: "Клиент",
  guardian: "Клиент / родитель",
  supplier: "Поставщик",
  partner: "Партнёр",
  enrollee: "Ребёнок",
  staff: "Сотрудник",
};

const commonStatusRu: Record<string, string> = {
  active: "Активен",
  inactive: "Неактивен",
  archived: "Архив",
  enabled: "Включён",
  disabled: "Отключён",
  draft: "Черновик",
  generated: "Сформирован",
  sent: "Отправлен",
  signed: "Подписан",
  paid: "Оплачен",
  unpaid: "Не оплачен",
  overdue: "Просрочен",
  cancelled: "Отменён",
  open: "Открыт",
  closed: "Закрыт",
  pending: "Ожидает",
  completed: "Завершён",
  in_progress: "В работе",
  won: "Успешно",
  lost: "Потеряно",
  rejected: "Отклонён",
  issued: "Выставлен",
  partial: "Частично оплачен",
  void: "Аннулирован",
  trial: "Тестовый период",
  suspended: "Приостановлен",
  past_due: "Есть задолженность",
  expired: "Истекла",
};

const documentStatusRu: Record<string, string> = {
  ...commonStatusRu,
  sent_for_review: "На проверке",
  sent_for_signature: "На подписании",
  partially_signed: "Частично подписан",
  voided: "Аннулирован",
};

const invoiceStatusRu: Record<string, string> = {
  ...commonStatusRu,
  partially_paid: "Частично оплачен",
};

const paymentStatusRu: Record<string, string> = {
  ...commonStatusRu,
  confirmed: "Подтверждён",
  failed: "Ошибка",
  refunded: "Возврат",
};

const signatureStatusRu: Record<string, string> = {
  pending: "Ожидает подписи",
  sent: "Отправлено на подпись",
  signed: "Подписано",
  declined: "Отклонено",
  rejected: "Отклонено",
  cancelled: "Отменено",
  expired: "Истекло",
};

const activityTypeRu: Record<string, string> = {
  note: "Заметка",
  call: "Звонок",
  email: "Email",
  meeting: "Встреча",
  task: "Задача",
  status_change: "Смена статуса",
  other: "Другое",
};

const workItemTypeRu: Record<string, string> = {
  inquiry: "Запрос",
  order: "Заказ",
  project: "Проект",
  support: "Поддержка",
};

const contactMethodRu: Record<string, string> = {
  email: "Email",
  phone: "Телефон",
  mobile: "Мобильный",
  telegram: "Telegram",
  whatsapp: "WhatsApp",
  other: "Другое",
};

const knownApiErrorsRu: Record<string, string> = {
  "User not found": "Пользователь не найден",
  "User with this email already exists": "Пользователь с таким email уже существует",
  "Request failed": "Запрос не выполнен",
};

function formatFromMap(map: Record<string, string>, value: string | null | undefined): string {
  if (!value) return "—";
  const key = value.toLowerCase();
  return map[key] ?? map[value] ?? value;
}

function mapValue(map: Record<string, string>, value: string | null | undefined): string {
  return formatFromMap(map, value);
}

export const moduleModeRu = {
  internal: "Внутренний",
  external: "Внешний",
  hybrid: "Гибридный",
  disabled: "Отключён",
} as const;

export function formatModuleMode(value?: string | null): string {
  return formatFromMap(moduleModeRu, value);
}

export function formatTenantStatus(value: string | null | undefined): string {
  return mapValue(tenantStatusRu, value);
}

export function formatMembershipRole(value: string | null | undefined): string {
  if (!value) return "доступ провайдера";
  return mapValue(membershipRoleRu, value);
}

export function formatPartyType(value: string | null | undefined): string {
  return mapValue(partyTypeRu, value);
}

export function formatPartyRole(value: string | null | undefined): string {
  return mapValue(partyRoleRu, value);
}

export function formatCommonStatus(value: string | null | undefined): string {
  return mapValue(commonStatusRu, value);
}

export function formatModuleStatus(value: string | null | undefined): string {
  return mapValue(commonStatusRu, value);
}

export function formatDocumentStatus(value: string | null | undefined): string {
  return mapValue(documentStatusRu, value);
}

export function formatInvoiceStatus(value: string | null | undefined): string {
  return mapValue(invoiceStatusRu, value);
}

export function formatPaymentStatus(value: string | null | undefined): string {
  return mapValue(paymentStatusRu, value);
}

export function formatSignatureStatus(value: string | null | undefined): string {
  return mapValue(signatureStatusRu, value);
}

export function formatActivityType(value: string | null | undefined): string {
  return mapValue(activityTypeRu, value);
}

export function formatWorkItemType(value: string | null | undefined): string {
  return mapValue(workItemTypeRu, value);
}

export function formatContactMethodType(value: string | null | undefined): string {
  return mapValue(contactMethodRu, value);
}

export function formatApiErrorMessage(message: string): string {
  return knownApiErrorsRu[message] ?? message;
}

export const ui = {
  platformConsole: "Консоль платформы",
  managerWorkspace: "Рабочее место менеджера",
  tenants: "Организации",
  dashboard: "Рабочий стол",
  crm: "CRM",
  crmPipeline: "CRM / Воронка",
  clients: "Клиенты",
  documents: "Документы",
  finance: "Финансы",
  reports: "Отчёты",
  workItem: "Заявка",
  overview: "Обзор",
  readOnly: "только просмотр",
  organization: "Организация",
  slug: "Идентификатор (slug)",
} as const;
