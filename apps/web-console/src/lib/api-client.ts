import type {
  ActionProposal,
  ApiEnvelope,
  AppRecord,
  GroundResult,
  BehaviorCandidateRecord,
  OcrStatusRecord,
  QualityReportRecord,
  RunRecord,
  RunSummary,
  SceneClassifyResult,
  ToolHealthRecord,
  UploadRecord,
  V3Health,
  V3ActionRecord,
  V3RunRecord,
  V3Summary,
  V3TaskConfig,
  WorkerRecord
} from "./api-types";
import {
  mockApps,
  mockBehaviorCandidates,
  mockOcrStatus,
  mockModelProviders,
  mockQualityReports,
  mockRuns,
  mockSummary,
  mockToolHealth,
  mockUploads,
  mockWorkers
} from "./mock-data";

type Fetcher = typeof fetch;
type RequestOptions = RequestInit & { fallbackLabel?: string };

export interface ApiClient {
  getHealth(): Promise<Record<string, unknown>>;
  listApps(): Promise<AppRecord[]>;
  createApp(app: AppRecord): Promise<AppRecord>;
  listRuns(): Promise<RunRecord[]>;
  createRun(payload: { run_id: string; app_id: string; target_min?: number; target_max?: number }): Promise<RunRecord>;
  getRun(runId: string): Promise<RunRecord>;
  startRun(runId: string): Promise<RunRecord>;
  getRunSummary(runId: string): Promise<RunSummary>;
  listWorkers(): Promise<WorkerRecord[]>;
  registerWorker(worker: { worker_id: string; type: string; capabilities: string[] }): Promise<WorkerRecord>;
  heartbeatWorker(workerId: string): Promise<WorkerRecord>;
  generateUploadManifest(runId: string): Promise<UploadRecord>;
  confirmUpload(runId: string): Promise<UploadRecord>;
  cleanupLocal(runId: string): Promise<UploadRecord>;
  finalizeRun(runId: string): Promise<UploadRecord>;
  sceneClassify(payload: Record<string, unknown>): Promise<SceneClassifyResult>;
  ground(payload: Record<string, unknown>): Promise<GroundResult>;
  act(payload: Record<string, unknown>): Promise<ActionProposal>;
  listModelProviders(): Promise<typeof mockModelProviders>;
  listQualityReports(): Promise<QualityReportRecord[]>;
  getOcrStatus(): Promise<OcrStatusRecord>;
  listBehaviorCandidates(): Promise<BehaviorCandidateRecord[]>;
  getBehaviorCandidate(candidatePackId: string): Promise<BehaviorCandidateRecord>;
  approveBehaviorCandidate(candidatePackId: string): Promise<BehaviorCandidateRecord>;
  rejectBehaviorCandidate(candidatePackId: string): Promise<BehaviorCandidateRecord>;
  rollbackBehaviorCandidate(candidatePackId: string): Promise<BehaviorCandidateRecord>;
  getToolHealth(): Promise<ToolHealthRecord>;
  getV3Health(): Promise<V3Health>;
  getV3Defaults(): Promise<V3TaskConfig>;
  listV3Runs(): Promise<V3RunRecord[]>;
  createV3Run(payload: { config: V3TaskConfig }): Promise<V3RunRecord>;
  startV3Run(runId: string): Promise<V3RunRecord>;
  pauseV3Run(runId: string): Promise<V3RunRecord>;
  stopV3Run(runId: string): Promise<V3RunRecord>;
  getV3Summary(runId: string): Promise<V3Summary>;
  getV3Actions(runId: string): Promise<V3ActionRecord[]>;
  isUsingMockFallback(): boolean;
}

const defaultBaseUrl = import.meta.env.VITE_MASTER_API_URL || "http://localhost:8000";

export function createApiClient(baseUrl = defaultBaseUrl, fetcher: Fetcher = fetch): ApiClient {
  let usingMockFallback = false;
  const root = baseUrl.replace(/\/$/, "");

  async function request<T>(path: string, fallback: T, options: RequestOptions = {}): Promise<T> {
    try {
      const response = await fetcher(`${root}${path}`, {
        headers: { "Content-Type": "application/json", ...(options.headers || {}) },
        ...options
      });
      if (!response.ok) {
        throw new Error(`${options.fallbackLabel || path} failed with ${response.status}`);
      }
      const envelope = (await response.json()) as ApiEnvelope<T>;
      if (!envelope.ok || envelope.data === undefined) {
        throw new Error(envelope.error || `${options.fallbackLabel || path} returned an error`);
      }
      return envelope.data;
    } catch {
      usingMockFallback = true;
      // mock fallback keeps the console usable when the local Master API is offline.
      return fallback;
    }
  }

  return {
    getHealth: () => request("/health", { status: "mock", database_backend: "offline" }),
    listApps: () => request("/api/apps", mockApps),
    createApp: (app) =>
      request("/api/apps", app, {
        method: "POST",
        body: JSON.stringify(app),
        fallbackLabel: "create app"
      }),
    listRuns: () => request("/api/runs", mockRuns),
    createRun: (payload) =>
      request(
        "/api/runs",
        {
          run_id: payload.run_id,
          app_id: payload.app_id,
          status: "pending",
          valid_total: 0,
          fixed_count: 0,
          low_count: 0,
          high_count: 0,
          rejected_count: 0,
          retry_round: 0,
          target_min: payload.target_min || 1000,
          target_max: payload.target_max || 5000
        } satisfies RunRecord,
        { method: "POST", body: JSON.stringify(payload), fallbackLabel: "create run" }
      ),
    getRun: (runId) => request(`/api/runs/${runId}`, mockRuns.find((run) => run.run_id === runId) || mockRuns[0]),
    startRun: (runId) =>
      request(`/api/runs/${runId}/start`, { ...(mockRuns.find((run) => run.run_id === runId) || mockRuns[0]), status: "running" }),
    getRunSummary: (runId) =>
      request(`/api/runs/${runId}/summary`, {
        ...mockSummary,
        ...(mockRuns.find((run) => run.run_id === runId) || {})
      }),
    listWorkers: () => request("/api/workers", mockWorkers),
    registerWorker: (worker) =>
      request(
        "/api/workers/register",
        { ...worker, state: "idle", heartbeat: new Date().toISOString() },
        { method: "POST", body: JSON.stringify(worker), fallbackLabel: "register worker" }
      ),
    heartbeatWorker: (workerId) =>
      request(`/api/workers/${workerId}/heartbeat`, mockWorkers.find((worker) => worker.worker_id === workerId) || mockWorkers[0], {
        method: "POST"
      }),
    generateUploadManifest: (runId) =>
      request(`/api/runs/${runId}/upload-manifest`, { upload_id: `${runId}:manifest`, run_id: runId, status: "upload_pending" }, { method: "POST" }),
    confirmUpload: (runId) =>
      request(`/api/runs/${runId}/confirm-upload`, { upload_id: `${runId}:confirm`, run_id: runId, status: "uploaded_confirmed" }, { method: "POST" }),
    cleanupLocal: (runId) =>
      request(`/api/runs/${runId}/cleanup`, { upload_id: `${runId}:cleanup`, run_id: runId, status: "local_deleted" }, { method: "POST" }),
    finalizeRun: (runId) =>
      request(`/api/runs/${runId}/finalize`, { upload_id: `${runId}:finalize`, run_id: runId, status: "completed" }, { method: "POST" }),
    sceneClassify: (payload) =>
      request(
        "/api/model/scene_classify",
        { scene_class: "unknown", confidence: 0.51, reason: "mock fallback scene", provider_name: "mock_gateway" },
        { method: "POST", body: JSON.stringify(payload) }
      ),
    ground: (payload) =>
      request(
        "/api/model/ground",
        { found: false, x: null, y: null, confidence: 0, reason: "mock fallback only", provider_name: "mock_gateway" },
        { method: "POST", body: JSON.stringify(payload) }
      ),
    act: (payload) =>
      request(
        "/api/model/act",
        {
          action_type: "request_manual",
          confidence: 1,
          reason: "mock fallback blocks execution",
          target: null,
          keys: null,
          risk_flags: ["mock_fallback"],
          provider_name: "mock_gateway"
        },
        { method: "POST", body: JSON.stringify(payload) }
      ),
    listModelProviders: async () => mockModelProviders,
    listQualityReports: () => request("/api/quality-reports", mockQualityReports),
    getOcrStatus: () => request("/api/ocr/status", mockOcrStatus),
    listBehaviorCandidates: () => request("/api/behavior-candidates", mockBehaviorCandidates),
    getBehaviorCandidate: (candidatePackId) =>
      request(
        `/api/behavior-candidates/${candidatePackId}`,
        mockBehaviorCandidates.find((candidate) => candidate.candidate_pack_id === candidatePackId) || mockBehaviorCandidates[0]
      ),
    approveBehaviorCandidate: (candidatePackId) =>
      request(
        `/api/behavior-candidates/${candidatePackId}/approve`,
        {
          ...(mockBehaviorCandidates.find((candidate) => candidate.candidate_pack_id === candidatePackId) || mockBehaviorCandidates[0]),
          status: "approved"
        },
        { method: "POST", body: JSON.stringify({}) }
      ),
    rejectBehaviorCandidate: (candidatePackId) =>
      request(
        `/api/behavior-candidates/${candidatePackId}/reject`,
        {
          ...(mockBehaviorCandidates.find((candidate) => candidate.candidate_pack_id === candidatePackId) || mockBehaviorCandidates[0]),
          status: "rejected"
        },
        { method: "POST", body: JSON.stringify({}) }
      ),
    rollbackBehaviorCandidate: (candidatePackId) =>
      request(
        `/api/behavior-candidates/${candidatePackId}/rollback`,
        {
          ...(mockBehaviorCandidates.find((candidate) => candidate.candidate_pack_id === candidatePackId) || mockBehaviorCandidates[0]),
          status: "pending_review"
        },
        { method: "POST", body: JSON.stringify({}) }
      ),
    getToolHealth: () => request("/api/tool-health", mockToolHealth),
    getV3Health: () =>
      request("/api/v3/health", {
        status: "degraded",
        ocr: [],
        models: [],
        complete_auto_mode_ready: false,
        full_auto_capture_ready: false,
        ocr_gpu_ready: false,
        ocr_performance_ready: false,
        ocr_production_ready: false,
        input_gateway_ready: false,
        cursor_read_ready: false,
        mouse_click_ready: false,
        same_desktop_session_ready: false,
        same_integrity_ready: false,
        interactive_desktop_ready: false,
        click_backend: "dry_run_backend",
        input_gateway_blockers: ["api_offline"],
        input_gateway_diagnosis_path: null,
        readiness_blockers: ["api_offline"],
        defaults: {
          app_name: "manual_target",
          app_type: "auto",
          target_language: "zh",
          capture_source: "folder_watch",
          capture_interval_ms: 1000,
          save_root: "runs/v3",
          enable_ocr: true,
          enable_ui_model: true,
          enable_auto_click: false,
          enable_game_explorer: false,
          delete_rejected: false,
          max_images: 100,
          max_actions: 5,
          safety_mode: "strict",
          observe_only: true,
          must_have_text: false
        }
      }),
    getV3Defaults: () => request("/api/v3/config/defaults", mockV3Defaults()),
    listV3Runs: () => request("/api/v3/runs", []),
    createV3Run: (payload) => request("/api/v3/runs", mockV3Run(payload.config), { method: "POST", body: JSON.stringify(payload) }),
    startV3Run: (runId) => request(`/api/v3/runs/${runId}/start`, mockV3Run(mockV3Defaults(), runId, "running"), { method: "POST" }),
    pauseV3Run: (runId) => request(`/api/v3/runs/${runId}/pause`, mockV3Run(mockV3Defaults(), runId, "paused"), { method: "POST" }),
    stopV3Run: (runId) => request(`/api/v3/runs/${runId}/stop`, mockV3Run(mockV3Defaults(), runId, "stopped"), { method: "POST" }),
    getV3Summary: (runId) =>
      request(`/api/v3/runs/${runId}/summary`, {
        run_id: runId,
        status: "created",
        counts: {},
        observe_only: true,
        auto_click_ready: false,
        full_auto_capture_ready: false,
        model_ready: false,
        ocr_ready: true,
        ocr_gpu_ready: false,
        ocr_performance_ready: false,
        ocr_production_ready: false,
        input_gateway_ready: false,
        cursor_read_ready: false,
        mouse_click_ready: false,
        same_desktop_session_ready: false,
        same_integrity_ready: false,
        interactive_desktop_ready: false,
        click_backend: "dry_run_backend",
        input_gateway_blockers: ["api_offline"],
        readiness_blockers: ["api_offline"],
        safety_gate_ready: true
      }),
    getV3Actions: (runId) => request(`/api/v3/runs/${runId}/actions`, []),
    isUsingMockFallback: () => usingMockFallback || mockUploads.length > 0
  };
}

export const apiClient = createApiClient();

function mockV3Defaults(): V3TaskConfig {
  return {
    app_name: "manual_target",
    app_type: "auto",
    target_language: "zh",
    capture_source: "folder_watch",
    capture_interval_ms: 1000,
    save_root: "runs/v3",
    enable_ocr: true,
    enable_ui_model: true,
    enable_auto_click: false,
    enable_game_explorer: false,
    delete_rejected: false,
    max_images: 100,
    max_actions: 5,
    safety_mode: "strict",
    observe_only: true,
    must_have_text: false
  };
}

function mockV3Run(config: V3TaskConfig, runId = "mock_v3_run", status: V3RunRecord["status"] = "created"): V3RunRecord {
  return {
    run_id: runId,
    status,
    config,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    counts: { pending: 0, accepted: 0, rejected: 0, deleted: 0, manual_review: 0, events: 0, actions: 0 },
    last_error: null
  };
}
