param(
  [string]$ModelRoot = "models"
)

$ErrorActionPreference = "Stop"
$root = Resolve-Path -LiteralPath (Join-Path (Get-Location) $ModelRoot) -ErrorAction SilentlyContinue
[pscustomobject]@{
  status = if ($root) { "ok" } else { "model_root_missing" }
  model_root = if ($root) { $root.Path } else { $ModelRoot }
  showui = Test-Path -LiteralPath (Join-Path $ModelRoot "showui")
  paddleocr = Test-Path -LiteralPath (Join-Path $ModelRoot "paddleocr")
  fasttext = Test-Path -LiteralPath (Join-Path $ModelRoot "fasttext")
  omniparser = Test-Path -LiteralPath (Join-Path $ModelRoot "omniparser")
  auto_download = $false
} | ConvertTo-Json -Depth 4
