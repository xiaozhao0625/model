export type RunStatus =
  | "pending"
  | "launching"
  | "waiting_manual"
  | "profiling"
  | "running"
  | "capture_completed"
  | "upload_pending"
  | "uploaded_confirmed"
  | "local_deleted"
  | "completed"
  | "needs_manual_seed"
  | "failed_low_yield"
  | "skipped_risk";

export type AppType = "pc_game" | "pc_app" | "web" | "android_app" | "android_game" | "other";

export interface AppRecord {
  app_id: string;
  name: string;
  type: AppType | string;
  platform: string;
}

export interface RunRecord {
  run_id: string;
  app_id: string;
  status: RunStatus;
  valid_total: number;
  fixed_count: number;
  low_count: number;
  high_count: number;
  rejected_count: number;
  retry_round: number;
  target_min?: number;
  target_max?: number;
  worker_id?: string;
  updated_at?: string;
}

export interface WorkerRecord {
  worker_id: string;
  type: string;
  machine_name?: string;
  capabilities: string[];
  state: "idle" | "assigned" | "running" | "stopped" | "failed" | string;
  heartbeat?: string | null;
  current_run_id?: string | null;
}

export interface UploadRecord {
  upload_id: string;
  run_id: string;
  status: RunStatus;
}

export interface RunSummary {
  run_id: string;
  app_id: string;
  status: RunStatus;
  valid_total: number;
  fixed_count: number;
  low_count: number;
  high_count: number;
  rejected_count: number;
  retry_round: number;
  target_min?: number;
  target_max?: number;
}

export interface RunLogEntry {
  timestamp: string;
  event: string;
  status: RunStatus | string;
  details: Record<string, unknown>;
}

export interface V3TaskConfig {
  app_name: string;
  app_type: "software" | "pc_app" | "game" | "web" | "auto";
  target_language: string;
  capture_source: "obs" | "folder_watch" | "window";
  capture_interval_ms: number;
  save_root: string;
  enable_ocr: boolean;
  enable_ui_model: boolean;
  enable_auto_click: boolean;
  enable_game_explorer: boolean;
  delete_rejected: boolean;
  max_images: number;
  max_actions: number;
  safety_mode: "strict" | "review" | "off";
  observe_only: boolean;
  must_have_text: boolean;
}

export interface V3ProviderHealth {
  provider: string;
  status: "ready" | "degraded" | "unavailable";
  enabled: boolean;
  reason?: string | null;
  details: Record<string, unknown>;
}

export interface V3Health {
  status: "ready" | "degraded";
  ocr: V3ProviderHealth[];
  models: V3ProviderHealth[];
  complete_auto_mode_ready: boolean;
  full_auto_capture_ready: boolean;
  ocr_gpu_ready: boolean;
  ocr_performance_ready: boolean;
  ocr_production_ready: boolean;
  input_gateway_ready: boolean;
  cursor_read_ready: boolean;
  mouse_click_ready: boolean;
  same_desktop_session_ready: boolean;
  same_integrity_ready: boolean;
  interactive_desktop_ready: boolean;
  click_backend: string;
  input_gateway_blockers: string[];
  input_gateway_diagnosis_path?: string | null;
  readiness_blockers: string[];
  defaults: V3TaskConfig;
}

export interface V3RunRecord {
  run_id: string;
  status: "created" | "running" | "paused" | "stopped" | "completed" | "failed";
  config: V3TaskConfig;
  created_at: string;
  updated_at: string;
  counts: Record<string, number>;
  last_error?: string | null;
}

export interface V3Summary {
  run_id: string;
  status: V3RunRecord["status"];
  counts: Record<string, number>;
  processed?: number;
  accepted?: number;
  rejected?: number;
  failed?: number;
  quarantined?: number;
  near_duplicate_count?: number;
  exact_duplicate_count?: number;
  action_representative_accepted_count?: number;
  visual_difference_accepted_count?: number;
  menu_state_accepted_count?: number;
  dialog_state_accepted_count?: number;
  periodic_static_rejected_count?: number;
  duplicate_policy_summary?: Record<string, unknown>;
  duplicate_explanation_report_path?: string | null;
  reject_reason_distribution?: Record<string, number>;
  accepted_by_ui_state_hint?: Record<string, number>;
  accepted_by_capture_reason?: Record<string, number>;
  observe_only: boolean;
  auto_click_ready: boolean;
  full_auto_capture_ready: boolean;
  model_ready: boolean;
  ocr_ready: boolean;
  ocr_gpu_ready: boolean;
  ocr_performance_ready: boolean;
  ocr_production_ready: boolean;
  input_gateway_ready: boolean;
  cursor_read_ready: boolean;
  mouse_click_ready: boolean;
  same_desktop_session_ready: boolean;
  same_integrity_ready: boolean;
  interactive_desktop_ready: boolean;
  click_backend: string;
  input_gateway_blockers: string[];
  readiness_blockers: string[];
  safety_gate_ready: boolean;
}

export interface V3ActionRecord {
  decision: Record<string, unknown>;
  result: {
    executed?: boolean;
    reason?: string;
    status?: string;
    clicked?: number[];
    rollback_reason?: string;
    click_backend?: string;
  };
  label?: string | null;
  source_candidate_id?: string | null;
  safety_result?: Record<string, unknown>;
  before_image?: string | null;
  after_image?: string | null;
}

export interface MetaEntry {
  image_id: string;
  bucket: "fixed" | "low" | "high" | "rejected";
  path: string;
  valid: boolean;
  content_hash?: string;
  reject_reason?: string | null;
}

export interface ModelProviderRecord {
  provider_name: string;
  provider_type: string;
  enabled: boolean;
  supports_scene_classify: boolean;
  supports_ground: boolean;
  supports_act: boolean;
  blocked_count: number;
  last_event: string;
}

export interface ApiEnvelope<T> {
  ok: boolean;
  data?: T;
  error?: string;
}

export interface SceneClassifyResult {
  scene_class: string;
  confidence: number;
  reason: string;
  provider_name: string;
}

export interface GroundResult {
  found: boolean;
  x: number | null;
  y: number | null;
  confidence: number;
  reason: string;
  provider_name: string;
}

export interface ActionProposal {
  action_type: "click" | "key_press" | "wait" | "no_op" | "request_manual" | "abort";
  confidence: number;
  reason: string;
  target?: string | null;
  keys?: string[] | null;
  risk_flags: string[];
  provider_name: string;
}

export interface QualityReportRecord {
  run_id: string;
  app_id: string;
  total_images: number;
  accepted_count: number;
  rejected_count: number;
  quality_pass_rate: number;
  black_screen_count: number;
  white_screen_count: number;
  blurry_count: number;
  wrong_window_count: number;
  browser_chrome_count: number;
  taskbar_count: number;
  near_duplicate_count: number;
  ocr_risk_hit_count: number;
  reject_reason_distribution: Record<string, number>;
}

export interface OcrStatusRecord {
  provider: string;
  available: boolean;
  status: "available" | "unavailable" | "skipped" | "disabled" | "unknown" | string;
  risk_hits: string[];
  scene_hints: string[];
  unavailable_reason?: string | null;
  paddleocr_optional_status: string;
  easyocr_optional_status: string;
}

export interface BehaviorCandidateRecord {
  candidate_pack_id: string;
  base_pack_id: string;
  game_type: string;
  version: string;
  status: "pending_review" | "approved" | "rejected" | "enabled" | string;
  enabled?: boolean;
  issues: string[];
  recommendations: string[];
  rollback_target: string;
  created_from_run_id: string;
}

export interface ToolHealthRecord {
  machine_ready: string;
  master_ready: string;
  worker_ready: string;
  tools: Record<string, "available" | "unavailable" | "skipped" | "disabled" | "unknown" | string>;
  android: {
    adb_available: boolean;
    devices: string[];
    selected_device: string | null;
    screencap_status: string;
    ui_dump_status: string;
    ocr_fallback_status: string;
    input_status: string;
  };
}
