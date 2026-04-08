import assert from "node:assert/strict";
import test from "node:test";
import { setImmediate as waitForImmediate } from "node:timers/promises";

import { submitStudioComposerMessage } from "./studio-chat-composer-support";

test("studio composer submit helper forwards trimmed message once", async () => {
  const sentMessages: string[] = [];

  const accepted = submitStudioComposerMessage({
    canChat: true,
    composerText: "  继续写这一段  ",
    isResponding: false,
    onSendMessage: (message) => {
      sentMessages.push(message);
      return true;
    },
  });

  await Promise.resolve();

  assert.equal(accepted, true);
  assert.deepEqual(sentMessages, ["继续写这一段"]);
});

test("studio composer submit helper blocks empty or unavailable sends", async () => {
  const sentMessages: string[] = [];

  assert.equal(
    submitStudioComposerMessage({
      canChat: true,
      composerText: "   ",
      isResponding: false,
      onSendMessage: (message) => {
        sentMessages.push(message);
        return true;
      },
    }),
    false,
  );
  assert.equal(
    submitStudioComposerMessage({
      canChat: false,
      composerText: "继续写",
      isResponding: false,
      onSendMessage: (message) => {
        sentMessages.push(message);
        return true;
      },
    }),
    false,
  );
  assert.equal(
    submitStudioComposerMessage({
      canChat: true,
      composerText: "继续写",
      isResponding: true,
      onSendMessage: (message) => {
        sentMessages.push(message);
        return true;
      },
    }),
    false,
  );

  await Promise.resolve();

  assert.deepEqual(sentMessages, []);
});

test("studio composer submit helper routes rejected sends to explicit error handler", async () => {
  const errors: unknown[] = [];
  const expectedError = new Error("unexpected send failure");

  const accepted = submitStudioComposerMessage({
    canChat: true,
    composerText: "继续写",
    isResponding: false,
    onSendMessage: async () => {
      throw expectedError;
    },
    onUnexpectedError: (error) => {
      errors.push(error);
    },
  });

  await waitForImmediate();

  assert.equal(accepted, true);
  assert.equal(errors.length, 1);
  assert.equal(errors[0], expectedError);
});

test("studio composer submit helper also captures synchronous send errors", async () => {
  const errors: unknown[] = [];
  const expectedError = new Error("sync send failure");

  const accepted = submitStudioComposerMessage({
    canChat: true,
    composerText: "继续写",
    isResponding: false,
    onSendMessage: () => {
      throw expectedError;
    },
    onUnexpectedError: (error) => {
      errors.push(error);
    },
  });

  await waitForImmediate();

  assert.equal(accepted, true);
  assert.equal(errors.length, 1);
  assert.equal(errors[0], expectedError);
});
