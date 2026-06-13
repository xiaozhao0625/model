# P13 .env 配置模板说明

## 安全原则

- 不提交 `.env`。
- 不在文档中写真实密码。
- 不打印完整 `DATABASE_URL`。
- Worker 不配置数据库连接串，只配置 `MASTER_URL`。

## M0 必填

```text
DATABASE_URL=postgresql+psycopg://screenshot_app:<password>@127.0.0.1:5432/ai_screenshot_platform
REDIS_URL=redis://127.0.0.1:6379/0
MASTER_HOST=0.0.0.0
MASTER_PORT=8000
WEB_CONSOLE_PORT=5173
MODEL_GATEWAY_MODE=mock
PSQL_PATH=D:\work\pgsql\bin\psql.exe
```

## W1 / W2 / W3 必填

```text
MASTER_URL=http://<M0_LAN_IP>:8000
WORKER_ID=<unique_worker_id>
WORKER_TYPE=<pc_game|pc_app_web|android>
MACHINE_NAME=<M0|W1|W2|W3>
CAPABILITIES=<comma_separated_capabilities>
LOCAL_CAPTURE_ROOT=<local_run_root>
```

## W3 Android 额外项

```text
ADB_SERIAL=<android_device_serial>
ANDROID_PROFILE_ID=<profile_id>
```

## Web Console 判断真实 API

Web Console 如果显示 mock fallback，需要检查：

1. M0 Master API 是否可访问。
2. `VITE_MASTER_API_URL` 是否指向 M0。
3. 浏览器控制台是否有跨域或网络错误。
4. production readiness API 是否有真实写入数据。
