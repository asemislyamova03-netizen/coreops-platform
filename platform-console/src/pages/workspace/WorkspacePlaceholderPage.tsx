import { Alert } from "../../components/ui/Alert";
import {
  membershipRoleLabel,
  useTenantWorkspace,
} from "../../auth/TenantWorkspaceContext";

interface WorkspacePlaceholderPageProps {
  title: string;
  description: string;
  plannedStage: string;
}

export function WorkspacePlaceholderPage({
  title,
  description,
  plannedStage,
}: WorkspacePlaceholderPageProps) {
  const { tenant, membership } = useTenantWorkspace();

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>{title}</h1>
          <p className="muted">{description}</p>
        </div>
      </div>

      <Alert variant="info">
        Раздел в разработке ({plannedStage}). Сейчас доступен только shell tenant workspace без
        бизнес-логики.
      </Alert>

      <div className="panel workspace-context-panel">
        <h3>Tenant context</h3>
        <dl className="detail-list">
          <dt>Tenant</dt>
          <dd>{tenant?.tenantName}</dd>
          <dt>Slug</dt>
          <dd>
            <code>{tenant?.tenantSlug}</code>
          </dd>
          <dt>Tenant ID</dt>
          <dd>
            <code>{tenant?.tenantId}</code>
          </dd>
          <dt>Your role</dt>
          <dd>{membershipRoleLabel(membership?.role ?? tenant?.role ?? null)}</dd>
        </dl>
      </div>
    </div>
  );
}
