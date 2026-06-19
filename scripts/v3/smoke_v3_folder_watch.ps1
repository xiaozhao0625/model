param(
  [string]$Folder = "runs/v3_smoke_input"
)

$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path $Folder | Out-Null
$sample = Join-Path $Folder "start_button.png"
if (!(Test-Path -LiteralPath $sample)) {
  [IO.File]::WriteAllBytes($sample, [byte[]](137,80,78,71,13,10,26,10))
}
python -c "from ai_screenshot_platform.v3.capture.folder_watch import list_new_images; import json; print(json.dumps({'found':[str(p) for p in list_new_images('runs/v3_smoke_input')]}))"
