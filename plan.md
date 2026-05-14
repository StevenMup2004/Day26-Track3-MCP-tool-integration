# Plan delivery hôm nay - 14/05/2026

## Status update - 14/05/2026

Done:

- [x] Created `implementation/` with `db.py`, `init_db.py`, `mcp_server.py`, `verify_server.py`, tests, and Inspector helper.
- [x] Installed and used packages from `.venv`: `fastmcp` and `pytest`.
- [x] Built reproducible SQLite database with `students`, `courses`, and `enrollments`.
- [x] Implemented `search`, `insert`, and `aggregate`.
- [x] Implemented `schema://database` and `schema://table/{table_name}`.
- [x] Added validation for table names, column names, operators, empty inserts, and invalid aggregate calls.
- [x] Verified with `implementation/verify_server.py`.
- [x] Verified automated tests with `pytest`: `3 passed`.
- [x] Configured Codex MCP client as `sqlite-lab`.
- [x] Ran Codex MCP smoke demo and saved output to `codex_demo_output.txt`.
- [x] Added browser UI dashboard for visualizing rows, schema, aggregates, and inserts.
- [x] Updated `README.md` with setup, tools, resources, verification, Inspector, and Codex demo steps.
- [x] Updated `Rubric.md` with current completion status and evidence.

Pending before final submission:

- [ ] Record 2-minute demo video or take screenshots from the UI and Codex if the grader requires visual evidence.
- [ ] Push the final repo to GitHub.

Verified commands:

```powershell
& ".venv\Scripts\python.exe" implementation\init_db.py
& ".venv\Scripts\python.exe" implementation\verify_server.py
& ".venv\Scripts\python.exe" -m pytest -q
& ".venv\Scripts\python.exe" implementation\ui_server.py --host 127.0.0.1 --port 8765
codex mcp list
codex mcp get sqlite-lab
```

## Tóm tắt delivery cần hoàn thành

Hôm nay cần nộp một repo GitHub có MCP server chạy được bằng FastMCP và SQLite. Server phải expose đủ 3 tool `search`, `insert`, `aggregate`, expose schema qua MCP resources, có validate input an toàn, có test/verification lặp lại được, có hướng dẫn setup/demo trong README, và có ít nhất một MCP client kết nối thành công.

Tình trạng hiện tại: implementation đã được tạo và verify bằng `.venv`. Repo hiện có FastMCP server, SQLite database init script, tests, repeatable verification, Codex MCP client config, và `codex_demo_output.txt`. Còn lại việc quay video/chụp screenshot nếu cần và push GitHub repo.

## Checklist công việc

### 1. Scaffold project implementation

- [ ] Tạo thư mục `implementation/`.
- [ ] Tạo các file chính: `implementation/db.py`, `implementation/init_db.py`, `implementation/mcp_server.py`, `implementation/verify_server.py`.
- [ ] Tạo `implementation/tests/test_server.py` nếu dùng pytest.
- [ ] Tạo file dependency nếu cần, ví dụ `requirements.txt` hoặc ghi rõ lệnh cài trong README.
- [ ] Kiểm tra môi trường Python trong `.venv` và cài package cần thiết: `fastmcp`, `pytest` nếu thiếu.

### 2. SQLite database và seed data

- [ ] Implement `init_db.py` để tạo database reproducible.
- [ ] Thiết kế schema tối thiểu gồm `students`, `courses`, `enrollments`.
- [ ] Seed data đủ để demo search, insert, aggregate, group by.
- [ ] Đảm bảo chạy lại init không làm DB bị lỗi hoặc dữ liệu bị nhân đôi ngoài ý muốn.
- [ ] Ghi lại đường dẫn database và lệnh init trong README.

### 3. Database adapter và validation

- [ ] Implement `SQLiteAdapter` trong `db.py`.
- [ ] Hỗ trợ list tables và inspect schema bằng SQLite metadata.
- [ ] Validate table name trước khi query.
- [ ] Validate column name cho selected columns, filters, order by, group by, insert values.
- [ ] Hỗ trợ filter operators an toàn, ví dụ `eq`, `ne`, `gt`, `gte`, `lt`, `lte`, `like`, `in`.
- [ ] Dùng parameterized SQL cho values và filters.
- [ ] Trả lỗi rõ ràng cho unknown table, unknown column, unsupported operator, empty insert, aggregate invalid.

### 4. MCP server tools

- [ ] Implement FastMCP server trong `mcp_server.py`.
- [ ] Tool `search`: hỗ trợ filters, columns, limit, offset, order_by, descending.
- [ ] Tool `insert`: insert record, commit transaction, trả payload vừa insert và id nếu có.
- [ ] Tool `aggregate`: hỗ trợ `count`, `avg`, `sum`, `min`, `max`, có filters và optional group_by.
- [ ] Đảm bảo response dạng structured JSON dễ đọc.
- [ ] Test server start bằng stdio mặc định.

### 5. MCP resources

- [ ] Expose full schema resource: `schema://database`.
- [ ] Expose per-table schema template: `schema://table/{table_name}`.
- [ ] Đảm bảo resource trả JSON text có table, columns, type, primary key/nullability nếu có.
- [ ] Kiểm tra resource invalid table trả lỗi rõ.

### 6. Verification tự động và manual

- [ ] Viết `verify_server.py` hoặc pytest để kiểm tra flow chính.
- [ ] Verify server starts correctly.
- [ ] Verify discover được 3 tools: `search`, `insert`, `aggregate`.
- [ ] Verify discover/read được schema resource.
- [ ] Verify valid calls:
  - [ ] Search students trong cohort `A1`.
  - [ ] Insert một student mới.
  - [ ] Count rows trong một table.
  - [ ] Average score theo cohort hoặc theo course.
- [ ] Verify invalid calls:
  - [ ] Search table không tồn tại.
  - [ ] Filter column không tồn tại.
  - [ ] Unsupported operator.
  - [ ] Empty insert.
  - [ ] Invalid aggregate request.
- [ ] Lưu command verify vào README.

### 7. MCP Inspector hoặc helper command

- [ ] Chuẩn bị command chạy MCP Inspector bằng absolute path.
- [ ] Nếu tiện, thêm helper script `implementation/start_inspector.ps1` hoặc ghi command trong README.
- [ ] Chụp screenshot tool list, resource list, valid call, invalid call nếu dùng screenshot thay video phụ.

### 8. Client integration

- [ ] Chọn ít nhất một client để demo: Gemini CLI, Claude Code, hoặc Codex.
- [ ] Tạo ví dụ config bằng absolute path thật trên máy local.
- [ ] Verify client thấy server ở trạng thái connected.
- [ ] Chạy ít nhất một prompt dùng MCP server, ví dụ search top students hoặc đọc schema.
- [ ] Ghi lại command/config và kết quả mong đợi trong README.

### 9. README và demo deliverables

- [ ] Cập nhật README với setup instructions từ clone repo đến chạy server.
- [ ] Mô tả tools: input, output, ví dụ gọi, lỗi thường gặp.
- [ ] Mô tả resources: `schema://database`, `schema://table/{table_name}`.
- [ ] Thêm testing steps: init DB, run tests/verify script, Inspector/client demo.
- [ ] Thêm client configuration example.
- [ ] Chuẩn bị demo video khoảng 2 phút hoặc screenshots:
  - [ ] 0:00-0:20: repo + setup nhanh.
  - [ ] 0:20-0:45: server/tools/resources discoverable.
  - [ ] 0:45-1:25: demo `search`, `insert`, `aggregate`.
  - [ ] 1:25-1:45: demo invalid request trả lỗi rõ.
  - [ ] 1:45-2:00: MCP client kết nối và gọi server.

### 10. Final check trước khi nộp

- [ ] Chạy lại init database từ đầu.
- [ ] Chạy lại tests hoặc verify script.
- [ ] Chạy thử server manual.
- [ ] Kiểm tra README không còn path placeholder quan trọng.
- [ ] Kiểm tra Git status, commit các file cần nộp.
- [ ] Push GitHub repo.
- [ ] Đảm bảo link repo, video/screenshot, và hướng dẫn demo đều sẵn sàng.

## Ưu tiên nếu thiếu thời gian

- [ ] P0: FastMCP server start được, DB init được, đủ 3 tools chạy được.
- [ ] P0: Schema resources đọc được.
- [ ] P0: Validate lỗi cơ bản và SQL parameterized.
- [ ] P0: README có setup/test/client demo tối thiểu.
- [ ] P1: Automated tests hoặc `verify_server.py` bao phủ valid/invalid cases.
- [ ] P1: Inspector screenshots hoặc demo video rõ ràng.
- [ ] P2: Bonus auth, PostgreSQL adapter, pagination polish.

## Definition of Done

- [ ] `python implementation/init_db.py` tạo được SQLite database.
- [ ] `python implementation/mcp_server.py` start server không lỗi.
- [ ] MCP Inspector hoặc client discover được `search`, `insert`, `aggregate`.
- [ ] `schema://database` và `schema://table/students` đọc được.
- [ ] Valid calls trả kết quả hữu ích; invalid calls trả lỗi rõ.
- [ ] README đủ để người chấm clone repo và chạy lại toàn bộ demo.
