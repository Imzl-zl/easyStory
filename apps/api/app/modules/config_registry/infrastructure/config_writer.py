from __future__ import annotations

from pathlib import Path
import shutil
from typing import Any

import yaml

TEMP_CONFIG_ROOT_NAME = "config"
TEMP_FILE_SUFFIX = ".tmp"
YAML_ROOT_KEY_AGENT = "agent"
YAML_ROOT_KEY_SKILL = "skill"


class _ConfigDumper(yaml.SafeDumper):
    pass


def _represent_string(dumper: _ConfigDumper, data: str):
    style = "|" if "\n" in data else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=style)


_ConfigDumper.add_representer(str, _represent_string)


def clone_config_root(config_root: Path, destination_root: Path) -> Path:
    staged_root = destination_root / TEMP_CONFIG_ROOT_NAME
    shutil.copytree(config_root, staged_root)
    return staged_root


def write_config_document(
    path: Path,
    *,
    root_key: str,
    payload: dict[str, Any],
) -> None:
    rendered = yaml.dump(
        {root_key: payload},
        Dumper=_ConfigDumper,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
    )
    temp_path = path.with_suffix(f"{path.suffix}{TEMP_FILE_SUFFIX}")
    temp_path.write_text(rendered, encoding="utf-8")
    temp_path.replace(path)
