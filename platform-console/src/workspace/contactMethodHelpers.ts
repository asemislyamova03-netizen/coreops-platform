import type { ContactMethod, ContactMethodCreate, ContactMethodType } from "../types/party";

const PHONE_TYPES = new Set(["phone", "mobile"]);
const EMAIL_TYPES = new Set(["email"]);

export function getPhoneFromContactMethods(methods: ContactMethod[]): string {
  const found = methods.find((method) => PHONE_TYPES.has(method.method_type));
  return found?.value ?? "";
}

export function getEmailFromContactMethods(methods: ContactMethod[]): string {
  const found = methods.find((method) => EMAIL_TYPES.has(method.method_type));
  return found?.value ?? "";
}

function toContactMethodCreate(method: ContactMethod): ContactMethodCreate {
  return {
    method_type: method.method_type as ContactMethodType,
    value: method.value,
    label: method.label,
    is_primary: method.is_primary,
  };
}

/** Preserve non-phone/email methods when PATCH replaces the full contact_methods list. */
export function mergePhoneEmailContactMethods(
  existing: ContactMethod[],
  phone: string,
  email: string,
): ContactMethodCreate[] {
  const others = existing
    .filter(
      (method) => !PHONE_TYPES.has(method.method_type) && !EMAIL_TYPES.has(method.method_type),
    )
    .map(toContactMethodCreate);

  const result: ContactMethodCreate[] = [...others];
  const trimmedPhone = phone.trim();
  const trimmedEmail = email.trim();

  if (trimmedPhone) {
    const existingPhone = existing.find((method) => PHONE_TYPES.has(method.method_type));
    result.push({
      method_type: (existingPhone?.method_type ?? "phone") as ContactMethodType,
      value: trimmedPhone,
      label: existingPhone?.label ?? null,
      is_primary: existingPhone?.is_primary ?? result.length === 0,
    });
  }

  if (trimmedEmail) {
    const existingEmail = existing.find((method) => EMAIL_TYPES.has(method.method_type));
    result.push({
      method_type: "email",
      value: trimmedEmail,
      label: existingEmail?.label ?? null,
      is_primary: existingEmail?.is_primary ?? result.length === 0,
    });
  }

  if (result.length > 0 && !result.some((method) => method.is_primary)) {
    result[0] = { ...result[0], is_primary: true };
  }

  return result;
}

export function contactMethodsChanged(
  existing: ContactMethod[],
  displayName: string,
  originalDisplayName: string,
  phone: string,
  email: string,
): boolean {
  if (displayName.trim() !== originalDisplayName.trim()) {
    return true;
  }
  return (
    phone.trim() !== getPhoneFromContactMethods(existing).trim() ||
    email.trim() !== getEmailFromContactMethods(existing).trim()
  );
}
