from pathlib import Path
import shutil
import uuid

import pytest

from app.infrastructure.config_loader import ConfigLoader, ConfigurationError
from app.schemas.config_schemas import AgentConfig, SkillConfig, WorkflowConfig


PROJECT_ROOT = Path(__file__).resolve().parents[4]
API_ROOT = Path(__file__).resolve().parents[2]
CONFIG_ROOT = PROJECT_ROOT / "config"


def test_repository_config_loads() -> None:
    loader = ConfigLoader(CONFIG_ROOT)

    workflow = loader.load_workflow("workflow.xuanhuan_manual")

    assert "skill.chapter.xuanhuan" in [item.id for item in loader.list_skills()]
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


def _write_yaml(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def _make_temp_config_root() -> Path:
    temp_root = API_ROOT / ".pytest-tmp" / uuid.uuid4().hex
    temp_root.mkdir(parents=True, exist_ok=True)
    return temp_root
