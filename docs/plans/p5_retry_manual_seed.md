# P5: 补采机制与人工补种子

## 目标

建立补采、失败恢复、人工补种子和任务再运行机制，保证有效图片数量和场景覆盖质量。

P5 必须继续服从 P1-P4 已固化的 bucket、`valid_total`、状态流、上传确认和安全边界。

## P5.1 Coverage Manager

状态：done。

已完成内容：

- 新增 `CoverageReason`。
- 新增 `CoverageDecision`。
- 新增 `CoverageManager.evaluate()`。
- `CoverageManager` 复用 `CompletionGate.evaluate()`，不重复实现完成判定规则。
- 覆盖判断只给出是否达标、是否缺少主桶、是否需要继续采集、是否应该停止采集和建议状态。

P5.1 明确未实现：

- 不做 Retry Policy。
- 不做人工补种子。
- 不做 Worker 调度。
- 不修改 `LocalRunSession` 状态。
- 不生成上传或清理文件。
- 不新增正式 run 状态。

## 覆盖判断规则

- fixed 可选。
- low 或 high 至少出现一种。
- `valid_total = fixed + low + high`。
- rejected 不计入 `valid_total`。
- `valid_total >= target_min` 且存在 low/high，才算覆盖达标。
- `target_min` 默认 1000。
- `target_max` 默认 5000。
- `fixed_cap` 默认 10。
- fixed 超过 cap 判定为 `fixed_cap_exceeded`。
- `valid_total == target_max` 判定 `should_stop_capture=true`，reason 为 `target_max_reached`。
- `valid_total > target_max` 判定 `should_stop_capture=true`，reason 为 `target_max_exceeded`。
- 覆盖达标时建议状态为 `capture_completed`。
- 未达标但仍可继续采集时建议状态为 `running`。

## 后续范围

- valid_total 不足时的补采计划。
- 重复率或质量不足时的补采计划。
- 人工补种子入口。
- 补采审计。
- 补采后的状态回写。

## 禁止范围

- 不自动绕过登录安全验证。
- 不自动发送聊天内容。
- 不自动购买、充值或支付。
- 不新增 `cleanup_completed`、`completed_max` 等正式状态。
