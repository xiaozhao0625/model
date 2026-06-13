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

## P5.2 Retry Policy

状态：done。

已完成内容：

- 新增 `RetryAction`。
- 新增 `RetryReason`。
- 新增 `RetryState`。
- 新增 `RetryDecision`。
- 新增 `RetryPolicy.evaluate()`。
- `RetryPolicy` 复用 `CoverageManager.evaluate()`，不重复实现 `CompletionGate`。
- 策略层只决定是否继续自动补采、是否切换策略、是否请求人工补种子、是否标记 `failed_low_yield`。

P5.2 明确未实现：

- 不执行任何补采动作。
- 不调 Worker。
- 不修改 `LocalRunSession` 状态。
- 不做人工补种子流程。
- 不写任何运行文件。
- 不新增 `retrying`、`completed_max`、`cleanup_completed` 等正式状态。

## Retry Policy 判断规则

- 覆盖已达标：`action=none`，建议状态 `capture_completed`。
- 未达 `target_min` 且自动轮次未耗尽：`action=continue_capture`，建议状态 `running`。
- 缺少 low/high 主桶且自动轮次未耗尽：`action=switch_strategy`，建议状态 `running`。
- 自动轮次耗尽且仍未达标：`action=request_manual_seed`，建议状态 `needs_manual_seed`。
- fixed 超过 cap：`action=fail_low_yield`，建议状态 `failed_low_yield`。
- 达到 `target_max` 且已达标：`action=none`，建议状态 `capture_completed`。
- 超过 `target_max`：`action=fail_low_yield`，建议状态 `failed_low_yield`。

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

- P5 已完成人工补种子入口、审计记录和状态回写。
- 后续 P12 才进入行为包自我深化，不在 P5 执行真实补采。
- 后续真实 Worker 调度仍需等待架构师指令。

## P5-Complete Manual Seed Gate

状态：done。

已完成内容：

- 新增 `ManualSeedRecord`。
- 新增 `ManualSeedGate.request_manual_seed()`。
- 新增 `ManualSeedGate.resume_after_manual_seed()`。
- `running -> needs_manual_seed` 必须通过 `RunLifecycle`。
- `needs_manual_seed -> running` 必须通过 `RunLifecycle`。
- 写入 `manual_seed_record.jsonl`，事件包含 `manual_seed_requested` 和 `manual_seed_completed`。
- `LocalRunSession` 增加 `request_manual_seed()` 和 `resume_after_manual_seed()`，并写入 `run.log`。

Manual Seed Gate 明确不做：

- 不执行真实补采动作。
- 不调用 Worker。
- 不保存截图。
- 不修改 fixed、low、high、rejected 计数。
- 不生成 `upload_manifest.json`。
- 不进入 `upload_pending`、`uploaded_confirmed`、`local_deleted`、`completed`。

## P5-Complete failed_low_yield 收口

状态：done。

已完成内容：

- `LocalRunSession.mark_failed_low_yield()` 仅允许 `running -> failed_low_yield`。
- 状态推进必须通过 `RunLifecycle`。
- `failed_low_yield` 表示多轮补采或人工补种子后仍不足目标数量。
- 写入 `run.log` 事件 `failed_low_yield`。
- `failed_low_yield` 是终止态，不进入 `completed`。

## P5 dry-run 总验收

状态：done。

已完成内容：

- 新增 `scripts/dev/mock_p5_recovery_run.py`。
- 场景 A `manual_seed_success`：retry 耗尽后进入 `needs_manual_seed`，人工补种子恢复到 `running`，随后达到 `target_min` 并进入 `capture_completed`。
- 场景 B `failed_low_yield`：retry 耗尽后进入人工补种子流程，仍不足目标数量后进入 `failed_low_yield`。
- dry-run 不生成 `upload_manifest.json`。
- dry-run 不进入 `upload_pending`、`uploaded_confirmed`、`local_deleted`、`completed`。

## 禁止范围

- 不自动绕过登录安全验证。
- 不自动发送聊天内容。
- 不自动购买、充值或支付。
- 不新增 `cleanup_completed`、`completed_max` 等正式状态。
