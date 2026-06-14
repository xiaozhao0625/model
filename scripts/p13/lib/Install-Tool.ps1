. "$PSScriptRoot\Detect-Tool.ps1"

$AllowedStagedTools = @('git', 'python', 'ffmpeg', 'adb')

function Resolve-Winget {
    $attempts = @()
    $cmd = Get-Command winget -ErrorAction SilentlyContinue
    $attempts += [pscustomobject]@{ method = 'Get-Command'; path = $(if ($cmd) { $cmd.Source } else { $null }); status = $(if ($cmd) { 'available' } else { 'missing' }) }
    if ($cmd) {
        return [pscustomobject]@{ status = 'available'; path = $cmd.Source; reason = $null; next_action = $null; attempts = $attempts }
    }

    try {
        $where = & where.exe winget 2>$null | Select-Object -First 1
        $attempts += [pscustomobject]@{ method = 'where.exe'; path = $where; status = $(if ($where) { 'available' } else { 'missing' }) }
        if ($where) {
            return [pscustomobject]@{ status = 'available'; path = $where; reason = $null; next_action = $null; attempts = $attempts }
        }
    } catch {
        $attempts += [pscustomobject]@{ method = 'where.exe'; path = $null; status = 'missing' }
    }

    $localAppDataWinget = Join-Path $env:LOCALAPPDATA 'Microsoft\WindowsApps\winget.exe'
    $attempts += [pscustomobject]@{ method = 'LOCALAPPDATA'; path = $localAppDataWinget; status = $(if (Test-Path -LiteralPath $localAppDataWinget) { 'available' } else { 'missing' }) }
    if (Test-Path -LiteralPath $localAppDataWinget) {
        return [pscustomobject]@{ status = 'available'; path = $localAppDataWinget; reason = $null; next_action = $null; attempts = $attempts }
    }

    $userWinget = "C:\Users\$env:USERNAME\AppData\Local\Microsoft\WindowsApps\winget.exe"
    $attempts += [pscustomobject]@{ method = 'user_profile'; path = $userWinget; status = $(if (Test-Path -LiteralPath $userWinget) { 'available' } else { 'missing' }) }
    if (Test-Path -LiteralPath $userWinget) {
        return [pscustomobject]@{ status = 'available'; path = $userWinget; reason = $null; next_action = $null; attempts = $attempts }
    }

    $appInstaller = Get-AppxPackage Microsoft.DesktopAppInstaller -ErrorAction SilentlyContinue
    $attempts += [pscustomobject]@{ method = 'Get-AppxPackage Microsoft.DesktopAppInstaller'; path = $appInstaller.InstallLocation; status = $(if ($appInstaller) { 'package_present' } else { 'missing' }) }
    $reason = if (-not $appInstaller) { 'app_installer_missing' } else { 'non_interactive_session_unavailable' }
    [pscustomobject]@{
        status = 'winget_not_available'
        path = $null
        reason = $reason
        next_action = 'use staged installer backend or manual install'
        attempts = $attempts
    }
}

function Get-StagedInstallerManifest {
    param([Parameter(Mandatory = $true)][string]$RepoRoot)
    $manifestPath = Join-Path $RepoRoot 'deploy\installers\manifest.json'
    if (-not (Test-Path -LiteralPath $manifestPath)) {
        return [pscustomobject]@{ status = 'manifest_missing'; path = $manifestPath; manifest = $null }
    }
    try {
        return [pscustomobject]@{ status = 'available'; path = $manifestPath; manifest = (Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json) }
    } catch {
        return [pscustomobject]@{ status = 'manifest_invalid'; path = $manifestPath; manifest = $null; message = $_.Exception.Message }
    }
}

function Invoke-StagedInstallStep {
    param(
        [Parameter(Mandatory = $true)]$Step,
        [Parameter(Mandatory = $true)][string]$Role,
        [Parameter(Mandatory = $true)][string]$RepoRoot
    )
    if ($AllowedStagedTools -notcontains $Step.name) {
        return [pscustomobject]@{ name = $Step.name; action = 'staged_install'; status = 'blocked'; message = 'Tool is not allowed for staged installer backend.'; next_action = 'Use manual process or a later phase.' }
    }
    $manifestResult = Get-StagedInstallerManifest -RepoRoot $RepoRoot
    if ($manifestResult.status -ne 'available') {
        return [pscustomobject]@{ name = $Step.name; action = 'staged_install'; status = 'installer_missing'; reason = $manifestResult.status; message = $manifestResult.path; next_action = 'Create deploy/installers/manifest.json from manifest.example.json.' }
    }
    $entry = $manifestResult.manifest.$($Step.name)
    if (-not $entry) {
        return [pscustomobject]@{ name = $Step.name; action = 'staged_install'; status = 'installer_not_declared'; message = 'Tool is not declared in staged installer manifest.'; next_action = 'Add a manifest entry before using staged install.' }
    }
    if (@($entry.allowed_roles) -notcontains $Role) {
        return [pscustomobject]@{ name = $Step.name; action = 'staged_install'; status = 'blocked'; message = 'Role is not allowed for this staged installer.'; next_action = 'Review manifest allowed_roles.' }
    }
    if (-not $entry.sha256 -or $entry.sha256 -match 'fill_exact_sha256|placeholder') {
        return [pscustomobject]@{ name = $Step.name; action = 'staged_install'; status = 'sha256_missing'; message = 'Manifest sha256 is missing or placeholder.'; next_action = 'Fill exact SHA256 before staged install.' }
    }
    $installerPath = Join-Path (Join-Path $RepoRoot 'deploy\installers') $entry.installer_filename
    if (-not (Test-Path -LiteralPath $installerPath)) {
        return [pscustomobject]@{ name = $Step.name; action = 'staged_install'; status = 'installer_missing'; message = $installerPath; next_action = 'Place the installer on M0; do not download from script.' }
    }
    $actualHash = (Get-FileHash -LiteralPath $installerPath -Algorithm SHA256).Hash.ToLowerInvariant()
    $expectedHash = ([string]$entry.sha256).ToLowerInvariant()
    if ($actualHash -ne $expectedHash) {
        return [pscustomobject]@{ name = $Step.name; action = 'staged_install'; status = 'sha256_mismatch'; message = 'Installer SHA256 did not match manifest.'; next_action = 'Replace installer or manifest hash.' }
    }
    try {
        $args = @($entry.silent_args)
        $process = Start-Process -FilePath $installerPath -ArgumentList $args -Wait -PassThru -WindowStyle Hidden
        $post = Test-Tool -CatalogItem @{ name = $Step.name; required = $true; detect_commands = @("$($entry.post_check -join ' ')") } -Role $Role
        return [pscustomobject]@{ name = $Step.name; action = 'staged_install'; status = $(if ($process.ExitCode -eq 0) { 'installed_or_already_present' } else { 'failed' }); exit_code = $process.ExitCode; post_check = $post; next_action = 'Rerun inventory.' }
    } catch {
        return [pscustomobject]@{ name = $Step.name; action = 'staged_install'; status = 'failed'; message = $_.Exception.Message; next_action = 'Review staged installer failure.' }
    }
}

function Get-InstallStep {
    param(
        [Parameter(Mandatory = $true)]$CatalogItem,
        [Parameter(Mandatory = $true)][string]$Role,
        $DetectionReport = $null
    )
    if ($DetectionReport -and $DetectionReport.status -eq 'available') {
        return [pscustomobject]@{
            name = $CatalogItem.name
            role = $Role
            required = [bool]$CatalogItem.required
            current_status = $DetectionReport.status
            detected_path = $DetectionReport.path
            detected_version = $DetectionReport.version
            winget_id = $CatalogItem.winget_id
            action = 'already_available'
            install_hint = $CatalogItem.install_hint
            manual_install_note = $CatalogItem.manual_install_note
        }
    }
    if ($DetectionReport -and $DetectionReport.status -eq 'partial') {
        return [pscustomobject]@{
            name = $CatalogItem.name
            role = $Role
            required = [bool]$CatalogItem.required
            current_status = $DetectionReport.status
            detected_path = $DetectionReport.path
            detected_version = $DetectionReport.version
            winget_id = $CatalogItem.winget_id
            action = 'manual_configuration_required'
            install_hint = $DetectionReport.next_action
            manual_install_note = $DetectionReport.message
        }
    }
    if ($CatalogItem.install_policy -eq 'detect_only') {
        return [pscustomobject]@{
            name = $CatalogItem.name
            role = $Role
            required = [bool]$CatalogItem.required
            current_status = $(if ($DetectionReport) { $DetectionReport.status } else { 'not_checked' })
            detected_path = $(if ($DetectionReport) { $DetectionReport.path } else { $null })
            detected_version = $(if ($DetectionReport) { $DetectionReport.version } else { $null })
            winget_id = $CatalogItem.winget_id
            action = 'blocked'
            install_hint = 'Detect-only in this phase; do not install automatically.'
            manual_install_note = 'Browser installation is blocked for P13.4.2 safe install.'
        }
    }
    $manual = [bool]$CatalogItem.manual_install_note -or -not $CatalogItem.winget_id
    [pscustomobject]@{
        name = $CatalogItem.name
        role = $Role
        required = [bool]$CatalogItem.required
        current_status = $(if ($DetectionReport) { $DetectionReport.status } else { 'not_checked' })
        detected_path = $(if ($DetectionReport) { $DetectionReport.path } else { $null })
        detected_version = $(if ($DetectionReport) { $DetectionReport.version } else { $null })
        winget_id = $CatalogItem.winget_id
        action = $(if ($manual) { 'manual_install_required' } else { 'winget_install' })
        install_hint = $CatalogItem.install_hint
        manual_install_note = $CatalogItem.manual_install_note
    }
}

function Invoke-InstallStep {
    param(
        [Parameter(Mandatory = $true)]$Step,
        [ValidateSet('Plan','Execute')][string]$Mode = 'Plan',
        [ValidateSet('winget','staged','auto')][string]$InstallBackend = 'winget',
        [string]$Role = '',
        [string]$RepoRoot = ''
    )
    if ($Mode -eq 'Plan') {
        return [pscustomobject]@{
            name = $Step.name
            action = $Step.action
            status = 'planned'
            message = 'Plan mode only; no installation executed.'
            next_action = $Step.install_hint
        }
    }
    if ($Step.action -eq 'already_available') {
        return [pscustomobject]@{
            name = $Step.name
            action = $Step.action
            status = 'already_available'
            message = 'Tool is already detected; no installation executed.'
            next_action = 'No action required.'
        }
    }
    if ($Step.action -eq 'manual_configuration_required') {
        return [pscustomobject]@{
            name = $Step.name
            action = $Step.action
            status = 'manual_configuration_required'
            message = $Step.manual_install_note
            next_action = $Step.install_hint
        }
    }
    if ($Step.action -eq 'manual_install_required') {
        return [pscustomobject]@{
            name = $Step.name
            action = $Step.action
            status = 'manual_install_required'
            message = 'This item is not automatically installed by P13.3.'
            next_action = $Step.manual_install_note
        }
    }
    if ($Step.action -eq 'blocked') {
        return [pscustomobject]@{
            name = $Step.name
            action = $Step.action
            status = 'blocked'
            message = 'Installation blocked by policy.'
            next_action = $Step.install_hint
        }
    }
    if ($InstallBackend -eq 'staged') {
        return Invoke-StagedInstallStep -Step $Step -Role $Role -RepoRoot $RepoRoot
    }
    $winget = Resolve-Winget
    if ($winget.status -ne 'available') {
        if ($InstallBackend -eq 'auto') {
            $stagedResult = Invoke-StagedInstallStep -Step $Step -Role $Role -RepoRoot $RepoRoot
            $stagedResult | Add-Member -NotePropertyName winget -NotePropertyValue $winget -Force
            return $stagedResult
        }
        return [pscustomobject]@{
            name = $Step.name
            action = $Step.action
            status = 'winget_not_available'
            reason = $winget.reason
            message = 'winget_not_available'
            next_action = $winget.next_action
            winget = $winget
        }
    }
    try {
        $args = @('install', '--id', $Step.winget_id, '--silent', '--accept-package-agreements', '--accept-source-agreements')
        $output = & $winget.path @args 2>&1
        return [pscustomobject]@{
            name = $Step.name
            action = $Step.action
            status = $(if ($LASTEXITCODE -eq 0) { 'installed_or_already_present' } else { 'failed' })
            message = (($output | Out-String).Trim())
            next_action = $(if ($LASTEXITCODE -eq 0) { 'Rerun inventory.' } else { 'Review winget output and install manually if needed.' })
        }
    } catch {
        return [pscustomobject]@{
            name = $Step.name
            action = $Step.action
            status = 'failed'
            message = $_.Exception.Message
            next_action = 'Review installer failure and retry.'
        }
    }
}
