# easyStory 前端页面 / 组件 / 样式对照

## 1. 这份文档看什么

这份文档用于回答三个问题：

1. 某个页面路由实际对应哪个 `page.tsx`
2. 这个页面真正的主组件在 `src/features/**` 哪个文件
3. 页面样式应该去哪里找

当前 `apps/web` 的样式不是“页面一个 css 文件”的模式，而是下面这套组合：

- 全局样式真值：`apps/web/src/app/globals.css`
- Tailwind token / 语义工具：`apps/web/tailwind.config.ts`
- Arco 基础样式：`apps/web/src/app/workspace/layout.tsx` 里引入的 `@arco-design/web-react/dist/css/arco.css`
- 页面专属样式：基本直接写在对应组件 `.tsx` 里的 Tailwind className 中

所以多数页面的“样式路径”其实就是：

- 该页面主组件文件本身
- 外加 `globals.css`
- 外加 `tailwind.config.ts`

## 2. 路由装配规则

前端页面的装配层级目前是：

```text
src/app/layout.tsx
  -> 引入 globals.css
  -> AppProviders（React Query + Arco ConfigProvider）

src/app/workspace/layout.tsx
  -> 引入 arco.css
  -> WorkspaceShell

src/app/**/page.tsx
  -> 只负责把路由挂到 features 页面组件
```

关键入口：

- 根布局：`apps/web/src/app/layout.tsx`
- 工作台布局：`apps/web/src/app/workspace/layout.tsx`
- 工作台壳层：`apps/web/src/features/workspace/components/workspace-shell.tsx`
- 全局样式：`apps/web/src/app/globals.css`
- Tailwind 配置：`apps/web/tailwind.config.ts`
- Provider 入口：`apps/web/src/lib/providers/app-providers.tsx`

## 3. 页面对照表

| 页面路由 | 路由入口 page | 主页面组件 | 关键子组件 / 壳层 | 样式路径 |
| --- | --- | --- | --- | --- |
| `/` | `apps/web/src/app/page.tsx` | 无，直接 `redirect("/auth/login")` | 无 | 无专属样式；只经过 `apps/web/src/app/layout.tsx` |
| `/auth/login` | `apps/web/src/app/auth/login/page.tsx` | `apps/web/src/features/auth/components/auth-form.tsx` | `AuthHero`、`AuthPanel` | `apps/web/src/features/auth/components/auth-form.tsx` + `apps/web/src/app/globals.css` + `apps/web/tailwind.config.ts` |
| `/auth/register` | `apps/web/src/app/auth/register/page.tsx` | `apps/web/src/features/auth/components/auth-form.tsx` | `AuthHero`、`AuthPanel` | `apps/web/src/features/auth/components/auth-form.tsx` + `apps/web/src/app/globals.css` + `apps/web/tailwind.config.ts` |
| `/workspace/lobby` | `apps/web/src/app/workspace/lobby/page.tsx` | `apps/web/src/features/lobby/components/lobby-page.tsx` | `WorkspaceShell`、`LobbyProjectShelf`、`LobbyEntryCard` | `apps/web/src/features/lobby/components/lobby-page.tsx`、`apps/web/src/features/lobby/components/lobby-project-shelf.tsx`、`apps/web/src/features/workspace/components/workspace-shell.tsx`、`apps/web/src/app/globals.css` |
| `/workspace/lobby/new` | `apps/web/src/app/workspace/lobby/new/page.tsx` | `apps/web/src/features/lobby/components/incubator-page.tsx` | `WorkspaceShell`、`IncubatorChatPanel`、`incubator-preview.tsx`、`incubator-panels-support.tsx` | `apps/web/src/features/lobby/components/incubator-page.tsx` 及其相邻组件 + `apps/web/src/features/workspace/components/workspace-shell.tsx` + `apps/web/src/app/globals.css` |
| `/workspace/lobby/templates` | `apps/web/src/app/workspace/lobby/templates/page.tsx` | `apps/web/src/features/lobby/components/template-library-page.tsx` | `WorkspaceShell`、`TemplateLibrarySidebar`、`TemplateLibraryDetailPanel`、`TemplateLibraryEditorPanel` | `apps/web/src/features/lobby/components/template-library-page.tsx` 及其相邻组件 + `apps/web/src/components/ui/section-card.tsx` + `apps/web/src/app/globals.css` |
| `/workspace/lobby/templates/[templateId]` | `apps/web/src/app/workspace/lobby/templates/[templateId]/page.tsx` | `apps/web/src/features/lobby/components/template-library-page.tsx` | 同模板库页，只是多了 `initialTemplateId` | 同上 |
| `/workspace/lobby/recycle-bin` | `apps/web/src/app/workspace/lobby/recycle-bin/page.tsx` | `apps/web/src/features/lobby/components/recycle-bin-page.tsx` | `WorkspaceShell`、`LobbyProjectShelf`、`RecycleBinClearDialog` | `apps/web/src/features/lobby/components/recycle-bin-page.tsx`、`apps/web/src/features/lobby/components/recycle-bin-dialogs.tsx`、`apps/web/src/app/globals.css` |
| `/workspace/lobby/settings` | `apps/web/src/app/workspace/lobby/settings/page.tsx` | `apps/web/src/features/lobby/components/lobby-settings-page.tsx` | `WorkspaceShell`、`LobbySettingsSidebar`、`LobbyAssistantSettingsPanel`、`CredentialCenter`、`AssistantSkillsPanel`、`AssistantAgentsPanel`、`AssistantHooksPanel`、`AssistantMcpPanel` | `apps/web/src/features/lobby/components/lobby-settings-page.tsx`、`apps/web/src/features/lobby/components/lobby-settings-sidebar.tsx`、`apps/web/src/features/lobby/components/lobby-assistant-settings-panel.tsx`、`apps/web/src/features/settings/components/**`、`apps/web/src/app/globals.css` |
| `/workspace/lobby/config-registry` | `apps/web/src/app/workspace/lobby/config-registry/page.tsx` | `apps/web/src/features/config-registry/components/config-registry-page.tsx` | `WorkspaceShell`、`ConfigRegistrySidebar`、`ConfigRegistryDetailPanel`、`ConfigRegistryEditorPanel` | `apps/web/src/features/config-registry/components/config-registry-page.tsx` 及其相邻组件 + `apps/web/src/app/globals.css` |
| `/workspace/project/[projectId]/studio` | `apps/web/src/app/workspace/project/[projectId]/studio/page.tsx` | `apps/web/src/features/studio/components/studio-page.tsx` | `WorkspaceShell`、`DocumentTree`、`MarkdownDocumentEditor`、`AiChatPanel`、`StudioChatComposer` | `apps/web/src/features/studio/components/studio-page.tsx`、`document-tree.tsx`、`markdown-document-editor.tsx`、`ai-chat-panel.tsx`、`studio-chat-composer.tsx`、`apps/web/src/features/workspace/components/workspace-shell.tsx`、`apps/web/src/app/globals.css` |
| `/workspace/project/[projectId]/engine` | `apps/web/src/app/workspace/project/[projectId]/engine/page.tsx` | `apps/web/src/features/engine/components/engine-page.tsx` | `WorkspaceShell`、`EnginePageShell`、`EngineDetailPanel`、`EngineExportPanel` | `apps/web/src/features/engine/components/engine-page.tsx`、`engine-page-shell.tsx`、其它 `engine-*.tsx`、`apps/web/src/features/workspace/components/workspace-shell.tsx`、`apps/web/src/app/globals.css` |
| `/workspace/project/[projectId]/lab` | `apps/web/src/app/workspace/project/[projectId]/lab/page.tsx` | `apps/web/src/features/lab/components/lab-page.tsx` | `WorkspaceShell`、`LabSidebar`、`LabDetailPanel`、`LabCreatePanel` | `apps/web/src/features/lab/components/lab-page.tsx` 及其相邻组件 + `apps/web/src/features/workspace/components/workspace-shell.tsx` + `apps/web/src/app/globals.css` |
| `/workspace/project/[projectId]/settings` | `apps/web/src/app/workspace/project/[projectId]/settings/page.tsx` | `apps/web/src/features/project-settings/components/project-settings-page.tsx` | `WorkspaceShell`、`ProjectSettingsSidebar`、`ProjectSettingsContent` | `apps/web/src/features/project-settings/components/project-settings-page.tsx`、`project-settings-sidebar.tsx`、`project-settings-content.tsx`、`apps/web/src/features/workspace/components/workspace-shell.tsx`、`apps/web/src/app/globals.css` |

## 4. 页面样式怎么找

### 4.1 先看这个顺序

如果你要改某个页面的样式，建议按下面顺序找：

1. 先找路由对应的 `src/app/**/page.tsx`
2. 看它导入了哪个 `src/features/**` 页面组件
3. 再看这个页面组件里拼了哪些子组件
4. 如果类名是 `panel-shell`、`hero-card`、`ink-input`、`ink-button-*` 这种语义类，去 `apps/web/src/app/globals.css`
5. 如果类名是 `text-accent-primary`、`rounded-4xl`、`p-card-xl` 这种 token 化工具，去 `apps/web/tailwind.config.ts`
6. 如果是 Arco 组件的默认外观，再看 `@arco-design/web-react/dist/css/arco.css` 和本地包裹组件

### 4.2 哪些样式主要在 `globals.css`

当前全局里最常用的页面样式原语包括：

- `panel-shell`
- `panel-muted`
- `hero-card`
- `ink-input`
- `ink-button`
- `ink-button-secondary`
- `ink-button-danger`
- `ink-button-hero`
- `label-text`
- `label-overline`

这些类的真值都在：

- `apps/web/src/app/globals.css`

### 4.3 哪些样式主要在页面组件自己

下面这些页面的布局和视觉主要写在页面组件本身，而不是拆到独立 css：

- `apps/web/src/features/auth/components/auth-form.tsx`
- `apps/web/src/features/lobby/components/lobby-page.tsx`
- `apps/web/src/features/lobby/components/incubator-page.tsx`
- `apps/web/src/features/studio/components/studio-page.tsx`
- `apps/web/src/features/engine/components/engine-page-shell.tsx`
- `apps/web/src/features/lab/components/lab-page.tsx`
- `apps/web/src/features/project-settings/components/project-settings-page.tsx`

## 5. 快速定位口诀

你以后要找某个页面，可以直接按这条路径走：

```text
路由
-> src/app/**/page.tsx
-> src/features/**/xxx-page.tsx
-> 同目录下的 sidebar / panel / dialog / shell 组件
-> globals.css
-> tailwind.config.ts
```

例如：

```text
/workspace/project/[projectId]/studio
-> src/app/workspace/project/[projectId]/studio/page.tsx
-> src/features/studio/components/studio-page.tsx
-> ai-chat-panel.tsx / studio-chat-composer.tsx / markdown-document-editor.tsx
-> src/app/globals.css
-> tailwind.config.ts
```

## 6. 当前结论

如果你觉得“页面不知道对应哪个组件和样式”，当前仓库最重要的认知是：

- `src/app/**` 不是页面实现主战场，只是路由挂载层
- 真正页面实现几乎都在 `src/features/**/components/`
- 样式没有分散到很多 css 文件，基本集中在：
  - `apps/web/src/app/globals.css`
  - `apps/web/tailwind.config.ts`
  - 各页面组件自己的 `className`
