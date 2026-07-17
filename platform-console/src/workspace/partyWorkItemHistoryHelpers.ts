/**
 * Helpers for LeadDetailModal party work-item history (E4).
 * Run: npx tsx src/workspace/partyWorkItemHistoryHelpers.test.ts
 */

import type { WorkItem } from "../types/workflows";

export const PARTY_HISTORY_FETCH_LIMIT = 20;
export const PARTY_HISTORY_DISPLAY_LIMIT = 5;

/** Exclude current WorkItem and keep top N (API already sorts updated_at DESC). */
export function selectPartyHistoryItems(
  items: WorkItem[],
  currentWorkItemId: string,
  displayLimit: number = PARTY_HISTORY_DISPLAY_LIMIT,
): WorkItem[] {
  return items.filter((item) => item.id !== currentWorkItemId).slice(0, displayLimit);
}
