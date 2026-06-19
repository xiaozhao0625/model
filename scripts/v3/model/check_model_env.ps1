param(
  [string]$AppShotHome = $env:APP_SHOT_HOME,
  [string]$ModelRoot = $env:APP_SHOT_MODELS
)

$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($AppShotHome)) {
  $AppShotHome = "D:\work\app-shot"
}
if ([string]::IsNullOrWhiteSpace($ModelRoot)) {
  $ModelRoot = Join-Path $AppShotHome "models"
}
if (![IO.Path]::IsPathRooted($ModelRoot)) {
  $ModelRoot = Join-Path (Get-Location) $ModelRoot
}
$root = Resolve-Path -LiteralPath $ModelRoot -ErrorAction SilentlyContinue
$modelRootPath = if ($root) { $root.Path } else { $ModelRoot }
[pscustomobject]@{
  status = if ($root) { "ok" } else { "model_root_missing" }
  app_shot_home = $AppShotHome
  model_root = $modelRootPath
  showui = Test-Path -LiteralPath (Join-Path $modelRootPath "showui")
  paddleocr = Test-Path -LiteralPath (Join-Path $modelRootPath "paddleocr")
  fasttext = Test-Path -LiteralPath (Join-Path $modelRootPath "fasttext")
  omniparser = Test-Path -LiteralPath (Join-Path $modelRootPath "omniparser")
  auto_download = $false
} | ConvertTo-Json -Depth 4
