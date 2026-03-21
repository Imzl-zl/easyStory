from __future__ import annotations

from sqlalchemy.orm import Session


class AsyncSessionAdapter:
    def __init__(self, session: Session) -> None:
        self._session = session

    def __getattr__(self, name: str):
        return getattr(self._session, name)

    async def scalar(self, statement):
        return self._session.scalar(statement)

    async def scalars(self, statement):
        return self._session.scalars(statement)

    async def execute(self, statement):
        return self._session.execute(statement)

    async def flush(self) -> None:
        self._session.flush()

    async def commit(self) -> None:
        self._session.commit()

    async def rollback(self) -> None:
        self._session.rollback()

    async def refresh(self, instance) -> None:
        self._session.refresh(instance)

    async def get(self, entity, ident):
        return self._session.get(entity, ident)

    async def delete(self, instance) -> None:
        self._session.delete(instance)


def async_db(session: Session) -> AsyncSessionAdapter:
    return AsyncSessionAdapter(session)
