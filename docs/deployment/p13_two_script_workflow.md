# P13 两脚本部署验收流程

## 第一类脚本：每台机器本地环境预检

M0/W1/W2/W3 各运行一次：

```powershell
.\scripts\deploy\p13\p13_env_preflight.ps1 -Role M0
.\scripts\deploy\p13\p13_env_preflight.ps1 -Role W1
.\scripts\deploy\p13\p13_env_preflight.ps1 -Role W2
.\scripts\deploy\p13\p13_env_preflight.ps1 -Role W3
```

每台机器会生成：

```text
preflight_report.json
preflight_summary.txt
diagnostics_{ROLE}_{timestamp}.zip
```

## 第二类脚本：M0 总控验收

只在 M0 运行：

```powershell
.\scripts\deploy\p13\p13_m0_overall_check.ps1
```

M0 会生成：

```text
overall_summary.json
overall_error_report.txt
p13_overall_diagnostics.zip
```

## 需要发给架构师

1. 每台机器的 `preflight_report.json`。
2. M0 的 `overall_summary.json`。
3. M0 的 `overall_error_report.txt`。
4. `p13_overall_diagnostics.zip`。

## 禁止事项

- 不提交 `.env`。
- 不发送数据库密码。
- 不发送安装包或模型权重。
- 不让 Worker 直连数据库。
