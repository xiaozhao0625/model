# P1：MVP 基础框架

## 目标

建立平台最小可运行基础框架，固化任务配置、桶规则、状态流转、元数据文件和 Worker 抽象。
P1 的可运行闭环只推进到 capture_completed；upload_pending、uploaded_confirmed、local_deleted、completed 由 P2 上传确认与清理流处理。

## 范围

- 任务配置 schema。
- fixed、low、high 桶规则校验。
- valid_total 上下限校验。
- 基础状态机。
- summary.json、meta.jsonl、run.log 写入约定。
- 本地 dry-run 验收脚本。
- 最小测试覆盖。

## 不做

- 不接模型。
- 不实现真实 Worker 自动化。
- 不接百度网盘上传。
- 不删除本地图片或临时视频。
- 不改 UI。
- 不生成 upload_manifest.json。
- 不进入 upload_pending。

## 验收标准

- fixed 可选，low 或 high 至少一个。
- valid_total >= 1000 才允许 capture_completed。
- valid_total <= 5000。
- P1 达标后最多进入 capture_completed，且 capture_completed 不等于 completed。
- P1 dry-run 不生成 upload_manifest.json。
- P1 dry-run 能生成 summary.json、meta.jsonl、run.log。
- 核心规则有测试。

## P1 收口结果

- P1.1 已实现核心领域模型与完成判定 Gate。
- P1.2 已实现本地分桶存储、meta.jsonl、summary.json。
- P1.3 已实现 run 内 sha256 content_hash 精确去重。
- P1.4 已实现从 meta.jsonl 恢复计数、编号和去重索引。
- P1.5 已实现 Run 生命周期状态机。
- P1.5.1 已统一正式 RunStatus 命名。
- P1.6 已实现 LocalRunSession 与 JSONL run.log。
- P1.7 已实现本地 mock dry-run 验收脚本。
