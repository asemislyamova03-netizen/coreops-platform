export function resolveHomePath(
  isProviderOwner: boolean,
  tenantSlugs: string[],
): string {
  if (isProviderOwner) {
    return "/tenants";
  }
  if (tenantSlugs.length > 0) {
    return `/workspace/${tenantSlugs[0]}/dashboard`;
  }
  return "/access-denied";
}
