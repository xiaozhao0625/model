. "$PSScriptRoot\Test-Network.ps1"

function Test-ProcessPresent {
    param([string]$Name)
    $proc = Get-Process -Name $Name -ErrorAction SilentlyContinue | Select-Object -First 1
    [pscustomobject]@{
        name = $Name
        status = $(if ($proc) { 'ok' } else { 'missing' })
        message = $(if ($proc) { "process $Name is running" } else { "process $Name not found" })
        next_action = $(if ($proc) { $null } else { "Start or verify $Name." })
    }
}

function Test-WindowsService {
    param([string]$Name)
    $svc = Get-Service -Name $Name -ErrorAction SilentlyContinue
    [pscustomobject]@{
        name = $Name
        status = $(if ($svc) { [string]$svc.Status } else { 'missing' })
        message = $(if ($svc) { "service $Name is $($svc.Status)" } else { "service $Name not found" })
        next_action = $(if ($svc -and $svc.Status -eq 'Running') { $null } else { "Install or start service $Name if required." })
    }
}

function Test-RolePort {
    param([string]$HostName, [int]$Port, [string]$Name)
    $result = Test-TcpPort -HostName $HostName -Port $Port
    $result | Add-Member -NotePropertyName name -NotePropertyValue $Name -Force
    return $result
}
