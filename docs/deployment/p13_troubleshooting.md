# P13 故障排查预备

## 常见问题

- Master API 不可达：检查 `MASTER_URL`、防火墙和端口。
- Worker 无真实工具：检查对应 `check_worker_ready.py` 输出，缺失工具应显示 `unavailable` 而不是失败。
- Android 无设备：`smoke_android_emulator_runtime.py` 应输出 `skipped_reason=adb_unavailable` 或 `no_devices`。
- OCR 不可用：默认 disabled/mock，PaddleOCR/EasyOCR 缺失不影响 pytest。

## 边界

排查脚本只检查和输出 JSON，不启动真实采集、不执行危险动作。
