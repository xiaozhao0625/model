# 架构实现基线

## 项目定位

本平台面向多类型应用和游戏的自动截图采集。平台需要统一任务状态、截图桶规则、质量检测、去重、本地暂存、上传确认、清理流、Worker 编排和审计日志。

## 能力边界

- 优先使用开源工具和开源模型。
- 不依赖闭源 Computer Use API 作为核心能力。
- AI 只做低频决策，包括启动、场景判断、按钮定位、卡住恢复等。
- 高频动作由稳定自动化、行为包、OBS/FFmpeg 抽帧、ADB、Playwright、pywinauto 等机制承担。

## 截图桶规则

- 支持 fixed、low、high 三类桶。
- fixed 可选。
- low 或 high 至少出现一种；换言之，low 或 high 至少一种。
- valid_total 必须 >= 1000 才能进入 capture_completed。
- valid_total 必须 <= 5000。
- fixed 桶用于固定位置或固定流程采样。
- low 桶用于低频、低成本、稳定自动化采样。
- high 桶用于高频或连续画面采样。

## 状态流转基线

```text
created
  -> capture_running
  -> capture_completed
  -> upload_pending
  -> uploaded_confirmed
  -> local_deleted
  -> completed
```

约束：

- valid_total < 1000 时不得进入 capture_completed。
- valid_total > 5000 时必须停止继续采集并进入异常处理或截断策略。
- capture_completed 后进入 upload_pending。
- 用户确认已上传百度网盘后，才能进入 uploaded_confirmed。
- 只有 uploaded_confirmed 后，才允许删除本地图片和临时视频，并记录 local_deleted。
- 正式上传清理状态流固定为 uploaded_confirmed -> local_deleted -> completed。
- 删除动作可以作为事件记录，但不能新增正式状态。
- 删除后必须保留 summary.json、meta.jsonl、upload_manifest.json、run.log。

## Worker 基线

- 浏览器 Worker 优先使用 Playwright。
- 普通软件 Worker 优先使用 pywinauto 等稳定自动化。
- Android Worker 优先复用 app-screenshot-agent 的 ADB、OCR、去重、质量检测、状态管理能力。
- PC 游戏 high 桶必须使用行为包 + OBS/FFmpeg 抽帧。
- PC 游戏 high 桶不得依赖 AI 逐帧决策。

## 安全边界

不允许自动处理以下场景：

- 验证码
- 支付
- 充值
- 购买
- 聊天发送
- 账号安全验证
- 反作弊绕过

遇到以上场景时，Worker 必须停止相关动作并记录需要人工处理。
