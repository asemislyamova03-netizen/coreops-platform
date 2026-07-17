import type { PipelineStage, WorkItem } from "../types/workflows";

export type CrmBoardViewMode = "active" | "closed" | "all";

export type CrmCardDensity = "comfortable" | "compact";

export type CrmDisplayMode = "board" | "list";

export const CRM_CARD_DENSITY_STORAGE_KEY = "flexity.crm.cardDensity";

export const CRM_DISPLAY_MODE_STORAGE_KEY = "flexity.crm.displayMode";

export const CRM_LIST_STAGE_FILTER_STORAGE_KEY = "flexity.crm.listStageFilter";

/** `all` or a pipeline stage id */
export type CrmListStageFilter = "all" | string;

export const CRM_BOARD_VIEW_OPTIONS: ReadonlyArray<{
  value: CrmBoardViewMode;
  label: string;
}> = [
  { value: "active", label: "Активные" },
  { value: "closed", label: "Закрытые" },
  { value: "all", label: "Все" },
];

export const CRM_CARD_DENSITY_OPTIONS: ReadonlyArray<{
  value: CrmCardDensity;
  label: string;
}> = [
  { value: "comfortable", label: "Комфортный" },
  { value: "compact", label: "Компактный" },
];

export const CRM_DISPLAY_MODE_OPTIONS: ReadonlyArray<{
  value: CrmDisplayMode;
  label: string;
}> = [
  { value: "board", label: "Доска" },
  { value: "list", label: "Список" },
];

export function readCardDensity(): CrmCardDensity {
  try {
    const stored = localStorage.getItem(CRM_CARD_DENSITY_STORAGE_KEY);
    if (stored === "comfortable" || stored === "compact") {
      return stored;
    }
  } catch {
    // localStorage may be unavailable in some contexts
  }
  return "comfortable";
}

export function writeCardDensity(density: CrmCardDensity): void {
  try {
    localStorage.setItem(CRM_CARD_DENSITY_STORAGE_KEY, density);
  } catch {
    // ignore persistence errors
  }
}

export function readDisplayMode(): CrmDisplayMode {
  try {
    const stored = localStorage.getItem(CRM_DISPLAY_MODE_STORAGE_KEY);
    if (stored === "board" || stored === "list") {
      return stored;
    }
  } catch {
    // localStorage may be unavailable in some contexts
  }
  return "board";
}

export function writeDisplayMode(mode: CrmDisplayMode): void {
  try {
    localStorage.setItem(CRM_DISPLAY_MODE_STORAGE_KEY, mode);
  } catch {
    // ignore persistence errors
  }
}

export function readListStageFilterRaw(): string {
  try {
    return localStorage.getItem(CRM_LIST_STAGE_FILTER_STORAGE_KEY) ?? "all";
  } catch {
    return "all";
  }
}

export function resolveListStageFilter(
  stages: PipelineStage[],
  stored?: string,
): CrmListStageFilter {
  const value = stored ?? readListStageFilterRaw();
  if (value === "all") {
    return "all";
  }
  return stages.some((stage) => stage.id === value) ? value : "all";
}

export function writeListStageFilter(filter: CrmListStageFilter): void {
  try {
    localStorage.setItem(CRM_LIST_STAGE_FILTER_STORAGE_KEY, filter);
  } catch {
    // ignore persistence errors
  }
}

/**
 * Filters work items for CRM board/list view modes (E1.1 active / closed / all).
 */
export function filterWorkItemsForBoardView(
  workItems: WorkItem[],
  stages: PipelineStage[],
  boardView: CrmBoardViewMode,
): WorkItem[] {
  const stageById = new Map(stages.map((stage) => [stage.id, stage]));

  return workItems.filter((item) => {
    const stage = stageById.get(item.stage_id);
    if (!stage) {
      return boardView === "all";
    }
    if (boardView === "active") {
      return !stage.is_terminal;
    }
    if (boardView === "closed") {
      return stage.is_terminal;
    }
    return true;
  });
}

/**
 * List view: boardView filter first, then optional stage filter (E1.4).
 */
export function filterWorkItemsForListView(
  workItems: WorkItem[],
  stages: PipelineStage[],
  boardView: CrmBoardViewMode,
  stageFilter: CrmListStageFilter,
): WorkItem[] {
  const byBoardView = filterWorkItemsForBoardView(workItems, stages, boardView);
  if (stageFilter === "all") {
    return byBoardView;
  }
  return byBoardView.filter((item) => item.stage_id === stageFilter);
}

export function sortWorkItemsByUpdatedAt(workItems: WorkItem[]): WorkItem[] {
  return [...workItems].sort(
    (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime(),
  );
}

export function emptyTextForBoardView(
  boardView: CrmBoardViewMode,
  workItemLabel: string,
): string {
  const label = workItemLabel.toLowerCase();
  if (boardView === "active") {
    return `Нет активных ${label} в выбранном виде.`;
  }
  if (boardView === "closed") {
    return `Нет закрытых ${label}.`;
  }
  return `Нет ${label} в выбранном виде.`;
}

export function emptyTextForListView(
  boardView: CrmBoardViewMode,
  stageFilter: CrmListStageFilter,
  workItemLabel: string,
): string {
  if (stageFilter !== "all") {
    return "Нет лидов по выбранным фильтрам";
  }
  return emptyTextForBoardView(boardView, workItemLabel);
}

export interface GroupedWorkItems {
  byStageId: Map<string, WorkItem[]>;
  orphans: WorkItem[];
}

export function groupWorkItemsByStage(
  stages: PipelineStage[],
  workItems: WorkItem[],
): GroupedWorkItems {
  const byStageId = new Map<string, WorkItem[]>();
  for (const stage of stages) {
    byStageId.set(stage.id, []);
  }

  const orphans: WorkItem[] = [];
  for (const item of workItems) {
    const bucket = byStageId.get(item.stage_id);
    if (bucket) {
      bucket.push(item);
    } else {
      orphans.push(item);
    }
  }

  return { byStageId, orphans };
}

export function splitPipelineStages(stages: PipelineStage[]): {
  activeStages: PipelineStage[];
  terminalStages: PipelineStage[];
} {
  const sorted = [...stages].sort((a, b) => a.sort_order - b.sort_order);
  return {
    activeStages: sorted.filter((stage) => !stage.is_terminal),
    terminalStages: sorted.filter((stage) => stage.is_terminal),
  };
}

export function shouldShowActiveBoardSection(view: CrmBoardViewMode): boolean {
  return view === "active" || view === "all";
}

export function shouldShowTerminalBoardSection(view: CrmBoardViewMode): boolean {
  return view === "closed" || view === "all";
}

export function scrollToPipelineStage(stageCode: string): void {
  window.setTimeout(() => {
    const target = document.querySelector(
      `[data-stage-code="${stageCode}"]`,
    ) as HTMLElement | null;
    target?.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" });
  }, 150);
}
