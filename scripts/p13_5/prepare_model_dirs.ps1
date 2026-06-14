param(
  [ValidateSet("M0", "W1", "W2", "W3")]
  [string]$Role = "M0",
  [switch]$Create
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonScript = Join-Path $scriptDir "prepare_model_dirs.py"
$argsList = @($pythonScript, "--role", $Role)
if ($Create) {
  $argsList += "--create"
}
python @argsList
