from __future__ import annotations

from app.shared.settings import get_settings

from .assistant_config_file_store import AssistantConfigFileStore


def build_default_assistant_config_store() -> AssistantConfigFileStore:
    return AssistantConfigFileStore(get_settings().assistant_config_root)
