# P13 网络与防火墙检查

## 检查项

- M0 Master API 端口对 W1/W2/W3 可达。
- Web Console 可访问 Master API。
- 数据库与 Redis 仅对可信机器开放。
- Worker 使用 `MASTER_URL` 连接 M0。

## 当前阶段边界

P12.5-P13Prep 不要求四台机器在线，不做真实分布式压测。
