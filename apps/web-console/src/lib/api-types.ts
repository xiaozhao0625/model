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

export interface MetaEntry {
  image_id: string;
  bucket: "fixed" | "low" | "high" | "rejected";
  path: string;
  valid: boolean;
  content_hash?: string;
  reject_reason?: string | null;
}

export interface ArtifactSampleRecord {
  file_id: string;
  file_name: string;
  bucket: "fixed" | "low" | "high" | "rejected" | "duplicates" | string;
  width: number;
  height: number;
  is_duplicate: boolean;
  rejected_reason?: string | null;
  thumbnail_url: string;
  safe_display_path: string;
  capture_method: string;
}

export interface RunArtifactRecord {
  run_id: string;
  task_id: string;
  worker_id: string;
  worker_role: string;
  worker_host: string;
  artifact_root: string;
  status: string;
  summary: Record<string, unknown>;
  bucket_counts: Record<string, number>;
  sample_files: ArtifactSampleRecord[];
  has_meta_jsonl: boolean;
  has_summary_json: boolean;
  can_open_folder: boolean;
  can_download_sample: boolean;
}

export interface ArtifactActionResult {
  run_id: string;
  worker_id: string;
  status: string;
  desktop_session_required?: boolean;
  zip_path?: string | null;
  file_count?: number;
  download_id?: string | null;
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
  ok?: boolean;
  code?: number;
  message?: string;
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
