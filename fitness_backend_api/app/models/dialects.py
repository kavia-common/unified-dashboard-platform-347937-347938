"""
Dialect-aware SQLAlchemy type helpers.

Why this exists:
- The production DB is PostgreSQL and we use PG-specific column types like CITEXT, UUID, JSONB, ARRAY.
- Some CI-safe tests use SQLite (in-memory) for speed/isolation.
- SQLite cannot compile PG-specific DDL for these types, causing test setup failures.

These helpers preserve production Postgres behavior while providing safe fallbacks
for SQLite and other dialects.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy import Text, func
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import mapped_column
from sqlalchemy.types import TypeDecorator


class DialectCITEXT(TypeDecorator):
    """Case-insensitive text on Postgres; plain text elsewhere."""

    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(postgresql.CITEXT())
        return dialect.type_descriptor(Text())


class DialectUUID(TypeDecorator):
    """UUID on Postgres; stored as TEXT elsewhere (e.g., SQLite)."""

    impl = Text
    cache_ok = True

    def __init__(self, *, as_uuid: bool = True) -> None:
        super().__init__()
        self.as_uuid = as_uuid

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(postgresql.UUID(as_uuid=self.as_uuid))
        return dialect.type_descriptor(Text())


class DialectJSONB(TypeDecorator):
    """
    JSONB on Postgres; stored as JSON text elsewhere.

    Note:
    - For SQLite fallback we store JSON as TEXT and (de)serialize in bind/result
      processors. This is sufficient for tests that don't require JSON operators.
    """

    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(postgresql.JSONB())
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value: Any, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        return json.dumps(value)

    def process_result_value(self, value: Any, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        try:
            return json.loads(value)
        except Exception:
            # Be forgiving if legacy/non-json values exist in tests.
            return value


class DialectARRAYText(TypeDecorator):
    """
    ARRAY(Text) on Postgres; stored as JSON text list elsewhere.

    Intended use in this repo: columns like tags/equipment stored as list[str].
    """

    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(postgresql.ARRAY(Text()))
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value: Any, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        # SQLite: store list as JSON string
        return json.dumps(list(value))

    def process_result_value(self, value: Any, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else []
        except Exception:
            return []


# PUBLIC_INTERFACE
def uuid_pk_column() -> Any:
    """Create a UUID primary key column that works on both Postgres and SQLite.

    Behavior:
    - PostgreSQL: use `server_default=gen_random_uuid()` so the DB generates UUIDs.
      This matches the production schema/migrations (and is efficient).
    - SQLite (tests): SQLite doesn't have `gen_random_uuid()`, so we generate UUIDs
      in Python via `default=uuid4`.

    Notes:
    - We return a SQLAlchemy `mapped_column(...)` so callers can use:
        id: Mapped[str] = uuid_pk_column()
    - The returned column uses our DialectUUID type to keep DDL cross-dialect.
    """

    def _py_uuid4_str() -> str:
        # Keep IDs as canonical text UUIDs in non-Postgres dialects.
        return str(uuid.uuid4())

    return mapped_column(
        DialectUUID(as_uuid=True),
        primary_key=True,
        default=_py_uuid4_str,
        server_default=func.gen_random_uuid(),
    )
