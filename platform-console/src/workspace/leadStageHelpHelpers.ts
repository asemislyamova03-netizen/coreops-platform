/**
 * Stage help copy for LeadDetailModal (E8-B).
 * Run: npx tsx src/workspace/leadStageHelpHelpers.test.ts
 */

export type LeadStageHelp = {
  stageCode: string;
  title: string;
  help: string;
};

const STAGE_HELP: Record<string, LeadStageHelp> = {
  accepted: {
    stageCode: "accepted",
    title: "Согласовано",
    help:
      "Клиент согласился на работу. Tenant создавать не обязательно: это может быть консультация, аудит, пилот или внедрение. Зафиксируйте условия и следующий шаг.",
  },
  converted_to_tenant: {
    stageCode: "converted_to_tenant",
    title: "Переведён в клиентский контур",
    help:
      "Используйте только когда рабочий tenant/workspace клиента реально создан. После этого лид считается завершённым как won, а работа уходит в delivery.",
  },
};

/** Return compact help for known sales stages; otherwise null. */
export function getLeadStageHelp(
  stageCode: string | null | undefined,
): LeadStageHelp | null {
  if (!stageCode) return null;
  return STAGE_HELP[stageCode] ?? null;
}
