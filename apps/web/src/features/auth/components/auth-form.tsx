"use client";

import { useMutation } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import type { ComponentProps } from "react";

import { login, register } from "@/lib/api/auth";
import { getErrorMessage } from "@/lib/api/client";
import { useAuthStore } from "@/lib/stores/auth-store";

const CREATION_STEPS = [
  ["起稿", "把一句念头整理成可写的世界、角色和冲突。"],
  ["推进", "在创作与推进之间来回切换，不再找后台入口。"],
  ["定稿", "分析、修订、导出都围着作品本身发生。"],
] as const;

const PRODUCT_PILLARS = [
  "规则、Skills 和模型连接会直接跟着你进入项目。",
  "工作区默认只关心作品、当前进度和下一步动作。",
  "不需要理解控制面，只需要继续写。",
] as const;

type AuthMode = "login" | "register";

type AuthFormProps = {
  mode: AuthMode;
};

type AuthCopy = {
  description: string;
  formTitle: string;
  heroTitle: string;
  submitLabel: string;
  switchHref: string;
  switchLabel: string;
  switchPrompt: string;
};

export function AuthForm({ mode }: AuthFormProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const setSession = useAuthStore((state) => state.setSession);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [email, setEmail] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
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
    <main className="min-h-screen flex items-center justify-center p-6 lg:p-8 [background:radial-gradient(circle_at_top_left,rgba(196,167,125,0.18),transparent_30%),radial-gradient(circle_at_right_20%,rgba(90,154,170,0.16),transparent_28%),linear-gradient(180deg,#f7f1e7_0%,#f4efe7_48%,#f8f6f1_100%)]">
      <div className="grid gap-6 w-full max-w-[1240px] mx-auto [grid-template-columns:1fr] lg:[grid-template-columns:minmax(0,1.15fr)_minmax(360px,460px)] lg:items-center">
        <AuthHero copy={copy} />
        <AuthPanel
          email={email}
          errorMessage={errorMessage}
          isPending={mutation.isPending}
          mode={mode}
          password={password}
          username={username}
          onEmailChange={setEmail}
          onPasswordChange={setPassword}
          onSubmit={() => mutation.mutate()}
          onUsernameChange={setUsername}
        />
      </div>
    </main>
  );
}

function AuthHero({ copy }: Readonly<{ copy: AuthCopy }>) {
  return (
    <section className="hero-card p-9 flex flex-col gap-7 max-lg:hidden">
      <div className="absolute -right-10 -bottom-14 w-[180px] h-[180px] rounded-full bg-[rgba(90,122,107,0.08)]" />
      <div className="flex items-center gap-3.5">
        <span className="inline-flex items-center justify-center w-12 h-12 rounded-4 bg-gradient-to-br from-[rgba(90,122,107,0.92)] to-[rgba(75,94,88,0.92)] text-white text-[15px] font-semibold tracking-[0.12em]">ES</span>
        <div>
          <p className="text-[15px] font-semibold">easyStory</p>
          <p className="mt-1 text-[var(--text-secondary)] text-[13px] leading-relaxed">写作不是填表，而是持续进入作品。</p>
        </div>
      </div>
      <div className="max-w-[620px]">
        <p className="label-overline">写作者入口</p>
        <h1 className="mt-4.5 font-serif text-[clamp(2.6rem,5vw,4.4rem)] font-semibold leading-tight">{copy.heroTitle}</h1>
        <p className="max-w-[580px] mt-4.5 text-[var(--text-secondary)] text-base leading-relaxed">{copy.description}</p>
      </div>
      <div className="grid gap-4.5 p-6 rounded-[22px] bg-gradient-to-b from-[rgba(250,246,237,0.94)] to-[rgba(247,241,231,0.88)]">
        <p className="font-serif text-xl leading-relaxed text-[var(--text-primary)]">
          "让产品先呈现作品与创作动作，而不是资源类型和后台配置。"
        </p>
        <ol className="grid gap-4 list-none">
          {CREATION_STEPS.map(([title, detail]) => (
            <li className="pt-4 border-t border-[rgba(61,61,61,0.08)]" key={title}>
              <span className="inline-block mb-1.5 text-[var(--accent-primary)] text-[13px] font-semibold tracking-[0.14em] uppercase">{title}</span>
              <p className="text-[var(--text-secondary)] text-sm leading-relaxed">{detail}</p>
            </li>
          ))}
        </ol>
      </div>
      <div className="grid gap-2.5">
        {PRODUCT_PILLARS.map((item) => (
          <p className="pl-4.5 relative text-[var(--text-secondary)] text-sm leading-relaxed" key={item}>
            <span className="absolute left-0 top-2.5 w-[7px] h-[7px] rounded-full bg-[rgba(90,122,107,0.44)]" />
            {item}
          </p>
        ))}
      </div>
    </section>
  );
}

function AuthPanel({
  email,
  errorMessage,
  isPending,
  mode,
  password,
  username,
  onEmailChange,
  onPasswordChange,
  onSubmit,
  onUsernameChange,
}: Readonly<{
  email: string;
  errorMessage: string | null;
  isPending: boolean;
  mode: AuthMode;
  password: string;
  username: string;
  onEmailChange: (value: string) => void;
  onPasswordChange: (value: string) => void;
  onSubmit: () => void;
  onUsernameChange: (value: string) => void;
}>) {
  const copy = buildAuthCopy(mode);

  return (
    <section className="flex items-center justify-center">
      <div className="hero-card w-full max-w-[460px] p-8">
        <div className="mb-7">
          <p className="label-overline">easyStory</p>
          <h2 className="mt-3.5 font-serif text-[34px] font-semibold">{copy.formTitle}</h2>
          <p className="mt-3 text-[var(--text-secondary)] text-sm leading-relaxed">登录后直接进入书架，继续上次创作。</p>
        </div>
        <form
          className="grid gap-4.5"
          onSubmit={(event) => {
            event.preventDefault();
            onSubmit();
          }}
        >
          <Field
            autoComplete="username"
            label="用户名"
            maxLength={100}
            minLength={3}
            placeholder="输入你的创作身份"
            required
            value={username}
            onChange={onUsernameChange}
          />
          {mode === "register" ? (
            <Field
              autoComplete="email"
              label="邮箱"
              maxLength={200}
              placeholder="用于接收重要通知，可留空"
              type="email"
              value={email}
              onChange={onEmailChange}
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
            onChange={onPasswordChange}
          />
          {errorMessage ? <ErrorNotice message={errorMessage} /> : null}
          <button className="ink-button-hero w-full" disabled={isPending} type="submit">
            {isPending ? "处理中..." : copy.submitLabel}
          </button>
        </form>
        <div className="flex gap-2 justify-center mt-6.5 pt-5.5 border-t border-[rgba(61,61,61,0.08)]">
          <span className="text-[var(--text-secondary)] text-sm">{copy.switchPrompt}</span>
          <Link className="text-[var(--accent-primary)] text-sm font-semibold" href={copy.switchHref}>
            {copy.switchLabel}
          </Link>
        </div>
      </div>
    </section>
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
      <span className="text-[var(--text-secondary)] text-[13px] font-medium">{label}</span>
      <input
        className="w-full min-h-12 px-3.5 border border-[rgba(61,61,61,0.09)] rounded-3.5 bg-[rgba(255,255,255,0.92)] transition-all hover:border-[rgba(61,61,61,0.2)] focus:border-[rgba(90,122,107,0.52)] focus:shadow-[0_0_0_4px_rgba(90,122,107,0.1)] focus:outline-none placeholder:text-[var(--text-placeholder)]"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        {...props}
      />
    </label>
  );
}

function ErrorNotice({ message }: Readonly<{ message: string }>) {
  return (
    <div className="flex items-center gap-2.5 px-3.5 py-3 rounded-4 bg-[rgba(196,90,90,0.1)] text-[var(--accent-danger)] text-[13px] leading-relaxed">
      <span className="inline-flex items-center justify-center w-[22px] h-[22px] rounded-full bg-[rgba(196,90,90,0.14)] font-bold">!</span>
      <span>{message}</span>
    </div>
  );
}

function buildAuthCopy(mode: AuthMode): AuthCopy {
  if (mode === "login") {
    return {
      description: "回到你的书架、创作桌面和洞察区，把故事从上次停下的地方继续写下去。",
      formTitle: "继续创作",
      heroTitle: "把故事继续写下去",
      submitLabel: "进入书架",
      switchHref: "/auth/register",
      switchLabel: "创建账号",
      switchPrompt: "还没有账号？",
    };
  }

  return {
    description: "注册后，你的规则、Skills 和模型连接会成为写作习惯的一部分，而不是后台设置项。",
    formTitle: "创建你的写作空间",
    heroTitle: "给故事一个真正的开始",
    submitLabel: "创建并进入",
    switchHref: "/auth/login",
    switchLabel: "返回登录",
    switchPrompt: "已经有账号？",
  };
}
