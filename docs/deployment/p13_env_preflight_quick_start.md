# P13 环境预检助手快速开始

## 用途

每台机器本地运行一次，告诉用户缺什么软件、去哪里下载、装完后怎么验证，并生成本地报告和 diagnostics zip。

## 命令

```powershell
.\scripts\deploy\p13\p13_env_preflight.ps1 -Role M0
.\scripts\deploy\p13\p13_env_preflight.ps1 -Role W1
.\scripts\deploy\p13\p13_env_preflight.ps1 -Role W2
.\scripts\deploy\p13\p13_env_preflight.ps1 -Role W3
```

## 可选上传

```powershell
.\scripts\deploy\p13\p13_env_preflight.ps1 -Role W2 -MasterUrl http://192.168.1.18:8000 -UploadReport
```

Master API 不可用时，报告仍保留在本地，稍后可重新上传。

## 输出

```text
runs/p13_preflight/{ROLE}/preflight_report.json
runs/p13_preflight/{ROLE}/preflight_summary.txt
runs/p13_preflight/{ROLE}/diagnostics_{ROLE}_{timestamp}.zip
```

## 安全边界

- 不下载软件。
- 不安装软件。
- 不修改 PATH。
- 不打印 `.env` 内容。
- 不打印数据库密码。
- 不远程执行其它机器命令。
