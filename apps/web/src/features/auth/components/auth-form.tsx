"use client";

import { useMutation } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import type { ComponentProps } from "react";

import { login, register } from "@/lib/api/auth";
import { getErrorMessage } from "@/lib/api/client";
import { useMounted } from "@/lib/hooks/use-mounted";
import { useAuthStore } from "@/lib/stores/auth-store";

type AuthMode = "login" | "register";

type AuthCopy = {
  formTitle: string;
  formSubtitle: string;
  submitLabel: string;
  switchHref: string;
  switchLabel: string;
  switchPrompt: string;
};

export function AuthForm({ mode }: { mode: AuthMode }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const setSession = useAuthStore((state) => state.setSession);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [email, setEmail] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const mounted = useMounted();
  const copy = buildAuthCopy(mode);

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
    onError: (error) => setErrorMessage(getErrorMessage(error)),
  });

  return (
    <main
      className="relative min-h-screen flex items-center justify-center p-6 overflow-hidden bg-canvas"
    >
      {/* 背景光晕 — 左上角暖金 */}
      <div
        className="absolute top-0 left-0 w-[500px] h-[500px] rounded-full blur-[120px] pointer-events-none"
        style={{
          background: "radial-gradient(circle, var(--glow-warm) 0%, transparent 70%)",
          opacity: mounted ? 0.8 : 0,
          transition: "opacity 2.5s ease 0.3s",
        }}
      />
      {/* 背景光晕 — 右下角冷蓝 */}
      <div
        className="absolute bottom-0 right-0 w-[400px] h-[400px] rounded-full blur-[100px] pointer-events-none"
        style={{
          background: "radial-gradient(circle, var(--glow-cool) 0%, transparent 70%)",
          opacity: mounted ? 0.5 : 0,
          transition: "opacity 2.5s ease 0.6s",
        }}
      />

      {/* 返回首页链接 */}
      <nav
        className="absolute top-6 left-6 z-20"
        style={{
          opacity: mounted ? 1 : 0,
          transition: "opacity 1s ease 0.8s",
        }}
      >
        <Link
          href="/"
          className="inline-flex items-center gap-2 text-[13px] font-medium text-text-tertiary"
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="m15 18-6-6 6-6" />
          </svg>
          返回首页
        </Link>
      </nav>

      {/* 主卡片 */}
      <div
        className="relative z-10 w-full max-w-[420px]"
        style={{
          opacity: mounted ? 1 : 0,
          transform: mounted ? "translateY(0)" : "translateY(20px)",
          transition: "all 1s cubic-bezier(0.4, 0, 0.2, 1) 0.4s",
        }}
      >
        {/* 卡片外发光 */}
        <div
          className="absolute -inset-[1px] rounded-[28px] pointer-events-none"
          style={{
            background: "linear-gradient(135deg, rgba(201,169,110,0.15), rgba(90,130,160,0.08), transparent)",
            opacity: mounted ? 1 : 0,
            transition: "opacity 2s ease 0.6s",
          }}
        />

        <div
          className="relative p-10"
          style={{
            background: "var(--bg-glass-heavy)",
            borderRadius: "var(--radius-4xl)",
            boxShadow: "var(--shadow-hero), inset 0 1px 0 rgba(255, 255, 255, 0.04)",
            backdropFilter: "blur(32px)",
            WebkitBackdropFilter: "blur(32px)",
          }}
        >
          {/* Logo */}
          <div className="flex justify-center mb-8">
            <div className="flex items-center gap-3">
              <span
                className="inline-flex items-center justify-center w-11 h-11 rounded-xl text-[14px] font-semibold tracking-[0.12em]"
                style={{
                  background: "linear-gradient(135deg, var(--accent-primary), var(--accent-primary-dark))",
                  color: "var(--text-on-accent)",
                }}
              >
                ES
              </span>
            </div>
          </div>

          {/* 标题 */}
          <div className="text-center mb-8">
            <h1
              className="font-serif text-[28px] font-semibold tracking-[-0.02em] text-text-primary"
            >
              {copy.formTitle}
            </h1>
            <p
              className="mt-2 text-[14px] leading-relaxed text-text-secondary"
            >
              {copy.formSubtitle}
            </p>
          </div>

          {/* 表单 */}
          <form
            className="grid gap-4"
            onSubmit={(event) => {
              event.preventDefault();
              mutation.mutate();
            }}
          >
            <Field
              autoComplete="username"
              label="用户名"
              maxLength={100}
              minLength={3}
              placeholder="你的创作身份"
              required
              value={username}
              onChange={setUsername}
            />
            {mode === "register" ? (
              <Field
                autoComplete="email"
                label="邮箱"
                maxLength={200}
                placeholder="可选，用于找回账号"
                type="email"
                value={email}
                onChange={setEmail}
              />
            ) : null}
            <Field
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              label="密码"
              maxLength={200}
              minLength={8}
              placeholder="至少 8 位"
              required
              type="password"
              value={password}
              onChange={setPassword}
            />
            {errorMessage ? <ErrorNotice message={errorMessage} /> : null}
            <button
              className="ink-button-hero w-full mt-2"
              disabled={mutation.isPending}
              type="submit"
            >
              {mutation.isPending ? "处理中..." : copy.submitLabel}
            </button>
          </form>

          {/* 切换模式 */}
          <div
            className="flex gap-2 justify-center mt-7 pt-6 border-t border-line-soft"
          >
            <span className="text-[13px] text-text-tertiary">
              {copy.switchPrompt}
            </span>
            <Link
              className="text-[13px] font-semibold text-accent-primary"
              href={copy.switchHref}
            >
              {copy.switchLabel}
            </Link>
          </div>
        </div>
      </div>

      {/* 底部文案 */}
      <div
        className="absolute bottom-6 left-0 right-0 flex justify-center"
        style={{
          opacity: mounted ? 0.4 : 0,
          transition: "opacity 2s ease 1.2s",
        }}
      >
        <p
          className="text-[11px] tracking-[0.15em] uppercase text-text-tertiary"
        >
          本地部署 · 数据由你掌控
        </p>
      </div>
    </main>
  );
}

function Field({
  label,
  onChange,
  value,
  ...props
}: Readonly<
  Omit<ComponentProps<"input">, "onChange" | "value"> & {
    label: string;
    onChange: (value: string) => void;
    value: string;
  }
>) {
  return (
    <label className="grid gap-2">
      <span
        className="text-[13px] font-medium text-text-secondary"
      >
        {label}
      </span>
      <input
        className="ink-input ink-input-roomy"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        {...props}
      />
    </label>
  );
}

function ErrorNotice({ message }: Readonly<{ message: string }>) {
  return (
    <div
      className="flex items-center gap-2.5 px-3.5 py-3 rounded-xl text-[13px] leading-relaxed bg-accent-danger-soft text-accent-danger"
    >
      <span
        className="inline-flex items-center justify-center w-[20px] h-[20px] rounded-full font-bold text-[10px] bg-accent-danger-muted"
      >
        !
      </span>
      <span>{message}</span>
    </div>
  );
}

function buildAuthCopy(mode: AuthMode): AuthCopy {
  if (mode === "login") {
    return {
      formTitle: "欢迎回来",
      formSubtitle: "继续你的故事",
      submitLabel: "进入书架",
      switchHref: "/auth/register",
      switchLabel: "创建账号",
      switchPrompt: "还没有账号？",
    };
  }

  return {
    formTitle: "开始创作",
    formSubtitle: "给故事一个起点",
    submitLabel: "创建并进入",
    switchHref: "/auth/login",
    switchLabel: "返回登录",
    switchPrompt: "已经有账号？",
  };
}
