# P13 启动顺序

## 单机启动前检查

1. 每台机器确认仓库代码版本一致。
2. 每台机器确认 `.env` 已从 example 模板复制并填写。
3. 每台机器运行对应 health check。
4. 确认防火墙允许 Worker 访问 M0 Master API 端口。

## 推荐启动顺序

1. M0：启动 PostgreSQL。
2. M0：启动 Redis。
3. M0：运行 PostgreSQL smoke。
4. M0：启动 Master API。
5. M0：启动 Web Console。
6. W1：启动 PC Game Worker。
7. W2：启动 PC App / Web Worker。
8. W3：启动 Android Worker。
9. Web Console：确认 W1/W2/W3 online。
10. 执行四机联动 smoke。

## 停止顺序

1. 停止 W1/W2/W3 Worker。
2. 停止 Web Console。
3. 停止 Master API。
4. 停止 Redis。
5. 停止 PostgreSQL。

## 注意

上传清理流仍然必须先由用户确认已上传百度网盘，才允许删除本地图片和临时视频。
