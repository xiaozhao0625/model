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
  "capture_completed is not completed",
  "upload_pending waits for manual Baidu Netdisk upload",
  "local_deleted means local heavy files were removed"
]) {
  assert(upload.includes(phrase), `missing lifecycle phrase ${phrase}`);
}

console.log("web_console_smoke_ok", requiredFiles.length);
