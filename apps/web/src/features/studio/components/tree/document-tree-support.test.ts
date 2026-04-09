import assert from "node:assert/strict";
import test from "node:test";

import {
  hasSelectedDescendant,
  resolveInitialNodeExpandedState,
  resolveNodeExpandedState,
} from "@/features/studio/components/tree/document-tree-support";

const selectionA = Symbol("selection-a");
const selectionB = Symbol("selection-b");
const selectionC = Symbol("selection-c");
const selectionD = Symbol("selection-d");
const selectionE = Symbol("selection-e");

test("hasSelectedDescendant only matches descendants, not the node itself", () => {
  assert.equal(hasSelectedDescendant("设定", "设定/世界观.md"), true);
  assert.equal(hasSelectedDescendant("设定", "设定"), false);
  assert.equal(hasSelectedDescendant("设定", "大纲/总大纲.md"), false);
});

test("resolveInitialNodeExpandedState keeps top-level setting open and expands selected ancestors", () => {
  assert.equal(
    resolveInitialNodeExpandedState({
      depth: 0,
      nodePath: "设定",
      selectedPath: null,
    }),
    true,
  );
  assert.equal(
    resolveInitialNodeExpandedState({
      depth: 0,
      nodePath: "附录",
      selectedPath: "附录/灵感碎片.md",
    }),
    true,
  );
  assert.equal(
    resolveInitialNodeExpandedState({
      depth: 0,
      nodePath: "附录",
      selectedPath: null,
    }),
    false,
  );
});

test("resolveNodeExpandedState lets selected ancestors auto-open without blocking manual collapse", () => {
  assert.equal(
    resolveNodeExpandedState({
      collapsedSelectionSignal: null,
      manualExpanded: false,
      nodePath: "设定",
      selectedPath: "设定/人物.md",
      selectedPathSignal: selectionA,
    }),
    true,
  );
  assert.equal(
    resolveNodeExpandedState({
      collapsedSelectionSignal: selectionB,
      manualExpanded: false,
      nodePath: "设定",
      selectedPath: "设定/世界观.md",
      selectedPathSignal: selectionB,
    }),
    false,
  );
  assert.equal(
    resolveNodeExpandedState({
      collapsedSelectionSignal: null,
      manualExpanded: true,
      nodePath: "设定",
      selectedPath: "附录/灵感碎片.md",
      selectedPathSignal: selectionC,
    }),
    true,
  );
  assert.equal(
    resolveNodeExpandedState({
      collapsedSelectionSignal: null,
      manualExpanded: false,
      nodePath: "设定",
      selectedPath: "附录/灵感碎片.md",
      selectedPathSignal: selectionD,
    }),
    false,
  );
  assert.equal(
    resolveNodeExpandedState({
      collapsedSelectionSignal: selectionB,
      manualExpanded: false,
      nodePath: "设定",
      selectedPath: "设定/世界观.md",
      selectedPathSignal: selectionE,
    }),
    true,
  );
});
