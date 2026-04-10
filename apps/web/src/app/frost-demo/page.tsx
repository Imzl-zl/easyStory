"use client";

import { useState } from "react";
import { cn } from "@/lib/utils/cn";
import {
  Surface,
  Button,
  Input,
  Textarea,
  Chip,
  Modal,
  SegmentedControl,
} from "@/components/ui/frost";

const PROJECTS = [
  { id: "1", title: "星尘编年史", genre: "科幻", chapters: 12, status: "active" as const },
  { id: "2", title: "雾城谜案", genre: "悬疑", chapters: 8, status: "draft" as const },
  { id: "3", title: "山海经·重述", genre: "奇幻", chapters: 24, status: "completed" as const },
  { id: "4", title: "深空回响", genre: "科幻", chapters: 3, status: "draft" as const },
];

const STATUS_MAP = {
  active: { label: "进行中", variant: "active" as const },
  draft: { label: "草稿", variant: "default" as const },
  completed: { label: "已完成", variant: "success" as const },
};

const WORKFLOW_STEPS = [
  { label: "大纲", value: "outline" },
  { label: "开篇", value: "opening" },
  { label: "章节", value: "chapter" },
  { label: "审核", value: "review" },
];

export default function FrostDemoPage() {
  const [view, setView] = useState("projects");
  const [workflowStep, setWorkflowStep] = useState("outline");
  const [modalOpen, setModalOpen] = useState(false);
  const [search, setSearch] = useState("");

  return (
    <div className="min-h-screen bg-canvas">
      <header className="sticky top-0 z-sticky border-b border-line-soft bg-glass-heavy backdrop-blur-xl">
        <div className="flex items-center justify-between gap-6 w-[min(100%-2.5rem,1560px)] mx-auto py-3">
          <div className="flex items-center gap-5">
            <span className="text-text-tertiary text-[0.68rem] tracking-[0.12em] uppercase font-medium">
              easyStory
            </span>
            <span className="text-text-primary text-lg font-semibold tracking-[-0.03em]">
              写作空间
            </span>
          </div>
          <nav className="flex items-center gap-1">
            <SegmentedControl
              onChange={setView}
              options={[
                { label: "书架", value: "projects" },
                { label: "创作", value: "studio" },
                { label: "推进", value: "engine" },
                { label: "洞察", value: "lab" },
              ]}
              value={view}
            />
          </nav>
          <div className="flex items-center gap-2.5">
            <Button size="sm" variant="secondary">我的助手</Button>
            <div className="flex items-center gap-2 py-1 px-2.5 rounded-pill bg-accent-soft">
              <div className="w-6 h-6 rounded-full bg-accent-primary text-text-on-accent flex items-center justify-center text-[10px] font-semibold">
                Z
              </div>
              <span className="text-sm font-medium text-text-primary">张路</span>
            </div>
          </div>
        </div>
      </header>

      <main className="w-[min(100%-2.5rem,1560px)] mx-auto py-6">
        <div className="grid grid-cols-[260px_minmax(0,1fr)] gap-5">
          <aside className="space-y-4">
            <Surface variant="glass" padding="md">
              <div className="space-y-3">
                <h3 className="text-sm font-semibold text-text-primary tracking-[-0.02em]">
                  导航
                </h3>
                <nav className="space-y-0.5">
                  {[
                    { label: "我的作品", active: true },
                    { label: "我的助手", active: false },
                    { label: "模板库", active: false },
                    { label: "回收站", active: false },
                  ].map((item) => (
                    <button
                      className={cn(
                        "w-full flex items-center px-3 py-2 rounded-lg text-sm font-medium transition-colors duration-fast cursor-pointer text-left",
                        item.active
                          ? "bg-accent-soft text-accent-primary"
                          : "text-text-secondary hover:bg-surface-hover hover:text-text-primary",
                      )}
                      key={item.label}
                      type="button"
                    >
                      {item.label}
                    </button>
                  ))}
                </nav>
              </div>
            </Surface>

            <Surface variant="glass" padding="md">
              <div className="space-y-3">
                <h3 className="text-sm font-semibold text-text-primary tracking-[-0.02em]">
                  当前节奏
                </h3>
                <div className="flex flex-wrap gap-1.5">
                  <Chip variant="active">创作中</Chip>
                  <Chip variant="success">已完成 3</Chip>
                  <Chip>草稿 2</Chip>
                </div>
                <div className="pt-1">
                  <div className="flex items-center justify-between text-[11px] text-text-tertiary mb-1.5">
                    <span>本周进度</span>
                    <span className="font-medium text-text-secondary">68%</span>
                  </div>
                  <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                    <div
                      className="h-full rounded-full bg-accent-primary transition-all duration-slow"
                      style={{ width: "68%" }}
                    />
                  </div>
                </div>
              </div>
            </Surface>
          </aside>

          <div className="space-y-5">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h1 className="text-2xl font-bold tracking-[-0.035em] text-text-primary">
                  我的作品
                </h1>
                <p className="mt-1 text-sm text-text-secondary">
                  管理你的创作项目，开启新的故事旅程
                </p>
              </div>
              <Button
                icon={
                  <svg fill="none" height="14" viewBox="0 0 14 14" width="14" xmlns="http://www.w3.org/2000/svg">
                    <path d="M7 1v12M1 7h12" stroke="currentColor" strokeLinecap="round" strokeWidth="1.5" />
                  </svg>
                }
                onClick={() => setModalOpen(true)}
              >
                新建作品
              </Button>
            </div>

            <div className="flex items-center gap-3">
              <Input
                className="max-w-xs"
                onChange={(e) => setSearch(e.target.value)}
                placeholder="搜索作品..."
                value={search}
                variant="glass"
              />
              <div className="flex items-center gap-1.5">
                <Chip variant="active">全部</Chip>
                <Chip>科幻</Chip>
                <Chip>悬疑</Chip>
                <Chip>奇幻</Chip>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              {PROJECTS.map((project) => {
                const statusInfo = STATUS_MAP[project.status];
                return (
                  <Surface hover key={project.id} variant="glass">
                    <div className="p-5 space-y-3.5">
                      <div className="flex items-start justify-between gap-3">
                        <div className="space-y-1 min-w-0">
                          <h3 className="text-[15px] font-semibold text-text-primary tracking-[-0.02em] truncate">
                            {project.title}
                          </h3>
                          <p className="text-xs text-text-tertiary">
                            {project.genre} · {project.chapters} 章
                          </p>
                        </div>
                        <Chip variant={statusInfo.variant}>
                          {statusInfo.label}
                        </Chip>
                      </div>
                      <div className="flex items-center gap-2">
                        <SegmentedControl
                          className="text-[10px]"
                          onChange={setWorkflowStep}
                          options={WORKFLOW_STEPS}
                          value={workflowStep}
                        />
                      </div>
                      <div className="flex items-center justify-between pt-1 border-t border-line-soft">
                        <span className="text-[11px] text-text-tertiary">
                          最近编辑 2 小时前
                        </span>
                        <div className="flex items-center gap-1">
                          <Button size="sm" variant="ghost">
                            设置
                          </Button>
                          <Button size="sm">继续创作</Button>
                        </div>
                      </div>
                    </div>
                  </Surface>
                );
              })}
            </div>

            <Surface variant="glass" padding="lg">
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h2 className="text-base font-semibold text-text-primary tracking-[-0.02em]">
                    快速起稿
                  </h2>
                  <Chip variant="default">AI 辅助</Chip>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label className="label-text">作品标题</label>
                    <Input placeholder="输入你的故事标题..." variant="glass" />
                  </div>
                  <div className="space-y-2">
                    <label className="label-text">类型</label>
                    <Input placeholder="科幻、悬疑、奇幻..." variant="glass" />
                  </div>
                </div>
                <div className="space-y-2">
                  <label className="label-text">故事概要</label>
                  <Textarea
                    placeholder="描述你想要创作的故事核心概念、主要角色或关键情节..."
                    rows={3}
                    variant="glass"
                  />
                </div>
                <div className="flex items-center justify-between pt-1">
                  <div className="flex items-center gap-2">
                    <Chip>世界观</Chip>
                    <Chip>角色设定</Chip>
                    <Chip variant="default">+ 添加标签</Chip>
                  </div>
                  <Button
                    icon={
                      <svg fill="none" height="14" viewBox="0 0 14 14" width="14" xmlns="http://www.w3.org/2000/svg">
                        <path
                          d="M2 7a5 5 0 0110 0 5 5 0 01-10 0z"
                          stroke="currentColor"
                          strokeLinecap="round"
                          strokeWidth="1.2"
                        />
                        <path d="M7 4.5V7l1.5 1" stroke="currentColor" strokeLinecap="round" strokeWidth="1.2" />
                      </svg>
                    }
                  >
                    开始创作
                  </Button>
                </div>
              </div>
            </Surface>

            <div className="grid grid-cols-3 gap-4">
              <Surface hover padding="md" variant="glass">
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-lg bg-accent-soft flex items-center justify-center">
                      <svg fill="none" height="16" viewBox="0 0 16 16" width="16" xmlns="http://www.w3.org/2000/svg">
                        <path d="M3 8h10M8 3v10" stroke="var(--accent-primary)" strokeLinecap="round" strokeWidth="1.5" />
                      </svg>
                    </div>
                    <span className="text-sm font-semibold text-text-primary">新建作品</span>
                  </div>
                  <p className="text-xs text-text-tertiary leading-relaxed">
                    从零开始，用 AI 对话梳理故事轮廓
                  </p>
                </div>
              </Surface>
              <Surface hover padding="md" variant="glass">
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-lg bg-[rgba(90,138,107,0.08)] flex items-center justify-center">
                      <svg fill="none" height="16" viewBox="0 0 16 16" width="16" xmlns="http://www.w3.org/2000/svg">
                        <path d="M4 4h8v8H4z" stroke="var(--accent-success)" strokeLinecap="round" strokeWidth="1.5" />
                        <path d="M4 8h8" stroke="var(--accent-success)" strokeWidth="1.2" />
                      </svg>
                    </div>
                    <span className="text-sm font-semibold text-text-primary">模板起稿</span>
                  </div>
                  <p className="text-xs text-text-tertiary leading-relaxed">
                    选择预设模板，快速搭建故事框架
                  </p>
                </div>
              </Surface>
              <Surface hover padding="md" variant="glass">
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-lg bg-[rgba(138,106,170,0.08)] flex items-center justify-center">
                      <svg fill="none" height="16" viewBox="0 0 16 16" width="16" xmlns="http://www.w3.org/2000/svg">
                        <path d="M8 2l2 4 4.5.7-3.3 3.1.8 4.5L8 12l-4 2.3.8-4.5L1.5 6.7 6 6z" stroke="var(--accent-purple)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.2" />
                      </svg>
                    </div>
                    <span className="text-sm font-semibold text-text-primary">导入作品</span>
                  </div>
                  <p className="text-xs text-text-tertiary leading-relaxed">
                    导入已有文本，AI 辅助续写和优化
                  </p>
                </div>
              </Surface>
            </div>
          </div>
        </div>
      </main>

      <Modal
        description="创建一个新的创作项目，AI 将协助你完成从构思到成稿的全过程。"
        onClose={() => setModalOpen(false)}
        open={modalOpen}
        size="md"
        title="新建作品"
      >
        <div className="space-y-5">
          <div className="space-y-2">
            <label className="label-text">作品标题</label>
            <Input placeholder="为你的故事命名..." />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="label-text">类型</label>
              <Input placeholder="科幻、悬疑、奇幻..." />
            </div>
            <div className="space-y-2">
              <label className="label-text">目标字数</label>
              <Input placeholder="例如：100000" />
            </div>
          </div>
          <div className="space-y-2">
            <label className="label-text">故事概要</label>
            <Textarea
              placeholder="描述你想要创作的故事核心概念..."
              rows={4}
            />
          </div>
          <div className="space-y-2">
            <label className="label-text">创作风格</label>
            <div className="flex flex-wrap gap-1.5">
              <Chip>文学性</Chip>
              <Chip variant="active">商业向</Chip>
              <Chip>实验性</Chip>
              <Chip>轻小说</Chip>
              <Chip>传统叙事</Chip>
            </div>
          </div>
          <div className="flex items-center justify-end gap-2 pt-2 border-t border-line-soft">
            <Button variant="secondary" onClick={() => setModalOpen(false)}>
              取消
            </Button>
            <Button onClick={() => setModalOpen(false)}>
              创建并开始
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}

