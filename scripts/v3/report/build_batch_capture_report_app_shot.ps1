param(
  [string]$AppShotHome = "D:\work\app-shot",
  [string[]]$RunIds = @(),
  [int]$AcceptedTarget = 100,
  [string]$OutputJson = "",
  [string]$OutputMarkdown = ""
)

$ErrorActionPreference = "Stop"

$RunsRoot = Join-Path $AppShotHome "runs\v3"
$ReportsRoot = Join-Path $AppShotHome "reports"
if ([string]::IsNullOrWhiteSpace($OutputJson)) {
  $OutputJson = Join-Path $ReportsRoot "v3_batch_capture_report.json"
}
if ([string]::IsNullOrWhiteSpace($OutputMarkdown)) {
  $OutputMarkdown = Join-Path $ReportsRoot "v3_batch_capture_report.md"
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
      $items += [pscustomobject]@{
        parse_error = $true
        raw = $line
      }
    }
  }
  return $items
}

function ConvertTo-Hashtable {
  param($Object)
  $result = @{}
  if ($null -eq $Object) {
    return $result
  }
  foreach ($prop in $Object.PSObject.Properties) {
    $result[$prop.Name] = $prop.Value
  }
  return $result
}

function Get-ActionText {
  param($Action)
  $parts = @()
  foreach ($name in @("label", "blocked_reason", "candidate_region_type", "source_candidate_id")) {
    if ($Action.PSObject.Properties.Name -contains $name -and $null -ne $Action.$name) {
      $parts += [string]$Action.$name
    }
  }
  if ($Action.PSObject.Properties.Name -contains "decision" -and $null -ne $Action.decision) {
    if ($Action.decision.PSObject.Properties.Name -contains "candidate" -and $null -ne $Action.decision.candidate) {
      foreach ($name in @("label", "text", "reason", "blocked_reason", "candidate_region_type")) {
        if ($Action.decision.candidate.PSObject.Properties.Name -contains $name -and $null -ne $Action.decision.candidate.$name) {
          $parts += [string]$Action.decision.candidate.$name
        }
      }
    }
  }
  return ($parts -join " ").ToLowerInvariant()
}

function Test-ExecutedAction {
  param($Action)
  if ($Action.PSObject.Properties.Name -contains "executed") {
    return [bool]$Action.executed
  }
  if ($Action.PSObject.Properties.Name -contains "result" -and $null -ne $Action.result) {
    if ($Action.result.PSObject.Properties.Name -contains "executed") {
      return [bool]$Action.result.executed
    }
    if ($Action.result.PSObject.Properties.Name -contains "reason") {
      return ([string]$Action.result.reason) -eq "real_click_executed"
    }
  }
  return $false
}

function Test-ContainsAnyTerm {
  param(
    [string]$Text,
    [string[]]$Terms
  )
  foreach ($term in $Terms) {
    $escaped = [regex]::Escape($term)
    $pattern = if ($term -match "^[a-z0-9 ]+$") {
      "(^|[^a-z0-9])$escaped([^a-z0-9]|$)"
    } else {
      $escaped
    }
    if ([regex]::IsMatch($Text, $pattern, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)) {
      return $true
    }
  }
  return $false
}

if ($RunIds.Count -eq 0) {
  $RunIds = Get-ChildItem -Path $RunsRoot -Directory |
    Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName "summary.json") } |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 5 -ExpandProperty Name
}

$requiredAuditFiles = @(
  "summary.json",
  "events.jsonl",
  "images.jsonl",
  "meta\ocr.jsonl",
  "meta\candidates.jsonl",
  "meta\actions.jsonl",
  "meta\rollback.jsonl",
  "meta\folder_watch_summary.json"
)

$titlebarTerms = @("titlebar", "title bar", "border", "close", "minimize", "maximize", "system button", "window controls")
$dangerTerms = @(
  "save", "save as", "save left", "save right", "save merged", "delete", "print", "exit",
  "open unknown", "external", "http", "www.", "login", "payment", "purchase", "buy",
  "upload", "send", "account", "password", "captcha", "verification"
)

$rows = @()
foreach ($runId in $RunIds) {
  $runDir = Join-Path $RunsRoot $runId
  $summaryPath = Join-Path $runDir "summary.json"
  $actionsPath = Join-Path $runDir "meta\actions.jsonl"
  $candidatesPath = Join-Path $runDir "meta\candidates.jsonl"
  $summary = Read-JsonFile -Path $summaryPath
  if ($null -eq $summary) {
    throw "Missing or invalid summary.json for run $runId"
  }

  $actions = Read-JsonLines -Path $actionsPath
  $candidates = Read-JsonLines -Path $candidatesPath
  $executedActions = @($actions | Where-Object { Test-ExecutedAction -Action $_ })
  $blockedActions = @($actions | Where-Object {
      ($_.PSObject.Properties.Name -contains "blocked_reason" -and $null -ne $_.blocked_reason -and ([string]$_.blocked_reason).Length -gt 0) -or
      ($_.PSObject.Properties.Name -contains "decision" -and $null -ne $_.decision -and $_.decision.PSObject.Properties.Name -contains "allowed" -and -not $_.decision.allowed)
    })

  $misclicked = $false
  $danger = $false
  foreach ($action in $executedActions) {
    $text = Get-ActionText -Action $action
    if (Test-ContainsAnyTerm -Text $text -Terms $titlebarTerms) {
      $misclicked = $true
    }
    if (Test-ContainsAnyTerm -Text $text -Terms $dangerTerms) {
      $danger = $true
    }
    if ($action.PSObject.Properties.Name -contains "candidate_region_type" -and ([string]$action.candidate_region_type) -eq "unsafe_chrome") {
      $misclicked = $true
      $danger = $true
    }
  }

  $auditFiles = @{}
  foreach ($relative in $requiredAuditFiles) {
    $auditFiles[$relative] = Test-Path -LiteralPath (Join-Path $runDir $relative)
  }

  $accepted = if ($summary.PSObject.Properties.Name -contains "accepted") { [int]$summary.accepted } else { [int]$summary.counts.accepted }
  $failed = if ($summary.PSObject.Properties.Name -contains "failed") { [int]$summary.failed } else { 0 }
  $quarantined = if ($summary.PSObject.Properties.Name -contains "quarantined") { [int]$summary.quarantined } else { 0 }
  $actionCount = if ($summary.PSObject.Properties.Name -contains "auto_click_count") { [int]$summary.auto_click_count } else { $executedActions.Count }
  $blockedCount = if ($summary.PSObject.Properties.Name -contains "blocked_count") { [int]$summary.blocked_count } else { $blockedActions.Count }
  $riskHitCount = if ($summary.PSObject.Properties.Name -contains "risk_hit_count") { [int]$summary.risk_hit_count } else { 0 }
  $acceptedTargetMet = $accepted -ge $AcceptedTarget
  $recommendLargerScale = $acceptedTargetMet -and $failed -eq 0 -and $quarantined -eq 0 -and -not $misclicked -and -not $danger -and $riskHitCount -eq 0

  $appName = if ($summary.PSObject.Properties.Name -contains "app_name" -and $summary.app_name) {
    [string]$summary.app_name
  } elseif ($summary.PSObject.Properties.Name -contains "config" -and $summary.config.PSObject.Properties.Name -contains "app_name") {
    [string]$summary.config.app_name
  } else {
    [string]$runId
  }

  $rows += [pscustomobject]@{
    software_name = $appName
    run_id = $runId
    processed = if ($summary.PSObject.Properties.Name -contains "processed") { [int]$summary.processed } else { 0 }
    accepted = $accepted
    rejected = if ($summary.PSObject.Properties.Name -contains "rejected") { [int]$summary.rejected } else { [int]$summary.counts.rejected }
    failed = $failed
    quarantined = $quarantined
    accepted_by_ui_state_hint = ConvertTo-Hashtable -Object $summary.accepted_by_ui_state_hint
    reject_reason_distribution = ConvertTo-Hashtable -Object $summary.reject_reason_distribution
    action_count = $actionCount
    blocked_count = $blockedCount
    risk_hit_count = $riskHitCount
    misclicked_titlebar_or_system_button = $misclicked
    dangerous_action_triggered = $danger
    accepted_target_met = $acceptedTargetMet
    recommend_larger_scale = $recommendLargerScale
    audit_files = $auditFiles
    summary_path = $summaryPath
    actions_path = $actionsPath
    candidates_path = $candidatesPath
    candidate_count = $candidates.Count
  }
}

$report = [pscustomobject]@{
  generated_at = (Get-Date).ToUniversalTime().ToString("o")
  app_shot_home = $AppShotHome
  accepted_target = $AcceptedTarget
  run_count = $rows.Count
  passed_count = @($rows | Where-Object { $_.accepted_target_met -and $_.failed -eq 0 -and $_.quarantined -eq 0 }).Count
  recommend_larger_scale_count = @($rows | Where-Object { $_.recommend_larger_scale }).Count
  runs = $rows
}

$report | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $OutputJson -Encoding UTF8

$md = New-Object System.Collections.Generic.List[string]
$md.Add("# V3 Batch Capture Report")
$md.Add("")
$md.Add("- Generated: $($report.generated_at)")
$md.Add("- Accepted target: $AcceptedTarget")
$md.Add("- Runs: $($rows.Count)")
$md.Add("")
$md.Add("| Software | Run | Processed | Accepted | Rejected | Failed | Quarantined | Actions | Blocked | Risk | Target | Larger scale |")
$md.Add("| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |")
foreach ($row in $rows) {
  $target = if ($row.accepted_target_met) { "yes" } else { "no" }
  $larger = if ($row.recommend_larger_scale) { "yes" } else { "no" }
  $md.Add("| $($row.software_name) | $($row.run_id) | $($row.processed) | $($row.accepted) | $($row.rejected) | $($row.failed) | $($row.quarantined) | $($row.action_count) | $($row.blocked_count) | $($row.risk_hit_count) | $target | $larger |")
}
$md.Add("")
$md.Add("## UI State Coverage")
$md.Add("")
foreach ($row in $rows) {
  $states = ($row.accepted_by_ui_state_hint.GetEnumerator() | Sort-Object Name | ForEach-Object { "$($_.Key)=$($_.Value)" }) -join ", "
  if ([string]::IsNullOrWhiteSpace($states)) {
    $states = "none"
  }
  $md.Add("- $($row.software_name) / $($row.run_id): $states")
}
$md.Add("")
$md.Add("## Safety")
$md.Add("")
foreach ($row in $rows) {
  $md.Add("- $($row.software_name): titlebar/system misclick=$($row.misclicked_titlebar_or_system_button); dangerous action=$($row.dangerous_action_triggered); summary.json=$($row.audit_files['summary.json']); meta\actions.jsonl=$($row.audit_files['meta\actions.jsonl']); meta\candidates.jsonl=$($row.audit_files['meta\candidates.jsonl'])")
}

$md | Set-Content -LiteralPath $OutputMarkdown -Encoding UTF8

Write-Output (@{
    report_json = $OutputJson
    report_markdown = $OutputMarkdown
    run_count = $rows.Count
    accepted_target = $AcceptedTarget
  } | ConvertTo-Json -Depth 6)
