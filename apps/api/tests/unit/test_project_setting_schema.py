from app.modules.project.schemas import ProjectSetting, merge_project_setting


def test_merge_project_setting_preserves_existing_locations_and_appends_new_ones() -> None:
    merged = merge_project_setting(
        ProjectSetting.model_validate(
            {
                "world_setting": {
                    "era_baseline": "宗门割据时代",
                    "key_locations": ["青岳宗", "边城"],
                }
            }
        ),
        ProjectSetting.model_validate(
            {
                "world_setting": {
                    "key_locations": ["边城", "皇都"],
                }
            }
        ),
    )

    assert merged.world_setting is not None
    assert merged.world_setting.key_locations == ["青岳宗", "边城", "皇都"]


def test_merge_project_setting_merges_supporting_roles_by_name_and_keeps_unmentioned_roles() -> None:
    merged = merge_project_setting(
        ProjectSetting.model_validate(
            {
                "key_supporting_roles": [
                    {"name": "苏晚", "identity": "医师", "goal": "救回师门"},
                    {"name": "顾沉", "identity": "剑修"},
                ]
            }
        ),
        ProjectSetting.model_validate(
            {
                "key_supporting_roles": [
                    {"name": "苏晚", "personality": "冷静克制"},
                    {"name": "赵焰", "identity": "皇都密探"},
                ]
            }
        ),
    )

    assert [
        item.model_dump(mode="json", exclude_none=True)
        for item in merged.key_supporting_roles
    ] == [
        {
            "name": "苏晚",
            "identity": "医师",
            "goal": "救回师门",
            "personality": "冷静克制",
        },
        {
            "name": "顾沉",
            "identity": "剑修",
        },
        {
            "name": "赵焰",
            "identity": "皇都密探",
        },
    ]
