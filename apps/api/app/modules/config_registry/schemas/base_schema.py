from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


__all__ = ["StrictSchema"]
