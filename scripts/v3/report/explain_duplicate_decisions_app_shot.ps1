param(
  [string]$AppShotHome = "D:\work\app-shot",
  [Parameter(Mandatory = $true)][string]$RunId,
  [string]$OutputJson = "",
  [string]$OutputMarkdown = ""
)

$ErrorActionPreference = "Stop"

$RunsRoot = Join-Path $AppShotHome "runs\v3"
$RunDir = Join-Path $RunsRoot $RunId
$ReportsRoot = Join-Path $AppShotHome "reports"
if ([string]::IsNullOrWhiteSpace($OutputJson)) {
  $OutputJson = Join-Path $ReportsRoot "duplicate_explain_$RunId.json"
}
if ([string]::IsNullOrWhiteSpace($OutputMarkdown)) {
  $OutputMarkdown = Join-Path $ReportsRoot "duplicate_explain_$RunId.md"
}
New-Item -ItemType Directory -Force -Path $ReportsRoot | Out-Null

function Read-JsonFile {
  param([string]$Path)
  if (-not (Test-Path -LiteralPath $Path)) {
    return $null
  }
  $raw = Get-Content -Raw -LiteralPath $Path
  if ([string]::IsNullOrWhiteSpace($raw)) {
    return $null
  }
  return $raw | ConvertFrom-Json
}

function Read-JsonLines {
  param([string]$Path)
  $items = @()
  if (-not (Test-Path -LiteralPath $Path)) {
    return $items
  }
  foreach ($line in Get-Content -LiteralPath $Path) {
    if ([string]::IsNullOrWhiteSpace($line)) {
      continue
    }
    try {
      $items += ($line | ConvertFrom-Json)
    } catch {
      $items += (ConvertFrom-BestEffortImageLine -Line $line)
    }
  }
  return $items
}

function Get-RegexValue {
  param([string]$Text, [string]$Pattern)
  $match = [regex]::Match($Text, $Pattern)
  if ($match.Success) {
    return $match.Groups[1].Value
  }
  return $null
}

function ConvertFrom-BestEffortImageLine {
  param([string]$Line)
  $rejectRaw = Get-RegexValue -Text $Line -Pattern '"reject_reason":(null|"([^"]*)")'
  $rejectReason = $null
  if ($rejectRaw -and $rejectRaw -ne "null") {
    $rejectReason = $rejectRaw.Trim('"')
  }
  $nearRaw = Get-RegexValue -Text $Line -Pattern '"near_duplicate":(true|false)'
  return [pscustomobject]@{
    image_id = Get-RegexValue -Text $Line -Pattern '"image_id":"([^"]*)"'
    path = (Get-RegexValue -Text $Line -Pattern '"path":"((?:\\.|[^"])*)"')
    bucket = Get-RegexValue -Text $Line -Pattern '"bucket":"([^"]*)"'
    sha256 = Get-RegexValue -Text $Line -Pattern '"sha256":"([^"]*)"'
    content_hash = Get-RegexValue -Text $Line -Pattern '"content_hash":"([^"]*)"'
    near_duplicate = $nearRaw -eq "true"
    reject_reason = $rejectReason
    meta = [pscustomobject]@{
      capture_reason = Get-RegexValue -Text $Line -Pattern '"capture_reason":"([^"]*)"'
      action_id = Get-RegexValue -Text $Line -Pattern '"action_id":(null|"([^"]*)")'
      ui_state_hint = Get-RegexValue -Text $Line -Pattern '"ui_state_hint":"([^"]*)"'
    }
    duplicate_decision = $null
  }
}

function Get-Prop {
  param($Object, [string]$Name, $Default = $null)
  if ($null -eq $Object) {
    return $Default
  }
  if ($Object.PSObject.Properties.Name -contains $Name) {
    $value = $Object.$Name
    if ($null -ne $value) {
      return $value
    }
  }
  return $Default
}

function To-Map {
  param($Object)
  $map = @{}
  if ($null -eq $Object) {
    return $map
  }
  foreach ($prop in $Object.PSObject.Properties) {
    $map[$prop.Name] = $prop.Value
  }
  return $map
}

function New-ReconstructedDecision {
  param($Image, [hashtable]$FirstSeen, [hashtable]$StateSeen, [hashtable]$RepresentativeSeen)
  $meta = Get-Prop $Image "meta" @{}
  $hash = [string](Get-Prop $Image "content_hash" (Get-Prop $Image "sha256" ""))
  $captureReason = [string](Get-Prop $meta "capture_reason" "periodic")
  $uiState = [string](Get-Prop $meta "ui_state_hint" "unknown")
  $actionId = Get-Prop $meta "action_id" $null
  $bucket = [string](Get-Prop $Image "bucket" "")
  $rejectReason = Get-Prop $Image "reject_reason" $null
  $compared = if ($hash -and $FirstSeen.ContainsKey($hash)) { $FirstSeen[$hash] } else { $null }
  $exact = $null -ne $compared
  $groupKey = if ($actionId) { "$actionId|$uiState" } else { $null }
  $repIndex = $null
  if ($groupKey) {
    $currentRepresentativeCount = if ($RepresentativeSeen.ContainsKey($groupKey)) { [int]$RepresentativeSeen[$groupKey] } else { 0 }
    $repIndex = $currentRepresentativeCount + 1
  }
  $acceptedRep = $bucket -eq "accepted" -and $exact -and $captureReason -in @("before_action", "after_action", "rollback_after", "menu_state", "dialog_state") -and $uiState -notin @("unknown", "editor")
  $reason = "visual_difference_accepted"
  if ($bucket -eq "accepted" -and $acceptedRep) {
    if ($captureReason -eq "menu_state") {
      $reason = "menu_state_representative_accepted"
    } elseif ($captureReason -eq "dialog_state") {
      $reason = "dialog_state_representative_accepted"
    } else {
      $reason = "after_action_representative_accepted"
    }
  } elseif ($bucket -eq "accepted" -and -not $exact) {
    $reason = if ($StateSeen.ContainsKey($uiState)) { "visual_difference_accepted" } else { "first_frame_for_ui_state" }
  } elseif ($bucket -eq "rejected" -and $exact -and $rejectReason -eq "near_duplicate" -and $captureReason -eq "periodic") {
    $reason = "periodic_static_frame_rejected"
  } elseif ($bucket -eq "rejected" -and $exact -and $rejectReason -eq "near_duplicate") {
    $reason = "near_duplicate_rejected"
  } elseif ($bucket -eq "rejected" -and $exact) {
    $reason = "exact_duplicate_rejected"
  } elseif ($bucket -eq "rejected" -and $rejectReason) {
    $reason = [string]$rejectReason
  }
  return [pscustomobject]@{
    content_hash = $hash
    exact_duplicate = $exact
    near_duplicate = $exact
    duplicate_algorithm = "sha256_exact"
    similarity_score = if ($exact) { 1.0 } else { 0.0 }
    duplicate_threshold = 1.0
    compared_with_image_id = if ($compared) { $compared.image_id } else { $null }
    compared_with_image_path = if ($compared) { $compared.path } else { $null }
    capture_reason = $captureReason
    ui_state_hint = $uiState
    action_id = $actionId
    accepted_as_action_representative = $acceptedRep
    representative_group_key = $groupKey
    representative_index = $repIndex
    representative_limit = 3
    duplicate_decision_reason = $reason
  }
}

$summaryPath = Join-Path $RunDir "summary.json"
$imagesPath = Join-Path $RunDir "images.jsonl"
$summary = Read-JsonFile -Path $summaryPath
if ($null -eq $summary) {
  throw "Missing summary.json for $RunId"
}
$images = Read-JsonLines -Path $imagesPath
$firstSeen = @{}
$stateSeen = @{}
$representativeSeen = @{}
$normalized = @()

foreach ($image in $images) {
  $decision = Get-Prop $image "duplicate_decision" $null
  if ($null -eq $decision -or @($decision.PSObject.Properties).Count -eq 0) {
    $decision = New-ReconstructedDecision -Image $image -FirstSeen $firstSeen -StateSeen $stateSeen -RepresentativeSeen $representativeSeen
  }
  $meta = Get-Prop $image "meta" @{}
  $hash = [string](Get-Prop $decision "content_hash" (Get-Prop $image "content_hash" ""))
  $uiState = [string](Get-Prop $decision "ui_state_hint" (Get-Prop $meta "ui_state_hint" "unknown"))
  $groupKey = Get-Prop $decision "representative_group_key" $null
  if ((Get-Prop $image "bucket" "") -eq "accepted") {
    $stateSeen[$uiState] = $true
  }
  if ((Get-Prop $decision "accepted_as_action_representative" $false) -and $groupKey) {
    $currentRepresentativeCount = if ($representativeSeen.ContainsKey($groupKey)) { [int]$representativeSeen[$groupKey] } else { 0 }
    $representativeSeen[$groupKey] = $currentRepresentativeCount + 1
  }
  if ($hash -and -not $firstSeen.ContainsKey($hash)) {
    $firstSeen[$hash] = [pscustomobject]@{
      image_id = Get-Prop $image "image_id" $null
      path = Get-Prop $image "path" $null
    }
  }
  $normalized += [pscustomobject]@{
    image = $image
    decision = $decision
    reason = [string](Get-Prop $decision "duplicate_decision_reason" (Get-Prop $image "reject_reason" "unknown"))
  }
}

$accepted = @($normalized | Where-Object { (Get-Prop $_.image "bucket" "") -eq "accepted" })
$rejectedNear = @($normalized | Where-Object { (Get-Prop $_.image "reject_reason" $null) -eq "near_duplicate" })
$actionRepresentative = @($normalized | Where-Object { Get-Prop $_.decision "accepted_as_action_representative" $false })
$rejectedReasons = @{}
foreach ($row in $normalized) {
  if ((Get-Prop $row.image "bucket" "") -ne "rejected") {
    continue
  }
  $reason = [string](Get-Prop $row.image "reject_reason" "unknown")
  $currentRejectedCount = if ($rejectedReasons.ContainsKey($reason)) { [int]$rejectedReasons[$reason] } else { 0 }
  $rejectedReasons[$reason] = $currentRejectedCount + 1
}

$representativeGroups = @()
foreach ($group in ($actionRepresentative | Group-Object { Get-Prop $_.decision "representative_group_key" "unknown" })) {
  $first = $group.Group[0].decision
  $limit = [int](Get-Prop $first "representative_limit" 3)
  $representativeGroups += [pscustomobject]@{
    action_id = Get-Prop $first "action_id" $null
    ui_state_hint = Get-Prop $first "ui_state_hint" "unknown"
    kept_count = $group.Count
    why_kept = Get-Prop $first "duplicate_decision_reason" "after_action_representative_accepted"
    representative_limit = $limit
    exceeded_limit = $group.Count -gt $limit
  }
}

$report = [pscustomobject]@{
  run_id = $RunId
  processed = [int](Get-Prop $summary "processed" $images.Count)
  accepted = [int](Get-Prop $summary "accepted" $accepted.Count)
  rejected = [int](Get-Prop $summary "rejected" ($images.Count - $accepted.Count))
  exact_duplicate_count = @($normalized | Where-Object { Get-Prop $_.decision "exact_duplicate" $false }).Count
  near_duplicate_count = [int](Get-Prop $summary "near_duplicate_count" $rejectedNear.Count)
  action_representative_accepted_count = $actionRepresentative.Count
  visual_difference_accepted_count = @($normalized | Where-Object { $_.reason -eq "visual_difference_accepted" }).Count
  menu_state_accepted_count = @($normalized | Where-Object { $_.reason -eq "menu_state_representative_accepted" }).Count
  dialog_state_accepted_count = @($normalized | Where-Object { $_.reason -eq "dialog_state_representative_accepted" }).Count
  periodic_static_rejected_count = @($normalized | Where-Object { $_.reason -eq "periodic_static_frame_rejected" }).Count
  accepted_by_ui_state_hint = To-Map (Get-Prop $summary "accepted_by_ui_state_hint" $null)
  accepted_by_capture_reason = To-Map (Get-Prop $summary "accepted_by_capture_reason" $null)
  rejected_by_reason = $rejectedReasons
  accepted_samples = @($accepted | Select-Object -First 20 | ForEach-Object {
      [pscustomobject]@{
        image_id = Get-Prop $_.image "image_id" $null
        path = Get-Prop $_.image "path" $null
        capture_reason = Get-Prop $_.decision "capture_reason" $null
        ui_state_hint = Get-Prop $_.decision "ui_state_hint" $null
        duplicate_decision_reason = $_.reason
        similarity_score = Get-Prop $_.decision "similarity_score" $null
        compared_with_image_id = Get-Prop $_.decision "compared_with_image_id" $null
      }
    })
  rejected_near_duplicate_samples = @($rejectedNear | Select-Object -First 20 | ForEach-Object {
      [pscustomobject]@{
        image_id = Get-Prop $_.image "image_id" $null
        path = Get-Prop $_.image "path" $null
        compared_with_image_id = Get-Prop $_.decision "compared_with_image_id" $null
        similarity_score = Get-Prop $_.decision "similarity_score" $null
        threshold = Get-Prop $_.decision "duplicate_threshold" $null
        reject_reason = Get-Prop $_.image "reject_reason" $null
      }
    })
  action_representative_samples = $representativeGroups
}

$report | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $OutputJson -Encoding UTF8

$md = New-Object System.Collections.Generic.List[string]
$md.Add("# Duplicate Decisions: $RunId")
$md.Add("")
$md.Add("- processed: $($report.processed)")
$md.Add("- accepted: $($report.accepted)")
$md.Add("- rejected: $($report.rejected)")
$md.Add("- exact_duplicate_count: $($report.exact_duplicate_count)")
$md.Add("- near_duplicate_count: $($report.near_duplicate_count)")
$md.Add("- action_representative_accepted_count: $($report.action_representative_accepted_count)")
$md.Add("- visual_difference_accepted_count: $($report.visual_difference_accepted_count)")
$md.Add("- menu_state_accepted_count: $($report.menu_state_accepted_count)")
$md.Add("- dialog_state_accepted_count: $($report.dialog_state_accepted_count)")
$md.Add("- periodic_static_rejected_count: $($report.periodic_static_rejected_count)")
$md.Add("")
$md.Add("## Accepted Samples")
$md.Add("")
$md.Add("| image_id | path | capture_reason | ui_state_hint | duplicate_decision_reason | similarity_score | compared_with_image_id |")
$md.Add("| --- | --- | --- | --- | --- | ---: | --- |")
foreach ($sample in $report.accepted_samples) {
  $md.Add("| $($sample.image_id) | $($sample.path) | $($sample.capture_reason) | $($sample.ui_state_hint) | $($sample.duplicate_decision_reason) | $($sample.similarity_score) | $($sample.compared_with_image_id) |")
}
$md.Add("")
$md.Add("## Rejected Near Duplicate Samples")
$md.Add("")
$md.Add("| image_id | path | compared_with_image_id | similarity_score | threshold | reject_reason |")
$md.Add("| --- | --- | --- | ---: | ---: | --- |")
foreach ($sample in $report.rejected_near_duplicate_samples) {
  $md.Add("| $($sample.image_id) | $($sample.path) | $($sample.compared_with_image_id) | $($sample.similarity_score) | $($sample.threshold) | $($sample.reject_reason) |")
}
$md.Add("")
$md.Add("## Action Representative Samples")
$md.Add("")
$md.Add("| action_id | ui_state_hint | kept_count | why_kept | representative_limit | exceeded_limit |")
$md.Add("| --- | --- | ---: | --- | ---: | --- |")
foreach ($sample in $report.action_representative_samples) {
  $md.Add("| $($sample.action_id) | $($sample.ui_state_hint) | $($sample.kept_count) | $($sample.why_kept) | $($sample.representative_limit) | $($sample.exceeded_limit) |")
}

$md | Set-Content -LiteralPath $OutputMarkdown -Encoding UTF8

Write-Output (@{
    run_id = $RunId
    report_json = $OutputJson
    report_markdown = $OutputMarkdown
  } | ConvertTo-Json -Depth 4)
