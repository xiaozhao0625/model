param(
    [Parameter(Mandatory = $true)][ValidateSet('M0','W1','W2','W3')][string]$Role
)

$ErrorActionPreference = 'Continue'
$RepoRoot = (Resolve-Path "$PSScriptRoot\..\..").Path
. "$PSScriptRoot\lib\Write-DeployLog.ps1"
. "$PSScriptRoot\lib\Detect-Tool.ps1"
. "$PSScriptRoot\lib\Test-Network.ps1"
. "$PSScriptRoot\lib\Test-Gpu.ps1"
. "$PSScriptRoot\lib\Test-Service.ps1"

$outDir = Join-Path $RepoRoot "logs/p13/$Role"
$logPath = Join-Path $outDir 'inventory.log'
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
Write-DeployLog -LogPath $logPath -Role $Role -Action 'inventory' -Message 'Starting local inventory.'

$matrix = Get-Content -LiteralPath (Join-Path $RepoRoot 'deploy/role_matrix.json') -Raw | ConvertFrom-Json
$roleConfig = $matrix.roles.$Role
$catalog = Get-Content -LiteralPath (Join-Path $RepoRoot 'deploy/software_catalog.json') -Raw | ConvertFrom-Json
$roleTools = @($roleConfig.required_tools + $roleConfig.optional_tools)
$toolReports = @()
foreach ($item in $catalog) {
    if ($roleTools -contains $item.name) {
        $item.required = @($roleConfig.required_tools) -contains $item.name
        $toolReports += Test-Tool -CatalogItem $item -Role $Role
    }
}

$portReports = @()
foreach ($p in $roleConfig.ports) {
    $portReports += Test-RolePort -HostName '127.0.0.1' -Port ([int]$p.port) -Name $p.name
}
$networkReport = [ordered]@{
    local_ips = @(Get-LocalIpAddresses)
    master_api = Test-HttpEndpoint -Url (($roleConfig.master_api_url.TrimEnd('/')) + '/health') -TimeoutSeconds 2
    ports = $portReports
}
$gpuReport = Test-Gpu
$serviceReport = [ordered]@{
    services = @($roleConfig.required_services | ForEach-Object { Test-WindowsService -Name $_ })
}

$envPath = Join-Path $RepoRoot '.env'
$missing = @($toolReports | Where-Object { $_.required -and $_.status -eq 'missing' })
$versionMismatch = @($toolReports | Where-Object { $_.status -eq 'version_mismatch' })
$manual = @($toolReports | Where-Object { $_.status -eq 'missing' -and $_.manual_install_note })

$inventory = [ordered]@{
    role = $Role
    role_config = $roleConfig
    timestamp = (Get-Date).ToUniversalTime().ToString('o')
    windows_version = (Get-CimInstance Win32_OperatingSystem -ErrorAction SilentlyContinue).Caption
    powershell_version = $PSVersionTable.PSVersion.ToString()
    is_admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    current_user = [Environment]::UserName
    machine_name = [Environment]::MachineName
    project_root = $RepoRoot
    env_exists = (Test-Path -LiteralPath $envPath)
    env_raw_output = $false
    tools = $toolReports
    network = $networkReport
    gpu = $gpuReport
    services = $serviceReport
    missing_tools = $missing
    version_mismatches = $versionMismatch
    manual_install_required = $manual
}

Save-SafeJson -InputObject $inventory -Path (Join-Path $outDir 'inventory.json')
Save-SafeJson -InputObject $missing -Path (Join-Path $outDir 'missing_tools.json')
Save-SafeJson -InputObject @{ role = $Role; version_mismatches = $versionMismatch; tools = $toolReports } -Path (Join-Path $outDir 'version_report.json')
Save-SafeJson -InputObject $networkReport -Path (Join-Path $outDir 'network_report.json')
Save-SafeJson -InputObject $gpuReport -Path (Join-Path $outDir 'gpu_report.json')
Save-SafeJson -InputObject $serviceReport -Path (Join-Path $outDir 'service_report.json')

$summary = @(
    "# P13.3 inventory summary - $Role",
    '',
    "- Project root: $RepoRoot",
    "- .env present: $($inventory.env_exists) (raw values not read or printed)",
    "- Missing required tools: $($missing.Count)",
    "- Version mismatches: $($versionMismatch.Count)",
    "- Manual install required: $($manual.Count)",
    "- Master API status: $($networkReport.master_api.status)"
)
Set-Content -LiteralPath (Join-Path $outDir 'inventory_summary.md') -Encoding UTF8 -Value $summary
Write-DeployLog -LogPath $logPath -Role $Role -Action 'inventory' -Message 'Inventory completed.' -Data @{ missing = $missing.Count; version_mismatches = $versionMismatch.Count }
$inventory | ConvertTo-SafeJson
