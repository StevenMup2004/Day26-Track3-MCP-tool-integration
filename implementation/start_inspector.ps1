$ErrorActionPreference = "Stop"

$ImplementationDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ImplementationDir
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$Server = Join-Path $ImplementationDir "mcp_server.py"
$NpmCache = Join-Path $RepoRoot ".npm-cache"

New-Item -ItemType Directory -Force -Path $NpmCache | Out-Null
$env:NPM_CONFIG_CACHE = $NpmCache

npx -y @modelcontextprotocol/inspector $Python $Server
