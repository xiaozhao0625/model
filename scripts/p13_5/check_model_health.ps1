param(
  [ValidateSet("M0", "W1", "W2", "W3")]
  [string]$Role = "M0"
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
python (Join-Path $scriptDir "check_model_health.py") --role $Role
