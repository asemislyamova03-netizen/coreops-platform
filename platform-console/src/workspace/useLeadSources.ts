import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { getTenantLeadSources } from "../api/leadSources";
import { buildLeadSourceLabelMap } from "./leadSourceHelpers";

export function useLeadSources(tenantId: string | null) {
  const query = useQuery({
    queryKey: ["workspace-lead-sources", tenantId],
    queryFn: () => getTenantLeadSources(tenantId!),
    enabled: Boolean(tenantId),
    staleTime: 5 * 60 * 1000,
  });

  const labelMap = useMemo(
    () => buildLeadSourceLabelMap(query.data ?? []),
    [query.data],
  );

  return {
    sources: query.data ?? [],
    labelMap,
    isLoading: query.isLoading,
    isError: query.isError,
  };
}
