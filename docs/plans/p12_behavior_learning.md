# P12：行为包自我深化引擎

## 目标

P12 建立离线行为包学习与建议引擎，读取 P1-P11 已产生的轻量审计产物，分析行为包在 run 中的覆盖、重复、卡住、低产、人工补种子和失败特征，生成可审查、可回滚的候选行为包。

## 输入

- `summary.json`
- `meta.jsonl`
- `run.log`
- `behavior_actions.jsonl`
- `manual_seed_record.jsonl`
- `upload_manifest.json`、`upload_record.json`、`cleanup_record.json`
- `model_gateway.log`
- Worker report 或 `failed_low_yield` 相关记录

读取历史 run 产物时必须保持只读，不允许修改原始 `run.log`、`summary.json`、`meta.jsonl` 或行为包执行记录。

## 输出

P12 输出写入独立目录 `behavior_learning/{app_id}/{run_id}/`，至少包含：

- `metrics.json`
- `analysis.json`
- `recommendation.json`
- `candidate_pack.json`
- `review_record.jsonl`
- `rollback_record.jsonl`

候选行为包默认状态为 `pending_review`，不得自动启用。

## 核心规则

- 仅做离线分析、指标计算、规则建议、候选包生成、人工审核和回滚记录。
- 不训练模型，不下载模型，不要求 GPU。
- 不接真实 OBS、FFmpeg、ADB、Playwright、pywinauto 或输入控制工具。
- 不执行真实鼠标、键盘或设备动作。
- 不新增正式 `RunStatus`。
- 行为包变更必须可审计、可人工批准、可拒绝、可回滚。
- `approved` 后才允许进入启用流程；`rejected` 不允许启用。

## FPS 分析

- 重复截图比例过高。
- 有效产出低。
- 卡住动作比例过高。
- 死亡或复活循环过高。
- 战斗覆盖不足。

## MOBA 分析

- 泉水或基地卡住。
- 对线覆盖不足。
- 商店停留过久。
- 技能使用不足。
- 团战画面不足。
- 镜头丢失。

## 验收标准

- 可从离线 run 产物生成指标、分析、建议和候选行为包。
- 候选包默认 `pending_review`。
- review/rollback 均写 JSONL 审计记录。
- dry-run 不修改原始 run 产物。
- 全量 pytest 通过。
