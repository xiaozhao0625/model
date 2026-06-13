param(
    [ValidateSet('M0','W1','W2','W3')][string]$Role = 'M0'
)

$ErrorActionPreference = 'Continue'
$RepoRoot = (Resolve-Path "$PSScriptRoot\..\..").Path
. "$PSScriptRoot\lib\Write-DeployLog.ps1"

$outDir = Join-Path $RepoRoot 'logs/p13/ssh'
$logPath = Join-Path $outDir 'ssh_prepare.log'
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
Write-DeployLog -LogPath $logPath -Role $Role -Action 'prepare_ssh' -Message 'Starting SSH preparation check.'

$client = Get-Command ssh -ErrorAction SilentlyContinue
$server = Get-Service sshd -ErrorAction SilentlyContinue
$sshDir = Join-Path $HOME '.ssh'
$pubKey = Join-Path $sshDir 'id_ed25519.pub'
$privateKey = Join-Path $sshDir 'id_ed25519'
$generated = $false

if (-not (Test-Path -LiteralPath $pubKey)) {
    New-Item -ItemType Directory -Force -Path $sshDir | Out-Null
    $sshKeygen = Get-Command ssh-keygen -ErrorAction SilentlyContinue
    if ($sshKeygen) {
        & ssh-keygen -t ed25519 -f $privateKey -N '' -C "p13-m0-orchestrator" | Out-Null
        $generated = $true
        Write-DeployLog -LogPath $logPath -Role $Role -Action 'prepare_ssh' -Message 'Generated M0 public key pair. Private key not logged.'
    }
}

$bootstrap = @(
    '# Run on W1/W2/W3 from an elevated PowerShell prompt:',
    'Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0',
    'Start-Service sshd',
    'Set-Service -Name sshd -StartupType Automatic',
    'New-NetFirewallRule -Name P13_M0_SSH_LAN -DisplayName "P13 M0 SSH LAN" -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22 -RemoteAddress 192.168.1.18',
    '# Append the M0 public key to %USERPROFILE%\.ssh\authorized_keys on each worker.',
    '# Do not store passwords, private keys, or API tokens in this repository.'
)

$result = [ordered]@{
    role = $Role
    openssh_client = $(if ($client) { 'available' } else { 'missing' })
    openssh_server = $(if ($server) { [string]$server.Status } else { 'missing' })
    public_key_present = (Test-Path -LiteralPath $pubKey)
    public_key_generated = $generated
    public_key_path = $pubKey
    private_key_logged = $false
    lan_only_remote_access = $true
    bootstrap_steps_file = 'ssh_bootstrap_steps.md'
}

Save-SafeJson -InputObject $result -Path (Join-Path $outDir 'ssh_prepare_result.json')
Set-Content -LiteralPath (Join-Path $outDir 'ssh_bootstrap_steps.md') -Encoding UTF8 -Value @(
    '# P13.3 SSH bootstrap',
    '',
    'Scope: only controlled LAN connections from M0 to W1/W2/W3 are intended.',
    '',
    '```powershell',
    ($bootstrap -join [Environment]::NewLine),
    '```',
    '',
    'The private key is never written to logs or reports.'
)
Write-DeployLog -LogPath $logPath -Role $Role -Action 'prepare_ssh' -Message 'SSH preparation completed.' -Data $result
$result | ConvertTo-SafeJson
