import assert from "node:assert/strict";
import test from "node:test";

import { resolveFloatingPanelStyle } from "@/components/ui/floating-panel-support";

test("resolveFloatingPanelStyle clamps right aligned bottom panel within viewport", () => {
  const style = resolveFloatingPanelStyle(
    {
      bottom: 120,
      left: 24,
      right: 336,
      top: 80,
    },
    {
      height: 844,
      width: 390,
    },
    {
      align: "right",
      maxHeight: 640,
      preferredWidth: 576,
      side: "bottom",
      zIndex: 160,
    },
  );

  assert.equal(style.position, "fixed");
  assert.equal(style.left, 16);
  assert.equal(style.top, 128);
  assert.equal(style.width, 358);
  assert.equal(style.zIndex, 160);
  assert.equal(style.maxHeight, 640);
});

test("resolveFloatingPanelStyle uses top placement with bounded height", () => {
  const style = resolveFloatingPanelStyle(
    {
      bottom: 680,
      left: 820,
      right: 1120,
      top: 640,
    },
    {
      height: 720,
      width: 1280,
    },
    {
      align: "right",
      maxHeight: 480,
      preferredWidth: 352,
      side: "top",
    },
  );

  assert.equal(style.position, "fixed");
  assert.equal(style.left, 768);
  assert.equal(style.bottom, 88);
  assert.equal(style.width, 352);
  assert.equal(style.maxHeight, 480);
});

test("resolveFloatingPanelStyle keeps left aligned panel inside viewport", () => {
  const style = resolveFloatingPanelStyle(
    {
      bottom: 220,
      left: -40,
      right: 120,
      top: 180,
    },
    {
      height: 720,
      width: 360,
    },
    {
      align: "left",
      maxHeight: 320,
      preferredWidth: 280,
      side: "bottom",
    },
  );

  assert.equal(style.left, 16);
  assert.equal(style.width, 280);
  assert.equal(style.top, 228);
  assert.equal(style.maxHeight, 320);
});
