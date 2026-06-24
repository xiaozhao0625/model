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
  collection_id?: string | null;
  task_name?: string | null;
  app_name: string;
  display_name?: string | null;
  app_type: "software" | "pc_app" | "pc_game" | "game" | "web" | "auto";
  target_language: string;
  capture_source: "obs" | "obs_websocket" | "folder_watch" | "window" | "screen" | "obs_projector";
  input_dir?: string | null;
  frame_pump_output_dir?: string | null;
  watch_dir?: string | null;
  obs_host?: string;
  obs_port?: number;
  obs_scene_name?: string | null;
  obs_source_name?: string | null;
  screenshot_target?: "source" | "scene";
  image_format?: "png" | "jpg" | "jpeg";
  image_quality?: number;
  capture_interval_ms: number;
  save_root: string;
  enable_ocr: boolean;
  enable_ui_model: boolean;
  enable_auto_click: boolean;
  enable_game_explorer: boolean;
  delete_rejected: boolean;
  target_accepted_min: number;
  target_accepted_soft: number;
  target_accepted_max: number;
  max_images: number;
  max_actions: number;
  safety_mode: "strict" | "review" | "off";
  observe_only: boolean;
  text_priority: boolean;
  must_have_text: boolean;
  allow_no_text_fill: boolean;
  no_text_fill_ratio: number;
  text_policy: "strict_text" | "text_priority_with_fill" | "visual_gameplay";
  game_mode: "menu" | "gameplay" | "auto";
  allow_no_text_gameplay: boolean;
  max_game_actions: number;
  game_action_preset: "screenshot_only" | "low_risk_ui_click" | "wasd_mouse" | "hotkey_explore" | "custom";
  allow_wasd_mouse: boolean;
  safe_game_scene_confirmed: boolean;
  enable_game_agent: boolean;
  game_agent_mode: "off" | "auto_explore";
  allow_ui_click: boolean;
  allow_hotkeys: boolean;
  allow_wasd: boolean;
  allow_mouse_look: boolean;
  allow_back_close: boolean;
  allow_inventory_map_explore: boolean;
  allow_training_movement: boolean;
  safe_scene_confirmed: boolean;
  action_interval_ms: number;
  target_window_hwnd?: number | null;
  target_window_title?: string | null;
  target_process_name?: string | null;
  target_process_id?: number | null;
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
  real_input_allowed: boolean;
  keyboard_input_ready: boolean;
  mouse_move_ready: boolean;
  cursor_read_ready: boolean;
  cursor_read_access_denied: boolean;
  mouse_click_ready: boolean;
  target_window_found: boolean;
  target_window_foreground: boolean;
  current_foreground_window?: Record<string, unknown> | null;
  same_desktop_session_ready: boolean;
  same_integrity_ready: boolean;
  interactive_desktop_ready: boolean;
  click_backend: string;
  input_gateway_blockers: string[];
  input_gateway_diagnosis_path?: string | null;
  real_input_enabled: boolean;
  readiness_blockers: string[];
  ocr_performance?: Record<string, unknown>;
  frame_pump?: Record<string, unknown>;
  power_policy?: Record<string, unknown>;
  defaults: V3TaskConfig;
}

export interface V3RunRecord {
  run_id: string;
  collection_id?: string | null;
  round_index?: number;
  status: "created" | "waiting_for_input" | "waiting_for_input_timeout" | "running" | "paused" | "stopped" | "completed" | "failed" | "deleted";
  config: V3TaskConfig;
  task_name?: string | null;
  app_name?: string | null;
  display_name?: string | null;
  created_at: string;
  updated_at: string;
  counts: Record<string, number>;
  last_error?: string | null;
}

export interface V3CollectionSummary {
  collection_id: string;
  status: string;
  task_name?: string | null;
  app_name?: string | null;
  display_name?: string | null;
  app_type: V3TaskConfig["app_type"];
  target_language: string;
  text_policy: V3TaskConfig["text_policy"];
  input_dir?: string | null;
  frame_pump_output_dir?: string | null;
  watch_dir?: string | null;
  target_accepted_min: number;
  target_accepted_soft: number;
  target_accepted_max: number;
  processed_total: number;
  accepted_total: number;
  accepted_unique_total: number;
  duplicate_across_runs_total: number;
  rejected_total: number;
  failed_total: number;
  action_total: number;
  run_count: number;
  latest_run_id?: string | null;
  latest_round_index: number;
  latest_round_processed: number;
  latest_round_accepted: number;
  latest_round_new_unique: number;
  latest_round_duplicate_across_runs: number;
  latest_round_rejected: number;
  latest_round_failed: number;
  latest_round_action_count: number;
  latest_round_action_attempt_count: number;
  latest_round_action_executed_count: number;
  latest_round_action_blocked_count: number;
  latest_round_top_reject_reasons: Array<{ reason: string; count: number }>;
  latest_action?: Record<string, unknown> | null;
  latest_blocked_reason?: string | null;
  game_agent_status?: string;
  game_agent_state?: string;
  game_agent_enabled_capabilities?: string[];
  enable_game_agent: boolean;
  game_agent_mode: "off" | "auto_explore" | string;
  allow_ui_click: boolean;
  allow_hotkeys: boolean;
  allow_wasd: boolean;
  allow_mouse_look: boolean;
  allow_back_close: boolean;
  allow_inventory_map_explore: boolean;
  allow_training_movement: boolean;
  allow_wasd_mouse: boolean;
  enable_game_explorer: boolean;
  safe_scene_confirmed: boolean;
  safe_game_scene_confirmed: boolean;
  action_interval_ms: number;
  real_input_enabled: boolean;
  agent_config_missing: boolean;
  keyboard_input_ready: boolean;
  mouse_move_ready: boolean;
  mouse_click_ready: boolean;
  cursor_read_ready: boolean;
  cursor_read_access_denied: boolean;
  target_window_hwnd?: number | null;
  target_window_title?: string | null;
  target_process_name?: string | null;
  target_process_id?: number | null;
  target_window_found: boolean;
  target_window_foreground: boolean;
  current_foreground_window?: Record<string, unknown> | null;
  action_attempt_total: number;
  action_executed_total: number;
  action_blocked_total: number;
  min_target_reached: boolean;
  soft_target_reached: boolean;
  max_target_reached: boolean;
  remaining_to_min: number;
  remaining_to_soft: number;
  visual_fill_total: number;
  visual_fill_ratio: number;
  continue_suggestion?: string | null;
  accepted_unique_dir?: string | null;
  export_dir?: string | null;
  runs: Array<Record<string, unknown>>;
}

export interface V3CollectionRecord {
  collection_id: string;
  status: string;
  config: V3TaskConfig;
  task_name?: string | null;
  app_name?: string | null;
  display_name?: string | null;
  created_at: string;
  updated_at: string;
  run_ids: string[];
  latest_run_id?: string | null;
}

export type V3AgentConfigRequest = Partial<
  Pick<
    V3TaskConfig,
    | "enable_game_agent"
    | "game_agent_mode"
    | "allow_ui_click"
    | "allow_hotkeys"
    | "allow_wasd"
    | "allow_mouse_look"
    | "allow_back_close"
    | "allow_inventory_map_explore"
    | "allow_training_movement"
    | "allow_wasd_mouse"
    | "enable_game_explorer"
    | "safe_scene_confirmed"
    | "safe_game_scene_confirmed"
    | "action_interval_ms"
  >
>;

export interface V3TargetWindowInfo {
  hwnd: number;
  title: string;
  process_name?: string | null;
  pid?: number | null;
  visible: boolean;
  foreground: boolean;
}

export interface V3ActionHealth {
  input_gateway_ready: boolean;
  real_input_allowed: boolean;
  keyboard_input_ready: boolean;
  mouse_move_ready: boolean;
  cursor_read_ready: boolean;
  cursor_read_access_denied: boolean;
  mouse_click_ready: boolean;
  target_window_found: boolean;
  target_window_foreground: boolean;
  current_foreground_window?: Record<string, unknown> | null;
  same_desktop_session_ready: boolean;
  same_integrity_ready: boolean;
  interactive_desktop_ready: boolean;
  click_backend: string;
  blockers: string[];
  diagnosis_path?: string | null;
  details: Record<string, unknown>;
}

export interface V3FocusTargetWindowResult {
  ok: boolean;
  focused: boolean;
  blocked_reason?: string | null;
  target_window?: V3TargetWindowInfo | null;
  current_foreground_window?: Record<string, unknown> | null;
}

export interface V3CollectionExportResult {
  collection_id: string;
  status: string;
  export_dir: string;
  archive_path?: string | null;
  zip_path?: string | null;
  manifest_path: string;
  summary_path: string;
  rejection_summary_path: string;
  duplicate_summary_path: string;
  accepted_unique_total: number;
  message?: string;
}

export interface V3InputStatus {
  watch_dir: string;
  exists: boolean;
  latest_file?: string | null;
  latest_file_path?: string | null;
  latest_file_time?: string | null;
  seconds_since_latest?: number | null;
  status: "receiving" | "waiting_for_input" | "stale" | "path_missing" | "unreadable";
  message: string;
}

export interface V3FramePumpStatus {
  status: "running" | "stopped" | "stale" | "error";
  output_dir: string;
  pid?: number | null;
  latest_frame?: string | null;
  latest_frame_path?: string | null;
  latest_frame_time?: string | null;
  seconds_since_latest?: number | null;
  frame_count: number;
  fps?: number | null;
  mode: string;
  source_mode?: "obs_websocket" | "screen" | "window" | "obs_projector" | string;
  obs_connected?: boolean;
  obs_scene_name?: string | null;
  obs_source_name?: string | null;
  message: string;
  heartbeat_path?: string | null;
  error?: string | null;
}

export interface V3FramePumpStartRequest {
  fps?: number;
  window_title?: string | null;
  full_screen?: boolean;
  source_mode?: "obs_websocket" | "screen" | "window" | "obs_projector";
  output_dir?: string;
  obs_host?: string;
  obs_port?: number;
  obs_password?: string;
  screenshot_target?: "source" | "scene";
  obs_scene_name?: string | null;
  obs_source_name?: string | null;
  image_format?: "png" | "jpg" | "jpeg";
  image_quality?: number;
}

export interface V3ObsConfigRequest {
  obs_host?: string;
  obs_port?: number;
  obs_password?: string;
  screenshot_target?: "source" | "scene";
  obs_scene_name?: string | null;
  obs_source_name?: string | null;
  output_dir?: string;
  image_format?: "png" | "jpg" | "jpeg";
  image_quality?: number;
}

export interface V3ObsStatus {
  ok: boolean;
  connected: boolean;
  host: string;
  port: number;
  message: string;
  version?: string | null;
  current_scene?: string | null;
  error?: string | null;
}

export interface V3ObsSceneRecord {
  name: string;
  current?: boolean;
}
export type V3ObsSceneOption = V3ObsSceneRecord | string;

export interface V3ObsSourceRecord {
  name: string;
  kind?: string | null;
  scene_name?: string | null;
}
export type V3ObsSourceOption = V3ObsSourceRecord | string;

export interface V3ObsScreenshotResult {
  ok: boolean;
  image_path?: string | null;
  width?: number | null;
  height?: number | null;
  source_mode?: string;
  obs_scene_name?: string | null;
  obs_source_name?: string | null;
  black_screen_detected?: boolean;
  message: string;
  error?: string | null;
}

export interface V3DeleteResult {
  target_type: "collection" | "run";
  target_id: string;
  status: "deleted" | "deleted_to_trash";
  delete_files: boolean;
  moved_to?: string | null;
  message: string;
}

export interface V3Summary {
  run_id: string;
  status: V3RunRecord["status"];
  counts: Record<string, number>;
  task_name?: string | null;
  app_name?: string | null;
  display_name?: string | null;
  target_accepted_min?: number;
  target_accepted_soft?: number;
  target_accepted_max?: number;
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
  accepted_text_ui_count?: number;
  accepted_text_hud_count?: number;
  accepted_visual_fill_count?: number;
  no_text_fill_ratio_actual?: number;
  no_text_fill_over_quota?: boolean;
  latest_input_at?: string | null;
  latest_accepted_at?: string | null;
  top_reject_reason?: string | null;
  input_status?: V3InputStatus | null;
  action_attempt_count?: number;
  action_executed_count?: number;
  action_blocked_count?: number;
  observe_only: boolean;
  auto_click_ready: boolean;
  full_auto_capture_ready: boolean;
  model_ready: boolean;
  ocr_ready: boolean;
  ocr_gpu_ready: boolean;
  ocr_performance_ready: boolean;
  ocr_production_ready: boolean;
  input_gateway_ready: boolean;
  real_input_allowed: boolean;
  keyboard_input_ready: boolean;
  mouse_move_ready: boolean;
  cursor_read_ready: boolean;
  cursor_read_access_denied: boolean;
  mouse_click_ready: boolean;
  target_window_found: boolean;
  target_window_foreground: boolean;
  current_foreground_window?: Record<string, unknown> | null;
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

export interface V3ImageRecord {
  image_id: string;
  path: string;
  absolute_path?: string;
  folder?: string;
  file_exists?: boolean;
  bucket: "pending" | "accepted" | "rejected" | "deleted" | "manual_review";
  sha256?: string | null;
  content_hash?: string | null;
  valid: boolean;
  near_duplicate: boolean;
  reject_reason?: string | null;
  created_at: string;
  meta: Record<string, unknown>;
  duplicate_decision: Record<string, unknown>;
}

export interface V3OpenPathResult {
  status: string;
  path: string;
  folder?: string;
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
  detail?: unknown;
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
