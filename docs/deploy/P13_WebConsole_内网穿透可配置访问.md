# P13 Web Console 内网穿透可配置访问

本说明用于让 Web Console 通过 natapp、frp、ngrok 等内网穿透域名访问，同时避免把具体域名写死到代码里。

## 访问结构

外部浏览器只访问当前 tunnel 域名：

```text
http://<current-tunnel-domain>
```

前端默认请求同域 `/api`，由 Vite dev server 代理到 M0 本机 Master API：

```text
Browser -> tunnel domain -> 192.168.1.18:5173 -> /api proxy -> http://127.0.0.1:8000
```

外部浏览器不需要也不应该直接访问：

```text
http://192.168.1.18:8000
http://localhost:8000
```

## 为什么不写死 tunnel 域名

natapp 免费域名可能会变化。域名写进代码后，每次更换都需要改代码、重新构建、提交。现在域名只放在本机 `.env.tunnel.local`，换域名只需要改配置并重启 Web Console。

## 首次配置

在 M0 执行：

```powershell
Set-Location E:\work\model\apps\web-console
Copy-Item .env.tunnel.example .env.tunnel.local
```

编辑 `apps/web-console/.env.tunnel.local`：

```env
WEB_CONSOLE_ALLOWED_HOSTS=你的当前域名,192.168.1.18,localhost
```

如果 tunnel 下页面能打开但 HMR websocket 报错，可以按需配置：

```env
WEB_CONSOLE_HMR_HOST=你的当前域名
WEB_CONSOLE_HMR_CLIENT_PORT=80
WEB_CONSOLE_HMR_PROTOCOL=ws
```

`.env.tunnel.local` 是本机文件，不提交 Git。

## 启动方式

```powershell
Set-Location E:\work\model\apps\web-console
npm run dev:tunnel -- --mode tunnel
```

默认端口是 `5173`。Master API 需要在 M0 本机 `127.0.0.1:8000` 可用。

## 换域名时怎么做

只修改：

```text
apps/web-console/.env.tunnel.local
```

把旧域名换成新域名：

```env
WEB_CONSOLE_ALLOWED_HOSTS=新的域名,192.168.1.18,localhost
```

如启用了 HMR 配置，也同步修改：

```env
WEB_CONSOLE_HMR_HOST=新的域名
```

然后重启 Web Console。不需要改代码。

## 验证

本机验证：

```powershell
Invoke-WebRequest http://127.0.0.1:8000/health -UseBasicParsing
Invoke-WebRequest http://127.0.0.1:5173 -UseBasicParsing
Invoke-WebRequest http://192.168.1.18:5173 -UseBasicParsing
Invoke-WebRequest http://127.0.0.1:5173/api/workers -UseBasicParsing
```

tunnel 域名验证：

```powershell
Invoke-WebRequest http://你的当前域名 -UseBasicParsing
Invoke-WebRequest http://你的当前域名/api/workers -UseBasicParsing
```

浏览器 DevTools Network 中，业务 API 应该访问当前域名下的 `/api/...`，不应出现 `localhost:8000` 或 `192.168.1.18:8000`。

## 常见问题

- 页面打不开：确认 natapp 映射到 `192.168.1.18:5173`，Web Console 使用 tunnel mode 启动。
- 显示 `Blocked request. This host is not allowed`：把当前域名加入 `WEB_CONSOLE_ALLOWED_HOSTS` 后重启。
- 页面能打开但数据失败：确认 Master API 本机 `http://127.0.0.1:8000/health` 正常，并检查 `/api/workers` 是否通过 Vite proxy 返回。
- HMR websocket 报错但页面和 API 正常：可先记录为 HMR warning；如需要热更新，再配置 `WEB_CONSOLE_HMR_*`。
- 不要设置 `allowedHosts: true`，这会扩大 DNS rebinding 风险。
