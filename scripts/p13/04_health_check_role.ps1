param(
    [Parameter(Mandatory = $true)][ValidateSet('M0','W1','W2','W3')][string]$Role
)

$ErrorActionPreference = 'Continue'
$RepoRoot = (Resolve-Path "$PSScriptRoot\..\..").Path
. "$PSScriptRoot\lib\Write-DeployLog.ps1"
. "$PSScriptRoot\lib\Test-Service.ps1"
. "$PSScriptRoot\lib\Test-Network.ps1"
. "$PSScriptRoot\lib\Detect-Tool.ps1"

$outDir = Join-Path $RepoRoot "logs/p13/$Role"
$logPath = Join-Path $outDir 'health.log'
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
Write-DeployLog -LogPath $logPath -Role $Role -Action 'health_check' -Message 'Starting role health check.'

$matrix = Get-Content -LiteralPath (Join-Path $RepoRoot 'deploy/role_matrix.json') -Raw | ConvertFrom-Json
$roleConfig = $matrix.roles.$Role
$catalog = Get-Content -LiteralPath (Join-Path $RepoRoot 'deploy/software_catalog.json') -Raw | ConvertFrom-Json
$checks = @()

foreach ($p in $roleConfig.ports) {
    $checks += Test-RolePort -HostName '127.0.0.1' -Port ([int]$p.port) -Name $p.name
}
$checks += Test-HttpEndpoint -Url (($roleConfig.master_api_url.TrimEnd('/')) + '/health') -TimeoutSeconds 2
if ($Role -eq 'M0') {
    $checks += Test-ProcessPresent -Name 'python'
    $checks += Test-ProcessPresent -Name 'node'
} else {
    $checks += [pscustomobject]@{ name = 'worker_registration'; status = 'worker_not_registered'; message = 'Registration requires a running Master API and worker runtime.'; next_action = 'Start worker runtime and verify registration via Master API.' }
}

$roleTools = @($roleConfig.required_tools)
foreach ($item in $catalog) {
    if ($roleTools -contains $item.name) {
        $tool = Test-Tool -CatalogItem $item -Role $Role
        $checks += [pscustomobject]@{
            name = "tool:$($tool.name)"
            status = $(if ($tool.status -eq 'available') { 'ok' } else { $tool.status })
            message = "tool status: $($tool.status)"
            next_action = $(if ($tool.status -eq 'available') { $null } else { $tool.install_hint })
        }
    }
}

$failures = @($checks | Where-Object { $_.status -notin @('ok','available') })
$payload = [ordered]@{
    role = $Role
    status = $(if ($failures.Count -eq 0) { 'healthy' } else { 'needs_attention' })
    checks = $checks
    failures = $failures
}
Save-SafeJson -InputObject $payload -Path (Join-Path $outDir 'health_result.json')
Set-Content -LiteralPath (Join-Path $outDir 'health_summary.md') -Encoding UTF8 -Value @(
    "# P13.3 health summary - $Role",
    '',
    "- Status: $($payload.status)",
    "- Checks: $($checks.Count)",
    "- Failures: $($failures.Count)",
    "- remote_unreachable, port_unreachable, and worker_not_registered are report states, not script crashes."
)
Write-DeployLog -LogPath $logPath -Role $Role -Action 'health_check' -Message 'Health check completed.' -Data @{ failures = $failures.Count }
$payload | ConvertTo-SafeJson
