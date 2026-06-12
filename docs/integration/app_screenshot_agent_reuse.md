# app-screenshot-agent 复用边界

## 复用定位

app-screenshot-agent 是 Android Worker 和公共质量模块的重要复用基础，但不整体替代本平台架构。新平台仍然负责统一任务模型、桶规则、状态流转、上传确认、清理流、多类型 Worker 编排和审计。

## 可复用能力

- ADB 设备连接与基础操作。
- Android 截图采集流程。
- OCR 能力。
- 图片去重能力。
- 图片质量检测能力。
- Android 端状态管理经验。
- 失败重试和基础运行日志经验。

## 不直接复用为平台核心的部分

- 不直接使用 app-screenshot-agent 的整体任务架构替代新平台任务架构。
- 不直接使用其状态流替代本平台 capture_completed、upload_pending、uploaded_confirmed、local_deleted、completed 规则。
- 不直接绕过本平台 valid_total、桶规则、上传确认、删除保护规则。
- 不把 Android 端实现方式强行套用到 PC 游戏、浏览器或普通软件 Worker。

## 集成原则

- Android Worker 可以封装 app-screenshot-agent 的可复用能力。
- 公共质量模块可以复用其 OCR、去重、质量检测经验或实现。
- 所有复用能力必须服从本平台统一状态机和审计日志。
- 对 app-screenshot-agent 的复用必须保持边界清晰，避免形成隐性双架构。

## P1-P4 落地建议

- P1 定义平台统一接口和状态模型，不直接绑定 app-screenshot-agent。
- P2 上传确认和清理流由新平台统一实现。
- P3 模型网关不由 app-screenshot-agent 主导。
- P4 Android Worker 再接入 app-screenshot-agent 的可复用模块。
