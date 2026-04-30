"use client";

import Link from "next/link";

import { useMounted } from "@/lib/hooks/use-mounted";
import { useParticleCanvas } from "@/lib/hooks/use-particle-canvas";

export default function HomePage() {
  const mounted = useMounted();
  const canvasRef = useParticleCanvas();

  return (
    <main className="relative min-h-screen overflow-hidden bg-canvas">
      {/* 背景粒子画布 */}
      <canvas
        ref={canvasRef}
        className="absolute inset-0 w-full h-full pointer-events-none"
        style={{ opacity: mounted ? 1 : 0, transition: "opacity 2s ease" }}
      />

      {/* 顶部导航 */}
      <nav
        className="relative z-10 flex items-center justify-between px-8 py-6 lg:px-16"
        style={{
          opacity: mounted ? 1 : 0,
          transform: mounted ? "translateY(0)" : "translateY(-12px)",
          transition: "all 1s cubic-bezier(0.4, 0, 0.2, 1) 0.3s",
        }}
      >
        <div className="flex items-center gap-3">
          <span
            className="inline-flex items-center justify-center w-10 h-10 rounded-xl text-[13px] font-semibold tracking-[0.12em]"
            style={{
              background:
                "linear-gradient(135deg, var(--accent-primary), var(--accent-primary-dark))",
              color: "var(--text-on-accent)",
            }}
          >
            ES
          </span>
          <span className="text-[15px] font-semibold tracking-[-0.01em] text-text-primary">
            easyStory
          </span>
        </div>
        <Link href="/auth/login" className="ink-link-button text-[13px]">
          登录
        </Link>
      </nav>

      {/* 主内容区 */}
      <div className="relative z-10 flex flex-col items-center justify-center min-h-[calc(100vh-88px)] px-6">
        {/* 中央视觉区域 */}
        <div className="flex flex-col items-center text-center max-w-3xl mx-auto">
          {/* 装饰标签 */}
          <div
            style={{
              opacity: mounted ? 1 : 0,
              transform: mounted ? "translateY(0)" : "translateY(16px)",
              transition: "all 1s cubic-bezier(0.4, 0, 0.2, 1) 0.5s",
            }}
          >
            <span
              className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-[12px] font-medium tracking-[0.08em]"
              style={{
                border: "1px solid var(--accent-primary-muted)",
                background: "var(--accent-primary-soft)",
                color: "var(--accent-primary)",
              }}
            >
              <span
                className="w-1.5 h-1.5 rounded-full animate-pulse"
                style={{ background: "var(--accent-primary)" }}
              />
              AI 小说创作平台
            </span>
          </div>

          {/* 主标题 */}
          <h1
            className="mt-10 font-serif text-[clamp(2.8rem,7vw,5.5rem)] font-semibold leading-[1.05] tracking-[-0.04em]"
            style={{
              color: "var(--text-primary)",
              opacity: mounted ? 1 : 0,
              transform: mounted ? "translateY(0)" : "translateY(24px)",
              transition: "all 1.2s cubic-bezier(0.4, 0, 0.2, 1) 0.7s",
            }}
          >
            故事，从一句话
            <br />
            <span className="relative inline-block">
              开始生长
              <svg
                className="absolute -bottom-2 left-0 w-full"
                height="12"
                viewBox="0 0 200 12"
                fill="none"
                preserveAspectRatio="none"
              >
                <path
                  d="M2 8C40 2 80 2 100 4C120 6 160 6 198 2"
                  style={{
                    stroke: "var(--accent-primary)",
                    strokeWidth: 2.5,
                    strokeLinecap: "round",
                    strokeDasharray: 300,
                    strokeDashoffset: mounted ? 0 : 300,
                    transition:
                      "stroke-dashoffset 1.5s cubic-bezier(0.4, 0, 0.2, 1) 1.4s",
                  }}
                />
              </svg>
            </span>
          </h1>

          {/* 副标题 */}
          <p
            className="mt-8 text-[clamp(1rem,2vw,1.25rem)] leading-relaxed max-w-xl"
            style={{
              color: "var(--text-secondary)",
              opacity: mounted ? 1 : 0,
              transform: mounted ? "translateY(0)" : "translateY(16px)",
              transition: "all 1s cubic-bezier(0.4, 0, 0.2, 1) 1s",
            }}
          >
            与 AI 对话，让灵感自然流淌。
            <br className="hidden sm:block" />
            不写大纲也能开始，写到哪，工具就跟到哪。
          </p>

          {/* CTA 按钮组 */}
          <div
            className="mt-12 flex flex-col sm:flex-row items-center gap-4"
            style={{
              opacity: mounted ? 1 : 0,
              transform: mounted ? "translateY(0)" : "translateY(16px)",
              transition: "all 1s cubic-bezier(0.4, 0, 0.2, 1) 1.2s",
            }}
          >
            <Link
              href="/auth/login"
              className="ink-button-hero text-[15px] min-h-[52px] px-9"
            >
              开始创作
              <svg
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M5 12h14" />
                <path d="m12 5 7 7-7 7" />
              </svg>
            </Link>
            <Link
              href="/auth/register"
              className="ink-button-secondary text-[14px] min-h-[44px] px-6"
            >
              创建账号
            </Link>
          </div>

          {/* 特性标签 */}
          <div
            className="mt-16 flex flex-wrap items-center justify-center gap-3"
            style={{
              opacity: mounted ? 1 : 0,
              transition: "opacity 1.5s ease 1.6s",
            }}
          >
            {["对话式创作", "智能大纲", "风格分析", "批量生成", "本地部署"].map(
              (tag) => (
                <span
                  key={tag}
                  className="px-3.5 py-1.5 rounded-full text-[12px] font-medium"
                  style={{
                    border: "1px solid var(--line-medium)",
                    background: "var(--bg-surface)",
                    color: "var(--text-tertiary)",
                  }}
                >
                  {tag}
                </span>
              ),
            )}
          </div>
        </div>

        {/* 底部装饰文字 */}
        <div
          className="absolute bottom-8 left-0 right-0 flex justify-center"
          style={{
            opacity: mounted ? 0.5 : 0,
            transition: "opacity 2s ease 2s",
          }}
        >
          <p className="text-[11px] tracking-[0.2em] uppercase text-text-tertiary">
            本地部署 · 数据由你掌控
          </p>
        </div>
      </div>

      {/* 角落装饰 */}
      <div
        className="absolute top-[15%] right-[8%] w-32 h-32 rounded-full blur-2xl pointer-events-none"
        style={{
          background: "linear-gradient(135deg, var(--glow-warm), transparent)",
          opacity: mounted ? 1 : 0,
          transform: mounted ? "scale(1)" : "scale(0.8)",
          transition: "all 2s ease 0.8s",
        }}
      />
      <div
        className="absolute bottom-[20%] left-[10%] w-40 h-40 rounded-full blur-3xl pointer-events-none"
        style={{
          background: "linear-gradient(225deg, var(--glow-cool), transparent)",
          opacity: mounted ? 1 : 0,
          transform: mounted ? "scale(1)" : "scale(0.8)",
          transition: "all 2s ease 1s",
        }}
      />
    </main>
  );
}
