param(
  [string]$ManifestPath = "models/model_manifest.example.json"
)

$ErrorActionPreference = "Stop"
if (!(Test-Path -LiteralPath $ManifestPath)) {
  throw "manifest not found: $ManifestPath"
}
Get-Content -LiteralPath $ManifestPath -Raw | ConvertFrom-Json | Out-Null
[pscustomobject]@{
  status = "ok"
  manifest = (Resolve-Path -LiteralPath $ManifestPath).Path
  note = "schema json parse passed; sha256 verification requires local model files"
} | ConvertTo-Json -Depth 4
