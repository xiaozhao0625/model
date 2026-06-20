param(
  [string]$RunRoot = "D:\work\app-shot\runs\v3",
  [string]$DiagnosisPath = "D:\work\app-shot\logs\input_gateway_diagnosis.json"
)

$ErrorActionPreference = "Stop"
$AppShotRoot = "D:\work\app-shot"
$ProjectRoot = "D:\work\app-shot\model"
$Python = "D:\work\app-shot\venvs\v3\Scripts\python.exe"
if (-not (Test-Path $Python)) {
  $Python = "D:\work\python311\python.exe"
}
$Diagnose = Join-Path $ProjectRoot "scripts\v3\action\diagnose_input_gateway_app_shot.ps1"
& powershell -NoProfile -ExecutionPolicy Bypass -File $Diagnose -OutputPath $DiagnosisPath | Out-Null

$env:APP_SHOT_HOME = $AppShotRoot
$env:APP_SHOT_INPUT_GATEWAY_DIAGNOSIS = $DiagnosisPath
$env:PYTHONPATH = "$ProjectRoot\src;$env:PYTHONPATH"

$script = @'
import json
import os
import sys
from pathlib import Path

from ai_screenshot_platform.v3.action.click_executor import ClickExecutor
from ai_screenshot_platform.v3.action.input_gateway import load_input_gateway_readiness
from ai_screenshot_platform.v3.runtime import V3Runtime
from ai_screenshot_platform.v3.schemas import ActionDecision, FusedCandidate, V3TaskConfig
from ai_screenshot_platform.v3.storage.run_store import V3RunStore

run_root = Path(sys.argv[1])
readiness = load_input_gateway_readiness()
if not readiness.input_gateway_ready:
    raise SystemExit("input_gateway_not_ready:" + ",".join(readiness.blockers))
run_root.mkdir(parents=True, exist_ok=True)
runtime = V3Runtime(store=V3RunStore(run_root))
run = runtime.create_run(
    V3TaskConfig(
        app_name="input_gateway_safe_button_smoke",
        app_type="web",
        target_language="en",
        save_root=str(run_root),
        enable_auto_click=True,
        observe_only=False,
        max_actions=1,
    )
)
candidate = FusedCandidate(
    label="Safe button",
    source="ocr_box",
    bbox=[20, 20, 140, 60],
    click_x=80,
    click_y=40,
    confidence=0.99,
    reason="risk button must remain blocked elsewhere",
    final_score=0.95,
)
executor = ClickExecutor(
    allow_real_click=bool(readiness.input_gateway_ready and os.environ.get("APP_SHOT_INPUT_GATEWAY_SMOKE_REAL") == "1"),
    target_client_rect=(0, 0, 400, 300),
)
safe = executor.execute(ActionDecision(action="click", allowed=True, reason="allowed", candidate=candidate))
risk = executor.execute(ActionDecision(action="click", allowed=False, reason="risk button blocked", candidate=candidate))
action = {
    "label": "Safe button",
    "source_candidate_id": "ocr_box:Safe button:20:20:140:60",
    "before_image": "local_html_before.png",
    "after_image": "local_html_after.png",
    "safety_result": {"allowed": True, "reason": "allowed"},
    "result": safe,
    "click_backend": safe.get("click_backend"),
}
runtime.record_action_audit(run.run_id, action)
runtime.record_action_audit(
    run.run_id,
    {
        "label": "risk button",
        "source_candidate_id": "ocr_box:risk:1:1:2:2",
        "before_image": "local_html_before.png",
        "after_image": "local_html_before.png",
        "safety_result": {"allowed": False, "reason": "risk button blocked"},
        "result": risk,
        "click_backend": risk.get("click_backend"),
    },
)
actions_path = run_root / run.run_id / "meta" / "actions.jsonl"
if not actions_path.is_file():
    raise SystemExit("actions.jsonl missing")
records = [json.loads(line) for line in actions_path.read_text(encoding="utf-8").splitlines() if line.strip()]
if not all(record.get("result", {}).get("click_backend") for record in records):
    raise SystemExit("click_backend missing from action audit")
print(json.dumps({"run_id": run.run_id, "input_gateway_ready": readiness.input_gateway_ready, "click_backend": readiness.click_backend, "actions_jsonl": str(actions_path), "risk_button_blocked": risk.get("status") == "blocked"}, ensure_ascii=False))
'@

$TempScript = Join-Path "D:\work\app-shot\logs" "input_gateway_smoke_tmp.py"
New-Item -ItemType Directory -Force -Path (Split-Path $TempScript) | Out-Null
[System.IO.File]::WriteAllText($TempScript, $script, [System.Text.Encoding]::UTF8)
try {
  & $Python $TempScript $RunRoot
  if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
  }
} finally {
  Remove-Item -LiteralPath $TempScript -Force -ErrorAction SilentlyContinue
}
