from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

try:
    from .db import SQLiteAdapter, ValidationError
    from .init_db import DEFAULT_DB_PATH, create_database
except ImportError:  # Allows `python implementation/mcp_server.py`.
    from db import SQLiteAdapter, ValidationError
    from init_db import DEFAULT_DB_PATH, create_database


SERVER_NAME = "SQLite Lab MCP Server"


def default_db_path() -> Path:
    return Path(os.environ.get("SQLITE_LAB_DB", DEFAULT_DB_PATH))


def default_adapter() -> SQLiteAdapter:
    db_path = default_db_path()
    if not db_path.exists():
        create_database(db_path)
    return SQLiteAdapter(db_path)


def create_mcp_server(adapter: SQLiteAdapter | None = None) -> FastMCP:
    db = adapter or default_adapter()
    mcp = FastMCP(SERVER_NAME)

    @mcp.tool(
        name="search",
        description=(
            "Search rows in a validated SQLite table with optional filters, "
            "column selection, ordering, limit, and offset."
        ),
    )
    def search(
        table: str,
        filters: Any = None,
        columns: list[str] | None = None,
        limit: int = 20,
        offset: int = 0,
        order_by: str | None = None,
        descending: bool = False,
    ) -> dict[str, Any]:
        try:
            return db.search(
                table=table,
                filters=filters,
                columns=columns,
                limit=limit,
                offset=offset,
                order_by=order_by,
                descending=descending,
            )
        except ValidationError as exc:
            raise ValueError(str(exc)) from exc

    @mcp.tool(
        name="insert",
        description="Insert one row into a validated SQLite table and return it.",
    )
    def insert(table: str, values: dict[str, Any]) -> dict[str, Any]:
        try:
            return db.insert(table=table, values=values)
        except ValidationError as exc:
            raise ValueError(str(exc)) from exc

    @mcp.tool(
        name="aggregate",
        description=(
            "Run a validated aggregate query using count, avg, sum, min, or max "
            "with optional filters and group_by."
        ),
    )
    def aggregate(
        table: str,
        metric: str,
        column: str | None = None,
        filters: Any = None,
        group_by: str | list[str] | None = None,
    ) -> dict[str, Any]:
        try:
            return db.aggregate(
                table=table,
                metric=metric,
                column=column,
                filters=filters,
                group_by=group_by,
            )
        except ValidationError as exc:
            raise ValueError(str(exc)) from exc

    @mcp.resource(
        "schema://database",
        name="database_schema",
        description="Full SQLite database schema as JSON.",
        mime_type="application/json",
    )
    def database_schema() -> str:
        return json.dumps(db.database_schema(), indent=2)

    @mcp.resource(
        "schema://table/{table_name}",
        name="table_schema",
        description="Schema for one SQLite table as JSON.",
        mime_type="application/json",
    )
    def table_schema(table_name: str) -> str:
        try:
            payload = {"table": table_name, "columns": db.get_table_schema(table_name)}
            return json.dumps(payload, indent=2)
        except ValidationError as exc:
            raise ValueError(str(exc)) from exc

    return mcp


mcp = create_mcp_server()


if __name__ == "__main__":
    mcp.run()
