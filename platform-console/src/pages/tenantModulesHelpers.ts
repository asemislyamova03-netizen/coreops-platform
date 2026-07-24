import type {
  ModuleDefinition,
  ModuleStatus,
  TenantModule,
  TenantModuleRow,
} from "../types/module";

const ACTIVE_STATUSES: ReadonlySet<ModuleStatus> = new Set(["enabled", "trial"]);

export function isModuleActive(status: ModuleStatus): boolean {
  return ACTIVE_STATUSES.has(status);
}

export function requiredDependenciesOf(
  definition: ModuleDefinition | undefined,
): string[] {
  const required = definition?.dependencies_json?.required ?? [];
  return Array.isArray(required) ? required.map(String) : [];
}

export function activeDependentsOf(
  moduleCode: string,
  registry: ModuleDefinition[],
  tenantModules: TenantModule[],
): string[] {
  const statusByCode = new Map(
    tenantModules.map((row) => [row.module_code, row.status] as const),
  );
  const dependents: string[] = [];
  for (const definition of registry) {
    if (!requiredDependenciesOf(definition).includes(moduleCode)) {
      continue;
    }
    const status = statusByCode.get(definition.code);
    if (status && isModuleActive(status)) {
      dependents.push(definition.code);
    }
  }
  return dependents.sort();
}

export function buildTenantModuleRows(
  tenantModules: TenantModule[],
  registry: ModuleDefinition[],
): TenantModuleRow[] {
  const byCode = new Map(registry.map((item) => [item.code, item] as const));
  return tenantModules.map((row) => {
    const definition = byCode.get(row.module_code);
    return {
      ...row,
      name: definition?.name ?? row.module_code,
      description: definition?.description ?? null,
      required_dependencies: requiredDependenciesOf(definition),
      active_dependents: activeDependentsOf(row.module_code, registry, tenantModules),
    };
  });
}

export function disableBlockedMessage(moduleCode: string, dependents: string[]): string {
  return (
    `Нельзя отключить «${moduleCode}»: его требуют активные модули: ${dependents.join(", ")}. ` +
    "Сначала отключите зависимые модули."
  );
}
