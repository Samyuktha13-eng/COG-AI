from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CognivBaseModel(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True, use_enum_values=True)

    @staticmethod
    def _utc_now() -> datetime:
        return datetime.now(timezone.utc)

    def model_dump(self, *args: Any, **kwargs: Any):
        return super().model_dump(*args, **kwargs)

    @classmethod
    def model_validate(cls, obj: Any):
        return super().model_validate(obj)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def ensure_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def simple_default(value: Any):
    return Field(default_factory=lambda: value)
