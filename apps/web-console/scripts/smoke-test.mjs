import { existsSync, readFileSync } from "node:fs";

const root = new URL("..", import.meta.url);
const read = (path) => readFileSync(new URL(path, root), "utf8");
const assert = (condition, message) => {
  if (!condition) {
    throw new Error(message);
  }
};

const requiredFiles = [
  "src/app.tsx",
  "src/lib/theme.ts",
  "src/lib/api-client.ts",
  "src/lib/mock-data.ts",
  "src/routes/dashboard.tsx",
  "src/routes/apps.tsx",
  "src/routes/runs.tsx",
  "src/routes/run-detail.tsx",
  "src/routes/workers.tsx",
  "src/routes/upload.tsx",
  "src/routes/model-gateway.tsx",
  "src/routes/quality-reports.tsx",
  "src/routes/ocr-status.tsx",
  "src/routes/behavior-candidates.tsx",
  "src/routes/tool-health.tsx",
  "src/routes/settings.tsx",
  "src/components/layout/theme-toggle.tsx"
];

for (const file of requiredFiles) {
  assert(existsSync(new URL(file, root)), `missing ${file}`);
}

const app = read("src/app.tsx");
for (const route of [
  "/",
  "/apps",
  "/runs",
  "/runs/:runId",
  "/workers",
  "/upload",
  "/model-gateway",
  "/quality-reports",
  "/ocr-status",
  "/behavior-candidates",
  "/tool-health",
  "/settings"
]) {
  assert(app.includes(route), `missing route ${route}`);
}

const apiClient = read("src/lib/api-client.ts");
for (const apiName of [
  "createApp",
  "listQualityReports",
  "getOcrStatus",
  "listBehaviorCandidates",
  "getBehaviorCandidate",
  "approveBehaviorCandidate",
  "rejectBehaviorCandidate",
  "rollbackBehaviorCandidate",
  "markRunFailedLowYield",
  "getToolHealth"
]) {
  assert(apiClient.includes(apiName), `missing api client method ${apiName}`);
}

for (const path of [
  "/api/runs/${runId}/mark-failed-low-yield",
  "/api/behavior-candidates",
  "/api/behavior-candidates/${candidatePackId}/approve",
  "/api/behavior-candidates/${candidatePackId}/reject",
  "/api/behavior-candidates/${candidatePackId}/rollback"
]) {
  assert(apiClient.includes(path), `missing behavior candidate api path ${path}`);
}

for (const phrase of ["disableFallback: true", "mark failed low yield"]) {
  assert(apiClient.includes(phrase), `missing mutation safety phrase ${phrase}`);
}

const runsRoute = read("src/routes/runs.tsx");
for (const phrase of ["executed_by", "assigned_worker_id", "未分配"]) {
  assert(runsRoute.includes(phrase), `missing run worker display phrase ${phrase}`);
}

const mockData = read("src/lib/mock-data.ts");
for (const key of [
  "mockQualityReports",
  "browser_chrome_visible",
  "os_taskbar_visible",
  "dangerous_page",
  "mockOcrStatus",
  "paddleocr_optional_status",
  "easyocr_optional_status",
  "mockBehaviorCandidates",
  "pending_review",
  "mockToolHealth",
  "adb_available",
  "screencap_status"
]) {
  assert(mockData.includes(key), `missing mock readiness key ${key}`);
}

const sidebar = read("src/components/layout/sidebar.tsx");
for (const label of ["质量报告", "OCR 状态", "行为候选", "工具健康"]) {
  assert(sidebar.includes(label), `missing sidebar label ${label}`);
}

const quality = read("src/routes/quality-reports.tsx");
for (const phrase of ["quality_report.json", "browser_chrome_visible", "os_taskbar_visible", "dangerous_page / ocr_risk_detected", "通过数", "拒绝数"]) {
  assert(quality.includes(phrase), `missing quality phrase ${phrase}`);
}

const ocr = read("src/routes/ocr-status.tsx");
for (const phrase of ["paddleocr optional", "easyocr optional", "risk_hits", "scene_hints"]) {
  assert(ocr.includes(phrase), `missing ocr phrase ${phrase}`);
}

const behavior = read("src/routes/behavior-candidates.tsx");
for (const phrase of ["pending_review", "approve", "reject", "rollback", "window.confirm", "rejected 不可启用"]) {
  assert(behavior.includes(phrase), `missing behavior candidate phrase ${phrase}`);
}

const tools = read("src/routes/tool-health.tsx");
for (const phrase of ["machine_ready", "master_ready", "worker_ready", "adb_available", "devices", "selected_device", "ocr_fallback_status", "input_status"]) {
  assert(tools.includes(phrase), `missing tool health phrase ${phrase}`);
}

const theme = `${read("src/lib/theme.ts")}\n${read("src/components/layout/theme-toggle.tsx")}\n${read("src/styles/globals.css")}`;
for (const phrase of ["localStorage", "web-console-theme", "data-theme", "light", "dark"]) {
  assert(theme.includes(phrase), `missing theme persistence phrase ${phrase}`);
}

console.log("web_console_smoke_ok", requiredFiles.length);
