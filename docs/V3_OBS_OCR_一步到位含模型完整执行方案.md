# V3 OBS-OCR 通用自动操作采集器执行方案

V3 是从旧四机复杂调度路线收敛出来的本地轻量闭环：用户手动打开目标软件或游戏并配置 OBS，系统负责截图、OCR、语言过滤、UI 模型候选、候选融合、安全门、observe_only 展示和受控动作评估。

## 核心原则

- OCR 是必要能力，但不是完整自动操作能力。
- UI 模型是必要能力，但模型只能输出候选、场景和风险，不能直接控制鼠标键盘。
- Safety Gate 优先级最高。
- 真实点击默认关闭，`observe_only=true` 默认开启。
- OBS 截图保存不能被 OCR 或模型推理阻塞。
- 模型权重、缓存、venv、截图和本地运行结果不得进入 Git。

## V3 第一版交付内容

- `/api/v3/*` Master API 路由。
- 本地 run store：`runs/v3/<run_id>/run.json`、`images.jsonl`、`events.jsonl`、`summary.json`。
- folder_watch 可用入口，OBS/window capture 安全骨架。
- mock OCR、PaddleOCR provider health、语言过滤、fastText optional health。
- mock UI model、ShowUI provider health、OmniParser license gate。
- OCR 候选、模型候选、候选融合。
- Safety Gate 与 observe_only action loop。
- V3 Web Console 页面。
- pytest 和 PowerShell smoke。

## 完整自动模式 Ready 条件

完整自动模式必须同时满足：

- OCR ready。
- language filter ready。
- UI model ready，通常是 ShowUI 或等价 UI 模型真实 inference smoke 通过。
- safety gate ready。
- coordinate mapper ready。
- observe_only 已人工检查通过。
- 用户明确启用 `enable_auto_click=true` 且 `observe_only=false`。

任一条件不满足时，系统只能运行 degraded / observe_only / OCR fallback。
