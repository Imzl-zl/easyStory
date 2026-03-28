"use client";

import { useMutation } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useMemo, useState } from "react";

import { login, register } from "@/lib/api/auth";
import { getErrorMessage } from "@/lib/api/client";
import { useAuthStore } from "@/lib/stores/auth-store";

type AuthFormProps = {
  mode: "login" | "register";
};

export function AuthForm({ mode }: AuthFormProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const setSession = useAuthStore((state) => state.setSession);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [email, setEmail] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: async () => {
      if (mode === "login") {
        return login({ username, password });
      }
      return register({ username, password, email: email || undefined });
    },
    onSuccess: (session) => {
      setSession(session);
      router.replace(searchParams.get("next") ?? "/workspace/lobby");
    },
    onError: (error) => {
      setErrorMessage(getErrorMessage(error));
    },
  });

  const title = useMemo(
    () => (mode === "login" ? "进入创作空间" : "创建账号"),
    [mode],
  );

  return (
    <main className="flex min-h-screen items-center justify-center p-6">
      <div className="grid w-full max-w-6xl gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <section className="panel-shell relative overflow-hidden p-8 lg:p-10">
          <div className="absolute inset-x-0 top-0 h-48 bg-gradient-to-br from-[rgba(46,111,106,0.18)] via-transparent to-[rgba(58,124,165,0.15)]" />
          <div className="relative space-y-8">
            <div className="space-y-4">
              <p className="text-sm uppercase tracking-[0.28em] text-[var(--accent-ink)]">
                easyStory
              </p>
              <h1 className="max-w-xl font-serif text-4xl leading-tight font-semibold md:text-5xl">
                {title}
              </h1>
              <p className="max-w-2xl text-base leading-8 text-[var(--text-secondary)]">
                统一管理项目、AI 聊天和创作流程。
              </p>
            </div>
            <div className="grid gap-4 md:grid-cols-3">
              <div className="panel-muted p-4">
                <p className="text-xs uppercase tracking-[0.24em] text-[var(--text-secondary)]">
                  工作室
                </p>
                <p className="mt-2 text-sm leading-6">章节与版本管理。</p>
              </div>
              <div className="panel-muted p-4">
                <p className="text-xs uppercase tracking-[0.24em] text-[var(--text-secondary)]">
                  引擎
                </p>
                <p className="mt-2 text-sm leading-6">AI 生成与进度。</p>
              </div>
              <div className="panel-muted p-4">
                <p className="text-xs uppercase tracking-[0.24em] text-[var(--text-secondary)]">
                  实验室
                </p>
                <p className="mt-2 text-sm leading-6">灵感与分析。</p>
              </div>
            </div>
          </div>
        </section>

        <section className="panel-shell fan-panel p-8 lg:p-10">
          <div className="space-y-6">
            <div className="space-y-2">
              <h2 className="font-serif text-3xl font-semibold">
                {mode === "login" ? "登录" : "注册"}
              </h2>
              <p className="text-sm leading-6 text-[var(--text-secondary)]">
                {mode === "login"
                  ? "登录后进入项目大厅。"
                  : "注册后进入创作空间。"}
              </p>
            </div>

            <form
              className="space-y-4"
              onSubmit={(event) => {
                event.preventDefault();
                setErrorMessage(null);
                mutation.mutate();
              }}
            >
              <label className="block">
                <span className="label-text">用户名</span>
                <input
                  className="ink-input"
                  minLength={3}
                  maxLength={100}
                  required
                  value={username}
                  onChange={(event) => setUsername(event.target.value)}
                />
              </label>

              {mode === "register" ? (
                <label className="block">
                  <span className="label-text">邮箱</span>
                  <input
                    className="ink-input"
                    maxLength={200}
                    type="email"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                  />
                </label>
              ) : null}

              <label className="block">
                <span className="label-text">密码</span>
                <input
                  className="ink-input"
                  minLength={8}
                  maxLength={200}
                  required
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                />
              </label>

              {errorMessage ? (
                <div className="rounded-2xl bg-[rgba(178,65,46,0.12)] px-4 py-3 text-sm text-[var(--accent-danger)]">
                  {errorMessage}
                </div>
              ) : null}

              <button className="ink-button w-full" disabled={mutation.isPending} type="submit">
                {mutation.isPending ? "正在处理…" : mode === "login" ? "进入项目大厅" : "创建账号"}
              </button>
            </form>

            <p className="text-sm text-[var(--text-secondary)]">
              {mode === "login" ? "还没有账号？" : "已经有账号了？"}{" "}
              <Link
                className="font-medium text-[var(--accent-ink)] underline decoration-[rgba(46,111,106,0.28)] underline-offset-4"
                href={mode === "login" ? "/auth/register" : "/auth/login"}
              >
                {mode === "login" ? "去注册" : "去登录"}
              </Link>
            </p>
          </div>
        </section>
      </div>
    </main>
  );
}
