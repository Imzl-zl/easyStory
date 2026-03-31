# easyStory UI 实施指南

| 字段 | 内容 |
|---|---|
| 文档类型 | 技术实施规格 |
| 文档状态 | 生效 |
| 创建时间 | 2026-03-31 |
| 适用范围 | 前端开发团队 |

---

## 1. 技术栈决策

### 1.1 核心技术

```
框架：Next.js 16 + React 19
样式：Tailwind CSS 4 + CSS Variables
状态：Zustand（全局） + useState（局部）
数据：TanStack Query（服务端状态）
编辑器：Monaco Editor（Markdown）
```

### 1.2 为什么选择 Tailwind CSS

**优势**：
- 快速开发，不需要写大量 CSS 文件
- 响应式设计简单（`md:` `lg:` 前缀）
- 与 CSS Variables 配合，保持设计系统一致性
- 生产构建时自动清除未使用的样式

**劣势**：
- 类名可能很长
- 需要团队熟悉 Tailwind 语法

**决策**：使用 Tailwind CSS 作为主要样式方案，配合 CSS Variables 管理设计 token

---

## 2. 样式架构

### 2.1 三层样式系统

```
┌─────────────────────────────────────────────────────────┐
│  第一层：CSS Variables（设计 token）                    │
│  - 色彩、字体、间距、圆角、阴影                         │
│  - 定义在 globals.css                                   │
│  - 全局可用，保证一致性                                 │
├─────────────────────────────────────────────────────────┤
│  第二层：Tailwind Utilities（原子类）                   │
│  - 布局、间距、文字、背景                               │
│  - 直接在 JSX 中使用                                    │
│  - 快速开发，响应式友好                                 │
├─────────────────────────────────────────────────────────┤
│  第三层：React Components（复用组件）                   │
│  - 按钮、卡片、输入框、对话框                           │
│  - 封装复杂交互逻辑                                     │
│  - 统一视觉和行为                                       │
└─────────────────────────────────────────────────────────┘
```

### 2.2 CSS Variables 定义

在 `apps/web/src/app/globals.css` 中定义：

```css
:root {
  /* 色彩 */
  --color-canvas: #faf9f6;
  --color-paper: #ffffff;
  --color-sidebar: #f5f4f0;
  --color-accent: #4a7c59;
  
  /* 文字 */
  --color-text-primary: #2a2a2a;
  --color-text-secondary: #5a5a5a;
  
  /* 间距 */
  --spacing-xs: 4px;
  --spacing-sm: 8px;
  --spacing-md: 16px;
  --spacing-lg: 24px;
  --spacing-xl: 32px;
  
  /* 圆角 */
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
  
  /* 字体 */
  --font-serif: "Noto Serif SC", Georgia, serif;
  --font-sans: -apple-system, sans-serif;
}
```

### 2.3 Tailwind 配置

在 `tailwind.config.ts` 中扩展：

```typescript
import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './src/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        canvas: 'var(--color-canvas)',
        paper: 'var(--color-paper)',
        sidebar: 'var(--color-sidebar)',
        accent: 'var(--color-accent)',
      },
      fontFamily: {
        serif: 'var(--font-serif)',
        sans: 'var(--font-sans)',
      },
      borderRadius: {
        'sm': 'var(--radius-sm)',
        'md': 'var(--radius-md)',
        'lg': 'var(--radius-lg)',
      },
    },
  },
}

export default config
```

---

## 3. 何时使用什么

### 3.1 决策树

```
需要样式？
  ├─ 是设计 token（颜色、字体、间距）？
  │   └─ 使用 CSS Variables
  │       例：style={{ color: 'var(--color-text-primary)' }}
  │
  ├─ 是简单的布局/间距/文字？
  │   └─ 使用 Tailwind 类
  │       例：className="flex gap-4 p-6 text-lg"
  │
  ├─ 是复杂的交互组件？
  │   └─ 创建 React 组件
  │       例：<Button variant="primary">保存</Button>
  │
  └─ 是页面级布局？
      └─ 组合使用 Tailwind + 组件
          例：<div className="flex h-screen">
                <Sidebar />
                <MainContent />
              </div>
```

### 3.2 具体规则

#### 规则 1：设计 token 用 CSS Variables

**✅ 正确**：
```tsx
<div style={{ 
  background: 'var(--color-paper)',
  color: 'var(--color-text-primary)',
  borderRadius: 'var(--radius-md)'
}}>
```

**❌ 错误**：
```tsx
<div style={{ 
  background: '#ffffff',
  color: '#2a2a2a',
  borderRadius: '8px'
}}>
```

**原因**：CSS Variables 保证设计系统一致性，方便全局修改

#### 规则 2：布局用 Tailwind

**✅ 正确**：
```tsx
<div className="flex flex-col gap-4 p-6">
  <div className="grid grid-cols-3 gap-6">
    {/* 内容 */}
  </div>
</div>
```

**❌ 错误**：
```tsx
<div style={{ 
  display: 'flex', 
  flexDirection: 'column', 
  gap: '16px', 
  padding: '24px' 
}}>
```

**原因**：Tailwind 更简洁，支持响应式（`md:grid-cols-2`）

#### 规则 3：复用组件封装

**✅ 正确**：
```tsx
// components/ui/Button.tsx
export function Button({ 
  variant = 'primary', 
  children 
}: ButtonProps) {
  return (
    <button className={cn(
      'px-5 py-2 rounded-md font-medium transition',
      variant === 'primary' && 'bg-accent text-white',
      variant === 'secondary' && 'bg-paper border'
    )}>
      {children}
    </button>
  )
}

// 使用
<Button variant="primary">保存</Button>
```

**❌ 错误**：
```tsx
// 每次都写一遍
<button className="px-5 py-2 rounded-md bg-accent text-white">
  保存
</button>
```

**原因**：组件保证一致性，方便维护

---

## 4. 组件库规范

### 4.1 组件目录结构

```
apps/web/src/components/
├── ui/                    # 基础 UI 组件
│   ├── Button.tsx
│   ├── Card.tsx
│   ├── Input.tsx
│   ├── Dialog.tsx
│   └── index.ts
├── layout/                # 布局组件
│   ├── Sidebar.tsx
│   ├── Header.tsx
│   └── PageContainer.tsx
└── domain/                # 业务组件
    ├── ProjectCard.tsx
    ├── ChatMessage.tsx
    └── DocumentTree.tsx
```

### 4.2 必须封装的组件

#### 基础组件（ui/）

```tsx
// Button - 按钮
<Button variant="primary | secondary | ghost">
<Button size="sm | md | lg">
<Button loading={true}>

// Card - 卡片
<Card hover={true}>
<Card padding="sm | md | lg">

// Input - 输入框
<Input placeholder="..." />
<Input error="错误信息" />

// Textarea - 文本域
<Textarea rows={4} />

// Badge - 徽章
<Badge variant="success | warning | danger">

// Dialog - 对话框
<Dialog open={isOpen} onClose={...}>
```

#### 布局组件（layout/）

```tsx
// PageContainer - 页面容器
<PageContainer>
  <Sidebar />
  <MainContent />
</PageContainer>

// Sidebar - 侧边栏
<Sidebar width="280px">

// Header - 顶部栏
<Header title="..." actions={...} />
```

#### 业务组件（domain/）

```tsx
// ProjectCard - 项目卡片
<ProjectCard 
  title="..."
  genre="..."
  wordCount="..."
/>

// ChatMessage - 聊天消息
<ChatMessage 
  role="user | assistant"
  content="..."
/>

// DocumentTree - 文档树
<DocumentTree 
  nodes={...}
  onSelect={...}
/>
```

### 4.3 组件开发规范

```tsx
// ✅ 好的组件示例
import { cn } from '@/lib/utils'

interface ButtonProps {
  variant?: 'primary' | 'secondary' | 'ghost'
  size?: 'sm' | 'md' | 'lg'
  loading?: boolean
  disabled?: boolean
  children: React.ReactNode
  onClick?: () => void
  className?: string
}

export function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  disabled = false,
  children,
  onClick,
  className,
}: ButtonProps) {
  return (
    <button
      className={cn(
        // 基础样式
        'inline-flex items-center justify-center',
        'font-medium rounded-md transition',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        
        // 尺寸
        size === 'sm' && 'px-3 py-1.5 text-sm',
        size === 'md' && 'px-5 py-2 text-base',
        size === 'lg' && 'px-6 py-3 text-lg',
        
        // 变体
        variant === 'primary' && 'bg-accent text-white hover:opacity-90',
        variant === 'secondary' && 'bg-paper border hover:bg-sidebar',
        variant === 'ghost' && 'hover:bg-sidebar',
        
        // 自定义类名
        className
      )}
      disabled={disabled || loading}
      onClick={onClick}
    >
      {loading && <Spinner className="mr-2" />}
      {children}
    </button>
  )
}
```

---

## 5. 页面开发规范

### 5.1 页面结构模板

```tsx
// ✅ 标准页面结构
'use client'

import { useState } from 'react'
import { Button, Card, Input } from '@/components/ui'
import { PageContainer, Sidebar, Header } from '@/components/layout'

export function LobbyPage() {
  const [searchText, setSearchText] = useState('')

  return (
    <PageContainer>
      {/* 侧边栏 */}
      <Sidebar>
        <SidebarContent />
      </Sidebar>

      {/* 主内容 */}
      <div className="flex-1 flex flex-col">
        {/* 顶部 */}
        <Header 
          title="我的作品"
          subtitle="这是你的创作空间"
        />

        {/* 内容区 */}
        <main className="flex-1 p-8 overflow-auto">
          {/* 搜索栏 */}
          <div className="mb-6">
            <Input
              placeholder="搜索作品..."
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
            />
          </div>

          {/* 卡片网格 */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {projects.map(project => (
              <ProjectCard key={project.id} {...project} />
            ))}
          </div>
        </main>
      </div>
    </PageContainer>
  )
}
```

### 5.2 响应式设计

```tsx
// ✅ 使用 Tailwind 响应式前缀
<div className="
  flex flex-col          // 移动端：垂直布局
  md:flex-row            // 平板：水平布局
  gap-4                  // 移动端：16px 间距
  md:gap-6               // 平板：24px 间距
  p-4                    // 移动端：16px 内边距
  md:p-8                 // 平板：32px 内边距
">
  <Sidebar className="
    w-full               // 移动端：全宽
    md:w-64              // 平板：固定宽度
  " />
  <MainContent />
</div>
```

### 5.3 状态管理

```tsx
// ✅ 局部状态用 useState
function SearchBar() {
  const [query, setQuery] = useState('')
  return <Input value={query} onChange={e => setQuery(e.target.value)} />
}

// ✅ 全局状态用 Zustand
// stores/ui-store.ts
import { create } from 'zustand'

interface UIStore {
  sidebarOpen: boolean
  toggleSidebar: () => void
}

export const useUIStore = create<UIStore>((set) => ({
  sidebarOpen: true,
  toggleSidebar: () => set((state) => ({ 
    sidebarOpen: !state.sidebarOpen 
  })),
}))

// 使用
function Sidebar() {
  const { sidebarOpen, toggleSidebar } = useUIStore()
  return sidebarOpen ? <div>...</div> : null
}

// ✅ 服务端状态用 TanStack Query
function ProjectList() {
  const { data, isLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: fetchProjects,
  })
  
  if (isLoading) return <Loading />
  return <div>{data.map(...)}</div>
}
```

---

## 6. 实施检查清单

### 6.1 开发前

- [ ] 阅读 UI 设计文档（`docs/ui/ui-design.md`）
- [ ] 确认页面属于哪个模块（Lobby / Incubator / Studio / Engine / Lab）
- [ ] 确认需要哪些组件（是否已存在？需要新建？）
- [ ] 确认响应式断点（移动端 / 平板 / 桌面）

### 6.2 开发中

- [ ] 使用 CSS Variables 定义颜色、字体、间距
- [ ] 使用 Tailwind 类处理布局和间距
- [ ] 复用组件保持一致性
- [ ] 添加响应式类名（`md:` `lg:`）
- [ ] 添加悬停/聚焦状态（`hover:` `focus:`）
- [ ] 添加过渡动画（`transition`）

### 6.3 开发后

- [ ] 在不同屏幕尺寸测试（375px / 768px / 1440px）
- [ ] 检查颜色对比度（无障碍）
- [ ] 检查键盘导航（Tab / Enter / Esc）
- [ ] 检查加载状态和错误状态
- [ ] 代码审查（组件复用、样式一致性）

---

## 7. 常见问题

### Q1: 什么时候用 inline style，什么时候用 className？

**A**: 
- **CSS Variables**：用 inline style（`style={{ color: 'var(--color-accent)' }}`）
- **布局/间距**：用 Tailwind className（`className="flex gap-4"`）
- **动态样式**：用 inline style（`style={{ width: `${progress}%` }}`）

### Q2: 组件太多了，怎么管理？

**A**: 
- 基础组件放 `components/ui/`
- 布局组件放 `components/layout/`
- 业务组件放 `components/domain/`
- 每个目录有 `index.ts` 统一导出

### Q3: Tailwind 类名太长怎么办？

**A**: 
- 使用 `cn()` 工具函数合并类名
- 提取为组件（如果重复使用）
- 使用 `@apply` 指令（谨慎使用）

### Q4: 如何保证设计一致性？

**A**: 
- 所有颜色、字体、间距都用 CSS Variables
- 复用组件而不是复制代码
- 定期代码审查
- 使用 Storybook 展示组件库（可选）

---

## 8. 参考资源

- [Tailwind CSS 文档](https://tailwindcss.com/docs)
- [Next.js 文档](https://nextjs.org/docs)
- [TanStack Query 文档](https://tanstack.com/query)
- [Zustand 文档](https://zustand-demo.pmnd.rs/)
- [UI 设计文档](./ui-design.md)
- [UI 设计 v2](./ui-design-v2.md)
