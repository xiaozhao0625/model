# W3 Android Worker 部署步骤

## 目标

W3 承载 Android Worker。Android 普通 App 默认进入 low 桶。app-screenshot-agent 只作为复用来源，不替代新平台架构。

## 手动准备

1. 安装 Python、Git、NVIDIA Driver。
2. 安装 Android SDK Platform-Tools。
3. 安装 Android Studio / Emulator 或指定模拟器。
4. 确认 `adb devices` 可识别设备或模拟器。
5. 克隆项目仓库。
6. 复制 `configs/deploy/w3_android_worker.production.env.example` 为本机 `.env`。

## 环境重点

```text
MASTER_URL=http://<M0_LAN_IP>:8000
WORKER_ID=W3-ANDROID
WORKER_TYPE=android
CAPABILITIES=capture_low,adb
LOCAL_CAPTURE_ROOT=D:\runs\w3
ADB_SERIAL=<android_device_serial>
ANDROID_PROFILE_ID=<profile_id>
```

## 启动

```powershell
scripts\deploy\p13\start_w3_android_worker.bat
```

## 健康检查

```powershell
python scripts/deploy/p13/check_w3_android_stack.py --master-url http://<M0_LAN_IP>:8000
```

## Smoke

1. 运行 `adb devices`。
2. 检查模拟器或真机 profile。
3. 执行 adb screencap。
4. 执行 uiautomator dump。
5. OCR fallback 默认 mock/disabled。
6. 输入动作默认 disabled/safe。
7. 写入 android_runtime_snapshot / diagnostics。
