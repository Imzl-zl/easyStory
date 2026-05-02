import { buildCredentialUserAgentPreview, type CredentialRuntimeKindValue } from "@/features/settings/components/credential/credential-center-client-identity-support";

export type CredentialUserAgentPresetValue =
  | ""
  | "codex-cli"
  | "claude-code"
  | "gemini-cli"
  | "chrome-browser"
  | "custom";

const PRESET_USER_AGENTS = {
  "codex-cli": "codex-cli/0.118.0 (server; node)",
  "claude-code": "claude-code/2.1.76 (server; node)",
  "gemini-cli": "gemini-cli/0.35.3 (server; node)",
  "chrome-browser": (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    + "(KHTML, like Gecko) Chrome/145.0.7632.6 Safari/537.36"
  ),
} as const satisfies Record<Exclude<CredentialUserAgentPresetValue, "" | "custom">, string>;

export const USER_AGENT_PRESET_OPTIONS: Array<{
  value: CredentialUserAgentPresetValue;
  label: string;
  description: string;
}> = [
  { value: "", label: "不覆盖", description: "不覆盖 User-Agent，继续使用下面的应用名/版本/运行环境。" },
  { value: "codex-cli", label: "Codex CLI", description: "填入常见的 Codex CLI User-Agent 模板，可继续手改。" },
  { value: "claude-code", label: "Claude Code", description: "填入常见的 Claude Code User-Agent 模板，可继续手改。" },
  { value: "gemini-cli", label: "Gemini CLI", description: "填入常见的 Gemini CLI User-Agent 模板，可继续手改。" },
  { value: "chrome-browser", label: "Chrome 浏览器", description: "填入常见的 Chrome 浏览器 User-Agent 模板，可继续手改。" },
  { value: "custom", label: "自定义 User-Agent", description: "填写完整 User-Agent，运行时优先发送它。" },
];

export function normalizeCredentialUserAgentOverride(value: string): string | null {
  const normalized = value.trim();
  if (!normalized) {
    return null;
  }
  if (normalized.includes("\n") || normalized.includes("\r")) {
    throw new Error("User-Agent 覆盖必须是一行文本，不能包含换行。");
  }
  return normalized;
}

export function detectCredentialUserAgentPreset(
  userAgentOverride: string,
): CredentialUserAgentPresetValue {
  const normalized = normalizeCredentialUserAgentOverride(userAgentOverride);
  if (normalized === null) {
    return "";
  }
  for (const [preset, template] of Object.entries(PRESET_USER_AGENTS)) {
    if (normalized === template) {
      return preset as Exclude<CredentialUserAgentPresetValue, "" | "custom">;
    }
  }
  return "custom";
}

export function applyCredentialUserAgentPreset(
  preset: CredentialUserAgentPresetValue,
  currentOverride: string,
): string {
  if (preset === "") {
    return "";
  }
  if (preset === "custom") {
    return currentOverride;
  }
  return PRESET_USER_AGENTS[preset];
}

export function buildResolvedCredentialUserAgentPreview(options: {
  clientName: string;
  clientVersion: string;
  runtimeKind: CredentialRuntimeKindValue;
  userAgentOverride: string;
}): string | null {
  return (
    normalizeCredentialUserAgentOverride(options.userAgentOverride)
    ?? buildCredentialUserAgentPreview(options)
  );
}
