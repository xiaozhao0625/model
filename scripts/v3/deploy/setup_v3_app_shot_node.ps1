param(
  [string]$Root = "D:\work\app-shot",
  [string]$RepoUrl = "https://github.com/xiaozhao0625/model.git",
  [string]$Branch = "feat/v3-obs-ocr-model-agent",
  [switch]$InstallPythonDeps,
  [switch]$InstallNodeDeps,
  [switch]$SkipGitPull
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Join-Path $Root "model"
$ReportsRoot = Join-Path $Root "reports"
$Dirs = @("tools", "downloads", "models", "cache", "runs\v3", "obs-output", "logs", "venvs", "reports")
foreach ($dir in $Dirs) {
  New-Item -ItemType Directory -Force -Path (Join-Path $Root $dir) | Out-Null
}

function Test-CommandAvailable {
  param([string]$Name)
  return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

if (-not (Test-Path -LiteralPath $ProjectRoot)) {
  git clone $RepoUrl $ProjectRoot
}
if (-not $SkipGitPull) {
  git -C $ProjectRoot fetch origin
}
git -C $ProjectRoot checkout $Branch
if (-not $SkipGitPull) {
  git -C $ProjectRoot pull --ff-only origin $Branch
}

$EnvDir = Join-Path $ProjectRoot "scripts\v3\env"
New-Item -ItemType Directory -Force -Path $EnvDir | Out-Null
$EnvScript = Join-Path $EnvDir "app_shot_env.ps1"
@"
`$env:APP_SHOT_HOME = "$Root"
`$env:APP_SHOT_PROJECT = "$ProjectRoot"
`$env:APP_SHOT_TOOLS = "$Root\tools"
`$env:APP_SHOT_MODELS = "$Root\models"
`$env:APP_SHOT_RUNS = "$Root\runs"
`$env:APP_SHOT_DOWNLOADS = "$Root\downloads"
`$env:APP_SHOT_OBS_OUTPUT = "$Root\obs-output"
`$env:PIP_CACHE_DIR = "$Root\cache\pip"
`$env:npm_config_cache = "$Root\cache\npm"
`$env:HF_HOME = "$Root\cache\huggingface"
`$env:HUGGINGFACE_HUB_CACHE = "$Root\cache\huggingface"
`$env:TRANSFORMERS_CACHE = "$Root\cache\huggingface"
`$env:TORCH_HOME = "$Root\cache\torch"
`$env:PADDLE_HOME = "$Root\cache\paddle"
`$env:PADDLE_PDX_CACHE_HOME = "$Root\models\paddleocr\paddlex"
`$env:PADDLE_PDX_MODEL_SOURCE = "modelscope"
`$env:PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK = "True"
`$env:PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT = "False"
`$env:APP_SHOT_ENABLE_PADDLEOCR = "1"
`$env:APP_SHOT_ENABLE_SHOWUI = "1"
"@ | Set-Content -LiteralPath $EnvScript -Encoding UTF8

$Python311 = "D:\work\python311\python.exe"
$Python = if (Test-Path -LiteralPath $Python311) { $Python311 } elseif (Test-CommandAvailable "python") { "python" } else { $null }
$GpuVenv = Join-Path $Root "venvs\v3-gpu"
if ($Python -and -not (Test-Path -LiteralPath (Join-Path $GpuVenv "Scripts\python.exe"))) {
  & $Python -m venv $GpuVenv
}

if ($InstallPythonDeps) {
  $VenvPython = Join-Path $GpuVenv "Scripts\python.exe"
  if (-not (Test-Path -LiteralPath $VenvPython)) { throw "v3-gpu python not found: $VenvPython" }
  & $VenvPython -m pip install -U pip
  & $VenvPython -m pip install -e $ProjectRoot
  & $VenvPython -m pip install uvicorn
}

if ($InstallNodeDeps) {
  $WebRoot = Join-Path $ProjectRoot "apps\web-console"
  npm --prefix $WebRoot install
}

$Report = [pscustomobject]@{
  generated_at = (Get-Date).ToUniversalTime().ToString("o")
  root = $Root
  repo_url = $RepoUrl
  branch = $Branch
  project_root = $ProjectRoot
  git_available = Test-CommandAvailable "git"
  python_available = [bool]$Python
  node_available = Test-CommandAvailable "node"
  npm_available = Test-CommandAvailable "npm"
  nvidia_smi_available = Test-CommandAvailable "nvidia-smi"
  obs_studio_path = Join-Path $Root "tools\obs-studio"
  obs_studio_present = Test-Path -LiteralPath (Join-Path $Root "tools\obs-studio")
  ffmpeg_path = Join-Path $Root "tools\ffmpeg"
  ffmpeg_present = Test-Path -LiteralPath (Join-Path $Root "tools\ffmpeg")
  venv_gpu = $GpuVenv
  env_script = $EnvScript
  redis_required = $false
  redis_note = "Redis is not required for V3 single-node mode."
  postgresql_required = $false
  postgresql_note = "PostgreSQL is not required for V3 single-node mode."
  docker_required = $false
  docker_note = "Docker is not required for V3 single-node mode."
  showui_model_dir = Join-Path $Root "models\showui"
  deploy_report_json = Join-Path $ReportsRoot "v3_deploy_report.json"
  deploy_report_md = Join-Path $ReportsRoot "v3_deploy_report.md"
}

$Report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $Report.deploy_report_json -Encoding UTF8
$md = @(
  "# V3 Single Node Deployment Report",
  "",
  "- Root: $Root",
  "- Repository: $ProjectRoot",
  "- Branch: $Branch",
  "- Frontend port: 5173",
  "- Frontend URL: http://localhost:5173/v3",
  "- Redis: not required for V3 single-node mode.",
  "- PostgreSQL: not required for V3 single-node mode.",
  "- Docker: not required for V3 single-node mode.",
  "- OBS: $($Report.obs_studio_present)",
  "- FFmpeg: $($Report.ffmpeg_present)",
  "- v3-gpu venv: $GpuVenv"
)
$md | Set-Content -LiteralPath $Report.deploy_report_md -Encoding UTF8

Write-Output ($Report | ConvertTo-Json -Depth 8)
