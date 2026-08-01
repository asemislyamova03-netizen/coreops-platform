/** Pure helpers for generic client signup UI (D1–D3). */

export function slugifyTenantName(name: string): string {
  return name
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

export function isValidTenantSlug(slug: string): boolean {
  return /^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(slug);
}

export function buildMarketingGuidePath(tenantSlug: string): string {
  return `/workspace/${tenantSlug}/marketing/guide`;
}

/** Browser path including Vite/console basename. */
export function buildConsoleMarketingGuidePath(tenantSlug: string): string {
  return `/console/workspace/${tenantSlug}/marketing/guide`;
}

export function mapSignupError(status: number, message: string): string {
  if (status === 409) {
    if (/email/i.test(message)) {
      return "Этот email уже зарегистрирован. Войдите или используйте другой email.";
    }
    if (/slug/i.test(message)) {
      return "Такой адрес организации (slug) уже занят. Выберите другой.";
    }
    if (/Idempotency/i.test(message)) {
      return "Повторная отправка формы с другими данными отклонена. Обновите страницу и попробуйте снова.";
    }
    return message || "Конфликт данных при регистрации.";
  }
  if (status === 403) {
    return "Самостоятельная регистрация сейчас отключена. Обратитесь к оператору Flexity.";
  }
  if (status === 503) {
    return "Регистрация временно недоступна (конфигурация провайдера). Попробуйте позже.";
  }
  if (status === 422) {
    return "Проверьте поля формы. Лишние или некорректные значения не принимаются.";
  }
  return message || "Не удалось завершить регистрацию.";
}
