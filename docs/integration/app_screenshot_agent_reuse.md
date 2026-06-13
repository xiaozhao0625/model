# app-screenshot-agent 复用边界

## 复用定位

app-screenshot-agent 是 Android Worker 和公共质量模块的重要复用来源，但不整体替代新平台架构。

新平台仍负责统一任务模型、bucket 规则、`valid_total` 规则、状态流转、上传确认、清理流、多类型 Worker 编排和审计日志。

## P4.6 复用映射

| app-screenshot-agent 能力 | 新平台边界 |
| --- | --- |
| ADB 控制 | `AndroidDeviceAdapter` |
| OCR Adapter | 后续 `common/ocr` |
| UIAutomator 解析 | `AndroidUiObserverAdapter` |
| QualityChecker | `AndroidQualityAdapter` |
| DuplicateChecker | 已由 `common/quality/dedup` 承接 |
| StateManager | 已由 `LocalRunSession` / `meta.jsonl` 恢复承接 |
| ScreenshotManager | 已由 `BucketedScreenshotStore` 承接 |

## 可复用能力

- ADB 设备连接与基础操作经验。
- Android 截图采集流程经验。
- OCR 能力和文本检测经验。
- 图片质量检测经验。
- Android UIAutomator 解析经验。
- Android 端状态管理经验。
- 失败重试和基础运行日志经验。

## 不直接复用为平台核心的部分

- 不直接使用 app-screenshot-agent 的整体任务架构替代新平台任务架构。
- 不直接使用 app-screenshot-agent 的状态流替代本平台 `capture_completed`、`upload_pending`、`uploaded_confirmed`、`local_deleted`、`completed` 规则。
- 不绕过本平台 `valid_total`、bucket、上传确认、删除保护规则。
- 不把 Android 端实现方式强行套用到 PC 游戏、浏览器或普通软件 Worker。
- 不复制整个 app-screenshot-agent 仓库作为新平台核心。

## P4.6 当前边界

- 只建立 Android Worker 合同、复用映射、stub adapter 和 stub pipeline。
- 不接真实 ADB、Airtest、Appium、模拟器或 OCR。
- 不执行 `subprocess adb`。
- Android 普通 App 默认进入 `low` 桶。
- Android pipeline 必须复用 `LocalRunSession`。
- P4.6 最多推进到 `capture_completed`，不进入上传确认、清理或 `completed`。

## 后续集成原则

- Android Worker 可以封装 app-screenshot-agent 中可复用的 ADB、UIAutomator、OCR、质量检测经验。
- 公共质量模块可以复用其 OCR、去重、质量检测经验或实现，但必须落入新平台 common 边界。
- 所有复用能力必须服从新平台统一状态机、审计日志和本地暂存/上传确认/删除保护规则。
- 对 app-screenshot-agent 的复用必须保持边界清晰，避免形成隐性双架构。
