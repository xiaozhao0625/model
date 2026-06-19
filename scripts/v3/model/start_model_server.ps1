param(
  [int]$Port = 8010
)

$ErrorActionPreference = "Stop"
python -m uvicorn ai_screenshot_platform.v3.model.inference_server:create_v3_model_server --factory --host 127.0.0.1 --port $Port
