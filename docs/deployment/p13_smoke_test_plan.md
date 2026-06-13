# P13 Smoke Test 计划

## M0 Smoke

1. 运行 `python scripts/master/smoke_postgres_connection.py`。
2. 检查 Redis。
3. 检查 Master API `/health`。
4. 检查 Web Console build/serve。
5. 检查 Model Gateway mock/fallback health。
6. 调用 production readiness API ingest/list。

## W1 PC Game Smoke

1. OBS health。
2. obs-websocket health。
3. FFmpeg health。
4. OBS source list。
5. short recording 或 source test。
6. FFmpeg extract frame。
7. high bucket test。
8. quality_report ingest to PostgreSQL。

## W2 PC App / Web Smoke

1. Playwright browser check。
2. Web page screenshot。
3. Browser content-only gate。
4. pywinauto availability。
5. mss/dxcam availability。
6. PC app/window capture dry-run。
7. low bucket test。
8. quality_report ingest to PostgreSQL。

## W3 Android Smoke

1. adb devices。
2. emulator profile load。
3. adb screencap。
4. uiautomator dump。
5. Android OCR fallback mock/disabled。
6. input default disabled/safe。
7. Android Worker dry-run。
8. android_runtime_snapshot ingest to PostgreSQL。

## 四机联动 Smoke

1. M0 启动 Master API / Web Console / PostgreSQL / Redis。
2. W1/W2/W3 启动 Worker。
3. Dashboard 确认 3 台 Worker online。
4. 创建 4 个小任务：Web、PC App、PC Game、Android。
5. 每个任务 `target_min=20` 或 `50`，`target_max=100`。
6. 每个任务进入 `capture_completed` 或明确 failed/unavailable。
7. 生成 quality_report / ocr_report / tool_health / diagnostics。
8. 写入 PostgreSQL。
9. Web Console 显示真实 API 数据，不只显示 mock fallback。
