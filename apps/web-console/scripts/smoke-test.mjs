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
for (const route of ["/v3", "/v3/new", "/v3/current", "/v3/collections", "/v3/collections/:collectionId/gallery", "/v3/gallery", "/v3/actions", "/v3/game", "/v3/status"]) {
  assert(app.includes(route), `missing route ${route}`);
}

const apiClient = read("src/lib/api-client.ts");
for (const phrase of [
  "listV3Collections",
  "createV3Collection",
  "continueV3Collection",
  "exportV3Collection",
  "getV3FramePumpStatus",
  "startV3FramePump",
  "stopV3FramePump",
  "/api/v3/collections",
  "/api/v3/frame-pump/status",
  "/api/v3/collections/${collectionId}/continue",
  "最大动作数是自动点击或键鼠动作次数"
]) {
  assert(apiClient.includes(phrase), `missing api phrase ${phrase}`);
}

const apiTypes = read("src/lib/api-types.ts");
for (const phrase of ["V3CollectionSummary", "accepted_unique_total", "duplicate_across_runs_total", "latest_round_new_unique", "V3CollectionExportResult"]) {
  assert(apiTypes.includes(phrase), `missing api type phrase ${phrase}`);
}
for (const phrase of ["latest_vision_state", "latest_stuck_score", "mouse_move_relative_total", "mouse_move_relative_ready"]) {
  assert(apiTypes.includes(phrase), `missing vision api type phrase ${phrase}`);
}
for (const phrase of ["ui_explore_action_total", "recovery_action_total", "recent_actions", "agent_paused_reason"]) {
  assert(apiTypes.includes(phrase), `missing recovery api type phrase ${phrase}`);
}

const current = read("src/routes/v3-current-run.tsx");
for (const phrase of [
  "当前采集项目",
  "collection 采集项目",
  "累计去重有效截图",
  "继续采集",
  "查看累计图库",
  "查看所有轮次",
  "导出最终有效图",
  "本轮新增有效",
  "本轮跨轮重复",
  "动作预算只限制本轮自动操作次数",
  "历史未归类任务 / 调试样本"
]) {
  assert(current.includes(phrase), `missing current phrase ${phrase}`);
}
for (const phrase of ["视觉状态", "疑似卡住", "下一步计划", "选择原因", "mouse_move_relative"]) {
  assert(current.includes(phrase), `missing vision current phrase ${phrase}`);
}
for (const phrase of ["UI 页面探索", "切回目标窗口并继续", "改为只截图模式继续", "最近 10 个动作", "after_frame_fresh"]) {
  assert(current.includes(phrase), `missing recovery current phrase ${phrase}`);
}

const gallery = read("src/routes/v3-gallery.tsx");
for (const phrase of ["最终有效图库", "accepted_unique", "只看跨轮重复", "复制图片路径", "高级调试信息", "来源 run_id"]) {
  assert(gallery.includes(phrase), `missing gallery phrase ${phrase}`);
}

const create = read("src/routes/v3-new-capture.tsx");
for (const phrase of ["软件采集", "游戏采集", "高级配置", "创建并开始采集", "无文字补充图比例", "最大软件动作数", "createV3Collection"]) {
  assert(create.includes(phrase), `missing create phrase ${phrase}`);
}

const game = read("src/routes/v3-game.tsx");
for (const phrase of ["游戏采集", "文字策略", "只截图，不操作", "启用游戏键鼠探索", "禁止自动登录", "安全场景", "createV3Collection"]) {
  assert(game.includes(phrase), `missing game phrase ${phrase}`);
}

const status = read("src/routes/tool-health.tsx");
for (const phrase of ["系统状态", "OBS 输入目录", "PaddleOCR", "OCR GPU", "ShowUI", "Input Gateway", "当前采集中项目"]) {
  assert(status.includes(phrase), `missing status phrase ${phrase}`);
}
for (const forbidden of ["Redis、PostgreSQL 或 Docker 是必需", "mockToolHealth", "getToolHealth"]) {
  assert(!status.includes(forbidden), `status page exposes forbidden legacy term ${forbidden}`);
}

for (const phrase of ["Frame Pump", "启动 Frame Pump", "停止 Frame Pump", "等待 Frame Pump 输出截图"]) {
  assert(current.includes(phrase) || status.includes(phrase), `missing frame pump phrase ${phrase}`);
}

console.log("web_console_smoke_ok", requiredFiles.length);
