# 项目设置页面 UI 文档

## 文档导航

### 核心文档

| 文档 | 内容 |
|------|------|
| [project-settings-ui-redesign.md](project-settings-ui-redesign.md) | 设计规范：页面结构、组件、交互边界 |
| [project-settings-ui-improvements.md](project-settings-ui-improvements.md) | 改进指南：问题修正、优化建议、涉及文件 |

---

## 快速查找

### 找页面
- 路由：`/workspace/project/[projectId]/settings`
- 入口：`apps/web/src/app/workspace/project/[projectId]/settings/page.tsx`

### 找组件
- 主页面：`ProjectSettingsPage` → `features/project-settings/components/`
- 项目设定：`ProjectSettingEditor` → `features/studio/components/`
- 规则/AI偏好/Skills/MCP：`Assistant*` → `features/settings/components/`
- 审计：`ProjectAuditPanel` → `features/project-settings/components/`

### 找样式
- 页面骨架：`project-settings-page.module.css`
- 全局 token：`apps/web/src/app/globals.css`

---

## 文档更新记录

- 2026-04-01：整合文档，删除冗余
