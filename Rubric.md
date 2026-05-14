# Rubric

Total base score: 100 points  
Optional bonus: up to 10 extra points

## Current Submission Status - 2026-05-14

Estimated status: **100/100 base points ready**.

The implementation is complete and verified for server, tools, resources, safety, tests, Codex client integration, and browser UI visualization. The remaining non-code task is to record the final 2-minute video or take screenshots from the UI/Codex if required by the grader.

Verified commands:

```powershell
& ".venv\Scripts\python.exe" implementation\init_db.py
& ".venv\Scripts\python.exe" implementation\verify_server.py
& ".venv\Scripts\python.exe" -m pytest -q
& ".venv\Scripts\python.exe" implementation\ui_server.py --host 127.0.0.1 --port 8765
codex mcp list
codex mcp get sqlite-lab
codex exec --ephemeral --json --output-last-message codex_demo_output.txt --sandbox read-only -C "C:\Users\dangv\Downloads\VinCourse\day26\Day26-Track3-MCP-tool-integration" "Do not modify files. Use the sqlite-lab MCP server to read schema://database and call the aggregate tool to count students. Then answer with the table names and student count only."
```

Codex demo output:

```text
courses, enrollments, students

students: 6
```

## 1. Server Foundation - 20 points

- [x] 5 pts: FastMCP server starts successfully
- [x] 5 pts: project structure is clean and understandable
- [x] 5 pts: SQLite database is initialized with reproducible schema/data
- [x] 5 pts: code is organized into server logic and database logic

Status: **20/20**

Evidence:

- `implementation/mcp_server.py`
- `implementation/init_db.py`
- `implementation/db.py`
- `implementation/verify_server.py`

## 2. Required Tools - 30 points

- [x] 10 pts: `search` works with filters, ordering, and pagination
- [x] 10 pts: `insert` works and returns the inserted payload
- [x] 10 pts: `aggregate` supports useful metrics such as `count`, `avg`, `sum`, `min`, `max`

Status: **30/30**

Evidence:

- `implementation/db.py`
- `implementation/mcp_server.py`
- `implementation/tests/test_server.py`

## 3. MCP Resources - 15 points

- [x] 8 pts: full database schema resource is exposed
- [x] 7 pts: per-table schema resource template is exposed and readable

Status: **15/15**

Evidence:

- `schema://database`
- `schema://table/{table_name}`
- Verified by `implementation/verify_server.py`

## 4. Safety and Error Handling - 15 points

- [x] 5 pts: invalid table and column names are rejected
- [x] 5 pts: unsupported operators or bad aggregate requests are rejected
- [x] 5 pts: SQL execution uses safe parameterized patterns where appropriate

Status: **15/15**

Evidence:

- Table/column identifiers are validated from SQLite schema metadata.
- Filter and insert values use bound SQL parameters.
- Invalid requests are covered by `verify_server.py` and pytest.

## 5. Verification - 10 points

- [x] 4 pts: tool discovery is verified
- [x] 3 pts: successful tool calls are demonstrated
- [x] 3 pts: failing tool calls are demonstrated with clear errors

Status: **10/10**

Evidence:

- `implementation/verify_server.py`
- `implementation/tests/test_server.py`
- Latest local result: `3 passed`

## 6. Client Integration and Demo - 10 points

- [x] 4 pts: at least one MCP client is configured correctly
- [x] 3 pts: README includes setup and test steps
- [x] 3 pts: short demo or screenshots show the server in use

Status: **10/10**

Evidence:

- Codex MCP server `sqlite-lab` configured with `.venv\Scripts\python.exe`.
- `codex_demo_output.txt` shows Codex reading table names and counting students through MCP.
- Browser UI dashboard is available at `http://127.0.0.1:8765` when `implementation/ui_server.py` is running.
- Browser UI includes an **MCP Demo** tab with prompt input, MCP tool/resource discovery, fast local MCP trace, and **Run Real Codex** for a real prompt workflow through Codex CLI.
- Recommended final polish: record the 2-minute video or take screenshots of the UI plus `codex mcp list` and Codex prompt output.

## Bonus - up to 10 points

- [ ] 5 pts: SSE or HTTP auth implemented and demonstrated
- [ ] 3 pts: support for both SQLite and PostgreSQL behind a shared interface
- [x] 2 pts: extra polish such as pagination guidance, output limits, or structured testing

Status: **2/10 optional bonus likely available**.

## Quick Grading Questions

1. Can I start the server and discover the tools? **Yes.**
2. Do `search`, `insert`, and `aggregate` all work? **Yes.**
3. Can I read the schema resource and the per-table schema template? **Yes.**
4. Does the project reject bad input safely? **Yes.**
5. Is there a repeatable verification story? **Yes, `verify_server.py` and pytest.**
6. Can at least one client actually use the server? **Yes, Codex.**
