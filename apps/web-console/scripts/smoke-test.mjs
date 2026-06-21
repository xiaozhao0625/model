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
  "src/lib/labels.ts",
  "src/routes/v3-dashboard.tsx",
  "src/routes/v3-new-capture.tsx",
  "src/routes/v3-current-run.tsx",
  "src/routes/v3-gallery.tsx",
  "src/routes/v3-actions.tsx",
  "src/routes/v3-game.tsx",
  "src/routes/v3-reports.tsx",
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
  "/v3",
  "/v3/new",
  "/v3/current",
  "/v3/runs/:runId/gallery",
  "/v3/runs/:runId/actions",
  "/v3/game",
  "/v3/reports",
  "/v3/status",
  "/tool-health",
  "/settings"
]) {
  assert(app.includes(route), `missing route ${route}`);
}

const apiClient = read("src/lib/api-client.ts");
for (const apiName of [
  "requestV3",
  "getV3Health",
  "getV3ModelHealth",
  "getV3ActionHealth",
  "getV3Defaults",
  "listV3Runs",
  "createV3Run",
  "getV3Summary",
  "getV3Actions",
  "getV3Images",
  "getV3ImagePreviewUrl",
  "getV3ImageThumbnailUrl",
  "revealV3Image",
  "openV3RunFolder",
  "isUsingMockFallback"
]) {
  assert(apiClient.includes(apiName), `missing api client method ${apiName}`);
}

for (const path of [
  "/api/v3/health",
  "/api/v3/model/health",
  "/api/v3/action/health",
  "/api/v3/runs",
  "/api/v3/runs/${runId}/summary",
  "/api/v3/runs/${runId}/actions",
  "/api/v3/runs/${runId}/images",
  "/api/v3/runs/${runId}/images/${imageId}/preview",
  "/api/v3/runs/${runId}/images/${imageId}/thumbnail",
  "/api/v3/runs/${runId}/images/${imageId}/reveal",
  "/api/v3/runs/${runId}/open-folder"
]) {
  assert(apiClient.includes(path), `missing api path ${path}`);
}

const sidebar = read("src/components/layout/sidebar.tsx");
for (const phrase of [
  "操作员采集台",
  "控制台",
  "新建采集",
  "当前任务",
  "采集结果",
  "运行审计",
  "游戏采集",
  "报告中心",
  "系统状态",
  "高级调试"
]) {
  assert(sidebar.includes(phrase), `missing sidebar phrase ${phrase}`);
}
for (const oldPrimary of ["应用库", "Worker 监控", "上传与清理", "行为包候选", "工具与模型健康"]) {
  assert(!sidebar.includes(`label: "${oldPrimary}"`), `old primary nav still visible ${oldPrimary}`);
}

const labels = read("src/lib/labels.ts");
for (const phrase of [
  "合格",
  "已拒绝",
  "近重复",
  "无文字",
  "输入网关就绪",
  "完整自动采集就绪",
  "OCR 生产就绪",
  "ShowUI 就绪",
  "OCR 文字框",
  "ShowUI 候选",
  "融合候选",
  "已阻断候选",
  "点击通道",
  "点击前截图",
  "点击后截图",
  "内容区域",
  "界面控件区域",
  "风险窗口区域"
]) {
  assert(labels.includes(phrase), `missing label phrase ${phrase}`);
}

const v3 = read("src/routes/v3-dashboard.tsx");
for (const phrase of [
  "当前系统状态",
  "当前运行任务",
  "新建软件采集",
  "新建游戏采集",
  "打开最近 run",
  "打开 runs 文件夹",
  "打开 obs-output 文件夹",
  "运行自检",
  "最近 5 个 run",
  "查看结果"
]) {
  assert(v3.includes(phrase), `missing v3 phrase ${phrase}`);
}

const gallery = read("src/routes/v3-gallery.tsx");
for (const phrase of [
  "采集结果",
  "最近 10 个 run",
  "合格",
  "已拒绝",
  "待人工审核",
  "复制图片路径",
  "打开图片所在文件夹",
  "打开 run 文件夹",
  "拒绝原因",
  "截图原因",
  "界面状态",
  "重复判定原因",
  "OCR 文本摘要",
  "动作 ID",
  "OCR 文字框",
  "ShowUI 候选",
  "融合候选",
  "已阻断候选",
  "内容区域",
  "界面控件区域",
  "风险窗口区域"
]) {
  assert(gallery.includes(phrase), `missing gallery phrase ${phrase}`);
}

const actions = read("src/routes/v3-actions.tsx");
for (const phrase of [
  "运行审计",
  "点击前截图",
  "点击后截图",
  "候选区域类型",
  "阻断原因",
  "风险词",
  "点之前",
  "点之后",
  "为什么点",
  "有没有成功",
  "有没有回退",
  "有没有被拦截",
  "高级调试"
]) {
  assert(actions.includes(phrase), `missing actions phrase ${phrase}`);
}

const game = read("src/routes/v3-game.tsx");
for (const phrase of [
  "游戏采集",
  "游戏菜单模式",
  "游戏对局模式",
  "自动判断",
  "是否允许无文字对局",
  "键鼠探索",
  "allow_no_text_gameplay",
  "enable_game_explorer",
  "禁止登录",
  "禁止验证码",
  "禁止充值",
  "禁止购买",
  "禁止匹配真人",
  "禁止排位",
  "禁止聊天",
  "禁止绕过反作弊",
  "画面变化过滤"
]) {
  assert(game.includes(phrase), `missing game phrase ${phrase}`);
}

const reports = read("src/routes/v3-reports.tsx");
for (const phrase of ["运行摘要", "重复帧解释报告", "批量采集报告", "系统自检报告", "报告路径", "打开文件夹", "复制路径", "核心统计"]) {
  assert(reports.includes(phrase), `missing report phrase ${phrase}`);
}

const status = read("src/routes/tool-health.tsx");
for (const phrase of [
  "系统状态",
  "/api/v3/health",
  "/api/v3/model/health",
  "/api/v3/action/health",
  "完整自动模式",
  "OCR 单帧性能",
  "鼠标点击",
  "电源策略",
  "未生成性能报告"
]) {
  assert(status.includes(phrase), `missing status phrase ${phrase}`);
}
for (const forbidden of ["ADB", "Android", "OCR fallback", "mockToolHealth", "getToolHealth"]) {
  assert(!status.includes(forbidden), `status page still exposes legacy health term ${forbidden}`);
}

const shell = read("src/components/layout/app-shell.tsx");
for (const forbidden of ["mockRunLogs", "mock fallback", "最近 run.log", "session_started", "upload_manifest_ready"]) {
  assert(!shell.includes(forbidden), `main shell still exposes debug term ${forbidden}`);
}

const theme = `${read("src/lib/theme.ts")}\n${read("src/components/layout/theme-toggle.tsx")}\n${read("src/styles/globals.css")}`;
for (const phrase of ["localStorage", "web-console-theme", "data-theme", "light", "dark"]) {
  assert(theme.includes(phrase), `missing theme persistence phrase ${phrase}`);
}

console.log("web_console_smoke_ok", requiredFiles.length);
