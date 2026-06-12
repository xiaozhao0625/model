# ADR-001：截图桶规则

## 状态

Accepted

## 背景

平台需要统一不同应用、软件、Android 和 PC 游戏的截图采集结果。若桶类型过多，会增加调度、质量统计、补采和上传清理复杂度。

## 决策

- 截图桶只有 fixed、low、high。
- fixed 可选。
- low 或 high 至少出现一种；换言之，low 或 high 至少一种。
- valid_total 必须 >= 1000 才能进入 capture_completed。
- valid_total 必须 <= 5000。

## 影响

- 后续配置、状态机、补采和质量统计必须基于这三类桶实现。
- P1 必须先实现桶规则测试。
- 任何新增桶类型都需要新的 ADR。
