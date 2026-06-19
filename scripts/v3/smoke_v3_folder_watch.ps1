param(
  [string]$Folder = "D:\work\app-shot\obs-output"
)

$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path $Folder | Out-Null
$sample = Join-Path $Folder "start_button.png"
if (!(Test-Path -LiteralPath $sample)) {
  [IO.File]::WriteAllBytes($sample, [byte[]](137,80,78,71,13,10,26,10))
}
$env:V3_SMOKE_FOLDER = $Folder
python -c "from ai_screenshot_platform.v3.capture.folder_watch import list_new_images; import json, os; folder=os.environ['V3_SMOKE_FOLDER']; print(json.dumps({'found':[str(p) for p in list_new_images(folder)]}))"
