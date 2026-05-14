# Demo Recording

Day 26 Track 3 - MCP Tool Integration  
Project: SQLite Lab MCP Server

## Video Link

[Open the demo recording on Google Drive](https://drive.google.com/file/d/16UF55hdR069NH06VdOkBf3wcpJQx8N7E/view?usp=sharing)

## Demo Coverage

- FastMCP server backed by a reproducible SQLite database.
- Required MCP tools: `search`, `insert`, and `aggregate`.
- MCP resources: `schema://database` and `schema://table/{table_name}`.
- Safe validation for unknown tables, unknown columns, unsupported operators, empty inserts, and invalid aggregate calls.
- Codex MCP client integration through the configured `sqlite-lab` server.
- Browser UI dashboard for visual demo of table search, aggregation, schema viewing, insert, reset, and real Codex prompt flow.

## Verification Evidence

The project was verified locally on 2026-05-14 with:

```powershell
& ".venv\Scripts\python.exe" implementation\init_db.py
& ".venv\Scripts\python.exe" implementation\verify_server.py
& ".venv\Scripts\python.exe" -m pytest -q
codex mcp list
codex mcp get sqlite-lab
```

Expected automated test result:

```text
3 passed
```

Expected Codex MCP smoke-demo output:

```text
courses, enrollments, students

students: 6
```

## Related Files

- `README.md` - setup, usage, tool examples, resources, verification, and Codex demo commands.
- `Rubric.md` - grading checklist and current completion status.
- `codex_demo_output.txt` - saved Codex MCP smoke-demo output.
