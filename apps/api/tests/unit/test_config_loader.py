from pathlib import Path
import shutil
import uuid

import pytest

from app.modules.config_registry.infrastructure.config_loader import (
    ConfigLoader,
    ConfigurationError,
)
from app.modules.config_registry.schemas.config_schemas import (
    AgentConfig,
    McpServerConfig,
    SkillConfig,
    WorkflowConfig,
)


PROJECT_ROOT = Path(__file__).resolve().parents[4]
API_ROOT = Path(__file__).resolve().parents[2]
CONFIG_ROOT = PROJECT_ROOT / "config"


def test_repository_config_loads() -> None:
    loader = ConfigLoader(CONFIG_ROOT)

    workflow = loader.load_workflow("workflow.xuanhuan_manual")
    project_setting_skill = loader.load_skill("skill.project_setting.conversation_extract")
    assistant_skill = loader.load_skill("skill.assistant.general_chat")
    assistant_agent = loader.load_agent("agent.general_assistant")
    example_mcp_server = loader.load_mcp_server("mcp.example.streamable_http")

    assert "skill.chapter.xuanhuan" in [item.id for item in loader.list_skills()]
    assert project_setting_skill.category == "project_setting"
    assert assistant_skill.category == "assistant"
    assert assistant_agent.skills == ["skill.assistant.general_chat"]
    assert example_mcp_server.transport == "streamable_http"
    assert "conversation_text" in project_setting_skill.variables
    assert workflow.settings.default_fix_skill == "skill.fix.xuanhuan"
    assert workflow.context_injection is not None
    assert workflow.context_injection.default_inject[0].inject_type == "project_setting"
    assert workflow.nodes[-1].node_type == "export"
    assert workflow.nodes[-1].formats == ["txt", "markdown"]


def test_loader_rejects_missing_references() -> None:
    temp_root = _make_temp_config_root()
    _write_yaml(
        temp_root / "agents" / "reviewers" / "broken.yaml",
        """
agent:
  id: "agent.broken"
  name: "Broken"
  type: "reviewer"
  system_prompt: "x"
  skills:
    - "skill.missing"
""",
    )

    try:
        with pytest.raises(ConfigurationError, match="skill.missing"):
            ConfigLoader(temp_root)
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def test_loader_rejects_missing_mcp_server_reference() -> None:
    temp_root = _make_temp_config_root()
    _write_yaml(
        temp_root / "agents" / "writers" / "broken.yaml",
        """
agent:
  id: "agent.mcp_broken"
  name: "Broken MCP Agent"
  type: "writer"
  system_prompt: "x"
  skills: []
  mcp_servers:
    - "mcp.missing"
""",
    )

    try:
        with pytest.raises(ConfigurationError, match="mcp.missing"):
            ConfigLoader(temp_root)
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def test_loader_rejects_unknown_fields() -> None:
    temp_root = _make_temp_config_root()
    _write_yaml(
        temp_root / "skills" / "bad.yaml",
        """
skill:
  id: "skill.bad"
  name: "Bad"
  category: "outline"
  prompt: "x"
  unexpected: true
""",
    )

    try:
        with pytest.raises(ConfigurationError, match="unexpected"):
            ConfigLoader(temp_root)
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def test_loader_rejects_duplicate_ids_across_config_types() -> None:
    temp_root = _make_temp_config_root()
    _write_yaml(
        temp_root / "skills" / "shared.yaml",
        """
skill:
  id: "config.shared"
  name: "Shared Skill"
  category: "outline"
  prompt: "x"
""",
    )
    _write_yaml(
        temp_root / "agents" / "shared.yaml",
        """
agent:
  id: "config.shared"
  name: "Shared Agent"
  type: "reviewer"
  system_prompt: "x"
  skills: []
""",
    )

    try:
        with pytest.raises(ConfigurationError, match="Duplicate config id 'config.shared'"):
            ConfigLoader(temp_root)
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def test_loader_rejects_skill_prompt_with_undeclared_variables() -> None:
    temp_root = _make_temp_config_root()
    _write_yaml(
        temp_root / "skills" / "bad.yaml",
        """
skill:
  id: "skill.bad"
  name: "Bad"
  category: "outline"
  prompt: "{{ declared }} {{ missing }}"
  variables:
    declared:
      type: "string"
      required: true
""",
    )

    try:
        with pytest.raises(ConfigurationError, match="Undeclared variable: missing"):
            ConfigLoader(temp_root)
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def test_loader_reload_picks_up_new_config_file() -> None:
    temp_root = _make_temp_config_root()
    _write_yaml(
        temp_root / "skills" / "outline.yaml",
        """
skill:
  id: "skill.outline"
  name: "Outline"
  category: "outline"
  prompt: "x"
""",
    )

    try:
        loader = ConfigLoader(temp_root)
        assert [item.id for item in loader.list_skills()] == ["skill.outline"]

        _write_yaml(
            temp_root / "skills" / "chapter.yaml",
            """
skill:
  id: "skill.chapter"
  name: "Chapter"
  category: "chapter"
  prompt: "y"
""",
        )
        loader.reload()

        assert sorted(item.id for item in loader.list_skills()) == [
            "skill.chapter",
            "skill.outline",
        ]
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def test_skill_schema_rejects_mixed_variable_modes() -> None:
    with pytest.raises(ValueError, match="mutually exclusive"):
        SkillConfig.model_validate(
            {
                "id": "skill.test",
                "name": "Test",
                "category": "outline",
                "prompt": "x",
                "variables": {"genre": {"type": "string", "required": True}},
                "inputs": {"genre": {"type": "string", "required": True}},
            }
        )


def test_agent_schema_rejects_output_schema_for_reviewer() -> None:
    with pytest.raises(ValueError, match="cannot define output_schema"):
        AgentConfig.model_validate(
            {
                "id": "agent.test",
                "name": "Test",
                "type": "reviewer",
                "system_prompt": "x",
                "output_schema": {"type": "object"},
            }
        )


def test_mcp_server_schema_accepts_streamable_http() -> None:
    config = McpServerConfig.model_validate(
        {
            "id": "mcp.test",
            "name": "Test MCP",
            "transport": "streamable_http",
            "url": "https://example.com/mcp",
        }
    )

    assert config.timeout == 30


def test_workflow_schema_accepts_new_fields() -> None:
    workflow = WorkflowConfig.model_validate(
        {
            "id": "workflow.test",
            "name": "Test",
            "mode": "manual",
            "settings": {"default_fix_skill": "skill.fix.xuanhuan"},
            "context_injection": {
                "enabled": True,
                "default_inject": [{"type": "outline", "required": True}],
            },
            "nodes": [
                {
                    "id": "chapter_gen",
                    "name": "生成章节",
                    "type": "generate",
                    "skill": "skill.chapter.xuanhuan",
                    "context_injection": [{"type": "chapter_task", "required": True}],
                },
                {
                    "id": "export",
                    "name": "导出",
                    "type": "export",
                    "depends_on": ["chapter_gen"],
                    "formats": ["markdown"],
                },
            ],
        }
    )

    assert workflow.settings.default_fix_skill == "skill.fix.xuanhuan"
    assert workflow.nodes[0].context_injection[0].inject_type == "chapter_task"


def test_loader_rejects_workflow_node_hook_with_assistant_event() -> None:
    temp_root = _make_temp_config_root()
    shutil.copytree(CONFIG_ROOT, temp_root, dirs_exist_ok=True)
    _write_yaml(
        temp_root / "hooks" / "assistant-only.yaml",
        """
hook:
  id: "hook.assistant_only"
  name: "Assistant Only"
  trigger:
    event: "before_assistant_response"
  action:
    type: "script"
    config:
      module: "app.hooks.builtin"
      function: "auto_save_content"
""",
    )
    _write_yaml(
        temp_root / "workflows" / "broken-assistant-hook.yaml",
        """
workflow:
  id: "workflow.broken_assistant_hook"
  name: "Broken Assistant Hook"
  mode: "manual"
  nodes:
    - id: "chapter_gen"
      name: "生成章节"
      type: "generate"
      skill: "skill.chapter.xuanhuan"
      hooks:
        after:
          - "hook.assistant_only"
""",
    )

    try:
        with pytest.raises(ConfigurationError, match="not supported on workflow nodes"):
            ConfigLoader(temp_root)
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def test_loader_rejects_workflow_node_hook_with_mismatched_stage() -> None:
    temp_root = _make_temp_config_root()
    shutil.copytree(CONFIG_ROOT, temp_root, dirs_exist_ok=True)
    _write_yaml(
        temp_root / "hooks" / "stage-mismatch.yaml",
        """
hook:
  id: "hook.stage_mismatch"
  name: "Stage Mismatch"
  trigger:
    event: "after_generate"
    node_types:
      - "generate"
  action:
    type: "script"
    config:
      module: "app.hooks.builtin"
      function: "auto_save_content"
""",
    )
    _write_yaml(
        temp_root / "workflows" / "broken-stage-hook.yaml",
        """
workflow:
  id: "workflow.broken_stage_hook"
  name: "Broken Stage Hook"
  mode: "manual"
  nodes:
    - id: "chapter_gen"
      name: "生成章节"
      type: "generate"
      skill: "skill.chapter.xuanhuan"
      hooks:
        before:
          - "hook.stage_mismatch"
""",
    )

    try:
        with pytest.raises(ConfigurationError, match="must use stage 'after'"):
            ConfigLoader(temp_root)
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def _write_yaml(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def _make_temp_config_root() -> Path:
    temp_root = API_ROOT / ".pytest-tmp" / uuid.uuid4().hex
    temp_root.mkdir(parents=True, exist_ok=True)
    return temp_root
