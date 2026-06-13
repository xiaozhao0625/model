param(
    [Parameter(Mandatory = $true)][ValidateSet('Inventory','PlanInstall','Install','StartServices','HealthCheck','CollectLogs','FullDryRun')][string]$Action,
    [ValidateSet('M0','W1','W2','W3')][string]$Role
)

$ErrorActionPreference = 'Continue'
$RepoRoot = (Resolve-Path "$PSScriptRoot\..\..").Path
. "$PSScriptRoot\lib\Write-DeployLog.ps1"
. "$PSScriptRoot\lib\Test-Network.ps1"

$outDir = Join-Path $RepoRoot 'deploy_output'
$logPath = Join-Path $outDir 'orchestrator.log'
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$matrix = Get-Content -LiteralPath (Join-Path $RepoRoot 'deploy/role_matrix.json') -Raw | ConvertFrom-Json
$targetRoles = if ($Role) { @($Role) } else { @('M0','W1','W2','W3') }

function Invoke-LocalP13Script {
    param([string]$ScriptName, [string[]]$Args)
    $scriptPath = Join-Path $PSScriptRoot $ScriptName
    $output = & powershell -NoProfile -ExecutionPolicy Bypass -File $scriptPath @Args 2>&1
    return [pscustomobject]@{
        exit_code = $LASTEXITCODE
        output = (($output | Out-String).Trim())
    }
}

function Invoke-RemoteP13Script {
    param([string]$TargetRole, [string]$ScriptName, [string[]]$Args)
    $roleConfig = $matrix.roles.$TargetRole
    $sshCheck = Test-TcpPort -HostName $roleConfig.ip -Port 22 -TimeoutSeconds 2
    if ($sshCheck.status -ne 'ok') {
        return [pscustomobject]@{
            role = $TargetRole
            status = 'remote_unreachable'
            message = $sshCheck.message
            next_action = 'Enable OpenSSH Server on the worker, verify LAN/firewall, then rerun.'
        }
    }
    $remoteScript = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts/p13/$ScriptName $($Args -join ' ')"
    try {
        $output = & ssh $roleConfig.ip $remoteScript 2>&1
        return [pscustomobject]@{
            role = $TargetRole
            status = $(if ($LASTEXITCODE -eq 0) { 'completed' } else { 'failed' })
            exit_code = $LASTEXITCODE
            output = (($output | Out-String).Trim())
            next_action = $(if ($LASTEXITCODE -eq 0) { $null } else { 'Review remote script output.' })
        }
    } catch {
        return [pscustomobject]@{
            role = $TargetRole
            status = 'remote_unreachable'
            message = $_.Exception.Message
            next_action = 'Verify SSH authentication and remote project path.'
        }
    }
}

function Invoke-RoleAction {
    param([string]$TargetRole, [string]$TargetAction)
    $script = $null
    $args = @()
    switch ($TargetAction) {
        'Inventory' { $script = '01_inventory_local.ps1'; $args = @('-Role', $TargetRole) }
        'PlanInstall' { $script = '02_install_role.ps1'; $args = @('-Role', $TargetRole, '-Mode', 'Plan') }
        'Install' { $script = '02_install_role.ps1'; $args = @('-Role', $TargetRole, '-Mode', 'Execute') }
        'StartServices' { $script = '03_start_role_services.ps1'; $args = @('-Role', $TargetRole) }
        'HealthCheck' { $script = '04_health_check_role.ps1'; $args = @('-Role', $TargetRole) }
        'CollectLogs' { $script = '05_collect_logs.ps1'; $args = @('-Role', $TargetRole) }
    }
    Write-DeployLog -LogPath $logPath -Role $TargetRole -Action $TargetAction -Message "Dispatching $script."
    if ($TargetRole -eq 'M0') {
        $result = Invoke-LocalP13Script -ScriptName $script -Args $args
        return [pscustomobject]@{
            role = $TargetRole
            action = $TargetAction
            status = $(if ($result.exit_code -eq 0 -or $null -eq $result.exit_code) { 'completed' } else { 'failed' })
            exit_code = $result.exit_code
            output = $result.output
            next_action = $(if ($result.exit_code -eq 0 -or $null -eq $result.exit_code) { $null } else { 'Review local script output.' })
        }
    }
    return Invoke-RemoteP13Script -TargetRole $TargetRole -ScriptName $script -Args $args
}

$actions = if ($Action -eq 'FullDryRun') { @('Inventory','PlanInstall','HealthCheck') } else { @($Action) }
$results = @()
foreach ($a in $actions) {
    foreach ($r in $targetRoles) {
        $results += Invoke-RoleAction -TargetRole $r -TargetAction $a
    }
}

$summaryRows = @()
foreach ($r in @('M0','W1','W2','W3')) {
    $roleResults = @($results | Where-Object { $_.role -eq $r })
    $summaryRows += [pscustomobject]@{
        role = $r
        status = $(if ($roleResults.Count -eq 0) { 'not_run' } elseif (@($roleResults | Where-Object { $_.status -in @('failed','remote_unreachable') }).Count -gt 0) { 'needs_attention' } else { 'completed' })
        missing_items = @($roleResults | Where-Object { $_.status -ne 'completed' } | ForEach-Object { $_.status })
        failed_items = @($roleResults | Where-Object { $_.status -eq 'failed' } | ForEach-Object { $_.action })
        next_action = $(if (@($roleResults | Where-Object { $_.status -eq 'remote_unreachable' }).Count -gt 0) { 'Prepare SSH and LAN access from M0.' } else { 'Read per-role logs under logs/p13.' })
    }
}

$report = [ordered]@{
    action = $Action
    generated_at = (Get-Date).ToUniversalTime().ToString('o')
    roles = $summaryRows
    results = $results
    safety = [ordered]@{
        force_push = $false
        reads_env_raw = $false
        installs_large_models = $false
        installs_paddle_or_easyocr = $false
        workers_direct_postgresql = $false
    }
}

Save-SafeJson -InputObject $report -Path (Join-Path $outDir 'overall_deploy_report.json')
$md = @(
    '# P13.3 overall deploy report',
    '',
    "- Action: $Action",
    "- Generated: $($report.generated_at)",
    '',
    '| Role | Status | Missing / failed | Next action |',
    '| --- | --- | --- | --- |'
)
foreach ($row in $summaryRows) {
    $missingText = if ($row.missing_items.Count -gt 0) { ($row.missing_items -join ', ') } else { 'none recorded' }
    $md += "| $($row.role) | $($row.status) | $missingText | $($row.next_action) |"
}
$md += ''
$md += 'Notes: workers W1/W2/W3 must use M0 Master API and must not connect to PostgreSQL directly. P13.3 does not download large models or install PaddleOCR/EasyOCR.'
Set-Content -LiteralPath (Join-Path $outDir 'overall_deploy_report.md') -Encoding UTF8 -Value $md
Write-DeployLog -LogPath $logPath -Role 'M0' -Action $Action -Message 'Orchestrator action completed.' -Data @{ result_count = $results.Count }
$report | ConvertTo-SafeJson
