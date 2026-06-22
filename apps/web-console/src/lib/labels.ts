export const statusLabels: Record<string, string> = {
  accepted: "合格",
  rejected: "已拒绝",
  manual_review: "待人工审核",
  deleted: "已删除",
  pending: "待处理",
  created: "已创建",
  waiting_for_input: "等待 OBS 输入",
  running: "采集中",
  paused: "已暂停",
  stopped: "已停止",
  completed: "已完成",
  failed: "失败",
  ready: "正常",
  degraded: "降级可用",
  unavailable: "不可用",
  receiving: "正常接收",
  stale: "长时间无输入",
  path_missing: "路径不存在",
  unreadable: "输入图片无法读取",
  blocked: "已阻止",
  true: "正常",
  false: "异常"
};

export const appTypeLabels: Record<string, string> = {
  software: "软件",
  pc_app: "PC 软件",
  pc_game: "PC 游戏",
  game: "游戏",
  web: "网页",
  auto: "自动判断"
};

export const languageLabels: Record<string, string> = {
  zh: "中文",
  en: "英文",
  ja: "日文",
  ko: "韩文"
};

export const rejectReasonLabels: Record<string, string> = {
  near_duplicate: "近重复",
  exact_duplicate: "完全重复",
  rejected_near_duplicate: "近重复",
  rejected_no_text_over_quota: "无文字补充图超过比例",
  rejected_no_visual_change: "无明显画面变化",
  rejected_unsafe_page: "风险页面",
  no_text: "未检测到文字",
  too_few_chars: "文字太少",
  wrong_language: "语言不匹配",
  mixed_language: "混合语言",
  low_ocr_confidence: "OCR 置信度低",
  black_screen: "黑屏",
  white_screen: "白屏",
  unsafe_text: "风险文字",
  ocr_failed: "OCR 失败"
};

export const fieldLabels: Record<string, string> = {
  run_id: "任务编号",
  app_type: "应用类型",
  processed: "已处理",
  accepted: "合格",
  rejected: "已拒绝",
  failed: "失败",
  quarantined: "隔离",
  action_count: "动作次数",
  images: "图片",
  actions: "动作审计",
  candidate: "候选区域",
  candidate_region_type: "候选区域类型",
  ocr_bbox: "OCR 文字框",
  showui_candidate: "ShowUI 候选",
  fusion_candidate: "融合候选",
  near_duplicate: "近重复",
  exact_duplicate: "完全重复",
  input_gateway_ready: "输入网关就绪",
  click_backend: "点击通道",
  blocked_reason: "阻止原因",
  risk_terms: "风险词"
};

export const overlayLabels: Record<string, string> = {
  ocr_boxes: "OCR 文字框",
  showui_candidates: "ShowUI 候选",
  fusion_candidates: "融合候选",
  blocked_candidates: "已阻止候选",
  click_points: "点击点"
};

export const regionTypeLabels: Record<string, string> = {
  content_area: "内容区域",
  ui_chrome: "界面控件区域",
  unsafe_chrome: "风险窗口区域",
  unknown: "未知区域"
};

export const gameModeLabels: Record<string, string> = {
  menu: "局外/菜单/背包/地图/仓库",
  gameplay: "训练场/对局",
  auto: "混合模式"
};

export const textPolicyLabels: Record<string, string> = {
  strict_text: "严格必须有文字",
  text_priority_with_fill: "文字优先，允许少量无文字补充图",
  visual_gameplay: "对局视觉变化模式"
};

export const gameActionPresetLabels: Record<string, string> = {
  screenshot_only: "只截图，不操作",
  low_risk_ui_click: "低风险 UI 点击",
  wasd_mouse: "WASD + 鼠标视角变化",
  hotkey_explore: "地图/背包/仓库热键探索",
  custom: "自定义允许按键"
};

export function labelStatus(value?: string | boolean | null) {
  if (typeof value === "boolean") return value ? "正常" : "异常";
  if (!value) return "未知";
  return statusLabels[value] || value;
}

export function labelAppType(value?: string | null) {
  if (!value) return "未知";
  return appTypeLabels[value] || value;
}

export function labelLanguage(value?: string | null) {
  if (!value) return "未知";
  return languageLabels[value] || value;
}

export function labelRejectReason(value?: string | null) {
  if (!value) return "-";
  return rejectReasonLabels[value] || value;
}

export function labelRegionType(value?: string | null) {
  if (!value) return "未知区域";
  return regionTypeLabels[value] || value;
}

export function labelField(value: string) {
  return fieldLabels[value] || value;
}

export function displayRunName(run: { display_name?: string | null; task_name?: string | null; app_name?: string | null; config?: { display_name?: string | null; task_name?: string | null; app_name?: string | null } }) {
  return run.display_name || run.task_name || run.app_name || run.config?.display_name || run.config?.task_name || run.config?.app_name || "未命名任务";
}

export function isDebugRun(run: { run_id: string; config?: { app_name?: string | null; task_name?: string | null; display_name?: string | null } }) {
  const text = `${run.run_id} ${run.config?.app_name || ""} ${run.config?.task_name || ""} ${run.config?.display_name || ""}`.toLowerCase();
  return ["smoke", "test", "demo", "v3_real_test", "wrong_language"].some((keyword) => text.includes(keyword));
}
