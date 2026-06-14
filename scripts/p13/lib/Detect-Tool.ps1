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

function Resolve-CandidatePath {
    param([string]$CandidatePath)
    if (-not $CandidatePath) { return $null }
    if ($CandidatePath -match '[\*\?]') {
        $match = Get-ChildItem -Path $CandidatePath -File -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($match) { return $match.FullName }
        return $null
    }
    if (Test-Path -LiteralPath $CandidatePath -PathType Leaf) {
        return (Resolve-Path -LiteralPath $CandidatePath).Path
    }
    return $null
}

function Get-ToolCandidatePaths {
    param($CatalogItem)
    $paths = @()
    foreach ($field in @('candidate_paths', 'known_paths')) {
        if ($CatalogItem.PSObject.Properties.Name -contains $field) {
            $value = $CatalogItem.$field
            if ($value) { $paths += @($value) }
        }
    }
    return @($paths)
}

function Get-ToolRegistryAppPaths {
    param($CatalogItem)
    $paths = @()
    if ($CatalogItem.PSObject.Properties.Name -contains 'registry_app_paths') {
        $value = $CatalogItem.registry_app_paths
        if ($value) { $paths += @($value) }
    }
    return @($paths)
}

function Invoke-DetectCandidatePath {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [string]$VersionArgument = '--version'
    )
    $resolved = Resolve-CandidatePath -CandidatePath $Path
    if (-not $resolved) {
        return [ordered]@{ ok = $false; output = 'candidate_path_not_found'; path = $Path }
    }
    try {
        $output = & $resolved $VersionArgument 2>&1 | Select-Object -First 5
        return [ordered]@{ ok = $true; output = (($output | Out-String).Trim()); path = $resolved }
    } catch {
        return [ordered]@{ ok = $false; output = $_.Exception.Message; path = $resolved }
    }
}

function Invoke-DetectRegistryAppPath {
    param([Parameter(Mandatory = $true)][string]$RegistryPath)
    try {
        $item = Get-ItemProperty -LiteralPath $RegistryPath -ErrorAction Stop
        $resolved = $item.'(default)'
        if (-not $resolved) { $resolved = $item.'(Default)' }
        if (-not $resolved) { $resolved = $item.PSChildName }
        if ($resolved -and (Test-Path -LiteralPath $resolved -PathType Leaf)) {
            $output = & $resolved --version 2>&1 | Select-Object -First 5
            return [ordered]@{ ok = $true; output = (($output | Out-String).Trim()); path = $resolved }
        }
        return [ordered]@{ ok = $false; output = 'registry_app_path_target_not_found'; path = $resolved }
    } catch {
        return [ordered]@{ ok = $false; output = $_.Exception.Message; path = $RegistryPath }
    }
}

function Test-PostgreSqlPort {
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $async = $client.BeginConnect('127.0.0.1', 5432, $null, $null)
        $ok = $async.AsyncWaitHandle.WaitOne(1000, $false)
        if ($ok) { $client.EndConnect($async) }
        $client.Close()
        return [bool]$ok
    } catch {
        return $false
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
    if (-not $available) {
        foreach ($candidatePath in (Get-ToolCandidatePaths -CatalogItem $CatalogItem)) {
            $result = Invoke-DetectCandidatePath -Path $candidatePath
            $attempts += [pscustomobject]@{
                command = "$candidatePath --version"
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
    }
    if (-not $available) {
        foreach ($registryPath in (Get-ToolRegistryAppPaths -CatalogItem $CatalogItem)) {
            $result = Invoke-DetectRegistryAppPath -RegistryPath $registryPath
            $attempts += [pscustomobject]@{
                command = "registry:$registryPath"
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
    }
    $versionOk = Compare-MinVersion -Actual $version -Minimum $CatalogItem.min_version
    $status = 'available'
    if (-not $available) { $status = 'missing' }
    elseif (-not $versionOk) { $status = 'version_mismatch' }
    $message = "tool status: $status"
    $nextAction = $CatalogItem.install_hint
    if ($CatalogItem.name -eq 'postgresql' -and -not $available -and (Test-PostgreSqlPort)) {
        $status = 'partial'
        $message = 'PostgreSQL port is reachable but psql client was not found'
        $nextAction = 'add PostgreSQL bin to PATH or configure known path'
    }
    [pscustomobject]@{
        name = $CatalogItem.name
        role = $Role
        required = $required
        status = $status
        message = $message
        next_action = $nextAction
        version = $version
        min_version = $CatalogItem.min_version
        path = $path
        candidate_paths = Get-ToolCandidatePaths -CatalogItem $CatalogItem
        registry_app_paths = Get-ToolRegistryAppPaths -CatalogItem $CatalogItem
        winget_id = $CatalogItem.winget_id
        install_hint = $CatalogItem.install_hint
        manual_install_note = $CatalogItem.manual_install_note
        detect_attempts = $attempts
    }
}
