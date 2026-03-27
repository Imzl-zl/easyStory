from __future__ import annotations

import argparse
import asyncio
import json

from sqlalchemy.ext.asyncio import AsyncEngine

from app.modules.project.service import (
    ProjectTrashCleanupResultDTO,
    create_project_deletion_service,
)
from app.modules.project.service.project_deletion_support import (
    DEFAULT_PROJECT_TRASH_BATCH_SIZE,
    DEFAULT_PROJECT_TRASH_RETENTION_DAYS,
)
from app.shared.db import create_async_session_factory


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Clean expired projects from trash.")
    parser.add_argument(
        "--database-url",
        help="Optional database URL override. Defaults to settings or local runtime DB.",
    )
    parser.add_argument(
        "--retention-days",
        type=int,
        default=DEFAULT_PROJECT_TRASH_RETENTION_DAYS,
        help="Delete projects soft-deleted for at least this many days.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_PROJECT_TRASH_BATCH_SIZE,
        help="Maximum number of projects to delete in one run.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = asyncio.run(_cleanup_expired_trash(args))
    print(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))
    return 0


async def _cleanup_expired_trash(args: argparse.Namespace) -> ProjectTrashCleanupResultDTO:
    async_session_factory = create_async_session_factory(args.database_url)
    engine = _resolve_async_engine(async_session_factory.kw.get("bind"))
    try:
        async with async_session_factory() as db:
            return await create_project_deletion_service().cleanup_expired_projects(
                db,
                retention_days=args.retention_days,
                batch_size=args.batch_size,
            )
    finally:
        await engine.dispose()


def _resolve_async_engine(bind: object) -> AsyncEngine:
    if not isinstance(bind, AsyncEngine):
        raise RuntimeError("Async database engine is not configured")
    return bind


if __name__ == "__main__":
    raise SystemExit(main())
