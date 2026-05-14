from __future__ import annotations

import asyncio
import json

import pytest
from fastmcp import Client

from implementation.db import SQLiteAdapter, ValidationError
from implementation.init_db import create_database
from implementation.mcp_server import create_mcp_server


def _make_adapter(tmp_path):
    db_path = create_database(tmp_path / "test.sqlite3")
    return SQLiteAdapter(db_path)


def test_search_insert_and_aggregate(tmp_path):
    adapter = _make_adapter(tmp_path)

    results = adapter.search(
        table="students",
        filters={"cohort": "A1"},
        order_by="score",
        descending=True,
    )
    assert results["count"] == 2
    assert results["rows"][0]["score"] >= results["rows"][1]["score"]

    inserted = adapter.insert(
        "students",
        {
            "name": "Local Tester",
            "email": "local.tester@example.com",
            "cohort": "A2",
            "age": 26,
            "score": 80.0,
        },
    )
    assert inserted["record"]["email"] == "local.tester@example.com"

    aggregate = adapter.aggregate("students", "avg", "score", group_by="cohort")
    assert {row["cohort"] for row in aggregate["rows"]} == {"A1", "A2", "B1"}


def test_validation_errors(tmp_path):
    adapter = _make_adapter(tmp_path)

    with pytest.raises(ValidationError, match="unknown table"):
        adapter.search("missing")

    with pytest.raises(ValidationError, match="unknown column"):
        adapter.search("students", filters={"missing_column": "x"})

    with pytest.raises(ValidationError, match="unsupported filter operator"):
        adapter.search(
            "students",
            filters=[{"column": "cohort", "operator": "contains", "value": "A"}],
        )

    with pytest.raises(ValidationError, match="non-empty values"):
        adapter.insert("students", {})

    with pytest.raises(ValidationError, match="requires a column"):
        adapter.aggregate("students", "avg")


def test_mcp_tools_and_resources(tmp_path):
    async def scenario():
        server = create_mcp_server(_make_adapter(tmp_path))
        async with Client(server) as client:
            tools = await client.list_tools()
            assert {tool.name for tool in tools} == {"search", "insert", "aggregate"}

            resources = await client.list_resources()
            assert "schema://database" in {str(resource.uri) for resource in resources}

            templates = await client.list_resource_templates()
            assert "schema://table/{table_name}" in {
                template.uriTemplate for template in templates
            }

            table_schema = await client.read_resource("schema://table/students")
            payload = json.loads(table_schema[0].text)
            assert payload["table"] == "students"

            result = await client.call_tool(
                "search", {"table": "students", "filters": {"cohort": "A1"}}
            )
            assert result.data["count"] == 2

            invalid = await client.call_tool(
                "search", {"table": "missing"}, raise_on_error=False
            )
            assert invalid.is_error
            assert "unknown table" in invalid.content[0].text.lower()

    asyncio.run(scenario())
