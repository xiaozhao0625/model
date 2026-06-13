. "$PSScriptRoot\ConvertTo-SafeJson.ps1"

function Write-DeployLog {
    param(
        [Parameter(Mandatory = $true)][string]$LogPath,
        [Parameter(Mandatory = $true)][string]$Role,
        [Parameter(Mandatory = $true)][string]$Action,
        [Parameter(Mandatory = $true)][string]$Message,
        [ValidateSet('DEBUG','INFO','WARN','ERROR')][string]$Level = 'INFO',
        $Data = $null
    )
    $parent = Split-Path -Parent $LogPath
    if ($parent) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }
    $entry = [ordered]@{
        timestamp = (Get-Date).ToUniversalTime().ToString('o')
        level = $Level
        role = $Role
        action = $Action
        message = $Message
        data = ConvertTo-SafeObject $Data
    }
    ($entry | ConvertTo-Json -Depth 8 -Compress) | Add-Content -LiteralPath $LogPath -Encoding UTF8
}
