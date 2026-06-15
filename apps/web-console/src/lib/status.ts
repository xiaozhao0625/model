import type { RunStatus } from "./api-types";

export const statusLabels: Record<RunStatus, string> = {
  pending: "待处理",
  dispatching: "分发中",
  launching: "启动中",
  waiting_manual: "等待人工",
  profiling: "识别中",
  running: "运行中",
  capture_completed: "采集完成",
  post_analysis_pending: "待离线分析",
  quality_report_ready: "质量报告就绪",
  upload_pending: "待上传确认",
  uploaded_confirmed: "已确认上传",
  local_delete_pending: "待本地清理",
  local_deleted: "本地已清理",
  completed: "已完成",
  needs_manual_seed: "需要人工补种",
  manual_required: "需要人工处理",
  blocked: "已阻塞",
  failed_low_yield: "低产失败",
  failed_tool_error: "工具失败",
  failed_worker_lost: "Worker 丢失",
  failed_timeout: "超时失败",
  stuck_recovered: "已恢复卡住任务",
  cancelled: "已取消",
  skipped_risk: "风险跳过"
};

export const statusTone: Record<RunStatus, string> = {
  pending: "border-slate-500/40 bg-slate-500/10 text-slate-300",
  dispatching: "border-blue-500/40 bg-blue-500/10 text-blue-300",
  launching: "border-blue-500/40 bg-blue-500/10 text-blue-300",
  waiting_manual: "border-amber-500/40 bg-amber-500/10 text-amber-300",
  profiling: "border-cyan-500/40 bg-cyan-500/10 text-cyan-300",
  running: "border-emerald-500/40 bg-emerald-500/10 text-emerald-300",
  capture_completed: "border-emerald-400/50 bg-emerald-400/10 text-emerald-200",
  post_analysis_pending: "border-cyan-400/50 bg-cyan-400/10 text-cyan-200",
  quality_report_ready: "border-sky-400/50 bg-sky-400/10 text-sky-200",
  upload_pending: "border-amber-400/50 bg-amber-400/10 text-amber-200",
  uploaded_confirmed: "border-blue-400/50 bg-blue-400/10 text-blue-200",
  local_delete_pending: "border-purple-400/50 bg-purple-400/10 text-purple-200",
  local_deleted: "border-purple-400/50 bg-purple-400/10 text-purple-200",
  completed: "border-slate-400/50 bg-slate-400/10 text-slate-200",
  needs_manual_seed: "border-orange-400/50 bg-orange-400/10 text-orange-200",
  manual_required: "border-orange-400/50 bg-orange-400/10 text-orange-200",
  blocked: "border-red-400/50 bg-red-400/10 text-red-200",
  failed_low_yield: "border-red-400/50 bg-red-400/10 text-red-200",
  failed_tool_error: "border-red-400/50 bg-red-400/10 text-red-200",
  failed_worker_lost: "border-red-400/50 bg-red-400/10 text-red-200",
  failed_timeout: "border-red-400/50 bg-red-400/10 text-red-200",
  stuck_recovered: "border-teal-400/50 bg-teal-400/10 text-teal-200",
  cancelled: "border-slate-500/50 bg-slate-500/10 text-slate-300",
  skipped_risk: "border-red-400/50 bg-red-400/10 text-red-200"
};

export const lifecycleSteps: RunStatus[] = [
  "pending",
  "dispatching",
  "launching",
  "profiling",
  "running",
  "capture_completed",
  "post_analysis_pending",
  "quality_report_ready",
  "upload_pending",
  "uploaded_confirmed",
  "local_delete_pending",
  "local_deleted",
  "completed"
];

export const bucketLabels: Record<string, string> = {
  fixed: "固定",
  low: "低频",
  high: "高频",
  rejected: "拒绝",
  duplicates: "重复"
};

export const workerTypeLabels: Record<string, string> = {
  pc_game: "PC 游戏 Worker",
  pc_app: "PC 软件 Worker",
  web: "Web Worker",
  android_app: "Android 应用",
  android_game: "Android 游戏",
  android: "Android Worker",
  mock: "Mock Worker",
  other: "其他类型"
};

export const workerStateLabels: Record<string, string> = {
  idle: "空闲",
  assigned: "已分配",
  running: "运行中",
  stopped: "已停止",
  failed: "故障"
};

export const capabilityLabels: Record<string, string> = {
  capture_low: "低频采集",
  capture_high: "高频采集",
  behavior_pack: "行为包",
  obs_capture: "OBS 采集",
  ffmpeg_extract: "FFmpeg 抽帧",
  pywinauto: "pywinauto 自动化",
  playwright: "Playwright 自动化",
  adb: "ADB",
  android_emulator: "Android 模拟器",
  mss: "mss 截图",
  dxcam: "dxcam 截图",
  "content_area_only=true": "仅内容区",
  "app-screenshot-agent-reuse": "复用 app-screenshot-agent"
};

export const providerTypeLabels: Record<string, string> = {
  mock: "Mock Provider",
  ui_tars: "UI-TARS 骨架",
  showui: "ShowUI",
  qwen_vl: "Qwen-VL 骨架",
  omniparser: "OmniParser 骨架",
  gui_actor: "GUI Actor 骨架",
  os_atlas: "OS-Atlas 骨架"
};

export const actionLabels: Record<string, string> = {
  start: "启动",
  stop: "停止",
  retry: "补采",
  manual_seed: "人工补种",
  mark_failed: "标记低产失败",
  upload_manifest: "生成上传清单",
  confirm_upload: "确认已上传",
  cleanup: "清理本地",
  finalize: "完成任务",
  view_detail: "查看详情"
};

export function isTerminalStatus(status: RunStatus): boolean {
  return ["completed", "failed_low_yield", "skipped_risk", "cancelled"].includes(status);
}
