# 项目设置页面 UI 文档中心

## 📚 文档导航

本目录包含项目设置页面的完整 UI/UX 设计文档。根据你的需求选择合适的文档：

### 🎯 我是...

#### 产品经理 / 设计师
👉 **推荐阅读**：
1. `project-settings-ui-redesign.md` - 了解页面的真实结构和设计规范
2. `project-settings-ui-analysis.md` - 了解当前设计的优缺点

#### 前端开发者
👉 **推荐阅读**：
1. `project-settings-quick-reference.md` - 快速找到你需要修改的文件
2. `project-settings-component-map.md` - 了解完整的组件结构
3. `project-settings-ui-improvements.md` - 了解需要改进的地方和具体方案

#### 新加入的团队成员
👉 **推荐阅读顺序**：
1. `project-settings-ui-redesign.md` - 了解页面的整体结构
2. `project-settings-component-map.md` - 了解各个组件的位置
3. `project-settings-quick-reference.md` - 学习常见的改进任务

---

## 📄 文档清单

### 1. 项目设置页面 UI/UX 设计规范
**文件**：`project-settings-ui-redesign.md`

**内容**：
- 文档定位和真值边界
- 页面路由和骨架结构
- 共享视觉基线
- 各标签页的真实结构和问题
- 响应式设计规范
- 后续实现约束

**适合**：了解页面的整体设计和约束

**关键信息**：
- 页面采用 `280px + 1fr` 双列布局
- 最大宽度 `1600px`
- 6 个标签页：设置、规则、AI偏好、Skills、MCP、审计
- 按 tab 粒度维护 dirty state

---

### 2. 项目设置页面 UI 布局分析报告
**文件**：`project-settings-ui-analysis.md`

**内容**：
- 执行摘要（整体评价 8.5/10）
- 布局架构验证
- 设计系统验证
- 各标签页布局分析
- 响应式设计验证
- 交互设计验证
- 问题清单和改进建议
- 代码质量评估
- 总体结论

**适合**：了解当前设计的优缺点

**关键发现**：
- ✅ 布局架构清晰，设计系统完整
- ⚠️ 内容卡片无宽度限制
- ⚠️ 表单字段间距不统一
- ⚠️ 移动端 < 640px 优化不足

---

### 3. 项目设置页面 UI 改进实施指南
**文件**：`project-settings-ui-improvements.md`

**内容**：
- 3 个高优先级问题（需立即改进）
- 5 个中低优先级建议
- 每个问题的具体代码示例
- 实施步骤和时间表
- 完整的测试清单

**适合**：了解具体的改进方案和实施步骤

**高优先级问题**：
1. 内容卡片宽度未限制 → 添加 `max-width: 900px`
2. 表单字段间距不统一 → 建立全局间距规范
3. 移动端 < 640px 优化不足 → 隐藏或改为抽屉式侧栏

---

### 4. 项目设置页面 - 完整组件映射表
**文件**：`project-settings-component-map.md`

**内容**：
- 页面路由和骨架组件
- 各标签页的完整组件结构
- 全局共享组件列表
- 样式文件总览
- 数据流向
- 改进建议映射
- 组件清单统计

**适合**：快速找到你需要修改的组件和文件

**关键统计**：
- 1 个主页面
- 3 个骨架组件
- 18 个标签页组件
- 15+ 个全局共享组件
- 20+ 个样式文件

---

### 5. 项目设置页面 - 快速参考指南
**文件**：`project-settings-quick-reference.md`

**内容**：
- 一句话总结
- 快速导航（找页面、找组件、找样式）
- 常见改进任务（7 个任务的具体步骤）
- 全局共享组件速查
- 文件结构速查
- 常见工作流
- 常见问题排查
- 下一步行动

**适合**：快速查找信息和解决问题

**常见任务**：
1. 修改页面布局
2. 修改项目设定表单
3. 修改规则编辑器
4. 修改 AI 偏好表单
5. 修改 Skills 面板
6. 修改 MCP 面板
7. 修改审计面板

---

## 🎯 快速开始

### 我要修改页面布局
1. 打开 `project-settings-quick-reference.md`
2. 找到"任务 1：修改页面布局"
3. 按照步骤修改 `project-settings-page.module.css`
4. 测试各个断点

### 我要了解组件结构
1. 打开 `project-settings-component-map.md`
2. 找到你感兴趣的标签页
3. 查看组件树和文件位置
4. 打开对应的源码文件

### 我要实施改进建议
1. 打开 `project-settings-ui-improvements.md`
2. 选择一个高优先级问题
3. 按照"改进方案"和"实施步骤"操作
4. 进行测试

### 我是新加入的团队成员
1. 阅读 `project-settings-ui-redesign.md` 了解整体结构
2. 阅读 `project-settings-component-map.md` 了解组件位置
3. 阅读 `project-settings-quick-reference.md` 学习常见任务
4. 打开源码文件，对照文档理解代码

---

## 📊 文档关系图

```
项目设置页面（1 个）
  ├─ 标签页 1：设置
  ├─ 标签页 2：规则
  ├─ 标签页 3：AI 偏好
  ├─ 标签页 4：Skills
  ├─ 标签页 5：MCP
  └─ 标签页 6：审计

project-settings-ui-redesign.md (设计规范)
    ↓
    ├─→ project-settings-ui-analysis.md (分析报告)
    │       ↓
    │       └─→ project-settings-ui-improvements.md (改进指南)
    │
    └─→ project-settings-component-map.md (组件映射)
            ↓
            └─→ project-settings-quick-reference.md (快速参考)
```

---

## 🔑 关键概念

### 页面结构
- **路由**：`/workspace/project/[projectId]/settings`
- **页面数量**：1 个项目设置页面
- **标签页数量**：6 个（通过 `?tab=xxx` 切换）
- **布局**：`280px 侧栏 + 1fr 内容区`
- **最大宽度**：`1600px`
- **标签页列表**：设置、规则、AI偏好、Skills、MCP、审计

### 设计系统
- **颜色**：全局 CSS 变量定义在 `globals.css`
- **排版**：使用 `--font-serif` 和 `--font-sans`
- **间距**：遵循 8px 倍数规范
- **组件**：复用全局共享组件，不单独定义

### 交互保护
- **Dirty State**：按 tab 粒度维护
- **未保存保护**：覆盖切换 tab、浏览器返回、刷新关闭
- **Escape 拦截**：防止误触关闭

---

## 📈 改进优先级

### 🔴 高优先级（立即改进）
- [ ] 添加内容卡片宽度限制
- [ ] 统一表单字段间距
- [ ] 优化移动端 < 640px 布局

### 🟡 中优先级（重要改进）
- [ ] 增强字段分组语义
- [ ] 改进加载态
- [ ] 增强可访问性

### 🟢 低优先级（体验优化）
- [ ] 优化审计页过滤器
- [ ] 添加微交互动画
- [ ] 完整的视觉回归测试

---

## 🔗 相关资源

### 源码位置
- **页面入口**：`apps/web/src/app/workspace/project/[projectId]/settings/page.tsx`
- **主页面**：`apps/web/src/features/project-settings/components/project-settings-page.tsx`
- **全局样式**：`apps/web/src/app/globals.css`
- **全局组件**：`apps/web/src/components/ui/`

### 其他文档
- **全局设计规范**：`docs/ui/ui-design.md`
- **实现指南**：`docs/ui/implementation-guide.md`

---

## 💡 使用建议

1. **第一次阅读**：按照"我是..."的推荐顺序阅读
2. **快速查找**：使用 `project-settings-quick-reference.md`
3. **深入理解**：阅读 `project-settings-component-map.md`
4. **实施改进**：按照 `project-settings-ui-improvements.md` 的步骤操作
5. **定期更新**：当源码发生变化时，更新相应的文档

---

## 📝 文档维护

### 何时更新文档
- 添加新的标签页或组件
- 修改页面布局或样式
- 变更全局设计 token
- 发现新的问题或改进方案

### 如何更新文档
1. 更新对应的源码文件
2. 更新 `project-settings-ui-redesign.md` 中的"真值边界"
3. 更新 `project-settings-component-map.md` 中的组件映射
4. 更新 `project-settings-quick-reference.md` 中的快速参考
5. 如有重大变化，更新 `project-settings-ui-analysis.md`

---

## ❓ 常见问题

**Q: 这些文档是否会自动更新？**
A: 不会。当源码发生变化时，需要手动更新文档。

**Q: 我应该按照哪个文档来修改代码？**
A: 优先参考 `project-settings-ui-redesign.md` 中的"真值边界"，然后查看源码。

**Q: 如果文档和源码不一致怎么办？**
A: 以源码为准。请更新文档以保持同步。

**Q: 我可以修改这些文档吗？**
A: 可以。请确保修改后的文档与源码保持一致。

---

## 📞 联系方式

如有问题或建议，请：
1. 查看 `project-settings-quick-reference.md` 中的"常见问题排查"
2. 查看源码注释
3. 与团队讨论

---

**最后更新**：2026-04-01
**文档版本**：1.0
**状态**：生效

