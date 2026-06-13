import { readFileSync, existsSync } from "node:fs";
import { join } from "node:path";

const root = new URL("..", import.meta.url);
const read = (path) => readFileSync(new URL(path, root), "utf8");
const assert = (condition, message) => {
  if (!condition) {
    throw new Error(message);
  }
};

const requiredFiles = [
  "src/app.tsx",
  "src/lib/api-client.ts",
  "src/lib/mock-data.ts",
  "src/routes/dashboard.tsx",
  "src/routes/apps.tsx",
  "src/routes/runs.tsx",
  "src/routes/run-detail.tsx",
  "src/routes/workers.tsx",
  "src/routes/upload.tsx",
  "src/routes/model-gateway.tsx",
  "src/routes/settings.tsx"
];

for (const file of requiredFiles) {
  assert(existsSync(new URL(file, root)), `missing ${file}`);
}

const app = read("src/app.tsx");
for (const route of ["/", "/apps", "/runs", "/runs/:runId", "/workers", "/upload", "/model-gateway", "/settings"]) {
  assert(app.includes(route), `missing route ${route}`);
}

const apiClient = read("src/lib/api-client.ts");
for (const apiName of [
  "getHealth",
  "listApps",
  "createApp",
  "listRuns",
  "createRun",
  "getRun",
  "startRun",
  "getRunSummary",
  "listWorkers",
  "registerWorker",
  "heartbeatWorker",
  "generateUploadManifest",
  "confirmUpload",
  "cleanupLocal",
  "finalizeRun",
  "sceneClassify",
  "ground",
  "act"
]) {
  assert(apiClient.includes(apiName), `missing api client method ${apiName}`);
}

assert(apiClient.includes("/api/runs/${runId}/upload-manifest"), "upload manifest must use run-scoped canonical route");
assert(apiClient.includes("mock fallback"), "api client should document mock fallback");

const mockData = read("src/lib/mock-data.ts");
for (const status of [
  "running",
  "capture_completed",
  "upload_pending",
  "uploaded_confirmed",
  "local_deleted",
  "completed",
  "needs_manual_seed",
  "failed_low_yield",
  "skipped_risk"
]) {
  assert(mockData.includes(status), `missing mock status ${status}`);
}

const workers = read("src/routes/workers.tsx");
assert(workers.includes("content_area_only=true"), "workers page must show web content_area_only rule");

const upload = `${read("src/routes/upload.tsx")}\n${read("src/components/upload/upload-flow-panel.tsx")}`;
for (const phrase of [
  "capture_completed 不等于 completed",
  "upload_pending 表示等待人工上传百度网盘",
  "local_deleted 表示本地大文件已清理"
]) {
  assert(upload.includes(phrase), `missing lifecycle phrase ${phrase}`);
}

const status = read("src/lib/status.ts");
for (const label of ["待处理", "启动中", "运行中", "采集完成", "待上传", "已确认上传", "本地已清理", "已完成", "需要人工补种子"]) {
  assert(status.includes(label), `missing chinese status label ${label}`);
}
for (const label of ["固定页", "低频", "高频", "已拒绝", "PC 游戏 Worker", "Web Worker", "生成上传清单", "确认已上传"]) {
  assert(status.includes(label), `missing chinese display label ${label}`);
}

const visibleSources = [
  read("index.html"),
  read("src/components/layout/sidebar.tsx"),
  read("src/components/layout/topbar.tsx"),
  read("src/components/layout/app-shell.tsx"),
  read("src/routes/dashboard.tsx"),
  read("src/routes/apps.tsx"),
  read("src/routes/runs.tsx"),
  read("src/routes/run-detail.tsx"),
  read("src/routes/workers.tsx"),
  read("src/routes/upload.tsx"),
  read("src/routes/model-gateway.tsx"),
  read("src/routes/settings.tsx"),
  read("src/components/runs/run-actions.tsx"),
  read("src/components/upload/cleanup-danger-zone.tsx"),
  status
].join("\n");

for (const label of ["系统控制中心", "应用库", "任务控制中心", "任务详情", "Worker 监控", "上传与清理", "模型网关", "系统设置"]) {
  assert(visibleSources.includes(label), `missing chinese page label ${label}`);
}
for (const label of ["新建应用", "启动", "人工补种子", "生成上传清单", "确认已上传", "清理本地", "完成任务", "查看详情"]) {
  assert(visibleSources.includes(label), `missing chinese action label ${label}`);
}

console.log("web_console_smoke_ok", requiredFiles.length);
