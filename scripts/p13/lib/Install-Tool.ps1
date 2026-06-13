. "$PSScriptRoot\Detect-Tool.ps1"

function Get-InstallStep {
    param(
        [Parameter(Mandatory = $true)]$CatalogItem,
        [Parameter(Mandatory = $true)][string]$Role
    )
    $manual = [bool]$CatalogItem.manual_install_note -or -not $CatalogItem.winget_id
    [pscustomobject]@{
        name = $CatalogItem.name
        role = $Role
        required = [bool]$CatalogItem.required
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
    if ($Step.action -eq 'manual_install_required') {
        return [pscustomobject]@{
            name = $Step.name
            action = $Step.action
            status = 'manual_install_required'
            message = 'This item is not automatically installed by P13.3.'
            next_action = $Step.manual_install_note
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
