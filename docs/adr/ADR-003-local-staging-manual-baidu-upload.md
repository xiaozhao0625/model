# ADR-003：本地暂存与人工确认百度网盘上传

## 状态

Accepted

## 背景

采集数据量较大，图片和临时视频删除不可逆。为避免误删，平台必须把上传确认和本地清理解耦。

## 决策

- 本地只暂存采集图片和临时视频。
- capture_completed 后进入 upload_pending。
- 用户确认已上传百度网盘后，才能进入 uploaded_confirmed。
- 只有 uploaded_confirmed 后，才允许删除本地图片和临时视频，并记录 local_deleted。
- 正式上传清理状态流固定为 uploaded_confirmed -> local_deleted -> completed。
- 删除动作可以作为事件记录，但不能新增正式状态。
- 删除后必须保留 summary.json、meta.jsonl、upload_manifest.json、run.log。

## 影响

- P2 必须实现删除保护。
- 不允许自动上传确认。
- upload_manifest.json 是清理和审计的重要依据。
