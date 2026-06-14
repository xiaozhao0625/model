. "$PSScriptRoot\Detect-Tool.ps1"

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
        [ValidateSet('Plan','Execute')][string]$Mode = 'Plan'
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
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if (-not $winget) {
        return [pscustomobject]@{
            name = $Step.name
            action = $Step.action
            status = 'failed'
            message = 'winget_not_available'
            next_action = 'Install or enable winget, then rerun Execute.'
        }
    }
    try {
        $args = @('install', '--id', $Step.winget_id, '--silent', '--accept-package-agreements', '--accept-source-agreements')
        $output = & winget @args 2>&1
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
