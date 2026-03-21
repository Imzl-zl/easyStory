import { requestJson } from "@/lib/api/client";
import type { AuthLoginPayload, AuthRegisterPayload, AuthToken } from "@/lib/api/types";

export function login(payload: AuthLoginPayload) {
  return requestJson<AuthToken>("/api/v1/auth/login", {
    method: "POST",
    body: payload,
    token: null,
  });
}

export function register(payload: AuthRegisterPayload) {
  return requestJson<AuthToken>("/api/v1/auth/register", {
    method: "POST",
    body: payload,
    token: null,
  });
}
