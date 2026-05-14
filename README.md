# SQLite Lab MCP Server

This project implements the Day 26 Track 3 delivery: a FastMCP server backed by SQLite. It exposes the required `search`, `insert`, and `aggregate` tools, plus schema resources for the full database and individual tables.

## Current Status

Verified on 2026-05-14 with:

- Python: `3.14.3` from `.venv`
- FastMCP: `3.2.4`
- Pytest: `9.0.3`
- Codex CLI: `0.130.0-alpha.5`

Completed:

- FastMCP stdio server
- SQLite schema and deterministic seed data
- Tools: `search`, `insert`, `aggregate`
- Resources: `schema://database`, `schema://table/{table_name}`
- Safe identifier validation and parameterized SQL values
- Repeatable verification script
- Automated pytest coverage
- Codex MCP client configuration and smoke demo
- Browser UI dashboard for visual demo

Still useful before final submission:

- Record the 2-minute demo video or take screenshots from the browser UI and Codex.
- Push the final repository to GitHub.

## Project Structure

```text
implementation/
  __init__.py
  db.py
  init_db.py
  mcp_server.py
  ui_server.py
  verify_server.py
  start_ui.ps1
  start_inspector.ps1
  ui/
    index.html
    styles.css
    app.js
  tests/
    test_server.py
requirements.txt
plan.md
Rubric.md
codex_demo_output.txt
```

## Setup

Use the project virtual environment:

```powershell
cd C:\Users\dangv\Downloads\VinCourse\day26\Day26-Track3-MCP-tool-integration
& ".venv\Scripts\python.exe" -m pip install -r requirements.txt
```

Initialize the SQLite database:

```powershell
& ".venv\Scripts\python.exe" implementation\init_db.py
```

This creates:

```text
implementation/sqlite_lab.db
```

The database contains:

- `students`
- `courses`
- `enrollments`

## Run the MCP Server

```powershell
& ".venv\Scripts\python.exe" implementation\mcp_server.py
```

The server runs on stdio by default.

## Visual UI Demo

The project includes a browser dashboard for demo and screenshots. It uses the same SQLite adapter as the MCP server, so table search, aggregate visualization, schema view, insert, and reset actions run against the real local database.

Start the UI:

```powershell
& ".venv\Scripts\python.exe" implementation\ui_server.py --host 127.0.0.1 --port 8765
```

Or:

```powershell
.\implementation\start_ui.ps1
```

Open:

```text
http://127.0.0.1:8765
```

Useful UI demo flow:

- Open the **MCP Demo** tab.
- Click **List Tools** to show MCP-discoverable tools and resources.
- Edit the prompt, then click **Run Prompt** to show the prompt, answer, and MCP call trace.
- Show `students` rows ordered by `score`.
- Filter `students` where `cohort = A1`.
- Visualize `avg(score)` grouped by `cohort`.
- Open the Schema tab and show columns/constraints.
- Insert a new student from the Insert tab.
- Click Reset to restore deterministic seed data.

Default MCP UI prompt:

```text
List the available MCP tools and resources. Read schema://database. Search students in cohort A1 ordered by score descending. Count students and calculate average score by cohort.
```

Prompt with invalid request demo:

```text
List tools, read schema, search A1 students, count students, average score by cohort, and show invalid error.
```

## Tools

### `search`

Search rows in a validated table.

Example arguments:

```json
{
  "table": "students",
  "filters": {"cohort": "A1"},
  "columns": ["id", "name", "cohort", "score"],
  "limit": 5,
  "offset": 0,
  "order_by": "score",
  "descending": true
}
```

Supported filter operators:

- `eq`
- `ne`
- `gt`
- `gte`
- `lt`
- `lte`
- `like`
- `in`

Filters may be simple:

```json
{"cohort": "A1"}
```

Or explicit:

```json
[
  {"column": "score", "operator": "gte", "value": 85}
]
```

### `insert`

Insert one row and return the inserted record.

Example arguments:

```json
{
  "table": "students",
  "values": {
    "name": "Test Student",
    "email": "test.student@example.com",
    "cohort": "A1",
    "age": 25,
    "score": 82.0
  }
}
```

### `aggregate`

Run `count`, `avg`, `sum`, `min`, or `max`.

Example count:

```json
{
  "table": "students",
  "metric": "count"
}
```

Example average score by cohort:

```json
{
  "table": "students",
  "metric": "avg",
  "column": "score",
  "group_by": "cohort"
}
```

## Resources

Full database schema:

```text
schema://database
```

Single table schema:

```text
schema://table/{table_name}
```

Example:

```text
schema://table/students
```

## Verification

Run the repeatable verification script:

```powershell
& ".venv\Scripts\python.exe" implementation\verify_server.py
```

Expected output:

```text
Verification passed:
- server initialized via FastMCP client
- tools discovered: aggregate, insert, search
- schema resource and table template discovered/read
- valid search/insert/aggregate calls passed
- invalid table/column/operator/insert/aggregate errors passed
```

Run automated tests:

```powershell
& ".venv\Scripts\python.exe" -m pytest -q
```

Verified result:

```text
3 passed
```

## Codex MCP Demo

Codex was used as the MCP client demo.

If `codex` is not recognized in PowerShell, run the helper script. It finds `codex.exe` from the OpenAI ChatGPT VS Code extension, adds `sqlite-lab` if needed, prints the MCP config, runs the smoke prompt, and prints `codex_demo_output.txt`.

```powershell
.\run_codex_mcp_demo.ps1
```

The server was added globally with:

```powershell
codex mcp add sqlite-lab -- "C:\Users\dangv\Downloads\VinCourse\day26\Day26-Track3-MCP-tool-integration\.venv\Scripts\python.exe" "C:\Users\dangv\Downloads\VinCourse\day26\Day26-Track3-MCP-tool-integration\implementation\mcp_server.py"
```

Check the configuration:

```powershell
codex mcp list
codex mcp get sqlite-lab
```

Verified local config:

```text
sqlite-lab
  enabled: true
  transport: stdio
  command: C:\Users\dangv\Downloads\VinCourse\day26\Day26-Track3-MCP-tool-integration\.venv\Scripts\python.exe
  args: C:\Users\dangv\Downloads\VinCourse\day26\Day26-Track3-MCP-tool-integration\implementation\mcp_server.py
```

Smoke demo command:

```powershell
codex exec --ephemeral --json --output-last-message codex_demo_output.txt --sandbox read-only -C "C:\Users\dangv\Downloads\VinCourse\day26\Day26-Track3-MCP-tool-integration" "Do not modify files. Use the sqlite-lab MCP server to read schema://database and call the aggregate tool to count students. Then answer with the table names and student count only."
```

Demo output saved in `codex_demo_output.txt`:

```text
courses, enrollments, students

students: 6
```

## MCP Inspector

Optional Inspector helper:

```powershell
.\implementation\start_inspector.ps1
```

Manual equivalent:

```powershell
$env:NPM_CONFIG_CACHE="$PWD\.npm-cache"
npx -y @modelcontextprotocol/inspector "C:\Users\dangv\Downloads\VinCourse\day26\Day26-Track3-MCP-tool-integration\.venv\Scripts\python.exe" "C:\Users\dangv\Downloads\VinCourse\day26\Day26-Track3-MCP-tool-integration\implementation\mcp_server.py"
```

## Error Handling

The server rejects:

- unknown table names
- unknown column names
- unsupported filter operators
- invalid aggregate requests
- empty inserts

SQL values are passed with bound parameters. Table and column identifiers are accepted only after checking SQLite schema metadata.
