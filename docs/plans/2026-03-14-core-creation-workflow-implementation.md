# easyStory 核心创作流程实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现 easyStory 的核心创作流程 MVP,包括节点系统、手动模式、上下文注入和串行审核功能。

**Architecture:** FastAPI + LangGraph + SQLAlchemy 后端,Next.js + React 前端。工作流引擎负责节点编排,配置系统负责 YAML 解析,LiteLLM 统一模型调用。

**Tech Stack:** Python 3.11+, FastAPI, LangGraph, SQLAlchemy, Pydantic, LiteLLM, Jinja2, PyYAML, Next.js 14, React 18, TypeScript

---

## MVP 范围

**Phase 1: 后端核心 (Tasks 1-8)**
- 数据库模型
- 配置系统
- 工作流引擎
- 上下文注入
- 串行审核

**Phase 2: API 层 (Tasks 9-11)**
- RESTful API
- WebSocket 通信

**Phase 3: 前端工作台 (Tasks 12-15)**
- 项目管理
- 节点配置
- 工作流监控

---

## Task 1: 数据库模型定义

**Test:** `backend/tests/unit/test_models.py`

```python
import pytest
from app.models.project import Project
from app.models.workflow import WorkflowExecution, NodeExecution
from app.models.content import Content, ContentVersion

def test_project_creation():
    project = Project(name="测试小说", description="测试")
    assert project.name == "测试小说"
    assert project.status == "active"

def test_workflow_execution():
    execution = WorkflowExecution(
        project_id=1,
        workflow_id="workflow.test",
        status="pending"
    )
    assert execution.status == "pending"
    assert execution.current_node_index == 0

def test_node_execution():
    node = NodeExecution(
        workflow_execution_id=1,
        node_id="outline",
        node_type="generate",
        status="pending"
    )
    assert node.status == "pending"
    assert node.retry_count == 0

def test_content_versioning():
    content = Content(project_id=1, content_type="outline", title="大纲")
    version = ContentVersion(
        content_id=1,
        version=1,
        content_text="内容",
        created_by="system"
    )
    assert version.version == 1
    assert version.is_current is True
```

**Run:** `pytest tests/unit/test_models.py -v`
**Expected:** FAIL - 模型未定义

**Implementation:** `backend/app/models/`

创建 `base.py`:
```python
from datetime import datetime
from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func

class Base(DeclarativeBase):
    pass

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

创建 `project.py`:
```python
from sqlalchemy import String, Text, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from enum import Enum
from .base import Base, TimestampMixin

class ProjectStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"

class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ProjectStatus] = mapped_column(SQLEnum(ProjectStatus), default=ProjectStatus.ACTIVE)

    workflow_executions: Mapped[list["WorkflowExecution"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    contents: Mapped[list["Content"]] = relationship(back_populates="project", cascade="all, delete-orphan")
```

创建 `workflow.py`:
```python
from sqlalchemy import String, Integer, Text, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from enum import Enum
from .base import Base, TimestampMixin

class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"

class WorkflowExecution(Base, TimestampMixin):
    __tablename__ = "workflow_executions"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    workflow_id: Mapped[str] = mapped_column(String(200))
    status: Mapped[ExecutionStatus] = mapped_column(SQLEnum(ExecutionStatus), default=ExecutionStatus.PENDING)
    current_node_index: Mapped[int] = mapped_column(Integer, default=0)
    config: Mapped[dict | None] = mapped_column(JSON)
    error_message: Mapped[str | None] = mapped_column(Text)

    project: Mapped["Project"] = relationship(back_populates="workflow_executions")
    node_executions: Mapped[list["NodeExecution"]] = relationship(back_populates="workflow_execution", cascade="all, delete-orphan")

class NodeExecution(Base, TimestampMixin):
    __tablename__ = "node_executions"

    id: Mapped[int] = mapped_column(primary_key=True)
    workflow_execution_id: Mapped[int] = mapped_column(ForeignKey("workflow_executions.id"))
    node_id: Mapped[str] = mapped_column(String(200))
    node_type: Mapped[str] = mapped_column(String(50))
    sequence: Mapped[int] = mapped_column(Integer)
    status: Mapped[ExecutionStatus] = mapped_column(SQLEnum(ExecutionStatus), default=ExecutionStatus.PENDING)
    input_data: Mapped[dict | None] = mapped_column(JSON)
    output_data: Mapped[dict | None] = mapped_column(JSON)
    error_message: Mapped[str | None] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)

    workflow_execution: Mapped["WorkflowExecution"] = relationship(back_populates="node_executions")
```

创建 `content.py`:
```python
from sqlalchemy import String, Integer, Text, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin

class Content(Base, TimestampMixin):
    __tablename__ = "contents"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    content_type: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(500))

    project: Mapped["Project"] = relationship(back_populates="contents")
    versions: Mapped[list["ContentVersion"]] = relationship(back_populates="content", cascade="all, delete-orphan")

class ContentVersion(Base, TimestampMixin):
    __tablename__ = "content_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    content_id: Mapped[int] = mapped_column(ForeignKey("contents.id"))
    version: Mapped[int] = mapped_column(Integer)
    content_text: Mapped[str] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(String(100))
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    change_description: Mapped[str | None] = mapped_column(Text)

    content: Mapped["Content"] = relationship(back_populates="versions")
```

**Run:** `pytest tests/unit/test_models.py -v`
**Expected:** PASS

**Commit:** `git commit -m "feat: implement database models for project, workflow, and content"`

---

## Task 2: 配置系统实现

**Test:** `backend/tests/unit/test_config_loader.py`

```python
import pytest
from pathlib import Path
from app.core.config_loader import ConfigLoader

@pytest.fixture
def config_loader():
    return ConfigLoader(config_root=Path("config"))

def test_load_skill(config_loader):
    skill = config_loader.load_skill("skill.outline.xuanhuan")
    assert skill.id == "skill.outline.xuanhuan"
    assert "玄幻" in skill.prompt

def test_load_workflow(config_loader):
    workflow = config_loader.load_workflow("workflow.xuanhuan_manual")
    assert workflow.id == "workflow.xuanhuan_manual"
    assert len(workflow.nodes) > 0

def test_validate_skill_input(config_loader):
    skill = config_loader.load_skill("skill.outline.xuanhuan")
    with pytest.raises(ValueError):
        config_loader.validate_skill_input(skill, {})

    valid_input = {"genre": "玄幻", "protagonist": "废柴", "world_setting": "修仙"}
    assert config_loader.validate_skill_input(skill, valid_input) is True
```

**Run:** `pytest tests/unit/test_config_loader.py -v`
**Expected:** FAIL

**Implementation:** `backend/app/schemas/config_schemas.py`

```python
from pydantic import BaseModel, Field
from typing import Literal

class SkillVariable(BaseModel):
    type: Literal["string", "integer", "boolean"]
    required: bool = False
    description: str | None = None

class SkillConfig(BaseModel):
    id: str
    name: str
    category: str
    prompt: str
    variables: dict[str, SkillVariable] = Field(default_factory=dict)

class NodeConfig(BaseModel):
    id: str
    name: str
    type: Literal["generate", "review", "export"]
    skill: str | None = None
    auto_proceed: bool = False
    auto_review: bool = False

class WorkflowConfig(BaseModel):
    id: str
    name: str
    nodes: list[NodeConfig]
```

**Implementation:** `backend/app/core/config_loader.py`

```python
import yaml
from pathlib import Path
from app.schemas.config_schemas import SkillConfig, WorkflowConfig

class ConfigLoader:
    def __init__(self, config_root: Path):
        self.config_root = config_root
        self.skills_cache: dict[str, SkillConfig] = {}
        self.workflows_cache: dict[str, WorkflowConfig] = {}
        self._load_all_configs()

    def _load_all_configs(self):
        skills_dir = self.config_root / "skills"
        if skills_dir.exists():
            for yaml_file in skills_dir.rglob("*.yaml"):
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    skill = SkillConfig(**data['skill'])
                    self.skills_cache[skill.id] = skill

        workflows_dir = self.config_root / "workflows"
        if workflows_dir.exists():
            for yaml_file in workflows_dir.glob("*.yaml"):
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    workflow = WorkflowConfig(**data['workflow'])
                    self.workflows_cache[workflow.id] = workflow

    def load_skill(self, skill_id: str) -> SkillConfig:
        if skill_id not in self.skills_cache:
            raise ValueError(f"Skill not found: {skill_id}")
        return self.skills_cache[skill_id]

    def load_workflow(self, workflow_id: str) -> WorkflowConfig:
        if workflow_id not in self.workflows_cache:
            raise ValueError(f"Workflow not found: {workflow_id}")
        return self.workflows_cache[workflow_id]

    def validate_skill_input(self, skill: SkillConfig, input_data: dict) -> bool:
        for var_name, var_config in skill.variables.items():
            if var_config.required and var_name not in input_data:
                raise ValueError(f"Required variable missing: {var_name}")
        return True
```

**示例配置:** `config/skills/outline/xuanhuan.yaml`

```yaml
skill:
  id: "skill.outline.xuanhuan"
  name: "玄幻大纲生成"
  category: "outline"
  prompt: |
    你是资深玄幻小说作家。

    【题材】{{ genre }}
    【主角】{{ protagonist }}
    【世界观】{{ world_setting }}

    生成包含开端、发展、高潮、结局的大纲。

  variables:
    genre:
      type: "string"
      required: true
    protagonist:
      type: "string"
      required: true
    world_setting:
      type: "string"
      required: true
```

**示例配置:** `config/workflows/xuanhuan-manual.yaml`

```yaml
workflow:
  id: "workflow.xuanhuan_manual"
  name: "玄幻小说手动创作"
  nodes:
    - id: "outline"
      name: "生成大纲"
      type: "generate"
      skill: "skill.outline.xuanhuan"
      auto_proceed: false
```

**Run:** `pytest tests/unit/test_config_loader.py -v`
**Expected:** PASS

**Commit:** `git commit -m "feat: implement configuration system with YAML loader"`

---

## Task 3: LangGraph 工作流引擎

**Test:** `backend/tests/unit/test_workflow_engine.py`

```python
import pytest
from app.services.workflow_engine import WorkflowEngine
from app.core.config_loader import ConfigLoader

@pytest.fixture
def engine():
    config_loader = ConfigLoader(Path("config"))
    return WorkflowEngine(config_loader)

@pytest.mark.asyncio
async def test_execute_node(engine):
    result = await engine.execute_node(
        node_id="outline",
        node_config={"type": "generate", "skill": "skill.outline.xuanhuan"},
        input_data={"genre": "玄幻", "protagonist": "废柴", "world_setting": "修仙"}
    )
    assert result["status"] == "completed"
    assert "output" in result

@pytest.mark.asyncio
async def test_manual_mode_pauses(engine):
    workflow_config = engine.config_loader.load_workflow("workflow.xuanhuan_manual")
    execution = await engine.start_workflow(workflow_config, project_id=1)

    assert execution.status == "paused"
    assert execution.current_node_index == 0
```

**Run:** `pytest tests/unit/test_workflow_engine.py -v`
**Expected:** FAIL

**Implementation:** `backend/app/services/workflow_engine.py`

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict
from app.core.config_loader import ConfigLoader
from app.schemas.config_schemas import WorkflowConfig, NodeConfig

class WorkflowState(TypedDict):
    project_id: int
    current_node: int
    nodes_data: dict
    status: str

class WorkflowEngine:
    def __init__(self, config_loader: ConfigLoader):
        self.config_loader = config_loader

    async def execute_node(self, node_id: str, node_config: dict, input_data: dict) -> dict:
        """执行单个节点"""
        if node_config["type"] == "generate":
            skill_id = node_config.get("skill")
            if skill_id:
                skill = self.config_loader.load_skill(skill_id)
                # 渲染提示词模板
                from jinja2 import Template
                prompt = Template(skill.prompt).render(**input_data)

                # 调用 LLM (简化版)
                output = await self._call_llm(prompt)

                return {"status": "completed", "output": output}

        return {"status": "failed", "error": "Unknown node type"}

    async def _call_llm(self, prompt: str) -> str:
        """调用 LLM (通过 LiteLLM)"""
        # TODO: 实现 LiteLLM 调用
        return "Generated content"

    async def start_workflow(self, workflow_config: WorkflowConfig, project_id: int):
        """启动工作流"""
        # 手动模式: 执行第一个节点后暂停
        first_node = workflow_config.nodes[0]

        if not first_node.auto_proceed:
            # 创建执行记录并暂停
            from app.models.workflow import WorkflowExecution, ExecutionStatus
            execution = WorkflowExecution(
                project_id=project_id,
                workflow_id=workflow_config.id,
                status=ExecutionStatus.PAUSED,
                current_node_index=0
            )
            return execution

        # 自动模式: 继续执行
        return await self._execute_workflow(workflow_config, project_id)

    async def _execute_workflow(self, workflow_config: WorkflowConfig, project_id: int):
        """执行完整工作流"""
        # TODO: 实现完整的工作流执行逻辑
        pass
```

**Run:** `pytest tests/unit/test_workflow_engine.py -v`
**Expected:** PASS

**Commit:** `git commit -m "feat: implement LangGraph workflow engine with manual mode"`

---

## Task 4: 上下文注入机制

**Test:** `backend/tests/unit/test_context_builder.py`

```python
import pytest
from app.services.context_builder import ContextBuilder

@pytest.mark.asyncio
async def test_build_context():
    builder = ContextBuilder()
    context = await builder.build_context(
        project_id=1,
        injection_rules=[
            {"type": "outline"},
            {"type": "previous_chapters", "count": 2}
        ]
    )
    assert "outline" in context
    assert "previous_chapters" in context
```

**Run:** `pytest tests/unit/test_context_builder.py -v`
**Expected:** FAIL

**Implementation:** `backend/app/services/context_builder.py`

```python
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.content import Content, ContentVersion

class ContextBuilder:
    async def build_context(self, project_id: int, injection_rules: list[dict], db: AsyncSession = None) -> dict:
        """构建上下文"""
        context = {}

        for rule in injection_rules:
            if rule["type"] == "outline":
                context["outline"] = await self._load_outline(project_id, db)
            elif rule["type"] == "previous_chapters":
                count = rule.get("count", 1)
                context["previous_chapters"] = await self._load_previous_chapters(project_id, count, db)

        return context

    async def _load_outline(self, project_id: int, db: AsyncSession) -> str:
        """加载大纲"""
        # TODO: 从数据库查询
        return "大纲内容"

    async def _load_previous_chapters(self, project_id: int, count: int, db: AsyncSession) -> list[str]:
        """加载前 N 章"""
        # TODO: 从数据库查询
        return ["第1章内容", "第2章内容"][:count]
```

**Run:** `pytest tests/unit/test_context_builder.py -v`
**Expected:** PASS

**Commit:** `git commit -m "feat: implement context injection mechanism"`

---

## Task 5: 串行审核系统

**Test:** `backend/tests/unit/test_review_executor.py`

```python
import pytest
from app.services.review_executor import ReviewExecutor

@pytest.mark.asyncio
async def test_serial_review():
    executor = ReviewExecutor()
    results = await executor.execute_serial_review(
        content="测试内容",
        reviewers=["agent.style_checker", "agent.logic_checker"]
    )
    assert len(results) == 2
    assert all(r["status"] in ["passed", "failed"] for r in results)
```

**Run:** `pytest tests/unit/test_review_executor.py -v`
**Expected:** FAIL

**Implementation:** `backend/app/services/review_executor.py`

```python
class ReviewExecutor:
    async def execute_serial_review(self, content: str, reviewers: list[str]) -> list[dict]:
        """串行执行审核"""
        results = []

        for reviewer_id in reviewers:
            result = await self._execute_single_review(content, reviewer_id)
            results.append(result)

            # 如果审核失败,可以选择中断
            if result["status"] == "failed":
                break

        return results

    async def _execute_single_review(self, content: str, reviewer_id: str) -> dict:
        """执行单个审核"""
        # TODO: 加载 Agent 配置并调用 LLM
        return {"reviewer": reviewer_id, "status": "passed", "feedback": ""}
```

**Run:** `pytest tests/unit/test_review_executor.py -v`
**Expected:** PASS

**Commit:** `git commit -m "feat: implement serial review executor"`

---

## Task 6-8: 数据库迁移、LiteLLM 集成、FastAPI 应用

**简化说明:**
- Task 6: 使用 Alembic 创建数据库迁移
- Task 7: 集成 LiteLLM 实现模型路由
- Task 8: 创建 FastAPI 应用入口和依赖注入

**关键文件:**
- `backend/alembic/versions/001_initial.py`
- `backend/app/services/model_router.py`
- `backend/app/main.py`

---

## Task 9-11: API 层实现

**关键端点:**

`backend/app/api/v1/projects.py`:
```python
from fastapi import APIRouter, Depends
from app.schemas.project_schemas import ProjectCreate, ProjectResponse

router = APIRouter()

@router.post("/", response_model=ProjectResponse)
async def create_project(project: ProjectCreate):
    # 创建项目
    pass

@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: int):
    # 获取项目
    pass
```

`backend/app/api/v1/workflows.py`:
```python
from fastapi import APIRouter

router = APIRouter()

@router.post("/{project_id}/workflows/start")
async def start_workflow(project_id: int, workflow_id: str):
    # 启动工作流
    pass

@router.post("/{project_id}/workflows/{execution_id}/continue")
async def continue_workflow(project_id: int, execution_id: int):
    # 继续执行工作流
    pass
```

`backend/app/api/v1/websocket.py`:
```python
from fastapi import WebSocket

@app.websocket("/ws/{project_id}")
async def websocket_endpoint(websocket: WebSocket, project_id: int):
    await websocket.accept()
    # 实时推送工作流状态
```

---

## Task 12-15: 前端工作台

**关键组件:**

`frontend/app/projects/page.tsx`:
```typescript
export default function ProjectsPage() {
  // 项目列表页面
  return <ProjectList />
}
```

`frontend/app/projects/[id]/workflow/page.tsx`:
```typescript
export default function WorkflowPage({ params }: { params: { id: string } }) {
  // 工作流配置和执行页面
  return <WorkflowEditor projectId={params.id} />
}
```

`frontend/components/NodeConfigForm.tsx`:
```typescript
export function NodeConfigForm({ node, onSave }: Props) {
  // 节点配置表单
  return (
    <form>
      <input name="id" />
      <input name="name" />
      <select name="type">
        <option value="generate">生成</option>
        <option value="review">审核</option>
      </select>
      <select name="skill">
        {/* 加载可用 Skills */}
      </select>
    </form>
  )
}
```

---

## 验证清单

完成所有任务后,运行以下命令验证:

```bash
# 后端测试
cd backend
pytest tests/ -v --cov=app

# 启动后端
uvicorn app.main:app --reload

# 前端测试
cd frontend
npm test

# 启动前端
npm run dev
```

**验证场景:**
1. 创建项目
2. 配置工作流(添加节点、选择 Skill)
3. 启动工作流(手动模式)
4. 执行节点并查看输出
5. 触发审核并查看结果
6. 继续下一个节点

---

*计划版本: 1.0.0*
*创建日期: 2026-03-14*
*预计工作量: 5-7 天*
