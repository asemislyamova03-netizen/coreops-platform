import type { LeadSource } from "../types/leadSources";

const LEGACY_SOURCE_ALIASES: Record<string, string> = {
  public_demo_form: "website_demo",
};

export function resolveLeadSourceLabel(
  sources: LeadSource[],
  code: string | null | undefined,
): string | null {
  if (!code) {
    return null;
  }
  const canonical = LEGACY_SOURCE_ALIASES[code] ?? code;
  const match = sources.find((item) => item.code === canonical);
  return match?.label_ru ?? code;
}

export function buildLeadSourceLabelMap(sources: LeadSource[]): Map<string, string> {
  const map = new Map<string, string>();
  for (const item of sources) {
    map.set(item.code, item.label_ru);
  }
  for (const [legacy, canonical] of Object.entries(LEGACY_SOURCE_ALIASES)) {
    const label = map.get(canonical);
    if (label) {
      map.set(legacy, label);
    }
  }
  return map;
}
