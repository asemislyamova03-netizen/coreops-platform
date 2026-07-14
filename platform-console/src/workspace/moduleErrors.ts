import { ApiError } from "../api/client";

const MODULE_DISABLED_PATTERNS = [
  /^Module '([^']+)' is not enabled/,
  /^Module '([^']+)' is not configured for tenant/,
];

export function getDisabledModuleCode(error: unknown): string | null {
  if (!(error instanceof ApiError)) return null;
  if (error.status !== 403) return null;

  for (const pattern of MODULE_DISABLED_PATTERNS) {
    const match = error.message.match(pattern);
    if (match?.[1]) {
      return match[1];
    }
  }

  return null;
}

export function isModuleDisabledError(error: unknown): boolean {
  return getDisabledModuleCode(error) !== null;
}

export function moduleDisabledMessage(moduleCode: string): string {
  const labels: Record<string, string> = {
    finance: "Финансовый модуль отключён для этой организации.",
    documents: "Модуль документов отключён для этой организации.",
    marketing: "Модуль маркетинга отключён для этой организации.",
  };
  return labels[moduleCode] ?? `Модуль «${moduleCode}» отключён для этой организации.`;
}

export function firstBlockingError(
  ...errors: Array<unknown | null | undefined>
): unknown | null {
  for (const error of errors) {
    if (error && !isModuleDisabledError(error)) {
      return error;
    }
  }
  return null;
}

export function isModuleDisabled(
  moduleCode: string,
  ...errors: Array<unknown | null | undefined>
): boolean {
  return errors.some((error) => getDisabledModuleCode(error) === moduleCode);
}
