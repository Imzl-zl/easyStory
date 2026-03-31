"use client";

import { useMutation } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import type { ComponentProps } from "react";

import { login, register } from "@/lib/api/auth";
import { getErrorMessage } from "@/lib/api/client";
import { useAuthStore } from "@/lib/stores/auth-store";

import styles from "./auth-form.module.css";

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
    <main className={styles.shell}>
      <div className={styles.layout}>
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
    <section className={styles.hero}>
      <BrandMark />
      <div className={styles.heroBody}>
        <p className={styles.eyebrow}>写作者入口</p>
        <h1 className={styles.heroTitle}>{copy.heroTitle}</h1>
        <p className={styles.heroDescription}>{copy.description}</p>
      </div>
      <div className={styles.heroPanel}>
        <p className={styles.heroQuote}>
          “让产品先呈现作品与创作动作，而不是资源类型和后台配置。”
        </p>
        <ol className={styles.stepList}>
          {CREATION_STEPS.map(([title, detail]) => (
            <li className={styles.stepItem} key={title}>
              <span className={styles.stepTitle}>{title}</span>
              <p className={styles.stepDetail}>{detail}</p>
            </li>
          ))}
        </ol>
      </div>
      <div className={styles.pillarList}>
        {PRODUCT_PILLARS.map((item) => (
          <p className={styles.pillarItem} key={item}>
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
    <section className={styles.panel}>
      <div className={styles.panelCard}>
        <div className={styles.panelHeader}>
          <p className={styles.panelEyebrow}>easyStory</p>
          <h2 className={styles.panelTitle}>{copy.formTitle}</h2>
          <p className={styles.panelHint}>登录后直接进入书架，继续上次创作。</p>
        </div>
        <form
          className={styles.form}
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
          <button className={styles.submitButton} disabled={isPending} type="submit">
            {isPending ? "处理中..." : copy.submitLabel}
          </button>
        </form>
        <div className={styles.footer}>
          <span className={styles.footerText}>{copy.switchPrompt}</span>
          <Link className={styles.footerLink} href={copy.switchHref}>
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
    <label className={styles.field}>
      <span className={styles.label}>{label}</span>
      <input
        className={styles.input}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        {...props}
      />
    </label>
  );
}

function ErrorNotice({ message }: Readonly<{ message: string }>) {
  return (
    <div className={styles.error}>
      <span className={styles.errorBadge}>!</span>
      <span>{message}</span>
    </div>
  );
}

function BrandMark() {
  return (
    <div className={styles.brand}>
      <span className={styles.brandStamp}>ES</span>
      <div>
        <p className={styles.brandName}>easyStory</p>
        <p className={styles.brandTag}>写作不是填表，而是持续进入作品。</p>
      </div>
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
