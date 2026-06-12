# P2：本地暂存、上传确认、清理流

## 目标

建立本地暂存、人工确认百度网盘上传、删除保护和清理后保留文件机制。

## 范围

- 本地暂存目录结构。
- upload_manifest.json 生成。
- upload_pending 状态。
- uploaded_confirmed 状态。
- local_deleted 状态。
- completed 状态。
- 删除本地图片和临时视频的保护条件。
- 清理审计日志。

## 核心规则

- capture_completed 后进入 upload_pending。
- 只有 capture_completed 后才能生成 upload_manifest.json；生成后进入 upload_pending。
- upload_manifest.json 记录 expected_upload_folder，不接真实百度网盘 API。
- P2.1 不删除 fixed、low、high、rejected、temp_video。
- 用户确认已上传百度网盘后，才能进入 uploaded_confirmed。
- P2.2 确认上传是用户声明，不接真实百度网盘 API。
- P2.2 确认上传后生成 upload_record.json，状态进入 uploaded_confirmed。
- uploaded_confirmed 只是允许后续删除，不代表已经删除。
- P2.2 不删除 fixed、low、high、rejected、temp_video。
- 正式上传清理状态流固定为 uploaded_confirmed -> local_deleted -> completed。
- 只有 uploaded_confirmed 后，才允许删除本地图片和临时视频，并记录 local_deleted。
- P2.3 只允许删除 fixed、low、high、rejected、temp_video。
- P2.3 清理后生成 cleanup_record.json，状态进入 local_deleted。
- P2.3 不进入 completed。
- 删除动作可以作为事件记录，但不能新增正式状态。
- 删除后必须保留 summary.json、meta.jsonl、upload_manifest.json、upload_record.json、run.log。

## 不做

- 不自动上传百度网盘。
- 不在用户确认前删除任何采集图片或临时视频。
- 不实现业务 Worker。

## 验收标准

- 未确认上传时删除动作被拒绝。
- 确认上传后仅删除允许删除的本地图片和临时视频。
- 保留文件完整存在。
