# 11 - 内容导出

| 字段 | 内容 |
|---|---|
| 文档类型 | 设计规格 |
| 所属领域 | 导出功能、格式支持、排版 |
| 优先级 | MVP 建议简化实现 |
| 来源 | design-review-supplement §6, §16, §24.12 |

---

## 1. 概述

easyStory 需要将生成的小说内容导出为用户可用的格式。本文档定义导出功能的完整规格：支持的格式、导出范围、版本选择、排版模板，以及导出时不完整内容的处理策略。

**关键决策**: 导出文件存储在文件系统上（非数据库 BLOB），数据库仅记录导出元数据和文件路径。

---

## 2. 支持的导出格式

### 2.1 格式优先级

| 格式 | 用途 | 优先级 |
|-----|------|--------|
| TXT | 纯文本，通用 | MVP 必须 |
| Markdown | 带格式，易编辑 | MVP 必须 |
| DOCX | Word 文档，出版社常用 | MVP 建议 |
| EPUB | 电子书格式 | 延后 |
| PDF | 打印/分享 | 延后 |

### 2.2 格式说明

- **TXT**: 无格式纯文本，兼容性最强，适合快速查看和复制
- **Markdown**: 保留标题、分隔符等结构信息，适合二次编辑
- **DOCX**: 支持复杂排版（字体、段落、页眉页脚），出版场景必备
- **EPUB / PDF**: 面向最终读者，排版要求更高，可延后实现

---

## 3. 导出配置

### 3.1 基础配置

```yaml
export:
  format: "txt"  # txt / markdown / docx
  include:
    - "outline"
    - "chapters"
  exclude:
    - "drafts"
  template: "default"  # 导出模板（控制格式）
  metadata:
    author: "{{ project.owner.username }}"
    title: "{{ project.name }}"
    created_at: "{{ project.created_at }}"
```

### 3.2 配置字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `format` | string | 导出格式 |
| `include` | list | 要包含的内容类型 |
| `exclude` | list | 要排除的内容类型 |
| `template` | string | 使用的排版模板名称 |
| `metadata` | object | 文档元信息，支持模板变量 |

### 3.3 导出模板示例（Jinja2）

```jinja2
# {{ metadata.title }}

作者: {{ metadata.author }}
创建时间: {{ metadata.created_at }}

---

## 大纲

{{ outline.content }}

---

{% for chapter in chapters %}
## {{ chapter.title }}

{{ chapter.content }}

{% endfor %}
```

---

## 4. 导出范围

### 4.1 可选范围

```
用户选择导出范围:
  +-- 整本书（所有已完成章节）
  +-- 选择章节（勾选要导出的章节）
  +-- 单章导出
  +-- 设定导出（大纲 + 人物 + 世界观）
```

### 4.2 范围说明

| 范围 | 包含内容 | 适用场景 |
|------|---------|---------|
| 整本书 | 所有已完成状态的章节 | 成书导出 |
| 选择章节 | 用户勾选的指定章节 | 部分导出、审阅 |
| 单章导出 | 单独一章 | 快速查看、分享单章 |
| 设定导出 | 大纲 + 人物设定 + 世界观设定 | 设定资料归档 |

---

## 5. 版本选择

### 5.1 版本策略

```yaml
export:
  version_strategy: "latest"
  # latest:   使用最新版本
  # specific: 指定各章版本
  # best:     使用标记为"最佳"的版本

  # 当 version_strategy 为 specific 时:
  chapter_versions:
    chapter_1: 3               # 第1章用版本3
    chapter_2: 2               # 第2章用版本2
    # 未指定的章节使用最新版本
```

### 5.2 策略说明

| 策略 | 行为 | 适用场景 |
|------|------|---------|
| `latest` | 每章取最新版本 | 默认选项，快速导出 |
| `specific` | 按 `chapter_versions` 指定 | 精细控制各章版本 |
| `best` | 取用户标记为"最佳"的版本 | 多版本迭代后选优导出 |

### 5.3 `best` 策略约束

- `best` 依赖 [内容编辑](./05-content-editor.md) 中 `ContentVersion.is_best`
- “最佳版本”必须由用户显式标记，不做自动推断
- 若某章节没有 `is_best=true` 的版本，导出预检必须明确提示用户：
  - 改用 `latest`
  - 为缺失章节手动指定版本
  - 取消导出

---

## 6. 排版模板

### 6.1 模板配置

```yaml
export:
  template: "novel_standard"   # 导出模板名称
  formatting:
    chapter_prefix: "第{n}章"   # 章节标题格式
    chapter_separator: "---"    # 章节分隔符
    include_title_page: true    # 是否包含封面页
    include_toc: true           # 是否包含目录
    paragraph_indent: true      # 段落首行缩进
    line_spacing: 1.5           # 行间距
```

### 6.2 排版参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `chapter_prefix` | string | `"第{n}章"` | 章节编号格式，`{n}` 为章节序号 |
| `chapter_separator` | string | `"---"` | 章节间分隔符 |
| `include_title_page` | bool | `true` | 是否生成封面页（含书名、作者） |
| `include_toc` | bool | `true` | 是否生成目录 |
| `paragraph_indent` | bool | `true` | 段落首行缩进（中文排版常用） |
| `line_spacing` | float | `1.5` | 行间距倍数 |

### 6.3 模板扩展

- 内置 `default` 和 `novel_standard` 两个模板
- 用户可自定义模板（保存为 YAML 配置）
- 不同格式（TXT / Markdown / DOCX）可使用不同模板

---

## 7. 不完整内容处理

### 7.1 导出前预检流程

```
导出前预检:

1. 扫描导出范围内的所有章节
2. 按状态分类:
   - completed:  正常导出
   - draft:      提示 "第X章为草稿状态"
   - failed:     提示 "第X章生成失败"
   - skipped:    提示 "第X章被跳过"
   - generating: 提示 "第X章正在生成中，请等待完成"

3. 如果有 draft / failed / skipped:
   弹出确认对话框（见 7.2）

4. 如果有 generating:
   阻止导出，提示等待完成。
```

### 7.2 用户处理选项

当导出范围内存在非 completed 状态的章节时，系统弹出确认对话框：

```
"以下章节状态异常:
  - 第5章: 草稿
  - 第8章: 已跳过

选择处理方式:
  ( ) 跳过这些章节（导出时不包含）
  ( ) 包含占位符（'[第X章: 待完成]'）
  ( ) 包含当前内容（草稿/最后可用版本）
  ( ) 取消导出"
```

### 7.3 各状态处理行为

| 章节状态 | "跳过" | "占位符" | "包含当前内容" |
|---------|--------|---------|--------------|
| completed | 正常导出 | 正常导出 | 正常导出 |
| draft | 不包含 | `[第X章: 待完成]` | 导出草稿内容 |
| failed | 不包含 | `[第X章: 待完成]` | 导出最后可用版本（如有） |
| skipped | 不包含 | `[第X章: 待完成]` | 不包含（无内容） |
| generating | 阻止导出 | 阻止导出 | 阻止导出 |

### 7.4 设计要点

- `generating` 状态始终阻止导出，避免导出不完整的中间结果
- "包含当前内容"选项对 failed 章节尝试导出最后可用版本；如果没有任何版本则等同于"跳过"
- 预检结果应在 UI 中清晰展示，让用户知情决策

---

## 8. 存储策略

导出文件存储在文件系统上，不使用数据库 BLOB：

- 导出文件写入项目对应的文件系统目录（如 `exports/{project_id}/`）
- 数据库中记录导出元数据：文件路径、格式、大小、创建时间、导出配置快照
- 文件系统存储便于大文件处理，避免数据库膨胀
- 清理策略：可配置导出文件保留期限，过期自动清理
