let activeWorkspaceTenantId: string | null = null;

export function setWorkspaceTenantId(tenantId: string | null): void {
  activeWorkspaceTenantId = tenantId;
}

export function getWorkspaceTenantId(): string | null {
  return activeWorkspaceTenantId;
}
