from typing import Any, Self

from pydantic import BaseModel

__all__ = ("BaseSchema",)


class BaseSchema(BaseModel):
    """Base schema for data class"""

    def to_dict(
        self,
        include: set[str] | None = None,
        exclude: set[str] | None = None,
        exclude_none: bool = False,
    ) -> dict[str, Any]:
        return self.model_dump(
            include=include,
            exclude=exclude,
            exclude_none=exclude_none,
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls.model_validate(data)

    def to_json(
        self,
        include: set[str] | None = None,
        exclude: set[str] | None = None,
        exclude_none: bool = False,
    ) -> str:
        return self.model_dump_json(
            include=include,
            exclude=exclude,
            exclude_none=exclude_none,
        )

    @classmethod
    def from_json(cls, data: str) -> Self:
        return cls.model_validate_json(data)

    def to_jsonb(
        self,
        include: set[str] | None = None,
        exclude: set[str] | None = None,
        exclude_none: bool = False,
    ) -> bytes:
        return self.model_dump_json(
            include=include,
            exclude=exclude,
            exclude_none=exclude_none,
        ).encode("utf-8")

    @classmethod
    def from_jsonb(cls, data: bytes) -> Self:
        return cls.model_validate_json(data.decode("utf-8"))

    @classmethod
    def json_schema(cls) -> dict[str, Any]:
        return cls.model_json_schema()
