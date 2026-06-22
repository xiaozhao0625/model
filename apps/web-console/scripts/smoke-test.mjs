import { existsSync, readFileSync } from "node:fs";

const root = new URL("..", import.meta.url);
const read = (path) => readFileSync(new URL(path, root), "utf8");
const assert = (condition, message) => {
  if (!condition) throw new Error(message);
};

const requiredFiles = [
  "src/App.tsx",
  "src/lib/api-client.ts",
  "src/lib/api-types.ts",
  "src/lib/labels.ts",
  "src/routes/v3-dashboard.tsx",
  "src/routes/v3-new-capture.tsx",
  "src/routes/v3-current-run.tsx",
  "src/routes/v3-gallery.tsx",
  "src/routes/v3-actions.tsx",
  "src/routes/v3-game.tsx",
  "src/routes/tool-health.tsx"
];

for (const file of requiredFiles) {
  assert(existsSync(new URL(file, root)), `missing ${file}`);
}

const app = read("src/App.tsx");
for (const route of ["/v3", "/v3/new", "/v3/current", "/v3/gallery", "/v3/actions", "/v3/game", "/v3/status"]) {
  assert(app.includes(route), `missing route ${route}`);
}

const apiClient = read("src/lib/api-client.ts");
for (const phrase of [
  "getV3InputStatus",
  "openV3InputFolder",
  "resumeV3Run",
  "getV3RunStatus",
  "/api/v3/input/status",
  "/api/v3/runs/${runId}/resume",
  "最大动作数是自动点击或键鼠动作次数"
]) {
  assert(apiClient.includes(phrase), `missing api phrase ${phrase}`);
}

const labels = read("src/lib/labels.ts");
for (const phrase of [
  "合格",
  "已拒绝",
  "近重复",
  "未检测到文字",
  "输入网关就绪",
  "OCR 文字框",
  "ShowUI 候选",
  "融合候选",
  "风险窗口区域"
]) {
  assert(labels.includes(phrase), `missing label phrase ${phrase}`);
}

const dashboard = read("src/routes/v3-dashboard.tsx");
for (const phrase of ["V3 操作员采集控制台", "新建采集任务", "当前任务与采集控制", "查看结果图库", "V3 单机模式不需要 Redis"]) {
  assert(dashboard.includes(phrase), `missing dashboard phrase ${phrase}`);
}

const current = read("src/routes/v3-current-run.tsx");
for (const phrase of ["OBS 输入状态", "开始采集", "暂停", "继续", "停止", "等待 OBS 输入", "历史测试任务 / 调试样本"]) {
  assert(current.includes(phrase), `missing current phrase ${phrase}`);
}

const create = read("src/routes/v3-new-capture.tsx");
for (const phrase of ["软件采集", "游戏采集", "高级配置", "创建并开始采集", "无文字补充图比例", "最大软件动作数"]) {
  assert(create.includes(phrase), `missing create phrase ${phrase}`);
}

const gallery = read("src/routes/v3-gallery.tsx");
for (const phrase of ["结果图库", "只看合格", "只看无文字补充图", "是否动作后截图", "复制图片路径", "高级调试信息"]) {
  assert(gallery.includes(phrase), `missing gallery phrase ${phrase}`);
}

const actions = read("src/routes/v3-actions.tsx");
for (const phrase of ["运行详情 / 审计", "动作前截图", "动作后截图", "候选区域类型", "阻止原因", "原始动作 JSON"]) {
  assert(actions.includes(phrase), `missing actions phrase ${phrase}`);
}

const game = read("src/routes/v3-game.tsx");
for (const phrase of ["游戏采集", "文字策略", "只截图，不操作", "启用游戏键鼠探索", "禁止自动登录", "安全场景"]) {
  assert(game.includes(phrase), `missing game phrase ${phrase}`);
}

const status = read("src/routes/tool-health.tsx");
for (const phrase of ["系统状态", "OBS 输入目录", "PaddleOCR", "OCR GPU", "ShowUI", "Input Gateway", "当前运行任务数"]) {
  assert(status.includes(phrase), `missing status phrase ${phrase}`);
}
for (const forbidden of ["Redis、PostgreSQL 或 Docker 是必需", "mockToolHealth", "getToolHealth"]) {
  assert(!status.includes(forbidden), `status page exposes forbidden legacy term ${forbidden}`);
}

console.log("web_console_smoke_ok", requiredFiles.length);
