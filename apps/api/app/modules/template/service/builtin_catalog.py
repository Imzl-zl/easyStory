from __future__ import annotations

from dataclasses import dataclass

DEFAULT_TEMPLATE_NODE_X_GAP = 220
DEFAULT_TEMPLATE_NODE_Y = 0


@dataclass(frozen=True)
class BuiltinTemplateSpec:
    template_key: str
    name: str
    description: str
    genre: str
    workflow_id: str
    guided_questions: tuple[tuple[str, str], ...]


BUILTIN_TEMPLATE_SPECS = (
    BuiltinTemplateSpec(
        template_key="template.xuanhuan",
        name="玄幻小说模板",
        description="适合创作玄幻、修仙类小说，默认绑定玄幻手动创作工作流。",
        genre="玄幻",
        workflow_id="workflow.xuanhuan_manual",
        guided_questions=(
            ("主角是什么身份?", "protagonist"),
            ("故事发生在什么世界?", "world_setting"),
            ("主要冲突是什么?", "core_conflict"),
        ),
    ),
)
