/**
 * Run: npx tsx src/workspace/crmPipelineBoardHelpers.test.ts
 */
import assert from "node:assert/strict";
import type { PipelineStage, WorkItem } from "../types/workflows";
import {
  filterWorkItemsForBoardView,
  filterWorkItemsForListView,
  groupWorkItemsByStage,
  readCardDensity,
  readDisplayMode,
  resolveListStageFilter,
  shouldShowActiveBoardSection,
  shouldShowTerminalBoardSection,
  sortWorkItemsByUpdatedAt,
  splitPipelineStages,
  writeCardDensity,
  writeDisplayMode,
  writeListStageFilter,
  CRM_CARD_DENSITY_STORAGE_KEY,
  CRM_DISPLAY_MODE_STORAGE_KEY,
  CRM_LIST_STAGE_FILTER_STORAGE_KEY,
} from "./crmPipelineBoardHelpers";

const stages: PipelineStage[] = [
  {
    id: "s-new",
    code: "new_lead",
    name: "Новый лид",
    sort_order: 10,
    is_terminal: false,
  },
  {
    id: "s-rejected",
    code: "rejected",
    name: "Отказ",
    sort_order: 80,
    is_terminal: true,
  },
];

const rejectedItem = {
  id: "wi-1",
  stage_id: "s-rejected",
  status: "lost",
  custom_fields: { disposition: "spam" },
} as WorkItem;

const activeItem = {
  id: "wi-2",
  stage_id: "s-new",
  status: "in_progress",
  custom_fields: {},
} as WorkItem;

const grouped = groupWorkItemsByStage(stages, [rejectedItem, activeItem]);
assert.equal(grouped.byStageId.get("s-rejected")?.length, 1);
assert.equal(grouped.byStageId.get("s-new")?.length, 1);
assert.equal(grouped.orphans.length, 0);

const split = splitPipelineStages(stages);
assert.equal(split.activeStages.length, 1);
assert.equal(split.terminalStages.length, 1);
assert.equal(split.terminalStages[0]?.code, "rejected");

const activeFiltered = filterWorkItemsForBoardView(
  [rejectedItem, activeItem],
  stages,
  "active",
);
assert.equal(activeFiltered.length, 1);
assert.equal(activeFiltered[0]?.id, "wi-2");

const closedFiltered = filterWorkItemsForBoardView(
  [rejectedItem, activeItem],
  stages,
  "closed",
);
assert.equal(closedFiltered.length, 1);
assert.equal(closedFiltered[0]?.id, "wi-1");

const allFiltered = filterWorkItemsForBoardView(
  [rejectedItem, activeItem],
  stages,
  "all",
);
assert.equal(allFiltered.length, 2);

const sorted = sortWorkItemsByUpdatedAt([
  { ...activeItem, updated_at: "2026-01-01T00:00:00Z" } as WorkItem,
  { ...rejectedItem, updated_at: "2026-06-01T00:00:00Z" } as WorkItem,
]);
assert.equal(sorted[0]?.id, "wi-1");

const acceptedStage = {
  id: "s-accepted",
  code: "accepted",
  name: "Согласовано",
  sort_order: 70,
  is_terminal: false,
} as PipelineStage;

const stagesWithAccepted = [...stages, acceptedStage];
const acceptedItem = {
  id: "wi-3",
  stage_id: "s-accepted",
  status: "in_progress",
  custom_fields: {},
} as WorkItem;

const listActiveAccepted = filterWorkItemsForListView(
  [rejectedItem, activeItem, acceptedItem],
  stagesWithAccepted,
  "active",
  "s-accepted",
);
assert.equal(listActiveAccepted.length, 1);
assert.equal(listActiveAccepted[0]?.id, "wi-3");

const listClosedRejected = filterWorkItemsForListView(
  [rejectedItem, activeItem],
  stages,
  "closed",
  "s-rejected",
);
assert.equal(listClosedRejected.length, 1);
assert.equal(listClosedRejected[0]?.id, "wi-1");

assert.equal(resolveListStageFilter(stages, "s-new"), "s-new");
assert.equal(resolveListStageFilter(stages, "missing-stage"), "all");

assert.equal(shouldShowActiveBoardSection("active"), true);
assert.equal(shouldShowActiveBoardSection("closed"), false);
assert.equal(shouldShowActiveBoardSection("all"), true);

assert.equal(shouldShowTerminalBoardSection("active"), false);
assert.equal(shouldShowTerminalBoardSection("closed"), true);
assert.equal(shouldShowTerminalBoardSection("all"), true);

const storage = globalThis.localStorage;
if (storage) {
  storage.removeItem(CRM_CARD_DENSITY_STORAGE_KEY);
  assert.equal(readCardDensity(), "comfortable");
  writeCardDensity("compact");
  assert.equal(readCardDensity(), "compact");
  storage.removeItem(CRM_CARD_DENSITY_STORAGE_KEY);

  storage.removeItem(CRM_DISPLAY_MODE_STORAGE_KEY);
  assert.equal(readDisplayMode(), "board");
  writeDisplayMode("list");
  assert.equal(readDisplayMode(), "list");
  storage.removeItem(CRM_DISPLAY_MODE_STORAGE_KEY);

  storage.removeItem(CRM_LIST_STAGE_FILTER_STORAGE_KEY);
  assert.equal(resolveListStageFilter(stages), "all");
  writeListStageFilter("s-new");
  assert.equal(resolveListStageFilter(stages), "s-new");
  assert.equal(resolveListStageFilter(stages, "gone"), "all");
  storage.removeItem(CRM_LIST_STAGE_FILTER_STORAGE_KEY);
}

console.log("crmPipelineBoardHelpers.test.ts: all assertions passed");
