import { requestJson } from "@/lib/api/client";
import type { AssistantTurnPayload, AssistantTurnResult } from "@/lib/api/types";

export function runAssistantTurn(payload: AssistantTurnPayload) {
  return requestJson<AssistantTurnResult>("/api/v1/assistant/turn", {
    method: "POST",
    body: payload,
  });
}
