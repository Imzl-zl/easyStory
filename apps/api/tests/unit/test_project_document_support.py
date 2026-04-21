from __future__ import annotations

import json

from app.modules.project.service.project_document_support import (
    CHARACTERS_DATA_DOCUMENT_PATH,
    build_project_document_template_seed,
)


def test_build_project_document_template_seed_escapes_character_json_content() -> None:
    content = build_project_document_template_seed(
        project_name="测试项目",
        project_status="draft",
        setting_payload={
            "protagonist": {
                "name": '林渊"\n第二行',
                "identity": "弃徒\t兼散修",
                "initial_situation": "被逐出宗门\n流落荒野",
                "goal": '活下去并查清"真相"',
            }
        },
        document_path=CHARACTERS_DATA_DOCUMENT_PATH,
    )

    payload = json.loads(content)

    assert payload == {
        "characters": [
            {
                "id": "char_001",
                "name": '林渊"\n第二行',
                "role": "protagonist",
                "identity": "弃徒\t兼散修",
                "initial_situation": "被逐出宗门\n流落荒野",
                "goal": '活下去并查清"真相"',
                "status": "alive",
            }
        ]
    }
