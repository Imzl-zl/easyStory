import assert from "node:assert/strict";
import test from "node:test";

import {
  createIncubatorMessage,
  INCUBATOR_INTERRUPTED_REPLY_MESSAGE,
} from "./incubator-chat-support";
import {
  createEmptyIncubatorChatSession,
  normalizePersistedIncubatorChatSession,
  useIncubatorChatStore,
} from "./incubator-chat-store";
import { migratePersistedState } from "./incubator-chat-store-support";

function resetStore() {
  useIncubatorChatStore.setState({
    hasHydrated: true,
    userStatesByUserId: {},
  });
}

test("incubator chat store normalizes pending assistant replies on restore", () => {
  const session = createEmptyIncubatorChatSession();
  const normalized = normalizePersistedIncubatorChatSession({
    ...session,
    messages: [
      ...session.messages,
      createIncubatorMessage("user", "给我两个方向"),
      createIncubatorMessage("assistant", "先给你两个方向", { status: "pending" }),
    ],
  });

  const lastMessage = normalized.messages.at(-1);
  assert.ok(lastMessage);
  assert.equal(lastMessage.status, "error");
  assert.equal(
    lastMessage.content,
    `先给你两个方向

${INCUBATOR_INTERRUPTED_REPLY_MESSAGE}`,
  );
});

test("incubator chat store drops legacy system messages on restore", () => {
  const session = createEmptyIncubatorChatSession();
  const normalized = normalizePersistedIncubatorChatSession({
    ...session,
    messages: [
      ...session.messages,
      { ...createIncubatorMessage("assistant", "旧隐藏指令"), role: "system" as never, hidden: true },
      createIncubatorMessage("user", "帮我想一个故事方向"),
    ] as unknown as typeof session.messages,
  });

  assert.equal(normalized.messages.length, 2);
  assert.deepEqual(
    normalized.messages.map((message) => message.role),
    ["assistant", "user"],
  );
  assert.equal(normalized.messages[1]?.content, "帮我想一个故事方向");
});

test("incubator chat store supports create, switch and delete conversation history", () => {
  resetStore();
  const store = useIncubatorChatStore.getState();

  const firstConversationId = store.createConversation("user-1");
  store.patchActiveConversation("user-1", (current) => ({
    ...current,
    messages: [...current.messages, createIncubatorMessage("user", "我想写玄幻成长故事")],
  }));

  const secondConversationId = store.createConversation("user-1");
  store.patchActiveConversation("user-1", (current) => ({
    ...current,
    projectName: "都市悬疑草稿",
  }));

  let userState = useIncubatorChatStore.getState().userStatesByUserId["user-1"];
  assert.ok(userState);
  assert.equal(userState.conversations.length, 2);
  assert.equal(userState.activeConversationId, secondConversationId);
  assert.equal(userState.conversations[0]?.title, "都市悬疑草稿");
  assert.equal(
    userState.conversations.find((conversation) => conversation.id === firstConversationId)?.title,
    "我想写玄幻成长故事",
  );

  useIncubatorChatStore.getState().selectConversation("user-1", firstConversationId);
  userState = useIncubatorChatStore.getState().userStatesByUserId["user-1"];
  assert.equal(userState.activeConversationId, firstConversationId);

  useIncubatorChatStore.getState().deleteConversation("user-1", firstConversationId);
  userState = useIncubatorChatStore.getState().userStatesByUserId["user-1"];
  assert.equal(userState.conversations.length, 1);
  assert.equal(userState.activeConversationId, secondConversationId);
});

test("incubator chat store keeps pending assistant reply while streaming in current session", () => {
  resetStore();
  const store = useIncubatorChatStore.getState();

  store.createConversation("user-1");
  store.patchActiveConversation("user-1", (current) => ({
    ...current,
    messages: [
      ...current.messages,
      createIncubatorMessage("user", "请只回复一个字：好"),
      createIncubatorMessage("assistant", "正", { status: "pending" }),
    ],
  }));

  const pendingMessage = useIncubatorChatStore.getState().userStatesByUserId["user-1"]
    ?.conversations[0]?.session.messages.at(-1);
  assert.ok(pendingMessage);
  assert.equal(pendingMessage.status, "pending");
  assert.equal(pendingMessage.content, "正");
});

test("incubator chat store does not reuse an active session with latest completed run id as empty conversation", () => {
  resetStore();
  const store = useIncubatorChatStore.getState();

  const firstConversationId = store.createConversation("user-1");
  store.patchActiveConversation("user-1", (current) => ({
    ...current,
    latestCompletedRunId: "run-incubator-keep-1",
  }));

  const nextConversationId = store.createConversation("user-1");
  const userState = useIncubatorChatStore.getState().userStatesByUserId["user-1"];

  assert.ok(userState);
  assert.equal(userState.conversations.length, 2);
  assert.equal(firstConversationId === nextConversationId, false);
  assert.equal(userState.activeConversationId, nextConversationId);
  assert.equal(userState.conversations[1]?.session.latestCompletedRunId, "run-incubator-keep-1");
});

test("incubator chat store does not rewrite active conversation when async result returns to a deleted history", () => {
  resetStore();
  const store = useIncubatorChatStore.getState();

  const conversationId = store.createConversation("user-1");
  store.patchActiveConversation("user-1", (current) => ({
    ...current,
    projectName: "当前会话",
  }));

  store.patchConversation("user-1", "missing-conversation", (current) => ({
    ...current,
    projectName: "不该写进当前会话",
  }));

  const session = useIncubatorChatStore.getState().userStatesByUserId["user-1"]
    ?.conversations.find((conversation) => conversation.id === conversationId)?.session;
  assert.equal(session?.projectName, "当前会话");
});

test("incubator chat store migrates legacy single-session persistence to conversation history", () => {
  const migrated = migratePersistedState({
    sessionsByUserId: {
      "user-1": {
        ...createEmptyIncubatorChatSession(),
        messages: [
          ...createEmptyIncubatorChatSession().messages,
          createIncubatorMessage("user", "帮我想一个悬疑点子"),
        ],
      },
    },
  });

  const userState = migrated.userStatesByUserId["user-1"];
  assert.ok(userState);
  assert.equal(userState.conversations.length, 1);
  assert.equal(userState.conversations[0]?.title, "帮我想一个悬疑点子");
});

test("incubator chat store tolerates malformed persisted user history", () => {
  const migrated = migratePersistedState({
    userStatesByUserId: {
      "user-1": {
        activeConversationId: 42,
        conversations: { broken: true },
      },
    },
  });

  const userState = migrated.userStatesByUserId["user-1"];
  assert.ok(userState);
  assert.equal(Array.isArray(userState.conversations), true);
  assert.equal(userState.conversations.length, 1);
  assert.equal(userState.conversations[0]?.title, "新对话");
});
