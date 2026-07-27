import { NavLink, useParams } from "react-router-dom";
import { ui } from "../../../i18n/ruUi";

export function MarketingPageHeader({
  title,
  subtitle,
}: {
  title: string;
  subtitle: string;
}) {
  const { tenantSlug = "" } = useParams();
  const base = `/workspace/${tenantSlug}/marketing`;

  return (
    <div className="page-header">
      <div>
        <h1>{title}</h1>
        <p className="muted">{subtitle}</p>
        <nav className="workspace-quick-links" aria-label="Разделы маркетинга">
          <NavLink
            to={base}
            end
            className={({ isActive }) => (isActive ? "active" : undefined)}
          >
            {ui.marketingOverview}
          </NavLink>
          <NavLink
            to={`${base}/topics`}
            className={({ isActive }) => (isActive ? "active" : undefined)}
          >
            {ui.marketingTopics}
          </NavLink>
          <NavLink
            to={`${base}/packs`}
            className={({ isActive }) => (isActive ? "active" : undefined)}
          >
            {ui.marketingPacks}
          </NavLink>
          <NavLink
            to={`${base}/connections`}
            className={({ isActive }) => (isActive ? "active" : undefined)}
          >
            {ui.marketingConnections}
          </NavLink>
          <NavLink
            to={`${base}/plans`}
            className={({ isActive }) => (isActive ? "active" : undefined)}
          >
            {ui.marketingPlans}
          </NavLink>
          <NavLink
            to={`${base}/guide`}
            className={({ isActive }) => (isActive ? "active" : undefined)}
          >
            {ui.marketingGuide}
          </NavLink>
          <NavLink
            to={`${base}/rubrics`}
            className={({ isActive }) => (isActive ? "active" : undefined)}
          >
            {ui.marketingRubrics}
          </NavLink>
        </nav>
      </div>
    </div>
  );
}
