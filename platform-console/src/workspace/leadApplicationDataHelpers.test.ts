/**
 * Run: npx tsx src/workspace/leadApplicationDataHelpers.test.ts
 */

import assert from "node:assert/strict";
import {
  buildLeadApplicationDataView,
  type LeadApplicationDataView,
} from "./leadApplicationDataHelpers";

function rowValues(view: LeadApplicationDataView): Record<string, string> {
  return Object.fromEntries(view.rows.map((row) => [row.key, row.value]));
}

function rowKeys(view: LeadApplicationDataView): string[] {
  return view.rows.map((row) => row.key);
}

function test(name: string, fn: () => void): void {
  try {
    fn();
    console.log(`ok - ${name}`);
  } catch (error) {
    console.error(`fail - ${name}`);
    throw error;
  }
}

test("hides block for manual lead without fields", () => {
  const view = buildLeadApplicationDataView({
    source: "manual",
    custom_fields: {},
  });
  assert.equal(view.shouldShow, false);
  assert.equal(view.rows.length, 0);
});

test("shows block for source website_demo", () => {
  const view = buildLeadApplicationDataView({
    source: "website_demo",
    custom_fields: {},
  }, { sourceLabel: "Сайт / demo" });
  assert.equal(view.shouldShow, true);
  assert.equal(rowValues(view).source, "Сайт / demo");
});

test("extracts form/page/UTM/consent", () => {
  const view = buildLeadApplicationDataView({
    source: "website_demo",
    custom_fields: {
      form_name: "demo_lead",
      page_url: "https://flexity.asia/demo",
      utm_source: "ig",
      utm_medium: "social",
      utm_campaign: "spring",
      utm_content: "reel1",
      utm_term: "crm",
      consent_accepted_at: "2026-07-13T10:00:00Z",
      referrer: "https://instagram.com/",
    },
  });
  assert.equal(view.shouldShow, true);
  const values = rowValues(view);
  assert.equal(values.form_name, "demo_lead");
  assert.equal(values.page_url, "https://flexity.asia/demo");
  assert.equal(values.utm_source, "ig");
  assert.equal(values.utm_medium, "social");
  assert.equal(values.utm_campaign, "spring");
  assert.equal(values.utm_content, "reel1");
  assert.equal(values.utm_term, "crm");
  assert.ok(values.consent_at);
  assert.equal(values.referrer, "https://instagram.com/");
});

test("hides empty UTM values", () => {
  const view = buildLeadApplicationDataView({
    source: "website_demo",
    custom_fields: {
      form_name: "demo_lead",
      utm_source: "  ",
      utm_medium: null,
      utm_campaign: "",
    },
  });
  const keys = rowKeys(view);
  assert.ok(!keys.includes("utm_source"));
  assert.ok(!keys.includes("utm_medium"));
  assert.ok(!keys.includes("utm_campaign"));
  assert.ok(keys.includes("form_name"));
});

test("exact match note produces safe text without raw ids", () => {
  const view = buildLeadApplicationDataView({
    source: "website_demo",
    custom_fields: {
      match_note: "exact_match",
      possible_match_party_ids: ["uuid-1", "uuid-2"],
    },
  });
  assert.equal(rowValues(view).match, "Контакт найден автоматически");
  assert.ok(!rowKeys(view).includes("possible_match_party_ids"));
  const serialized = JSON.stringify(view);
  assert.ok(!serialized.includes("uuid-1"));
  assert.ok(!serialized.includes("uuid-2"));
});

test("weak match count produces safe text", () => {
  const view = buildLeadApplicationDataView({
    source: "website_demo",
    custom_fields: {
      possible_match_count: 2,
      possible_match_party_ids: ["a", "b"],
    },
  });
  assert.equal(rowValues(view).match, "Есть возможное совпадение: 2");
});

test("possible_match_party_ids are not exposed as display row", () => {
  const view = buildLeadApplicationDataView({
    source: "manual",
    custom_fields: {
      form_name: "x",
      possible_match_party_ids: ["secret-id"],
    },
  });
  assert.ok(!rowKeys(view).includes("possible_match_party_ids"));
  assert.ok(!JSON.stringify(view).includes("secret-id"));
});

test("handles unknown/non-string values safely", () => {
  const view = buildLeadApplicationDataView({
    source: "manual",
    custom_fields: {
      form_name: { nested: true },
      page_url: ["arr"],
      utm_source: 42,
      possible_match_count: "3",
    },
  });
  assert.equal(view.shouldShow, true);
  const values = rowValues(view);
  assert.equal(values.utm_source, "42");
  assert.equal(values.match, "Есть возможное совпадение: 3");
  assert.ok(!rowKeys(view).includes("form_name"));
  assert.ok(!rowKeys(view).includes("page_url"));
});

console.log("All leadApplicationDataHelpers tests passed.");
