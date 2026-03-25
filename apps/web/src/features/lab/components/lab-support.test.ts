import assert from "node:assert/strict";
import test from "node:test";

import type { AnalysisSummary } from "@/lib/api/types";
import {
  buildLabAnalysisSummary,
  buildLabAnalysisListOptions,
  buildLabCreatePayload,
  formatLabAnalysisTime,
  matchesLabAnalysisListOptions,
  prependLabAnalysisSummary,
  resolveActiveLabAnalysisId,
  resolveNextLabSelectedIdAfterDelete,
} from "./lab-support";

test("buildLabAnalysisListOptions normalizes Lab filters to backend query fields", () => {
  assert.deepEqual(
    buildLabAnalysisListOptions({
      analysisType: "all",
      contentId: "  ",
      generatedSkillKey: " skill.style.river ",
    }),
    {
      analysisType: undefined,
      contentId: undefined,
      generatedSkillKey: "skill.style.river",
    },
  );
});

test("buildLabCreatePayload trims optional fields and parses JSON objects", () => {
  assert.deepEqual(
    buildLabCreatePayload({
      analysisType: "style",
      generatedSkillKey: " skill.style.river ",
      result: '{ "summary": "ok" }',
      sourceTitle: " 风格样本 ",
      suggestions: '{ "next_step": "keep" }',
    }),
    {
      analysis_type: "style",
      generated_skill_key: "skill.style.river",
      result: { summary: "ok" },
      source_title: "风格样本",
      suggestions: { next_step: "keep" },
    },
  );
});

test("buildLabCreatePayload rejects non-object result JSON", () => {
  assert.throws(
    () =>
      buildLabCreatePayload({
        analysisType: "plot",
        generatedSkillKey: "",
        result: '["bad"]',
        sourceTitle: "剧情样本",
        suggestions: "",
      }),
    /result 必须是 JSON object/,
  );
});

test("buildLabCreatePayload rejects empty result object", () => {
  assert.throws(
    () =>
      buildLabCreatePayload({
        analysisType: "plot",
        generatedSkillKey: "",
        result: "{}",
        sourceTitle: "剧情样本",
        suggestions: "",
      }),
    /result 不能为空/,
  );
});

test("matchesLabAnalysisListOptions compares summary fields against active filters", () => {
  const analysis = createAnalysisSummary({
    analysis_type: "style",
    content_id: "content-1",
    generated_skill_key: "skill.style.river",
  });

  assert.equal(
    matchesLabAnalysisListOptions(analysis, {
      analysisType: "style",
      contentId: "content-1",
      generatedSkillKey: "skill.style.river",
    }),
    true,
  );
  assert.equal(
    matchesLabAnalysisListOptions(analysis, {
      analysisType: "plot",
    }),
    false,
  );
});

test("buildLabAnalysisSummary keeps detail/list shared fields aligned", () => {
  assert.deepEqual(
    buildLabAnalysisSummary({
      analysis_type: "style",
      content_id: "content-1",
      created_at: "2026-03-25T06:08:00Z",
      generated_skill_key: "skill.style.river",
      id: "analysis-2",
      project_id: "project-1",
      source_title: "风格分析",
    }),
    createAnalysisSummary({
      analysis_type: "style",
      content_id: "content-1",
      generated_skill_key: "skill.style.river",
      id: "analysis-2",
      source_title: "风格分析",
    }),
  );
});

test("prependLabAnalysisSummary keeps latest created analysis at the top without duplicates", () => {
  const analyses = [
    createAnalysisSummary({ id: "analysis-1" }),
    createAnalysisSummary({ id: "analysis-2" }),
  ];

  assert.deepEqual(
    prependLabAnalysisSummary(analyses, createAnalysisSummary({ id: "analysis-2", source_title: "更新后的分析" })).map(
      (analysis) => analysis.id,
    ),
    ["analysis-2", "analysis-1"],
  );
});

test("resolveActiveLabAnalysisId and delete fallback keep selection stable", () => {
  const analyses = [
    createAnalysisSummary({ id: "analysis-1" }),
    createAnalysisSummary({ id: "analysis-2" }),
    createAnalysisSummary({ id: "analysis-3" }),
  ];

  assert.equal(resolveActiveLabAnalysisId(analyses, "analysis-2"), "analysis-2");
  assert.equal(resolveActiveLabAnalysisId(analyses, "missing"), "analysis-1");
  assert.equal(resolveNextLabSelectedIdAfterDelete(analyses, "analysis-2", "analysis-2"), "analysis-3");
  assert.equal(resolveNextLabSelectedIdAfterDelete(analyses, "analysis-3", "analysis-3"), "analysis-2");
  assert.equal(resolveNextLabSelectedIdAfterDelete(analyses, "analysis-1", "analysis-2"), "analysis-1");
});

test("formatLabAnalysisTime renders UTC consistently", () => {
  assert.equal(formatLabAnalysisTime("2026-03-25T06:08:00Z"), "03/25 06:08 UTC");
});

function createAnalysisSummary(overrides: Partial<AnalysisSummary> = {}): AnalysisSummary {
  return {
    analysis_type: "plot",
    content_id: null,
    created_at: "2026-03-25T06:08:00Z",
    generated_skill_key: null,
    id: "analysis-1",
    project_id: "project-1",
    source_title: "分析记录",
    ...overrides,
  };
}
