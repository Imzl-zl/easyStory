from __future__ import annotations

import pytest

from scripts.project_trash_cleanup import build_parser


def test_project_trash_cleanup_script_rejects_non_positive_numbers() -> None:
    parser = build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(["--retention-days", "0"])
    with pytest.raises(SystemExit):
        parser.parse_args(["--batch-size", "-1"])
