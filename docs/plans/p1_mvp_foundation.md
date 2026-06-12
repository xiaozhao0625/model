# P1：MVP 基础框架

## 目标

建立平台最小可运行基础框架，固化任务配置、桶规则、状态流转、元数据文件和 Worker 抽象。

## 范围

- 任务配置 schema。
- fixed、low、high 桶规则校验。
- valid_total 上下限校验。
- 基础状态机。
- summary.json、meta.jsonl、run.log 写入约定。
- Worker 抽象接口。
- 最小测试覆盖。

## 不做

- 不接模型。
- 不实现真实 Worker 自动化。
- 不接百度网盘上传。
- 不删除本地图片或临时视频。
- 不改 UI。

## 验收标准

- fixed 可选，low 或 high 至少一个。
- valid_total >= 1000 才允许 capture_completed。
- valid_total <= 5000。
- capture_completed 后只能进入 upload_pending。
- 核心规则有测试。

