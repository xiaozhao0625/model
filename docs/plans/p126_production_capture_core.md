# P12.6：生产采集核心补齐

## 目标

P12.6 建立生产采集前的规则核心：Runtime Profiler、Scene Classifier、Capture Engine、Action Gateway 和内容驱动器。

## 模块

- Runtime Profiler：根据 platform、worker、app_type 输出运行画像和推荐 bucket。
- Scene Classifier：综合 metadata 与 OCR scene hints 输出 scene_class。
- Capture Engine：根据 scene、quality、profile 自动决定 `fixed`、`low`、`high`、`rejected`。
- Action Gateway：真实动作执行前的安全门，拦截文本风险、risk_flags 和 OCR 风险。
- Content Drivers：Web / PC App 内容变化计划，只产出安全动作计划，不执行真实操作。

## 边界

- 不执行真实鼠标键盘动作。
- 不接真实 Worker 调度。
- 不改变 P1-P12 状态语义。
- 不新增正式 RunStatus。
