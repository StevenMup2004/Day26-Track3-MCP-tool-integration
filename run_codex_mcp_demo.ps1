$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$McpServer = Join-Path $RepoRoot "implementation\mcp_server.py"
$OutputFile = Join-Path $RepoRoot "codex_demo_output.txt"
$RunLog = Join-Path $RepoRoot "codex_demo_run.log"

$Codex = Get-Command codex -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty Source

if (-not $Codex) {
    $Codex = Get-ChildItem "$env:USERPROFILE\.vscode\extensions" -Recurse -Filter codex.exe -ErrorAction SilentlyContinue |
        Sort-Object FullName -Descending |
        Select-Object -First 1 -ExpandProperty FullName
}

if (-not $Codex) {
    throw "Could not find codex.exe. Install/open the OpenAI ChatGPT VS Code extension or add Codex CLI to PATH."
}

Write-Host "Using Codex CLI:" $Codex
Write-Host ""

$existing = & $Codex mcp get sqlite-lab 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Adding sqlite-lab MCP server..."
    & $Codex mcp add sqlite-lab -- $Python $McpServer
}

Write-Host "Configured MCP servers:"
& $Codex mcp list
Write-Host ""

Write-Host "sqlite-lab details:"
& $Codex mcp get sqlite-lab
Write-Host ""

Write-Host "Running Codex MCP smoke demo..."
$Prompt = "Do not modify files. Do not use shell commands. Only use the sqlite-lab MCP server. Read schema://database and call the aggregate MCP tool with table students, metric count, column id. Answer with the table names and student count only."

$StartInfo = [System.Diagnostics.ProcessStartInfo]::new()
$StartInfo.FileName = $Codex
$StartInfo.WorkingDirectory = $RepoRoot
$StartInfo.UseShellExecute = $false
$StartInfo.RedirectStandardOutput = $true
$StartInfo.RedirectStandardError = $true

function Format-ProcessArgument {
    param([string] $Value)
    '"' + ($Value -replace '"', '\"') + '"'
}

$ProcessArguments = @(
    "exec",
    "--ephemeral",
    "--output-last-message",
    $OutputFile,
    "--dangerously-bypass-approvals-and-sandbox",
    "-C",
    $RepoRoot,
    $Prompt
)
$StartInfo.Arguments = [string]::Join(" ", ($ProcessArguments | ForEach-Object { Format-ProcessArgument $_ }))

$Process = [System.Diagnostics.Process]::Start($StartInfo)
$StdoutTask = $Process.StandardOutput.ReadToEndAsync()
$StderrTask = $Process.StandardError.ReadToEndAsync()

if (-not $Process.WaitForExit(180000)) {
    try {
        $Process.Kill($true)
    } catch {
        $Process.Kill()
    }
    throw "Codex demo timed out after 180 seconds. See $RunLog"
}

$StdoutTask.Wait()
$StderrTask.Wait()
Set-Content -Path $RunLog -Value ($StdoutTask.Result + "`n" + $StderrTask.Result)

if ($Process.ExitCode -ne 0) {
    throw "Codex demo failed with exit code $($Process.ExitCode). See $RunLog"
}

$DemoOutput = Get-Content $OutputFile -Raw
if ($DemoOutput -notmatch "student count:\s*6") {
    throw "Codex demo did not return the expected student count. See $RunLog"
}

Write-Host ""
Write-Host "Codex run log:" $RunLog
Write-Host "Demo output:"
Write-Host $DemoOutput
