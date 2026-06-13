param(
    [Parameter(Mandatory = $true)][ValidateSet('M0','W1','W2','W3')][string]$Role
)

$ErrorActionPreference = 'Continue'
$RepoRoot = (Resolve-Path "$PSScriptRoot\..\..").Path
. "$PSScriptRoot\lib\Write-DeployLog.ps1"

$outDir = Join-Path $RepoRoot "logs/p13/$Role"
$logPath = Join-Path $outDir 'collect_logs.log'
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
Write-DeployLog -LogPath $logPath -Role $Role -Action 'collect_logs' -Message 'Starting diagnostics collection.'

$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$zipPath = Join-Path $outDir "diagnostics_${Role}_${timestamp}.zip"
$stage = Join-Path $outDir "_diagnostics_${timestamp}"
New-Item -ItemType Directory -Force -Path $stage | Out-Null

$deny = '(?i)(^\.env$|\.env\.|password|passwd|secret|token|api[_-]?key|credentials|\.png$|\.jpg$|\.jpeg$|\.webp$|\.mp4$|\.zip$|models|installer|node_modules|\.venv|venv|__pycache__|pytest_cache)'
$included = @()
Get-ChildItem -LiteralPath $outDir -File -ErrorAction SilentlyContinue | ForEach-Object {
    if ($_.Name -notmatch $deny) {
        Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $stage $_.Name) -Force
        $included += $_.Name
    }
}

Set-Content -LiteralPath (Join-Path $stage 'error_report.md') -Encoding UTF8 -Value "# Error report - $Role`n`nReview JSON files for failed items and next_action fields."
Compress-Archive -LiteralPath (Join-Path $stage '*') -DestinationPath $zipPath -Force
Remove-Item -LiteralPath $stage -Recurse -Force

$payload = [ordered]@{
    role = $Role
    status = 'completed'
    zip_path = $zipPath
    included_files = $included
    excluded_sensitive_inputs = $true
}
Save-SafeJson -InputObject $payload -Path (Join-Path $outDir 'collect_logs_result.json')
Set-Content -LiteralPath (Join-Path $outDir 'collect_logs_summary.md') -Encoding UTF8 -Value @(
    "# P13.3 collect logs summary - $Role",
    '',
    "- Zip: $zipPath",
    "- Included files: $($included.Count)",
    "- .env, credentials, screenshots, installers, model files, and prior zip bundles are excluded."
)
Write-DeployLog -LogPath $logPath -Role $Role -Action 'collect_logs' -Message 'Diagnostics collection completed.' -Data $payload
$payload | ConvertTo-SafeJson
