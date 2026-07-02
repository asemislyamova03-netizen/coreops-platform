import { useQuery } from "@tanstack/react-query";
import {
  createContext,
  useContext,
  useMemo,
  type ReactNode,
} from "react";
import { getTenantLabels } from "../api/labels";
import { DEFAULT_WORKSPACE_LABELS, type TenantLabelsConfig } from "../types/labels";
import {
  entityLabel,
  normalizeTenantLabels,
  partyRoleLabel,
  pickClientsSectionPartyRoleKey,
  pickDefaultPartyRole,
} from "./labelHelpers";

interface WorkspaceLabelsContextValue {
  labels: TenantLabelsConfig;
  isLoading: boolean;
  isError: boolean;
  entityLabel: (key: string, fallback: string) => string;
  partyRoleLabel: (key: string, fallback: string) => string;
  defaultPartyRole: string;
  crmSectionTitle: string;
  clientsSectionTitle: string;
}

const WorkspaceLabelsContext = createContext<WorkspaceLabelsContextValue | null>(null);

export function WorkspaceLabelsProvider({
  tenantId,
  children,
}: {
  tenantId: string | null;
  children: ReactNode;
}) {
  const query = useQuery({
    queryKey: ["workspace-labels", tenantId],
    queryFn: () => getTenantLabels(tenantId!),
    enabled: Boolean(tenantId),
    staleTime: 5 * 60 * 1000,
  });

  const labels = useMemo(
    () => normalizeTenantLabels(query.data),
    [query.data],
  );

  const value = useMemo<WorkspaceLabelsContextValue>(() => {
    const entity = (key: string, fallback: string) => entityLabel(labels, key, fallback);
    const role = (key: string, fallback: string) => partyRoleLabel(labels, key, fallback);

    const workItem = entity("work_item", "Заявка");
    const pipeline = entity("pipeline", "Воронка");
    const party = entity("party", "Контрагент");
    const defaultPartyRole = pickDefaultPartyRole(labels);
    const sectionRoleKey = pickClientsSectionPartyRoleKey(labels);
    const sectionRole = role(sectionRoleKey, sectionRoleKey);

    return {
      labels,
      isLoading: query.isLoading,
      isError: query.isError,
      entityLabel: entity,
      partyRoleLabel: role,
      defaultPartyRole,
      crmSectionTitle: `${workItem} / ${pipeline}`,
      clientsSectionTitle: `${sectionRole} / ${party}`,
    };
  }, [labels, query.isLoading, query.isError]);

  return (
    <WorkspaceLabelsContext.Provider value={value}>
      {children}
    </WorkspaceLabelsContext.Provider>
  );
}

export function useWorkspaceLabels(): WorkspaceLabelsContextValue {
  const ctx = useContext(WorkspaceLabelsContext);
  if (!ctx) {
    return {
      labels: DEFAULT_WORKSPACE_LABELS,
      isLoading: false,
      isError: false,
      entityLabel: (key, fallback) => entityLabel(DEFAULT_WORKSPACE_LABELS, key, fallback),
      partyRoleLabel: (key, fallback) =>
        partyRoleLabel(DEFAULT_WORKSPACE_LABELS, key, fallback),
      defaultPartyRole: pickDefaultPartyRole(DEFAULT_WORKSPACE_LABELS),
      crmSectionTitle: "Заявки / Воронка",
      clientsSectionTitle: "Родители / Контрагенты",
    };
  }
  return ctx;
}
