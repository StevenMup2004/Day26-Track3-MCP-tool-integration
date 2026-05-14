$ErrorActionPreference = "Stop"

$ImplementationDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ImplementationDir
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$Server = Join-Path $ImplementationDir "ui_server.py"

& $Python $Server --host 127.0.0.1 --port 8765
