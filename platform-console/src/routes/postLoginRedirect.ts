export type UserHomeContext = {
  isProvider: boolean;
  tenantSlugs: string[];
  fallbackPath: string;
};

const BLOCKED_PATHS = new Set([
  "/login",
  "/access-denied",
  "/workspace-access-denied",
]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function buildPathFromLocation(from: unknown): string | null {
  if (!isRecord(from)) return null;

  const pathname = from.pathname;
  if (typeof pathname !== "string") return null;

  const search = typeof from.search === "string" ? from.search : "";
  const hash = typeof from.hash === "string" ? from.hash : "";

  return `${pathname}${search}${hash}`;
}

function pathnameOnly(path: string): string {
  return path.split(/[?#]/)[0] ?? path;
}

function isSafeInternalPath(path: string): boolean {
  if (!path.startsWith("/")) return false;
  if (path.startsWith("//")) return false;
  if (/^[a-zA-Z][a-zA-Z\d+\-.]*:/.test(path)) return false;

  const pathname = pathnameOnly(path);
  if (BLOCKED_PATHS.has(pathname)) return false;
  if (pathname.startsWith("/console")) return false;

  return true;
}

function isTenantsPath(pathname: string): boolean {
  return pathname === "/tenants" || pathname.startsWith("/tenants/");
}

function isWorkspacePath(pathname: string): boolean {
  return pathname === "/workspace" || pathname.startsWith("/workspace/");
}

function workspaceTenantSlug(pathname: string): string | null {
  const match = pathname.match(/^\/workspace\/([^/]+)/);
  return match?.[1] ?? null;
}

export function resolvePostLoginRedirect(
  from: unknown,
  context: UserHomeContext,
): string {
  const candidate = buildPathFromLocation(from);
  if (!candidate || !isSafeInternalPath(candidate)) {
    return context.fallbackPath;
  }

  const pathname = pathnameOnly(candidate);

  if (context.isProvider) {
    if (isTenantsPath(pathname) || isWorkspacePath(pathname)) {
      return candidate;
    }
    return context.fallbackPath;
  }

  if (!isWorkspacePath(pathname)) {
    return context.fallbackPath;
  }

  const slug = workspaceTenantSlug(pathname);
  if (!slug || !context.tenantSlugs.includes(slug)) {
    return context.fallbackPath;
  }

  return candidate;
}
