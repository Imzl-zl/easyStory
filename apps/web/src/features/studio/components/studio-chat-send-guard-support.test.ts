import assert from "node:assert/strict";
import test from "node:test";

import { runStudioSendOnce } from "./studio-chat-send-guard-support";

test("studio send guard prevents concurrent send attempts until the first one settles", async () => {
  const guard = { current: false };
  const started: string[] = [];
  let releaseFirst: (() => void) | null = null;

  const firstAttempt = runStudioSendOnce(guard, async () => {
    started.push("first");
    await new Promise<void>((resolve) => {
      releaseFirst = resolve;
    });
    return true;
  });
  const secondAttempt = await runStudioSendOnce(guard, async () => {
    started.push("second");
    return true;
  });

  assert.equal(secondAttempt, false);
  assert.deepEqual(started, ["first"]);
  assert.equal(guard.current, true);

  releaseFirst?.();
  assert.equal(await firstAttempt, true);
  assert.equal(guard.current, false);

  const thirdAttempt = await runStudioSendOnce(guard, async () => {
    started.push("third");
    return true;
  });

  assert.equal(thirdAttempt, true);
  assert.deepEqual(started, ["first", "third"]);
});

test("studio send guard releases the claim after action throws", async () => {
  const guard = { current: false };
  const expectedError = new Error("send failed");

  await assert.rejects(
    () => runStudioSendOnce(guard, async () => {
      throw expectedError;
    }),
    /send failed/,
  );
  assert.equal(guard.current, false);

  const nextAttempt = await runStudioSendOnce(guard, async () => true);
  assert.equal(nextAttempt, true);
});
