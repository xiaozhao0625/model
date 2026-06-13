# P13 M0 总控验收脚本快速开始

## 用途

只在 M0 运行，用于汇总四机环境预检报告、Master API、PostgreSQL、Worker 注册、tool health、diagnostics 和 smoke 状态。

M0 总控脚本不会远程执行 W1/W2/W3 命令，也不需要 WinRM/SSH。

## 命令

```powershell
.\scripts\deploy\p13\p13_m0_overall_check.ps1
```

无真实网络环境时可以先运行：

```powershell
.\scripts\deploy\p13\p13_m0_overall_check.ps1 -SkipNetwork -SkipSmoke
```

## 输出

```text
runs/p13_overall/overall_summary.json
runs/p13_overall/overall_error_report.txt
runs/p13_overall/p13_overall_diagnostics.zip
```

## 结果解释

- `status=ok`：当前可进入下一步 smoke 或验收。
- `status=warning`：存在未完成项，但不是硬阻塞。
- `status=failed`：存在阻塞项，需要先处理。

如果 W1/W2/W3 没有报告，脚本会提示在对应机器运行 `p13_env_preflight.ps1` 或启动 Worker。
