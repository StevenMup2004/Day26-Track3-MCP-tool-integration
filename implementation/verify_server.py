from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

os.environ.setdefault("FASTMCP_LOG_LEVEL", "CRITICAL")
os.environ.setdefault("FASTMCP_ENABLE_RICH_TRACEBACKS", "false")

from fastmcp import Client

try:
    from .db import SQLiteAdapter
    from .init_db import DEFAULT_DB_PATH, create_database
    from .mcp_server import create_mcp_server
except ImportError:  # Allows `python implementation/verify_server.py`.
    from db import SQLiteAdapter
    from init_db import DEFAULT_DB_PATH, create_database
    from mcp_server import create_mcp_server


def _data(result: Any) -> Any:
    return result.data if result.data is not None else result.structured_content


def _text_resource(contents: list[Any]) -> str:
    if not contents:
        raise AssertionError("resource returned no contents")
    content = contents[0]
    if not hasattr(content, "text"):
        raise AssertionError("expected a text resource")
    return content.text


async def run_verification(db_path: str | Path = DEFAULT_DB_PATH) -> None:
    path = create_database(db_path)
    server = create_mcp_server(SQLiteAdapter(path))

    async with Client(server) as client:
        tools = await client.list_tools()
        tool_names = {tool.name for tool in tools}
        expected_tools = {"search", "insert", "aggregate"}
        assert expected_tools == tool_names, f"expected {expected_tools}, got {tool_names}"

        resources = await client.list_resources()
        resource_uris = {str(resource.uri) for resource in resources}
        assert "schema://database" in resource_uris

        templates = await client.list_resource_templates()
        template_uris = {template.uriTemplate for template in templates}
        assert "schema://table/{table_name}" in template_uris

        schema_text = _text_resource(await client.read_resource("schema://database"))
        schema = json.loads(schema_text)
        assert {"students", "courses", "enrollments"} <= set(schema["tables"])

        students_schema_text = _text_resource(
            await client.read_resource("schema://table/students")
        )
        students_schema = json.loads(students_schema_text)
        assert students_schema["table"] == "students"

        search_result = _data(
            await client.call_tool(
                "search",
                {
                    "table": "students",
                    "filters": {"cohort": "A1"},
                    "order_by": "score",
                    "descending": True,
                    "limit": 5,
                },
            )
        )
        assert search_result["count"] == 2
        assert search_result["rows"][0]["score"] >= search_result["rows"][1]["score"]

        insert_result = _data(
            await client.call_tool(
                "insert",
                {
                    "table": "students",
                    "values": {
                        "name": "Test Student",
                        "email": "test.student@example.com",
                        "cohort": "A1",
                        "age": 25,
                        "score": 82.0,
                    },
                },
            )
        )
        assert insert_result["record"]["email"] == "test.student@example.com"

        count_result = _data(
            await client.call_tool("aggregate", {"table": "students", "metric": "count"})
        )
        assert count_result["rows"][0]["value"] == 7

        avg_result = _data(
            await client.call_tool(
                "aggregate",
                {
                    "table": "students",
                    "metric": "avg",
                    "column": "score",
                    "group_by": "cohort",
                },
            )
        )
        assert {row["cohort"] for row in avg_result["rows"]} == {"A1", "A2", "B1"}

        bad_table = await client.call_tool(
            "search",
            {"table": "missing_table"},
            raise_on_error=False,
        )
        assert bad_table.is_error
        assert "unknown table" in bad_table.content[0].text.lower()

        bad_column = await client.call_tool(
            "search",
            {"table": "students", "filters": {"missing_column": "x"}},
            raise_on_error=False,
        )
        assert bad_column.is_error
        assert "unknown column" in bad_column.content[0].text.lower()

        bad_operator = await client.call_tool(
            "search",
            {
                "table": "students",
                "filters": [
                    {"column": "cohort", "operator": "contains", "value": "A"}
                ],
            },
            raise_on_error=False,
        )
        assert bad_operator.is_error
        assert "unsupported filter operator" in bad_operator.content[0].text.lower()

        empty_insert = await client.call_tool(
            "insert",
            {"table": "students", "values": {}},
            raise_on_error=False,
        )
        assert empty_insert.is_error
        assert "non-empty values" in empty_insert.content[0].text.lower()

        bad_aggregate = await client.call_tool(
            "aggregate",
            {"table": "students", "metric": "avg"},
            raise_on_error=False,
        )
        assert bad_aggregate.is_error
        assert "requires a column" in bad_aggregate.content[0].text.lower()

    create_database(path)

    print("Verification passed:")
    print("- server initialized via FastMCP client")
    print("- tools discovered: aggregate, insert, search")
    print("- schema resource and table template discovered/read")
    print("- valid search/insert/aggregate calls passed")
    print("- invalid table/column/operator/insert/aggregate errors passed")
    print(f"- database path: {path}")


if __name__ == "__main__":
    asyncio.run(run_verification())
