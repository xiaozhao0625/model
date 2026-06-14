param(
    [Parameter(Mandatory = $true)][ValidateSet('M0','W1','W2','W3')][string]$Role,
    [ValidateSet('Plan','Execute')][string]$Mode = 'Plan',
    [string[]]$AllowTools = @()
)

$ErrorActionPreference = 'Continue'
$RepoRoot = (Resolve-Path "$PSScriptRoot\..\..").Path
. "$PSScriptRoot\lib\Write-DeployLog.ps1"
. "$PSScriptRoot\lib\Install-Tool.ps1"

$outDir = Join-Path $RepoRoot "logs/p13/$Role"
$logPath = Join-Path $outDir 'install.log'
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
Write-DeployLog -LogPath $logPath -Role $Role -Action 'install' -Message "Starting install in $Mode mode."

if ($Mode -eq 'Execute' -and @($AllowTools).Count -eq 0) {
    $blocked = [ordered]@{
        role = $Role
        mode = $Mode
        status = 'blocked'
        message = 'Execute mode requires -AllowTools whitelist.'
        allowed_tools = @()
    }
    Save-SafeJson -InputObject $blocked -Path (Join-Path $outDir 'install_result.json')
    Write-DeployLog -LogPath $logPath -Role $Role -Action 'install' -Level 'ERROR' -Message 'Execute blocked because AllowTools is empty.'
    $blocked | ConvertTo-SafeJson
    exit 2
}

$matrix = Get-Content -LiteralPath (Join-Path $RepoRoot 'deploy/role_matrix.json') -Raw | ConvertFrom-Json
$roleConfig = $matrix.roles.$Role
$catalog = Get-Content -LiteralPath (Join-Path $RepoRoot 'deploy/software_catalog.json') -Raw | ConvertFrom-Json
$roleTools = @($roleConfig.required_tools + $roleConfig.optional_tools)
$plan = @()
foreach ($item in $catalog) {
    if ($roleTools -contains $item.name) {
        $item.required = @($roleConfig.required_tools) -contains $item.name
        $detection = Test-Tool -CatalogItem $item -Role $Role
        $plan += Get-InstallStep -CatalogItem $item -Role $Role -DetectionReport $detection
    }
}

$planPayload = [ordered]@{
    role = $Role
    mode = $Mode
    generated_at = (Get-Date).ToUniversalTime().ToString('o')
    execute_required_for_install = $true
    downloads_large_models = $false
    installs_real_ocr = $false
    allowed_tools = @($AllowTools)
    steps = $plan
}
Save-SafeJson -InputObject $planPayload -Path (Join-Path $outDir 'install_plan.json')

$results = @()
foreach ($step in $plan) {
    if ($Mode -eq 'Execute' -and (@($AllowTools) -notcontains $step.name)) {
        $result = [pscustomobject]@{
            name = $step.name
            action = $step.action
            status = 'skipped'
            message = 'Skipped because tool is not in AllowTools whitelist.'
            next_action = 'No action.'
        }
    } else {
        $result = Invoke-InstallStep -Step $step -Mode $Mode
    }
    $results += $result
    Write-DeployLog -LogPath $logPath -Role $Role -Action 'install' -Message "Install step $($step.name): $($result.status)" -Data $result
}
$resultPayload = [ordered]@{
    role = $Role
    mode = $Mode
    status = $(if (@($results | Where-Object { $_.status -eq 'failed' }).Count -gt 0) { 'needs_attention' } else { 'completed' })
    steps = $results
}
Save-SafeJson -InputObject $resultPayload -Path (Join-Path $outDir 'install_result.json')
Set-Content -LiteralPath (Join-Path $outDir 'install_summary.md') -Encoding UTF8 -Value @(
    "# P13.3 install summary - $Role",
    '',
    "- Mode: $Mode",
    "- Planned steps: $($plan.Count)",
    "- Failed steps: $(@($results | Where-Object { $_.status -eq 'failed' }).Count)",
    "- Manual steps: $(@($results | Where-Object { $_.status -eq 'manual_install_required' }).Count)",
    "- Plan mode performs no installation."
)
$resultPayload | ConvertTo-SafeJson
