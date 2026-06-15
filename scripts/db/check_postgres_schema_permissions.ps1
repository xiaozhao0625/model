param(
  [switch]$Json,
  [switch]$ApplyAdminSql,
  [string]$PsqlPath = "E:\work\pgsql\bin\psql.exe",
  [string]$Database = "ai_screenshot_platform",
  [string]$AdminUser = "postgres"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$python = "E:\work\venvs\ai-screenshot-master\Scripts\python.exe"
$checkScript = Join-Path $PSScriptRoot "check_postgres_schema_permissions.py"
$repairSql = Join-Path $repoRoot "deploy\db_admin_repair_p14_4.sql"

if ($ApplyAdminSql) {
  if (!(Test-Path -LiteralPath $PsqlPath)) {
    throw "psql not found: $PsqlPath"
  }
  if (!(Test-Path -LiteralPath $repairSql)) {
    throw "repair SQL not found: $repairSql"
  }
  Write-Host "Applying controlled PostgreSQL admin repair. psql may prompt for the admin password."
  & $PsqlPath -U $AdminUser -d $Database -f $repairSql
  if ($LASTEXITCODE -ne 0) {
    throw "psql repair failed with exit code $LASTEXITCODE"
  }
}

$env:PYTHONPATH = Join-Path $repoRoot "src"
if ($Json) {
  & $python $checkScript --json
} else {
  & $python $checkScript
}
