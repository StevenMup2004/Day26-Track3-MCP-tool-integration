from __future__ import annotations

import argparse
import asyncio
import json
import mimetypes
import time
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from fastmcp import Client

try:
    from .db import SQLiteAdapter, ValidationError
    from .init_db import DEFAULT_DB_PATH, create_database
    from .mcp_server import create_mcp_server
except ImportError:  # Allows `python implementation/ui_server.py`.
    from db import SQLiteAdapter, ValidationError
    from init_db import DEFAULT_DB_PATH, create_database
    from mcp_server import create_mcp_server


IMPLEMENTATION_DIR = Path(__file__).resolve().parent
UI_DIR = IMPLEMENTATION_DIR / "ui"


class DashboardHandler(SimpleHTTPRequestHandler):
    adapter: SQLiteAdapter
    db_path: Path

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(UI_DIR), **kwargs)

    def log_message(self, format: str, *args: Any) -> None:
        print(f"[ui] {self.address_string()} - {format % args}")

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            self._handle_api_get(parsed.path, parse_qs(parsed.query))
            return
        if parsed.path == "/":
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if not parsed.path.startswith("/api/"):
            self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(length).decode("utf-8") if length else "{}"
            payload = json.loads(raw_body or "{}")
        except json.JSONDecodeError as exc:
            self._send_json({"error": f"invalid JSON: {exc}"}, HTTPStatus.BAD_REQUEST)
            return
        self._handle_api_post(parsed.path, payload)

    def guess_type(self, path: str) -> str:
        if path.endswith(".js"):
            return "text/javascript"
        return mimetypes.guess_type(path)[0] or "application/octet-stream"

    def _handle_api_get(self, path: str, query: dict[str, list[str]]) -> None:
        try:
            if path == "/api/health":
                self._send_json(
                    {"ok": True, "database": str(self.db_path), "tables": self.adapter.list_tables()}
                )
            elif path == "/api/schema":
                self._send_json(self.adapter.database_schema())
            elif path == "/api/table":
                table = self._query_value(query, "name")
                self._send_json({"table": table, "columns": self.adapter.get_table_schema(table)})
            elif path == "/api/search":
                self._send_json(
                    self.adapter.search(
                        table=self._query_value(query, "table", "students"),
                        limit=int(self._query_value(query, "limit", "20")),
                        offset=int(self._query_value(query, "offset", "0")),
                        order_by=self._query_optional(query, "order_by"),
                        descending=self._query_value(query, "descending", "false").lower()
                        == "true",
                    )
                )
            elif path == "/api/mcp/metadata":
                self._send_json(asyncio.run(self._mcp_metadata()))
            else:
                self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)
        except (ValidationError, ValueError) as exc:
            self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

    def _handle_api_post(self, path: str, payload: dict[str, Any]) -> None:
        try:
            if path == "/api/search":
                self._send_json(self.adapter.search(**payload))
            elif path == "/api/insert":
                self._send_json(self.adapter.insert(**payload), HTTPStatus.CREATED)
            elif path == "/api/aggregate":
                self._send_json(self.adapter.aggregate(**payload))
            elif path == "/api/reset":
                create_database(self.db_path)
                self._send_json({"ok": True, "database": str(self.db_path)})
            elif path == "/api/mcp/prompt":
                prompt = str(payload.get("prompt", "")).strip()
                self._send_json(asyncio.run(self._run_mcp_prompt(prompt)))
            else:
                self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)
        except (TypeError, ValidationError, ValueError) as exc:
            self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

    async def _mcp_metadata(self) -> dict[str, Any]:
        server = create_mcp_server(SQLiteAdapter(self.db_path))
        async with Client(server) as client:
            tools = await client.list_tools()
            resources = await client.list_resources()
            templates = await client.list_resource_templates()
        return {
            "tools": [self._model_to_json(tool) for tool in tools],
            "resources": [self._model_to_json(resource) for resource in resources],
            "resource_templates": [
                self._model_to_json(template) for template in templates
            ],
        }

    async def _run_mcp_prompt(self, prompt: str) -> dict[str, Any]:
        if not prompt:
            prompt = DEFAULT_PROMPT

        normalized = prompt.lower()
        trace: list[dict[str, Any]] = []
        answer_parts: list[str] = []
        server = create_mcp_server(SQLiteAdapter(self.db_path))

        async with Client(server) as client:
            tools = await client.list_tools()
            resources = await client.list_resources()
            templates = await client.list_resource_templates()
            tool_names = [tool.name for tool in tools]

            trace.append(
                {
                    "step": "discover",
                    "operation": "list_tools",
                    "ok": True,
                    "result": {"tools": tool_names},
                }
            )
            trace.append(
                {
                    "step": "discover",
                    "operation": "list_resources",
                    "ok": True,
                    "result": {
                        "resources": [str(resource.uri) for resource in resources],
                        "resource_templates": [
                            template.uriTemplate for template in templates
                        ],
                    },
                }
            )

            schema_contents = await client.read_resource("schema://database")
            schema_text = schema_contents[0].text
            schema = json.loads(schema_text)
            table_names = sorted(schema["tables"])
            trace.append(
                {
                    "step": "resource",
                    "operation": "read_resource",
                    "arguments": {"uri": "schema://database"},
                    "ok": True,
                    "result": {"tables": table_names},
                }
            )
            answer_parts.append(f"Tools: {', '.join(tool_names)}")
            answer_parts.append(f"Tables: {', '.join(table_names)}")

            wants_search = self._mentions_any(
                normalized, ["search", "student", "students", "a1", "cohort", "tim", "tìm", "lọc"]
            )
            wants_average = self._mentions_any(
                normalized,
                ["avg", "average", "trung bình", "cohort", "aggregate", "thống kê"],
            )
            wants_count = self._mentions_any(
                normalized, ["count", "đếm", "dem", "bao nhiêu", "student count"]
            )
            wants_invalid = self._mentions_any(
                normalized, ["invalid", "error", "lỗi", "missing", "sai"]
            )

            if not any([wants_search, wants_average, wants_count, wants_invalid]):
                wants_search = True
                wants_average = True
                wants_count = True

            if wants_search:
                args = {
                    "table": "students",
                    "filters": {"cohort": "A1"},
                    "columns": ["id", "name", "cohort", "score"],
                    "limit": 10,
                    "order_by": "score",
                    "descending": True,
                }
                result = await client.call_tool("search", args)
                data = self._tool_data(result)
                trace.append(
                    {
                        "step": "tool",
                        "operation": "search",
                        "arguments": args,
                        "ok": True,
                        "result": data,
                    }
                )
                students = ", ".join(
                    f"{row['name']} ({row['score']})" for row in data["rows"]
                )
                answer_parts.append(f"A1 students by score: {students}")

            if wants_count:
                args = {"table": "students", "metric": "count", "column": "id"}
                result = await client.call_tool("aggregate", args)
                data = self._tool_data(result)
                trace.append(
                    {
                        "step": "tool",
                        "operation": "aggregate",
                        "arguments": args,
                        "ok": True,
                        "result": data,
                    }
                )
                answer_parts.append(f"Student count: {data['rows'][0]['value']}")

            if wants_average:
                args = {
                    "table": "students",
                    "metric": "avg",
                    "column": "score",
                    "group_by": "cohort",
                }
                result = await client.call_tool("aggregate", args)
                data = self._tool_data(result)
                trace.append(
                    {
                        "step": "tool",
                        "operation": "aggregate",
                        "arguments": args,
                        "ok": True,
                        "result": data,
                    }
                )
                averages = ", ".join(
                    f"{row['cohort']}: {round(row['value'], 2)}"
                    for row in data["rows"]
                )
                answer_parts.append(f"Average score by cohort: {averages}")

            if wants_invalid:
                args = {"table": "missing_table"}
                result = await client.call_tool(
                    "search", args, raise_on_error=False
                )
                error_text = result.content[0].text if result.content else ""
                trace.append(
                    {
                        "step": "tool",
                        "operation": "search",
                        "arguments": args,
                        "ok": False,
                        "error": error_text,
                    }
                )
                answer_parts.append(f"Invalid request demo: {error_text}")

        return {
            "prompt": prompt,
            "answer": "\n".join(answer_parts),
            "trace": trace,
            "ran_at": int(time.time()),
        }

    def _send_json(
        self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK
    ) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    @staticmethod
    def _query_value(
        query: dict[str, list[str]], key: str, default: str | None = None
    ) -> str:
        values = query.get(key)
        if values and values[0] != "":
            return values[0]
        if default is not None:
            return default
        raise ValidationError(f"missing query parameter: {key}")

    @staticmethod
    def _query_optional(query: dict[str, list[str]], key: str) -> str | None:
        values = query.get(key)
        if values and values[0] != "":
            return values[0]
        return None

    @staticmethod
    def _model_to_json(value: Any) -> dict[str, Any]:
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json")
        if hasattr(value, "dict"):
            return value.dict()
        return dict(value)

    @staticmethod
    def _tool_data(result: Any) -> Any:
        if getattr(result, "data", None) is not None:
            return result.data
        return getattr(result, "structured_content", None)

    @staticmethod
    def _mentions_any(text: str, terms: list[str]) -> bool:
        return any(term in text for term in terms)


DEFAULT_PROMPT = (
    "List the available MCP tools and resources. Read schema://database. "
    "Search students in cohort A1 ordered by score descending. "
    "Count students and calculate average score by cohort."
)


def run(host: str, port: int, db_path: Path) -> None:
    if not db_path.exists():
        create_database(db_path)
    DashboardHandler.adapter = SQLiteAdapter(db_path)
    DashboardHandler.db_path = db_path
    server = ThreadingHTTPServer((host, port), DashboardHandler)
    print(f"SQLite Lab UI running at http://{host}:{port}")
    print(f"Database: {db_path}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopping UI server")
    finally:
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the SQLite Lab dashboard UI.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    args = parser.parse_args()
    run(args.host, args.port, args.db)


if __name__ == "__main__":
    main()
