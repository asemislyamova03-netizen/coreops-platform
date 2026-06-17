export interface TenantLabelsConfig {
  entities?: Record<string, string>;
  party_roles?: Record<string, string>;
  catalog_item_types?: Record<string, string>;
}

export const DEFAULT_WORKSPACE_LABELS: TenantLabelsConfig = {
  entities: {
    work_item: "Заявка",
    party: "Контрагент",
    invoice: "Счёт",
    payment: "Оплата",
    pipeline: "Воронка",
    document: "Документ",
  },
  party_roles: {
    enrollee: "Ребёнок",
    guardian: "Родитель",
    staff: "Сотрудник",
  },
  catalog_item_types: {
    subscription_service: "Абонемент",
    fee: "Сбор",
  },
};
