# easyStory 后端核心实施计划 V2

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现 easyStory 的完整后端核心，包含数据模型、配置系统、工作流引擎、上下文注入、审核精修、成本控制和 API 层，完全对齐设计文档。

**Architecture:** 分层架构（Entry → Service → Engine → Infrastructure），Service 层不依赖 HTTP（DTO 入参/返回），为 MCP 预留接入点。工作流通过 WorkflowStateMachine 管理状态转换，模板渲染使用 SandboxedEnvironment，LLM 调用通过 LiteLLM 统一接口。

**Tech Stack:** Python 3.12+, FastAPI 0.115+, SQLAlchemy 2.0 (async), Pydantic 2.x, LangGraph 0.2.70+, LiteLLM 1.82+, Jinja2 (Sandboxed), PyYAML, aiosqlite (dev) / asyncpg (prod)

**Source of Truth:** `docs/specs/` 和 `docs/design/` 目录下的设计文档。与本计划有冲突时，以设计文档为准。

---

## 概览

### Phase 1: 数据模型层 (Task 1-4)

搭建项目骨架，实现所有数据库模型。这是最关键的基础——模型字段错了，上层全部要改。

### Phase 2: 配置与基础设施 (Task 5-8)

完善 Pydantic Schema、ConfigLoader、模板渲染器、TokenCounter。

### Phase 3: 引擎核心 (Task 9-14)

WorkflowStateMachine、ContextBuilder、ReviewExecutor、FixExecutor、LLM Service、WorkflowEngine。

### Phase 4: 服务层 (Task 15-18)

ProjectService、ContentService、WorkflowService、CredentialService。

### Phase 5: API 层 (Task 19-23)

FastAPI 入口、Auth、REST endpoints、SSE。

### 任务依赖图

```
Phase 1: [T1] → [T2] → [T3] → [T4]
Phase 2: [T5] → [T6] → [T7], [T8]
Phase 3: [T9], [T10] → [T11] → [T12], [T13] → [T14]
Phase 4: [T15] → [T16] → [T17], [T18]
Phase 5: [T19] → [T20] → [T21], [T22], [T23]
```

---

## Phase 1: 数据模型层

### Task 1: 项目骨架与基础模型

**目标：** 搭建 Python 项目结构，实现 Base/Mixin/User 模型。

**Files:**
- Rewrite: `apps/api/pyproject.toml`
- Rewrite: `apps/api/app/models/base.py`
- Create: `apps/api/app/models/user.py`
- Rewrite: `apps/api/app/models/__init__.py`
- Create: `apps/api/tests/conftest.py`
- Rewrite: `apps/api/tests/unit/test_models.py`

**Step 1: 更新 pyproject.toml**

```toml
[project]
name = "easystory-api"
version = "0.1.0"
description = "easyStory AI Novel Creation Platform - Backend API"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.34",
    "sqlalchemy[asyncio]>=2.0",
    "aiosqlite>=0.21",
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
    "pyyaml>=6.0",
    "jinja2>=3.1",
    "litellm>=1.82",
    "langgraph>=0.2.70",
    "python-jose[cryptography]>=3.3",
    "passlib[bcrypt]>=1.7",
    "alembic>=1.14",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "pytest-cov>=6.0",
    "ruff>=0.8",
    "httpx>=0.28",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["app"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
pythonpath = ["."]

[tool.ruff]
target-version = "py312"
line-length = 100
```

**Step 2: 实现 base.py**

```python
# apps/api/app/models/base.py
import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class UUIDMixin:
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)


class SoftDeleteMixin:
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
```

**Step 3: 实现 user.py**

> 来源: docs/design/10-user-and-credentials.md §2

```python
# apps/api/app/models/user.py
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDMixin


class User(Base, TimestampMixin, UUIDMixin):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(100), unique=True)
    email: Mapped[str | None] = mapped_column(String(200))
    hashed_password: Mapped[str] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    projects: Mapped[list["Project"]] = relationship(back_populates="owner")
```

**Step 4: 创建 conftest.py（测试共享 fixture）**

```python
# apps/api/tests/conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.base import Base


@pytest.fixture
def engine():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)


@pytest.fixture
def db(engine):
    with Session(engine) as session:
        yield session
```

**Step 5: 写测试**

```python
# apps/api/tests/unit/test_models.py (部分，后续 Task 会追加)
from app.models.user import User


def test_user_creation(db):
    user = User(username="testuser", hashed_password="hashed123")
    db.add(user)
    db.commit()
    db.refresh(user)
    assert user.username == "testuser"
    assert user.id is not None
    assert user.is_active is True
```

**Run:** `cd apps/api && python -m pytest tests/unit/test_models.py -v`
**Expected:** PASS

**Commit:** `feat: scaffold project and implement base models with User`

---

### Task 2: 核心业务模型 — Project, Content, ContentVersion

**目标：** 实现项目、内容、版本模型，与设计文档完全对齐。

**Files:**
- Rewrite: `apps/api/app/models/project.py`
- Rewrite: `apps/api/app/models/content.py`
- Update: `apps/api/app/models/__init__.py`
- Update: `apps/api/tests/unit/test_models.py`

**关键设计约束（来源）：**
- Project 有 `owner_id` FK → users（10-user-and-credentials §2.2）
- Project 有 `deleted_at` 软删除（18-data-backup）
- Content 有 `parent_id` 自引用（database-design）
- ContentVersion 有 `change_source`、`context_snapshot_hash`、`is_current`（05-content-editor）

**Implementation: project.py**

```python
# apps/api/app/models/project.py
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from .base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin


class Project(Base, TimestampMixin, UUIDMixin, SoftDeleteMixin):
    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(String(255))
    genre: Mapped[str | None] = mapped_column(String(100))
    target_words: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(50), default="draft")
    template_id: Mapped[uuid.UUID | None] = mapped_column()
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    config: Mapped[dict | None] = mapped_column(JSON)

    owner: Mapped["User"] = relationship(back_populates="projects")
    contents: Mapped[list["Content"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    workflow_executions: Mapped[list["WorkflowExecution"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
```

**Implementation: content.py**

```python
# apps/api/app/models/content.py
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from .base import Base, TimestampMixin, UUIDMixin


class Content(Base, TimestampMixin, UUIDMixin):
    __tablename__ = "contents"

    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"))
    parent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("contents.id"))
    content_type: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(255))
    chapter_number: Mapped[int | None] = mapped_column(Integer)
    order_index: Mapped[int | None] = mapped_column(Integer)
    content: Mapped[str | None] = mapped_column(Text)
    word_count: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(50), default="draft")
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON)
    last_edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    project: Mapped["Project"] = relationship(back_populates="contents")
    versions: Mapped[list["ContentVersion"]] = relationship(
        back_populates="content_ref", cascade="all, delete-orphan"
    )


class ContentVersion(Base, TimestampMixin, UUIDMixin):
    __tablename__ = "content_versions"

    content_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("contents.id"))
    version_number: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    word_count: Mapped[int | None] = mapped_column(Integer)
    change_summary: Mapped[str | None] = mapped_column(Text)
    change_source: Mapped[str] = mapped_column(String(50), default="system")
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    context_snapshot_hash: Mapped[str | None] = mapped_column(String(64))
    ai_conversation_id: Mapped[uuid.UUID | None] = mapped_column()

    content_ref: Mapped["Content"] = relationship(back_populates="versions")
```

**Tests:**

```python
def test_project_requires_owner(db):
    user = User(username="writer", hashed_password="x")
    db.add(user)
    db.commit()
    project = Project(name="测试小说", owner_id=user.id, genre="玄幻")
    db.add(project)
    db.commit()
    db.refresh(project)
    assert project.owner_id == user.id
    assert project.status == "draft"
    assert project.deleted_at is None

def test_content_version_with_change_source(db):
    user = User(username="u1", hashed_password="x")
    db.add(user)
    db.commit()
    project = Project(name="p1", owner_id=user.id)
    db.add(project)
    db.commit()
    content = Content(project_id=project.id, content_type="chapter", title="第一章")
    db.add(content)
    db.commit()
    v1 = ContentVersion(
        content_id=content.id, version_number=1, content="初版内容",
        change_source="system", is_current=True,
    )
    db.add(v1)
    db.commit()
    assert v1.change_source == "system"
    assert v1.is_current is True
```

**Run:** `pytest tests/unit/test_models.py -v`
**Expected:** PASS

**Commit:** `feat: implement Project, Content, ContentVersion models`

---

### Task 3: 工作流模型 — WorkflowExecution, NodeExecution, Artifact, ReviewAction

**目标：** 完整实现工作流相关模型，含状态快照、唯一约束、审核产物。

**关键设计约束：**
- WorkflowExecution 需 `pause_reason`、`resume_from_node`、`snapshot`（01-core-workflow §4.2）
- WorkflowExecution 需配置快照字段（17-cross-module-contracts §6.1）
- NodeExecution 需 `(workflow_execution_id, node_id, sequence)` 唯一约束（17-cross-module-contracts §2.3）
- ReviewAction.review_type 为自由字符串（database-design §5）

**Files:**
- Rewrite: `apps/api/app/models/workflow.py`
- Create: `apps/api/app/models/artifact.py`
- Create: `apps/api/app/models/review.py`

**Implementation: workflow.py**

```python
# apps/api/app/models/workflow.py
import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime, ForeignKey, Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from .base import Base, TimestampMixin, UUIDMixin


class WorkflowExecution(Base, TimestampMixin, UUIDMixin):
    __tablename__ = "workflow_executions"

    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"))
    template_id: Mapped[uuid.UUID | None] = mapped_column()
    status: Mapped[str] = mapped_column(String(50), default="created")
    current_node: Mapped[int] = mapped_column(Integer, default=0)
    pause_reason: Mapped[str | None] = mapped_column(String(50))
    resume_from_node: Mapped[str | None] = mapped_column(String(200))
    snapshot: Mapped[dict | None] = mapped_column(JSON)
    workflow_snapshot: Mapped[dict | None] = mapped_column(JSON)
    skills_snapshot: Mapped[dict | None] = mapped_column(JSON)
    agents_snapshot: Mapped[dict | None] = mapped_column(JSON)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    project: Mapped["Project"] = relationship(back_populates="workflow_executions")
    node_executions: Mapped[list["NodeExecution"]] = relationship(
        back_populates="workflow_execution", cascade="all, delete-orphan"
    )


class NodeExecution(Base, TimestampMixin, UUIDMixin):
    __tablename__ = "node_executions"
    __table_args__ = (
        UniqueConstraint(
            "workflow_execution_id", "node_id", "sequence",
            name="uq_node_execution_unique",
        ),
    )

    workflow_execution_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflow_executions.id")
    )
    node_id: Mapped[str] = mapped_column(String(200))
    sequence: Mapped[int] = mapped_column(Integer, default=0)
    node_order: Mapped[int] = mapped_column(Integer, default=0)
    node_type: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(50), default="pending")
    input_data: Mapped[dict | None] = mapped_column(JSON)
    output_data: Mapped[dict | None] = mapped_column(JSON)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    execution_time_ms: Mapped[int | None] = mapped_column(Integer)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    workflow_execution: Mapped["WorkflowExecution"] = relationship(
        back_populates="node_executions"
    )
    artifacts: Mapped[list["Artifact"]] = relationship(
        back_populates="node_execution", cascade="all, delete-orphan"
    )
    review_actions: Mapped[list["ReviewAction"]] = relationship(
        back_populates="node_execution", cascade="all, delete-orphan"
    )
```

**Implementation: artifact.py**

```python
# apps/api/app/models/artifact.py
import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDMixin


class Artifact(Base, TimestampMixin, UUIDMixin):
    __tablename__ = "artifacts"

    node_execution_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("node_executions.id")
    )
    artifact_type: Mapped[str] = mapped_column(String(50))
    content: Mapped[str] = mapped_column(Text)
    word_count: Mapped[int | None] = mapped_column(Integer)

    node_execution: Mapped["NodeExecution"] = relationship(
        back_populates="artifacts"
    )
```

**Implementation: review.py**

```python
# apps/api/app/models/review.py
import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from .base import Base, TimestampMixin, UUIDMixin


class ReviewAction(Base, TimestampMixin, UUIDMixin):
    __tablename__ = "review_actions"

    node_execution_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("node_executions.id")
    )
    agent_id: Mapped[str] = mapped_column(String(100))
    review_type: Mapped[str] = mapped_column(String(100))
    result: Mapped[str] = mapped_column(String(50))
    issues: Mapped[dict | None] = mapped_column(JSON)

    node_execution: Mapped["NodeExecution"] = relationship(
        back_populates="review_actions"
    )
```

**Tests:**

```python
def test_node_execution_unique_constraint(db):
    """(workflow_execution_id, node_id, sequence) 唯一约束"""
    # ... 创建 user, project, workflow_execution
    # 插入第一个 node_execution: node_id="outline", sequence=0 -> OK
    # 插入相同组合 -> 应抛 IntegrityError
    from sqlalchemy.exc import IntegrityError
    import pytest
    # ... (完整测试代码在执行时编写)

def test_workflow_execution_snapshots(db):
    """验证工作流配置快照字段"""
    # ... 创建带 workflow_snapshot 的 WorkflowExecution
    assert wf.workflow_snapshot == {"id": "test"}
    assert wf.pause_reason is None

def test_artifact_belongs_to_node(db):
    """产物关联到节点执行"""
    # ...

def test_review_action_with_issues(db):
    """审核动作含结构化问题列表"""
    # ...
```

**Run:** `pytest tests/unit/test_models.py -v`
**Commit:** `feat: implement workflow, artifact, review models with constraints`

---

### Task 4: 支撑模型 — ChapterTask, StoryFact, TokenUsage, ModelCredential, ExecutionLog, Export

**目标：** 实现所有剩余模型，覆盖设计文档中的全部数据表。

**关键来源：**
- ChapterTask: 04-chapter-generation §4
- StoryFact: 02-context-injection §4.3
- TokenUsage: 08-cost-and-safety §4
- ModelCredential: 10-user-and-credentials §4.1
- ExecutionLog: 18-data-backup
- Export: 11-export + database-design

**Files:**
- Create: `apps/api/app/models/chapter_task.py`
- Create: `apps/api/app/models/story_fact.py`
- Create: `apps/api/app/models/token_usage.py`
- Create: `apps/api/app/models/credential.py`
- Create: `apps/api/app/models/execution_log.py`
- Create: `apps/api/app/models/export.py`
- Update: `apps/api/app/models/__init__.py`

**Implementation: chapter_task.py**

```python
# apps/api/app/models/chapter_task.py
import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDMixin


class ChapterTask(Base, TimestampMixin, UUIDMixin):
    __tablename__ = "chapter_tasks"

    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"))
    chapter_number: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(255))
    brief: Mapped[str] = mapped_column(Text)
    key_characters: Mapped[dict | None] = mapped_column("key_characters", type_=JSON)
    key_events: Mapped[dict | None] = mapped_column("key_events", type_=JSON)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    content_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("contents.id"))
```

**Implementation: story_fact.py**

```python
# apps/api/app/models/story_fact.py
import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDMixin


class StoryFact(Base, TimestampMixin, UUIDMixin):
    __tablename__ = "story_facts"

    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"))
    chapter_number: Mapped[int] = mapped_column(Integer)
    source_content_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("content_versions.id")
    )
    fact_type: Mapped[str] = mapped_column(String(50))
    subject: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    superseded_by: Mapped[uuid.UUID | None] = mapped_column()
```

**Implementation: token_usage.py**

```python
# apps/api/app/models/token_usage.py
import uuid

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDMixin


class TokenUsage(Base, TimestampMixin, UUIDMixin):
    __tablename__ = "token_usages"

    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"))
    node_execution_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("node_executions.id")
    )
    credential_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("model_credentials.id")
    )
    model_name: Mapped[str] = mapped_column(String(100))
    input_tokens: Mapped[int] = mapped_column(Integer)
    output_tokens: Mapped[int] = mapped_column(Integer)
    estimated_cost: Mapped[float] = mapped_column(Float)
```

**Implementation: credential.py**

```python
# apps/api/app/models/credential.py
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDMixin


class ModelCredential(Base, TimestampMixin, UUIDMixin):
    __tablename__ = "model_credentials"

    owner_type: Mapped[str] = mapped_column(String(20))
    owner_id: Mapped[uuid.UUID | None] = mapped_column()
    provider: Mapped[str] = mapped_column(String(50))
    display_name: Mapped[str] = mapped_column(String(100))
    encrypted_key: Mapped[str] = mapped_column(Text)
    base_url: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
```

**Implementation: execution_log.py**

```python
# apps/api/app/models/execution_log.py
import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from .base import Base, TimestampMixin, UUIDMixin


class ExecutionLog(Base, TimestampMixin, UUIDMixin):
    __tablename__ = "execution_logs"

    workflow_execution_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflow_executions.id")
    )
    node_execution_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("node_executions.id")
    )
    level: Mapped[str] = mapped_column(String(20))
    message: Mapped[str] = mapped_column(Text)
    details: Mapped[dict | None] = mapped_column(JSON)


class PromptReplay(Base, TimestampMixin, UUIDMixin):
    __tablename__ = "prompt_replays"

    node_execution_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("node_executions.id")
    )
    replay_type: Mapped[str] = mapped_column(String(50))
    model_name: Mapped[str] = mapped_column(String(100))
    prompt_text: Mapped[str] = mapped_column(Text)
    response_text: Mapped[str | None] = mapped_column(Text)
    input_tokens: Mapped[int | None] = mapped_column()
    output_tokens: Mapped[int | None] = mapped_column()
```

**Implementation: export.py**

```python
# apps/api/app/models/export.py
import uuid

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from .base import Base, TimestampMixin, UUIDMixin


class Export(Base, TimestampMixin, UUIDMixin):
    __tablename__ = "exports"

    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"))
    format: Mapped[str] = mapped_column(String(20))
    filename: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(500))
    file_size: Mapped[int | None] = mapped_column(Integer)
    config: Mapped[dict | None] = mapped_column(JSON)
```

**Update: `__init__.py` 导出所有模型**

```python
from .base import Base, TimestampMixin, UUIDMixin, SoftDeleteMixin
from .user import User
from .project import Project
from .content import Content, ContentVersion
from .workflow import WorkflowExecution, NodeExecution
from .artifact import Artifact
from .review import ReviewAction
from .chapter_task import ChapterTask
from .story_fact import StoryFact
from .token_usage import TokenUsage
from .credential import ModelCredential
from .execution_log import ExecutionLog, PromptReplay
from .export import Export
```

**Tests:** 为每个新模型编写基本 CRUD 测试。

**Run:** `pytest tests/ -v`
**Commit:** `feat: implement all supporting models (ChapterTask, StoryFact, TokenUsage, etc.)`

---

## Phase 2: 配置与基础设施

### Task 5: 完善 Pydantic 配置 Schema

**目标：** Pydantic Schema 完全对齐 config-format.md + 各设计文档中的配置项。

**关键新增（相比 V1）：**
- NodeConfig: `review_mode`, `review_config`, `fix_skill`, `fix_strategy`, `loop`
- WorkflowConfig: `mode`, `budget`, `safety`, `retry`, `model_fallback`
- ReviewResult/ReviewIssue/AggregatedReviewResult（03-review-and-fix §3）
- SkillConfig: `inputs`/`outputs` 增强 Schema（config-format §3）

**Files:**
- Rewrite: `apps/api/app/schemas/config_schemas.py`
- Create: `apps/api/app/schemas/review_schemas.py`
- Create: `apps/api/tests/unit/test_schemas.py`

**Implementation: config_schemas.py（关键新增部分）**

```python
# 新增到 NodeConfig
class LoopConfig(BaseModel):
    enabled: bool = False
    count_from: str | None = None
    item_var: str = "chapter_index"

class ReviewConfig(BaseModel):
    pass_rule: Literal["all_pass", "majority_pass", "no_critical"] = "no_critical"
    re_review_scope: Literal["all", "failed_only"] = "all"

class FixStrategy(BaseModel):
    mode: Literal["targeted", "full_rewrite"] = "targeted"
    selection_rule: Literal["auto", "targeted", "full_rewrite"] = "auto"
    targeted_threshold: int = 3
    rewrite_threshold: int = 6

class NodeConfig(BaseModel):
    # ... 现有字段 ...
    review_mode: Literal["parallel", "serial"] = "serial"
    max_concurrent_reviewers: int = 3
    review_config: ReviewConfig = Field(default_factory=ReviewConfig)
    fix_skill: str | None = None
    fix_strategy: FixStrategy = Field(default_factory=FixStrategy)
    loop: LoopConfig = Field(default_factory=LoopConfig)

# 新增到 WorkflowConfig
class BudgetConfig(BaseModel):
    max_tokens_per_node: int = 50000
    max_tokens_per_workflow: int = 500000
    max_tokens_per_day: int = 2000000
    warning_threshold: float = 0.8
    on_exceed: Literal["pause", "skip", "fail"] = "pause"

class SafetyConfig(BaseModel):
    max_retry_per_node: int = 3
    max_fix_attempts: int = 3
    max_total_retries: int = 10
    execution_timeout: int = 3600
    node_timeout: int = 300

class RetryConfig(BaseModel):
    strategy: Literal["exponential_backoff", "fixed", "none"] = "exponential_backoff"
    initial_delay: float = 1.0
    max_delay: float = 30.0
    max_attempts: int = 3

class ModelFallbackConfig(BaseModel):
    enabled: bool = False
    chain: list[ModelConfig] = Field(default_factory=list)
    on_all_fail: Literal["pause", "fail", "skip"] = "pause"

class WorkflowConfig(BaseModel):
    # ... 现有字段 ...
    mode: Literal["manual", "auto"] = "manual"
    budget: BudgetConfig = Field(default_factory=BudgetConfig)
    safety: SafetyConfig = Field(default_factory=SafetyConfig)
    retry: RetryConfig = Field(default_factory=RetryConfig)
    model_fallback: ModelFallbackConfig = Field(default_factory=ModelFallbackConfig)
```

**Implementation: review_schemas.py**

> 来源: 03-review-and-fix §3

```python
# apps/api/app/schemas/review_schemas.py
from pydantic import BaseModel, Field
from typing import Literal


class ReviewLocation(BaseModel):
    paragraph_index: int | None = None
    start_offset: int | None = None
    end_offset: int | None = None
    quoted_text: str | None = None


class ReviewIssue(BaseModel):
    category: Literal[
        "plot_inconsistency", "character_inconsistency", "style_deviation",
        "banned_words", "ai_flavor", "logic_error", "quality_low", "other",
    ]
    severity: Literal["critical", "major", "minor", "suggestion"]
    location: ReviewLocation | None = None
    description: str
    suggested_fix: str | None = None
    evidence: str | None = None


class ReviewResult(BaseModel):
    reviewer_id: str
    reviewer_name: str
    status: Literal["passed", "failed", "warning"]
    score: float | None = None
    issues: list[ReviewIssue] = Field(default_factory=list)
    summary: str
    execution_time_ms: int
    tokens_used: int


class AggregatedReviewResult(BaseModel):
    overall_status: Literal["passed", "failed"]
    results: list[ReviewResult] = Field(default_factory=list)
    total_issues: int = 0
    critical_count: int = 0
    major_count: int = 0
    minor_count: int = 0
    pass_rule: Literal["all_pass", "majority_pass", "no_critical"] = "no_critical"
```

**Tests:** 验证所有 Schema 能正确序列化/反序列化，默认值正确。

**Run:** `pytest tests/unit/test_schemas.py -v`
**Commit:** `feat: complete config and review schemas aligned with design docs`

---

### Task 6: 完善 ConfigLoader

**目标：** ConfigLoader 支持完整 Schema，增加引用完整性检查。

**关键新增：**
- 加载时检查 Skill/Agent 引用是否存在
- list 方法返回全部配置
- 支持配置刷新

**Files:**
- Rewrite: `apps/api/app/core/config_loader.py`
- Update: `apps/api/tests/unit/test_config_loader.py`
- Update: YAML 配置文件（添加新增字段）

**Commit:** `feat: enhance ConfigLoader with reference validation`

---

### Task 7: 实现 SkillTemplateRenderer

**目标：** 使用 SandboxedEnvironment + StrictUndefined 渲染模板。

> 来源: 17-cross-module-contracts §4

**Files:**
- Create: `apps/api/app/core/template_renderer.py`
- Create: `apps/api/tests/unit/test_template_renderer.py`

**Implementation:**

```python
# apps/api/app/core/template_renderer.py
from jinja2 import StrictUndefined
from jinja2.sandbox import SandboxedEnvironment


class SkillTemplateRenderer:
    def __init__(self):
        self.env = SandboxedEnvironment(undefined=StrictUndefined)
        self.env.filters.update({
            "truncate": self._safe_truncate,
            "default": self._safe_default,
        })

    def render(self, template_str: str, variables: dict) -> str:
        template = self.env.from_string(template_str)
        return template.render(**variables)

    def validate(self, template_str: str, declared_variables: set[str]) -> list[str]:
        """校验模板引用的变量是否都已声明，返回错误列表"""
        from jinja2 import meta
        ast = self.env.parse(template_str)
        referenced = meta.find_undeclared_variables(ast)
        missing = referenced - declared_variables
        return [f"Undeclared variable: {v}" for v in sorted(missing)]

    @staticmethod
    def _safe_truncate(value: str, length: int = 100) -> str:
        return value[:length] + "..." if len(value) > length else value

    @staticmethod
    def _safe_default(value, default_value=""):
        return value if value else default_value
```

**Tests:**

```python
def test_render_basic():
    renderer = SkillTemplateRenderer()
    result = renderer.render("Hello {{ name }}", {"name": "World"})
    assert result == "Hello World"

def test_strict_undefined_raises():
    renderer = SkillTemplateRenderer()
    with pytest.raises(UndefinedError):
        renderer.render("{{ missing_var }}", {})

def test_sandbox_blocks_dangerous():
    renderer = SkillTemplateRenderer()
    with pytest.raises(SecurityError):
        renderer.render("{{ ''.__class__ }}", {})

def test_validate_finds_missing_vars():
    renderer = SkillTemplateRenderer()
    errors = renderer.validate("{{ a }} {{ b }}", {"a"})
    assert len(errors) == 1
    assert "b" in errors[0]
```

**Commit:** `feat: implement sandboxed template renderer with validation`

---

### Task 8: 实现 TokenCounter + ModelPricing

**目标：** Token 计数和费用计算的单一事实来源。

> 来源: 08-cost-and-safety §6, §7; 17-cross-module-contracts §3

**Files:**
- Create: `apps/api/app/core/token_counter.py`
- Create: `config/model_pricing.yaml`
- Create: `apps/api/tests/unit/test_token_counter.py`

**Implementation:**

```python
# apps/api/app/core/token_counter.py
import yaml
from pathlib import Path
from dataclasses import dataclass

MODEL_TOKEN_RATIOS: dict[str, float] = {
    "default": 1.5,  # 中文约 1.5 字/token
}


@dataclass
class ModelPrice:
    input_per_1k: float
    output_per_1k: float
    context_window: int


class TokenCounter:
    def count(self, text: str, model: str = "default") -> int:
        """精确计数（有 tokenizer 时使用，否则退化为 estimate）"""
        return self.estimate(text, model)

    def estimate(self, text: str, model: str = "default") -> int:
        """快速估算"""
        ratio = MODEL_TOKEN_RATIOS.get(model, MODEL_TOKEN_RATIOS["default"])
        return max(1, int(len(text) / ratio))


class ModelPricing:
    def __init__(self, config_path: Path | None = None):
        self._prices: dict[str, ModelPrice] = {}
        if config_path and config_path.exists():
            self._load(config_path)

    def _load(self, path: Path) -> None:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        for model_name, info in data.get("models", {}).items():
            self._prices[model_name] = ModelPrice(**info)

    def calculate_cost(
        self, model: str, input_tokens: int, output_tokens: int
    ) -> float:
        price = self._prices.get(model)
        if not price:
            return 0.0
        return (
            input_tokens * price.input_per_1k / 1000
            + output_tokens * price.output_per_1k / 1000
        )

    def get_context_window(self, model: str) -> int:
        price = self._prices.get(model)
        return price.context_window if price else 128000
```

**Commit:** `feat: implement TokenCounter and ModelPricing`

---

## Phase 3: 引擎核心

### Task 9: 工作流状态机

> 来源: 01-core-workflow §4; 17-cross-module-contracts §2

**Files:**
- Create: `apps/api/app/engine/state_machine.py`
- Create: `apps/api/tests/unit/test_state_machine.py`

**Implementation:**

```python
# apps/api/app/engine/state_machine.py


class InvalidTransitionError(Exception):
    def __init__(self, current: str, target: str):
        super().__init__(f"Invalid transition: {current} -> {target}")
        self.current = current
        self.target = target


class WorkflowStateMachine:
    VALID_TRANSITIONS: dict[str, list[str]] = {
        "created":   ["running"],
        "running":   ["paused", "completed", "failed"],
        "paused":    ["running", "cancelled"],
        "failed":    ["running"],
        "completed": [],
        "cancelled": [],
    }

    TERMINAL_STATES = {"completed", "cancelled"}

    @classmethod
    def validate_transition(cls, current: str, target: str) -> None:
        allowed = cls.VALID_TRANSITIONS.get(current, [])
        if target not in allowed:
            raise InvalidTransitionError(current, target)

    @classmethod
    def can_transition(cls, current: str, target: str) -> bool:
        return target in cls.VALID_TRANSITIONS.get(current, [])

    @classmethod
    def is_terminal(cls, status: str) -> bool:
        return status in cls.TERMINAL_STATES
```

**Tests:** 覆盖所有合法/非法转换组合。

**Commit:** `feat: implement workflow state machine`

---

### Task 10: 上下文构建器

> 来源: 02-context-injection; 17-cross-module-contracts §4.4

**目标：** 三层优先级合并 + 模式匹配 + Token 裁剪 + 构建报告

**Files:**
- Create: `apps/api/app/engine/context_builder.py`
- Create: `apps/api/tests/unit/test_context_builder.py`

**核心方法：**
- `merge_rules(global_rules, pattern_rules, node_id, node_rules)` → 合并后的 rules dict
- `match_patterns(pattern_rules, node_id)` → 匹配的 inject 项
- `build_context(project_id, injection_rules, db)` → variables dict + context_report
- `truncate_context(sections, budget)` → 裁剪后的 sections

**Commit:** `feat: implement context builder with three-layer priority and truncation`

---

### Task 11: 审核执行器

> 来源: 03-review-and-fix §2-4

**目标：** 支持并行/串行审核，输出统一 ReviewResult，按聚合规则判定。

**Files:**
- Create: `apps/api/app/engine/review_executor.py`
- Create: `apps/api/tests/unit/test_review_executor.py`

**核心方法：**
- `execute_review(content, reviewers, mode, config)` → AggregatedReviewResult
- `_execute_parallel(content, reviewers, semaphore)` → list[ReviewResult]
- `_execute_serial(content, reviewers)` → list[ReviewResult]
- `aggregate(results, pass_rule)` → AggregatedReviewResult

**Commit:** `feat: implement review executor with parallel/serial modes`

---

### Task 12: 精修执行器

> 来源: 03-review-and-fix §5

**Files:**
- Create: `apps/api/app/engine/fix_executor.py`
- Create: `apps/api/tests/unit/test_fix_executor.py`

**核心方法：**
- `determine_strategy(aggregated_result, config)` → "targeted" | "full_rewrite"
- `execute_fix(original, feedback, strategy, fix_skill)` → fixed_content

**Commit:** `feat: implement fix executor with auto strategy selection`

---

### Task 13: LLM 服务

> 来源: 09-error-handling; tech-stack（LiteLLM）

**Files:**
- Create: `apps/api/app/engine/llm_service.py`
- Create: `apps/api/tests/unit/test_llm_service.py`

**核心方法：**
- `call(prompt, model_config, credential)` → LLMResponse
- `call_stream(prompt, model_config, credential)` → AsyncGenerator[str]
- `_retry_with_backoff(fn, config)` → result
- `_fallback(fn, fallback_chain)` → result

**Commit:** `feat: implement LLM service with retry and model fallback`

---

### Task 14: 工作流引擎（完整版）

> 来源: 01-core-workflow; 04-chapter-generation

**Files:**
- Rewrite: `apps/api/app/services/workflow_engine.py` → 移至 `app/engine/workflow_engine.py`
- Create: `apps/api/tests/unit/test_workflow_engine.py`

**核心方法：**
- `start_workflow(workflow_config, project_id)` → WorkflowExecution
- `resume_workflow(execution_id)` → WorkflowExecution（幂等）
- `pause_workflow(execution_id, reason)` → WorkflowExecution
- `cancel_workflow(execution_id)` → WorkflowExecution
- `execute_node(node, context)` → NodeResult
- `execute_chapter_loop(loop_config, ...)` → list[NodeResult]

**状态机集成：**
- 所有状态变更必须通过 `WorkflowStateMachine.validate_transition()`
- start 前检查同项目无 running/paused 工作流

**Commit:** `feat: implement complete workflow engine with state machine and chapter loop`

---

## Phase 4: 服务层（概要）

### Task 15: Database Session + Alembic

- 创建 `app/core/database.py`（async engine, session factory）
- 初始化 Alembic，生成 initial migration
- Commit: `feat: setup database session and alembic migrations`

### Task 16: ProjectService + ContentService

- `ProjectService`: create, get, list, update, soft_delete, restore, physical_delete
- `ContentService`: create, get, list, update_content, create_version, get_versions, rollback
- 入参/返回用 Pydantic DTO，不依赖 HTTP
- Commit: `feat: implement project and content services`

### Task 17: WorkflowService

- 编排层：调用 WorkflowEngine + ContentService + ContextBuilder
- 保存配置快照、创建 NodeExecution 记录、记录 TokenUsage
- Commit: `feat: implement workflow orchestration service`

### Task 18: CredentialService

- CRUD + AES-256-GCM 加解密
- 优先级解析（project > user > system）
- 连通性测试
- Commit: `feat: implement credential service with encryption`

---

## Phase 5: API 层（概要）

### Task 19: FastAPI 应用入口

- `app/main.py`: 创建 app, 注册 router, 配置 CORS, 依赖注入
- `app/core/deps.py`: get_db, get_current_user, get_config_loader
- Commit: `feat: setup FastAPI application with dependency injection`

### Task 20: Auth API

- `POST /api/auth/register`, `POST /api/auth/login`
- JWT token 生成/校验
- Commit: `feat: implement auth endpoints with JWT`

### Task 21: Project + Content API

- `GET/POST /api/v1/projects`, `GET/PUT/DELETE /api/v1/projects/{id}`
- `GET/POST /api/v1/projects/{id}/contents`, version endpoints
- Commit: `feat: implement project and content API endpoints`

### Task 22: Workflow API + SSE

- `POST /api/v1/projects/{id}/workflows/start`
- `POST /api/v1/workflows/{id}/resume|pause|cancel`
- `GET /api/v1/workflows/{id}/stream` (SSE)
- Commit: `feat: implement workflow API with SSE streaming`

### Task 23: Config API

- `GET /api/v1/config/skills|agents|hooks|workflows`
- `PUT /api/v1/config/skills/{id}` (编辑后写回 YAML)
- Commit: `feat: implement config management API`

---

## 验证清单

完成所有任务后：

```bash
# 全量测试
cd apps/api && pytest tests/ -v --cov=app --cov-report=term-missing

# 启动服务
uvicorn app.main:app --reload --port 8000

# API 文档
open http://localhost:8000/docs
```

**端到端验证场景：**
1. 注册用户 → 登录获取 JWT
2. 创建项目 → 配置工作流
3. 启动工作流（手动模式）→ 第一个节点暂停
4. 查看节点输出 → 手动确认 → 继续
5. 触发审核 → 查看 ReviewResult
6. 暂停/恢复工作流
7. 导出 Markdown

---

## 与设计文档的字段对照表

确保不遗漏任何字段。执行时请对照：
- `docs/specs/database-design.md` §2 所有表定义
- `docs/design/01-core-workflow.md` §4.2 暂停恢复字段
- `docs/design/02-context-injection.md` §4.3 StoryFact 模型
- `docs/design/03-review-and-fix.md` §3 ReviewResult Schema
- `docs/design/04-chapter-generation.md` §4 ChapterTask 模型
- `docs/design/05-content-editor.md` ContentVersion 扩展字段
- `docs/design/08-cost-and-safety.md` §4 TokenUsage 模型
- `docs/design/10-user-and-credentials.md` §2 User + §4 ModelCredential
- `docs/design/17-cross-module-contracts.md` 全部约束
- `docs/design/18-data-backup.md` ExecutionLog + PromptReplay

---

*计划版本: 2.0.0*
*创建日期: 2026-03-17*
*基于: 19 个设计文档全面审查*
*预计任务数: 23 个*
