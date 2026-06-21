export const statusLabels: Record<string, string> = {
  accepted: "合格",
  rejected: "拒绝",
  manual_review: "待人工审核",
  deleted: "已删除",
  pending: "待处理",
  created: "已创建",
  running: "运行中",
  paused: "已暂停",
  stopped: "已停止",
  completed: "已完成",
  failed: "失败",
  ready: "就绪",
  degraded: "降级可用",
  unavailable: "不可用",
  blocked: "已阻断",
  enabled: "已启用",
  disabled: "已禁用",
  observe_only: "仅观察",
  executed: "已执行",
  not_executed: "未执行",
  not_ready: "未就绪",
  true: "就绪",
  false: "未就绪"
};

export const rejectReasonLabels: Record<string, string> = {
  near_duplicate: "近重复",
  no_text: "无文字",
  too_few_chars: "文字过少",
  wrong_language: "语言不符",
  mixed_language: "混合语言",
  low_ocr_confidence: "OCR 置信度低",
  black_screen: "黑屏",
  white_screen: "白屏",
  unsafe_text: "风险文本",
  ocr_failed: "OCR 失败"
};

export const fieldLabels: Record<string, string> = {
  run_id: "运行 ID",
  image_id: "图片 ID",
  bucket: "分桶",
  capture_reason: "截图原因",
  ui_state_hint: "界面状态",
  duplicate_decision_reason: "重复判定原因",
  candidate_region_type: "候选区域类型",
  input_gateway_ready: "输入网关就绪",
  full_auto_capture_ready: "完整自动采集就绪",
  ocr_production_ready: "OCR 生产就绪",
  ocr_gpu_ready: "OCR GPU 就绪",
  ocr_performance_ready: "OCR 性能就绪",
  showui_ready: "ShowUI 就绪",
  safety_gate_ready: "Safety Gate 就绪",
  frame_pump: "Frame Pump",
  duplicate_summary: "重复帧摘要",
  batch_report: "批量采集报告",
  action_audit: "动作审计",
  candidates: "候选点",
  images: "截图",
  reports: "报告"
};

export const regionTypeLabels: Record<string, string> = {
  content_area: "内容区域",
  ui_chrome: "界面控件区域",
  unsafe_chrome: "风险窗口区域",
  unknown: "未知区域"
};

export const gameModeLabels: Record<string, string> = {
  menu: "游戏菜单模式",
  gameplay: "游戏对局模式",
  auto: "自动判断"
};

export function labelStatus(value?: string | boolean | null) {
  if (typeof value === "boolean") {
    return value ? "就绪" : "未就绪";
  }
  if (!value) {
    return "未知";
  }
  return statusLabels[value] || value;
}

export function labelRejectReason(value?: string | null) {
  if (!value) {
    return "-";
  }
  return rejectReasonLabels[value] || value;
}

export function labelRegionType(value?: string | null) {
  if (!value) {
    return "未知区域";
  }
  return regionTypeLabels[value] || value;
}
