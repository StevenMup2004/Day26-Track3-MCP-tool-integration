from __future__ import annotations

import argparse
import json
import mimetypes
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

try:
    from .db import SQLiteAdapter, ValidationError
    from .init_db import DEFAULT_DB_PATH, create_database
except ImportError:  # Allows `python implementation/ui_server.py`.
    from db import SQLiteAdapter, ValidationError
    from init_db import DEFAULT_DB_PATH, create_database


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
            else:
                self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)
        except (TypeError, ValidationError, ValueError) as exc:
            self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

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
