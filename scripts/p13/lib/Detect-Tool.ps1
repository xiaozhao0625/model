. "$PSScriptRoot\ConvertTo-SafeJson.ps1"

function Get-CommandNameFromDetectCommand {
    param([Parameter(Mandatory = $true)][string]$DetectCommand)
    $trimmed = $DetectCommand.Trim()
    if ($trimmed.StartsWith('Get-Service')) { return 'powershell-service' }
    return ($trimmed -split '\s+')[0].Trim('"')
}

function Get-VersionFromText {
    param([string]$Text)
    if ($Text -match '(\d+)(\.\d+){0,3}') { return $Matches[0] }
    return $null
}

function Compare-MinVersion {
    param([string]$Actual, [string]$Minimum)
    if (-not $Minimum -or -not $Actual) { return $true }
    try {
        return ([version]$Actual) -ge ([version]$Minimum)
    } catch {
        return $true
    }
}

function Invoke-DetectCommand {
    param([Parameter(Mandatory = $true)][string]$DetectCommand)
    if ($DetectCommand.Trim().StartsWith('Get-Service')) {
        $serviceName = ($DetectCommand -split '\s+')[-1]
        $service = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
        if ($service) {
            return [ordered]@{ ok = $true; output = "$($service.Name) $($service.Status)"; path = $null }
        }
        return [ordered]@{ ok = $false; output = 'service_not_found'; path = $null }
    }
    $commandName = Get-CommandNameFromDetectCommand $DetectCommand
    $cmd = Get-Command -Name $commandName -ErrorAction SilentlyContinue
    if (-not $cmd) { return [ordered]@{ ok = $false; output = 'command_not_found'; path = $null } }
    try {
        $output = & powershell -NoProfile -ExecutionPolicy Bypass -Command $DetectCommand 2>&1 | Select-Object -First 5
        return [ordered]@{ ok = $true; output = (($output | Out-String).Trim()); path = $cmd.Source }
    } catch {
        return [ordered]@{ ok = $false; output = $_.Exception.Message; path = $cmd.Source }
    }
}

function Test-Tool {
    param(
        [Parameter(Mandatory = $true)]$CatalogItem,
        [Parameter(Mandatory = $true)][string]$Role
    )
    $required = [bool]$CatalogItem.required
    $attempts = @()
    $available = $false
    $path = $null
    $version = $null
    foreach ($detectCommand in $CatalogItem.detect_commands) {
        $result = Invoke-DetectCommand -DetectCommand $detectCommand
        $attempts += [pscustomobject]@{
            command = $detectCommand
            ok = $result.ok
            output = $result.output
            path = $result.path
        }
        if ($result.ok) {
            $available = $true
            $path = $result.path
            $version = Get-VersionFromText $result.output
            break
        }
    }
    $versionOk = Compare-MinVersion -Actual $version -Minimum $CatalogItem.min_version
    $status = 'available'
    if (-not $available) { $status = 'missing' }
    elseif (-not $versionOk) { $status = 'version_mismatch' }
    [pscustomobject]@{
        name = $CatalogItem.name
        role = $Role
        required = $required
        status = $status
        version = $version
        min_version = $CatalogItem.min_version
        path = $path
        winget_id = $CatalogItem.winget_id
        install_hint = $CatalogItem.install_hint
        manual_install_note = $CatalogItem.manual_install_note
        detect_attempts = $attempts
    }
}
