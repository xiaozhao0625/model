# P2：本地暂存、上传确认、清理流

## 目标

建立本地暂存、人工确认百度网盘上传、删除保护、清理审计、最终 completed 收口和本地状态恢复能力。

## 范围

- upload_manifest.json 生成。
- upload_pending 状态推进。
- upload_record.json 生成。
- uploaded_confirmed 状态推进。
- local_deleted 安全清理。
- cleanup_record.json 生成。
- completed 最终收口。
- P2 全流程 dry-run 验收脚本。
- 基于本地轻量记录文件的 run 状态恢复。

## 核心规则

- 不新增正式状态。
- capture_completed 不等于 completed。
- upload_pending 不等于 completed。
- uploaded_confirmed 不等于 completed。
- completed 只能表示完整上传清理流程已结束。
- 只有 capture_completed 后才能生成 upload_manifest.json。
- 生成 upload_manifest.json 后，状态进入 upload_pending。
- upload_pending 表示等待用户手动上传百度网盘。
- 确认上传是用户声明，不接真实百度网盘 API。
- 必须先存在 upload_manifest.json，才能确认上传。
- 用户确认上传后，状态进入 uploaded_confirmed，并生成 upload_record.json。
- uploaded_confirmed 只是允许后续删除，不代表已经删除。
- 只有 uploaded_confirmed 状态才允许本地清理。
- 本地清理必须存在 upload_manifest.json 和 upload_record.json。
- upload_record.json 中 delete_allowed 必须为 true。
- 清理只允许删除 fixed/、low/、high/、rejected/、temp_video/。
- 清理后必须保留 summary.json、meta.jsonl、upload_manifest.json、upload_record.json、cleanup_record.json、run.log。
- 清理完成后状态进入 local_deleted。
- completed 只能在 local_deleted 后进入。
- 正式 P2 状态流固定为：running -> capture_completed -> upload_pending -> uploaded_confirmed -> local_deleted -> completed。
- 删除动作可以作为事件记录，但不能新增正式状态。
- 本地状态恢复必须依赖已有轻量记录文件。
- 本地状态恢复不删除任何文件。
- 本地状态恢复不生成新的上传或清理记录。

## P2.1 upload_manifest.json

- 从 summary.json 读取统计。
- manifest 统计必须与 summary.json 一致。
- manifest 记录 expected_upload_folder。
- manifest 记录 file_count 和 total_bytes。
- 生成 manifest 后进入 upload_pending。
- 不删除任何目录或文件。

## P2.2 upload_record.json

- 只有 upload_pending 状态允许确认上传。
- 确认后生成 upload_record.json。
- actual_upload_folder 未传时默认等于 expected_upload_folder。
- delete_allowed 固定为 true。
- 确认后进入 uploaded_confirmed。
- 写入 run.log 事件 upload_confirmed。
- 不删除任何目录或文件。

## P2.3 local_deleted 清理

- 只有 uploaded_confirmed 状态允许清理。
- 只删除 fixed/、low/、high/、rejected/、temp_video/。
- 删除前统计 deleted_file_count 和 deleted_total_bytes。
- 生成 cleanup_record.json。
- 清理后进入 local_deleted。
- 写入 run.log 事件 local_deleted。
- 不进入 completed。
- 重复清理保持幂等。

## P2.4 completed 收口

- LocalRunSession.finalize_completed() 只能从 local_deleted 执行。
- finalize_completed() 使用 RunLifecycle 推进 local_deleted -> completed。
- 非 local_deleted 状态调用 finalize_completed() 必须失败。
- 写入 run.log 事件 completed。
- 新增 scripts/dev/mock_upload_cleanup_run.py。
- dry-run 覆盖 running -> capture_completed -> upload_pending -> uploaded_confirmed -> local_deleted -> completed。
- dry-run 不生成真实上传行为。
- dry-run 不删除保留文件。

## P2.5 本地状态恢复

- RunStatusResolver.resolve(run_dir) 只读取本地 run 目录已有轻量记录文件。
- 恢复优先级固定为：run.log completed 事件 -> cleanup_record.json -> upload_record.json -> upload_manifest.json -> summary.json 达标 -> running。
- run.log 解析失败时必须抛出明确异常。
- summary.json 缺失时不报错，恢复为 running。
- LocalRunSession.restore_status() 使用 RunStatusResolver 恢复当前状态。
- 不新增 cleanup_completed。
- 不新增 completed_max。
- 不生成新的 upload_manifest.json、upload_record.json 或 cleanup_record.json。
- 不删除任何文件。

## 不做

- 不自动上传百度网盘。
- 不接真实百度网盘 API。
- 不在用户确认前删除任何采集图片或临时视频。
- 不实现 FastAPI。
- 不实现 UI。
- 不接数据库。
- 不实现 Worker。
- 不接模型。
- 不接 OBS、ADB、OCR、pHash/dHash。

## 验收标准

- 未 capture_completed 时不能生成 upload_manifest.json。
- 未 upload_pending 时不能确认上传。
- 未 uploaded_confirmed 时不能本地清理。
- 未 local_deleted 时不能进入 completed。
- 清理只删除允许删除的目录。
- 保留文件完整存在。
- run.log 包含 session_started、image_saved、duplicate_rejected、capture_completed、upload_confirmed、local_deleted、completed。
- P2 dry-run 最终状态为 completed。
- 本地状态恢复按固定优先级返回最高状态。
- 非法 run.log JSON 行会抛出明确异常。
