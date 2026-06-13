import type {
  AppRecord,
  MetaEntry,
  ModelProviderRecord,
  RunLogEntry,
  RunRecord,
  RunSummary,
  UploadRecord,
  WorkerRecord
} from "./api-types";

export const mockApps: AppRecord[] = [
  { app_id: "fps_arena", name: "FPS Arena", type: "pc_game", platform: "windows" },
  { app_id: "office_suite", name: "Office Suite", type: "pc_app", platform: "windows" },
  { app_id: "web_portal", name: "Web Portal", type: "web", platform: "browser" },
  { app_id: "android_shop", name: "Android Shop", type: "android_app", platform: "android" }
];

export const mockRuns: RunRecord[] = [
  {
    run_id: "run_live_001",
    app_id: "fps_arena",
    status: "running",
    valid_total: 642,
    fixed_count: 3,
    low_count: 0,
    high_count: 639,
    rejected_count: 24,
    retry_round: 1,
    target_min: 1000,
    target_max: 5000,
    worker_id: "W1-PC-GAME",
    updated_at: "2026-06-13T10:08:00Z"
  },
  {
    run_id: "run_capture_done",
    app_id: "web_portal",
    status: "capture_completed",
    valid_total: 1240,
    fixed_count: 4,
    low_count: 1236,
    high_count: 0,
    rejected_count: 31,
    retry_round: 0,
    target_min: 1000,
    target_max: 5000,
    worker_id: "W3-WEB",
    updated_at: "2026-06-13T09:32:00Z"
  },
  {
    run_id: "run_upload_wait",
    app_id: "office_suite",
    status: "upload_pending",
    valid_total: 1508,
    fixed_count: 6,
    low_count: 1502,
    high_count: 0,
    rejected_count: 12,
    retry_round: 0,
    target_min: 1000,
    target_max: 5000,
    worker_id: "W2-PC-APP",
    updated_at: "2026-06-13T08:44:00Z"
  },
  {
    run_id: "run_upload_confirmed",
    app_id: "android_shop",
    status: "uploaded_confirmed",
    valid_total: 1015,
    fixed_count: 2,
    low_count: 1013,
    high_count: 0,
    rejected_count: 18,
    retry_round: 2,
    target_min: 1000,
    target_max: 5000,
    worker_id: "W4-ANDROID",
    updated_at: "2026-06-13T07:59:00Z"
  },
  {
    run_id: "run_local_deleted",
    app_id: "office_suite",
    status: "local_deleted",
    valid_total: 1198,
    fixed_count: 5,
    low_count: 1193,
    high_count: 0,
    rejected_count: 7,
    retry_round: 0,
    target_min: 1000,
    target_max: 5000,
    worker_id: "W2-PC-APP",
    updated_at: "2026-06-12T18:00:00Z"
  },
  {
    run_id: "run_complete_001",
    app_id: "web_portal",
    status: "completed",
    valid_total: 1824,
    fixed_count: 8,
    low_count: 1816,
    high_count: 0,
    rejected_count: 43,
    retry_round: 1,
    target_min: 1000,
    target_max: 5000,
    worker_id: "W3-WEB",
    updated_at: "2026-06-12T12:11:00Z"
  },
  {
    run_id: "run_manual_seed",
    app_id: "fps_arena",
    status: "needs_manual_seed",
    valid_total: 748,
    fixed_count: 1,
    low_count: 0,
    high_count: 747,
    rejected_count: 56,
    retry_round: 2,
    target_min: 1000,
    target_max: 5000,
    worker_id: "W1-PC-GAME",
    updated_at: "2026-06-12T10:25:00Z"
  },
  {
    run_id: "run_low_yield",
    app_id: "android_shop",
    status: "failed_low_yield",
    valid_total: 412,
    fixed_count: 2,
    low_count: 410,
    high_count: 0,
    rejected_count: 90,
    retry_round: 2,
    target_min: 1000,
    target_max: 5000,
    worker_id: "W4-ANDROID",
    updated_at: "2026-06-12T09:25:00Z"
  },
  {
    run_id: "run_risk_skip",
    app_id: "android_shop",
    status: "skipped_risk",
    valid_total: 0,
    fixed_count: 0,
    low_count: 0,
    high_count: 0,
    rejected_count: 0,
    retry_round: 0,
    target_min: 1000,
    target_max: 5000,
    worker_id: "W4-ANDROID",
    updated_at: "2026-06-12T08:00:00Z"
  }
];

export const mockWorkers: WorkerRecord[] = [
  {
    worker_id: "W1-PC-GAME",
    type: "pc_game",
    machine_name: "capture-node-01",
    capabilities: ["capture_high", "behavior_pack", "obs_capture", "ffmpeg_extract"],
    state: "running",
    heartbeat: "2026-06-13T10:10:00Z",
    current_run_id: "run_live_001"
  },
  {
    worker_id: "W2-PC-APP",
    type: "pc_app",
    machine_name: "capture-node-02",
    capabilities: ["capture_low", "pywinauto"],
    state: "idle",
    heartbeat: "2026-06-13T10:09:28Z",
    current_run_id: null
  },
  {
    worker_id: "W3-WEB",
    type: "web",
    machine_name: "browser-node-01",
    capabilities: ["capture_low", "playwright", "content_area_only=true"],
    state: "idle",
    heartbeat: "2026-06-13T10:09:48Z",
    current_run_id: null
  },
  {
    worker_id: "W4-ANDROID",
    type: "android",
    machine_name: "android-node-01",
    capabilities: ["capture_low", "adb", "app-screenshot-agent-reuse"],
    state: "stopped",
    heartbeat: "2026-06-13T09:35:00Z",
    current_run_id: null
  }
];

export const mockUploads: UploadRecord[] = [
  { upload_id: "run_upload_wait:manifest", run_id: "run_upload_wait", status: "upload_pending" },
  { upload_id: "run_upload_confirmed:confirm", run_id: "run_upload_confirmed", status: "uploaded_confirmed" },
  { upload_id: "run_local_deleted:cleanup", run_id: "run_local_deleted", status: "local_deleted" }
];

export const mockModelProviders: ModelProviderRecord[] = [
  {
    provider_name: "mock_gateway",
    provider_type: "mock",
    enabled: true,
    supports_scene_classify: true,
    supports_ground: true,
    supports_act: true,
    blocked_count: 7,
    last_event: "request_manual blocked payment intent"
  },
  {
    provider_name: "ui_tars_stub",
    provider_type: "ui_tars",
    enabled: false,
    supports_scene_classify: false,
    supports_ground: true,
    supports_act: true,
    blocked_count: 0,
    last_event: "stub only"
  },
  {
    provider_name: "qwen_vl_stub",
    provider_type: "qwen_vl",
    enabled: false,
    supports_scene_classify: true,
    supports_ground: false,
    supports_act: false,
    blocked_count: 0,
    last_event: "model not deployed"
  }
];

export const mockRunLogs: RunLogEntry[] = [
  {
    timestamp: "2026-06-13T09:31:00Z",
    event: "session_started",
    status: "running",
    details: { worker_id: "W3-WEB" }
  },
  {
    timestamp: "2026-06-13T09:32:10Z",
    event: "capture_completed",
    status: "capture_completed",
    details: { valid_total: 1240, bucket: "low" }
  },
  {
    timestamp: "2026-06-13T09:33:00Z",
    event: "upload_manifest_ready",
    status: "upload_pending",
    details: { expected_upload_folder: "BaiduNetdisk:/screenshots/web_portal/run_capture_done" }
  }
];

export const mockMeta: MetaEntry[] = [
  {
    image_id: "00000001",
    bucket: "low",
    path: "low/00000001.webp",
    valid: true,
    content_hash: "sha256:19ef"
  },
  {
    image_id: "00000002",
    bucket: "low",
    path: "low/00000002.webp",
    valid: true,
    content_hash: "sha256:23ac"
  },
  {
    image_id: "00000003",
    bucket: "rejected",
    path: "rejected/00000003.webp",
    valid: false,
    reject_reason: "duplicate_content_hash"
  }
];

export const mockSummary: RunSummary = {
  run_id: "run_capture_done",
  app_id: "web_portal",
  status: "capture_completed",
  valid_total: 1240,
  fixed_count: 4,
  low_count: 1236,
  high_count: 0,
  rejected_count: 31,
  retry_round: 0,
  target_min: 1000,
  target_max: 5000
};
