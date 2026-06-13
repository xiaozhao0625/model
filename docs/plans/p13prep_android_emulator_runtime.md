# P13-Prep：Android 模拟器 Runtime 与四机部署预备

## 目标

在不进入真实四机部署的前提下，补齐 Android 模拟器生产闭环前置能力和四机部署材料。

## Android Runtime

- AndroidEmulatorProfile 统一描述 emulator_type、adb_serial、app package/activity、截图、UI dump、OCR fallback 和 snapshot 策略。
- AdbRuntime 提供 `check_adb_available`、`list_devices`、`screencap`、`uiautomator_dump`、输入命令等边界。
- 无 adb 时返回 `unavailable/skipped`，默认 pytest 不依赖真实设备。
- Android 输入控制默认安全：文本输入 disabled，越界坐标 blocked，风险页面 request_manual/blocked。
- PermissionHandler 默认 `request_manual`。

## Deploy Prep

四机部署材料包含 topology、env 模板、Windows 启动脚本、机器健康检查脚本、软件下载清单、网络与故障排查文档。

本阶段只生成材料与检查脚本，不实际部署四台机器，不做并发压测。
