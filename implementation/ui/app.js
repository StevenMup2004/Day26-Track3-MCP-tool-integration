const state = {
  schema: null,
  table: "students",
  rows: [],
  aggregateRows: [],
  mcpMetadata: null,
};

const $ = (id) => document.getElementById(id);

function showToast(message, isError = false) {
  const toast = $("toast");
  toast.textContent = message;
  toast.classList.toggle("error", isError);
  toast.classList.add("show");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => toast.classList.remove("show"), 3200);
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || `Request failed: ${response.status}`);
  }
  return payload;
}

function columnsFor(table) {
  return state.schema?.tables?.[table]?.columns || [];
}

function columnNames(table = state.table) {
  return columnsFor(table).map((column) => column.name);
}

function fillSelect(select, options, selected, includeBlank = false) {
  select.innerHTML = "";
  if (includeBlank) {
    const blank = document.createElement("option");
    blank.value = "";
    blank.textContent = "None";
    select.appendChild(blank);
  }
  options.forEach((option) => {
    const node = document.createElement("option");
    node.value = option;
    node.textContent = option;
    if (option === selected) node.selected = true;
    select.appendChild(node);
  });
}

function renderTable(target, rows) {
  if (!rows.length) {
    target.innerHTML = "<tbody><tr><td>No rows</td></tr></tbody>";
    return;
  }
  const headers = Object.keys(rows[0]);
  target.innerHTML = `
    <thead>
      <tr>${headers.map((header) => `<th>${escapeHtml(header)}</th>`).join("")}</tr>
    </thead>
    <tbody>
      ${rows
        .map(
          (row) => `
            <tr>
              ${headers.map((header) => `<td>${escapeHtml(formatValue(row[header]))}</td>`).join("")}
            </tr>
          `,
        )
        .join("")}
    </tbody>
  `;
}

function renderSchema() {
  const rows = columnsFor(state.table).map((column) => ({
    name: column.name,
    type: column.type,
    required: column.not_null ? "yes" : "no",
    primary_key: column.primary_key ? "yes" : "no",
    default: column.default ?? "",
  }));
  renderTable($("schemaTable"), rows);
  $("schemaLabel").textContent = `${state.table} schema`;
}

function renderBars(rows) {
  const chart = $("barChart");
  if (!rows.length) {
    chart.innerHTML = "<div class=\"empty-state\">No aggregate data</div>";
    return;
  }

  const max = Math.max(...rows.map((row) => Number(row.value) || 0), 1);
  chart.innerHTML = rows
    .map((row, index) => {
      const keys = Object.keys(row).filter((key) => key !== "value");
      const label = keys.length ? keys.map((key) => row[key]).join(" / ") : `Result ${index + 1}`;
      const value = Number(row.value) || 0;
      const width = Math.max(2, (value / max) * 100);
      return `
        <div class="bar-row">
          <div class="bar-label" title="${escapeHtml(label)}">${escapeHtml(label)}</div>
          <div class="bar-track" aria-label="${escapeHtml(label)} ${value}">
            <div class="bar-fill" style="width:${width}%"></div>
          </div>
          <div class="bar-value">${formatValue(roundNumber(value))}</div>
        </div>
      `;
    })
    .join("");
}

function renderInsertForm() {
  const skip = new Set(["id", "created_at", "enrolled_at"]);
  const fields = columnsFor(state.table).filter((column) => !skip.has(column.name));
  $("insertForm").innerHTML = `
    ${fields
      .map(
        (column) => `
          <label>
            ${escapeHtml(column.name)}
            <input name="${escapeHtml(column.name)}" type="${inputType(column.type)}" placeholder="${escapeHtml(column.type)}" />
          </label>
        `,
      )
      .join("")}
    <button class="primary-button" type="submit">Insert Row</button>
  `;
}

function refreshControls() {
  const tables = Object.keys(state.schema.tables);
  fillSelect($("tableSelect"), tables, state.table);

  const names = columnNames();
  fillSelect($("filterColumn"), names, names.includes("cohort") ? "cohort" : names[0]);
  fillSelect($("orderBy"), names, names.includes("score") ? "score" : names[0], true);
  fillSelect($("metricColumn"), names, names.includes("score") ? "score" : names[0], true);
  fillSelect($("groupBy"), names, names.includes("cohort") ? "cohort" : "", true);

  $("activeTable").textContent = state.table;
  $("databaseName").textContent = state.schema.database.split(/[\\/]/).pop();
  renderSchema();
  renderInsertForm();
}

async function loadSchema() {
  state.schema = await api("/api/schema");
  state.table = Object.keys(state.schema.tables).includes(state.table)
    ? state.table
    : Object.keys(state.schema.tables)[0];
  refreshControls();
  $("statusPill").textContent = "Ready";
  $("statusPill").classList.add("ready");
}

function buildFilters() {
  const value = $("filterValue").value.trim();
  if (!value) return null;
  return [
    {
      column: $("filterColumn").value,
      operator: $("filterOperator").value,
      value: coerceInput(value),
    },
  ];
}

async function runSearch() {
  const payload = {
    table: state.table,
    filters: buildFilters(),
    limit: Number($("limitInput").value || 20),
    offset: 0,
    order_by: $("orderBy").value || null,
    descending: $("descending").checked,
  };
  const result = await api("/api/search", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  state.rows = result.rows;
  $("rowCount").textContent = String(result.count);
  $("queryLabel").textContent = payload.filters ? "Filtered search" : "Latest search";
  renderTable($("rowsTable"), result.rows);
}

async function runAggregate() {
  const metric = $("metricSelect").value;
  const payload = {
    table: state.table,
    metric,
    column: metric === "count" ? $("metricColumn").value || null : $("metricColumn").value,
    group_by: $("groupBy").value || null,
  };
  if (metric !== "count" && !payload.column) {
    showToast("Choose a column for this aggregate metric", true);
    return;
  }
  const result = await api("/api/aggregate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  state.aggregateRows = result.rows;
  $("aggregateLabel").textContent = `${metric}${payload.group_by ? ` by ${payload.group_by}` : ""}`;
  renderBars(result.rows);
  renderTable($("aggregateTable"), result.rows);
}

async function insertRow(event) {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const values = {};
  for (const [key, rawValue] of form.entries()) {
    const value = String(rawValue).trim();
    if (value !== "") values[key] = coerceInput(value);
  }
  const result = await api("/api/insert", {
    method: "POST",
    body: JSON.stringify({ table: state.table, values }),
  });
  $("insertResult").textContent = JSON.stringify(result, null, 2);
  showToast("Inserted row");
  await runSearch();
  await runAggregate();
}

async function resetDatabase() {
  await api("/api/reset", { method: "POST", body: "{}" });
  showToast("Seed data restored");
  await loadSchema();
  await runSearch();
  await runAggregate();
}

async function loadMcpMetadata() {
  const metadata = await api("/api/mcp/metadata");
  state.mcpMetadata = metadata;
  renderMcpMetadata(metadata);
  showToast("MCP tools and resources discovered");
}

function renderMcpMetadata(metadata) {
  $("toolList").innerHTML = metadata.tools
    .map((tool) => {
      const schema = tool.inputSchema || tool.input_schema || {};
      const properties = Object.keys(schema.properties || {});
      return `
        <article class="tool-item">
          <div class="tool-title">${escapeHtml(tool.name)}</div>
          <div class="tool-description">${escapeHtml(tool.description || "")}</div>
          <div class="tool-args">${escapeHtml(properties.join(", ") || "no args")}</div>
        </article>
      `;
    })
    .join("");

  const resources = [
    ...(metadata.resources || []).map((resource) => resource.uri),
    ...(metadata.resource_templates || []).map((template) => template.uriTemplate),
  ];
  $("resourceList").innerHTML = resources
    .map((resource) => `<div class="resource-item">${escapeHtml(resource)}</div>`)
    .join("");
}

async function runMcpPrompt() {
  $("runPromptButton").disabled = true;
  $("runPromptButton").textContent = "Running";
  try {
    const result = await api("/api/mcp/prompt", {
      method: "POST",
      body: JSON.stringify({ prompt: $("promptInput").value }),
    });
    $("promptAnswer").textContent = result.answer;
    $("traceLabel").textContent = `${result.trace.length} MCP steps`;
    renderMcpTrace(result.trace);
    showToast("Prompt completed through MCP");
  } finally {
    $("runPromptButton").disabled = false;
    $("runPromptButton").textContent = "Run Prompt";
  }
}

async function runRealCodexPrompt() {
  $("runCodexButton").disabled = true;
  $("runCodexButton").textContent = "Running Codex";
  $("promptAnswer").textContent = "Starting Codex CLI. This can take 30-90 seconds...";
  $("traceLabel").textContent = "waiting for Codex";
  $("mcpTrace").innerHTML = "";
  try {
    const result = await api("/api/codex/prompt", {
      method: "POST",
      body: JSON.stringify({ prompt: $("promptInput").value }),
    });
    $("promptAnswer").textContent = result.answer;
    $("traceLabel").textContent = `${result.trace.length} Codex events`;
    renderMcpTrace(result.trace);
    showToast("Real Codex prompt completed");
  } finally {
    $("runCodexButton").disabled = false;
    $("runCodexButton").textContent = "Run Real Codex";
  }
}

function renderMcpTrace(trace) {
  $("mcpTrace").innerHTML = trace
    .map(
      (step, index) => `
        <article class="trace-item ${step.ok ? "ok" : "failed"}">
          <header>
            <span class="trace-index">${index + 1}</span>
            <strong>${escapeHtml(step.operation)}</strong>
            <span>${escapeHtml(step.step)}</span>
          </header>
          ${step.arguments ? `<pre>${escapeHtml(JSON.stringify(step.arguments, null, 2))}</pre>` : ""}
          <pre>${escapeHtml(JSON.stringify(step.result || { error: step.error }, null, 2))}</pre>
        </article>
      `,
    )
    .join("");
}

function bindEvents() {
  $("tableSelect").addEventListener("change", async (event) => {
    state.table = event.target.value;
    refreshControls();
    await runSearch();
    await runAggregate();
  });

  $("metricSelect").addEventListener("change", () => {
    const isCount = $("metricSelect").value === "count";
    $("metricColumn").disabled = isCount;
  });

  $("searchButton").addEventListener("click", () =>
    runSearch().catch((error) => showToast(error.message, true)),
  );
  $("aggregateButton").addEventListener("click", () =>
    runAggregate().catch((error) => showToast(error.message, true)),
  );
  $("resetButton").addEventListener("click", () =>
    resetDatabase().catch((error) => showToast(error.message, true)),
  );
  $("loadMcpButton").addEventListener("click", () =>
    loadMcpMetadata().catch((error) => showToast(error.message, true)),
  );
  $("runPromptButton").addEventListener("click", () =>
    runMcpPrompt().catch((error) => showToast(error.message, true)),
  );
  $("runCodexButton").addEventListener("click", () =>
    runRealCodexPrompt().catch((error) => showToast(error.message, true)),
  );
  $("insertForm").addEventListener("submit", (event) =>
    insertRow(event).catch((error) => showToast(error.message, true)),
  );

  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((node) => node.classList.remove("active"));
      document.querySelectorAll(".tab-panel").forEach((node) => node.classList.remove("active"));
      tab.classList.add("active");
      $(`${tab.dataset.tab}Tab`).classList.add("active");
    });
  });
}

function inputType(sqlType) {
  const normalized = sqlType.toLowerCase();
  if (normalized.includes("int") || normalized.includes("real")) return "number";
  return "text";
}

function coerceInput(value) {
  if (value === "true") return true;
  if (value === "false") return false;
  if (value !== "" && !Number.isNaN(Number(value))) return Number(value);
  return value;
}

function formatValue(value) {
  if (value === null || value === undefined) return "";
  if (typeof value === "number") return String(roundNumber(value));
  return String(value);
}

function roundNumber(value) {
  return Math.round(value * 100) / 100;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function boot() {
  bindEvents();
  try {
    await loadSchema();
    await loadMcpMetadata();
    $("metricSelect").dispatchEvent(new Event("change"));
    await runSearch();
    await runAggregate();
  } catch (error) {
    $("statusPill").textContent = "Error";
    showToast(error.message, true);
  }
}

boot();
