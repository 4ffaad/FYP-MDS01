"""Reusable database types for compatibility-safe model serialization."""

from __future__ import annotations

from enum import Enum

from sqlalchemy import String, TypeDecorator


class EnumString(TypeDecorator):
    """Persist enum values while reading both values and legacy names."""

    impl = String(32)
    cache_ok = True

    def __init__(self, enum_type: type[Enum]) -> None:
        super().__init__()
        self.enum_type = enum_type

    def process_bind_param(self, value, dialect):
        return value.value if isinstance(value, Enum) else value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        try:
            return self.enum_type(value)
        except ValueError:
            return self.enum_type[value]
