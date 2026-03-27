import assert from "node:assert/strict";
import test from "node:test";

import {
  buildIncubatorCredentialNotice,
  buildIncubatorCredentialOptions,
  pickIncubatorCredentialOption,
} from "./incubator-chat-credential-support";

test("incubator chat credential support keeps only active unique providers", () => {
  const options = buildIncubatorCredentialOptions([
    {
      api_dialect: "openai_responses",
      api_key_header_name: null,
      auth_strategy: null,
      base_url: null,
      default_model: "gpt-4.1-mini",
      display_name: "OpenAI 主账号",
      extra_headers: null,
      id: "1",
      is_active: true,
      last_verified_at: null,
      masked_key: "***",
      owner_id: "u1",
      owner_type: "user",
      provider: "openai",
    },
    {
      api_dialect: "openai_responses",
      api_key_header_name: null,
      auth_strategy: null,
      base_url: null,
      default_model: "gpt-4.1",
      display_name: "OpenAI 备用",
      extra_headers: null,
      id: "2",
      is_active: true,
      last_verified_at: null,
      masked_key: "***",
      owner_id: "u1",
      owner_type: "user",
      provider: "openai",
    },
    {
      api_dialect: "gemini_generate_content",
      api_key_header_name: null,
      auth_strategy: null,
      base_url: null,
      default_model: "gemini-2.5-flash",
      display_name: "Gemini",
      extra_headers: null,
      id: "3",
      is_active: false,
      last_verified_at: null,
      masked_key: "***",
      owner_id: "u1",
      owner_type: "user",
      provider: "gemini",
    },
  ]);

  assert.deepEqual(options, [
    {
      defaultModel: "gpt-4.1-mini",
      displayLabel: "OpenAI 主账号 · gpt-4.1-mini",
      provider: "openai",
    },
  ]);
  const selectedOption = pickIncubatorCredentialOption(options, "");
  assert.ok(selectedOption);
  assert.equal(selectedOption.provider, "openai");
});

test("incubator chat credential support builds setup notice when no credential exists", () => {
  assert.equal(buildIncubatorCredentialNotice(true, []), null);
  assert.equal(
    buildIncubatorCredentialNotice(false, []),
    "当前账号还没有启用任何模型连接。先去模型连接里启用一条，再回来继续聊天。",
  );
});
