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
  V3InputStatus,
  V3FramePumpStartRequest,
  V3FramePumpStatus,
  V3CollectionExportResult,
  V3CollectionRecord,
  V3CollectionSummary,
  V3ActionRecord,
  V3ImageRecord,
  V3OpenPathResult,
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
  getV3ModelHealth(): Promise<V3Health>;
  getV3ActionHealth(): Promise<Record<string, unknown>>;
  getV3Defaults(): Promise<V3TaskConfig>;
  listV3Collections(): Promise<V3CollectionSummary[]>;
  createV3Collection(payload: { config: V3TaskConfig; start_immediately?: boolean }): Promise<V3CollectionRecord | { collection: V3CollectionRecord; run: V3RunRecord }>;
  getV3Collection(collectionId: string): Promise<V3CollectionRecord>;
  getV3CollectionSummary(collectionId: string): Promise<V3CollectionSummary>;
  getV3CollectionGallery(collectionId: string): Promise<V3ImageRecord[]>;
  continueV3Collection(collectionId: string): Promise<V3RunRecord>;
  stopV3Collection(collectionId: string): Promise<V3CollectionRecord>;
  exportV3Collection(collectionId: string): Promise<V3CollectionExportResult>;
  listV3Runs(): Promise<V3RunRecord[]>;
  createV3Run(payload: { config: V3TaskConfig; start_immediately?: boolean }): Promise<V3RunRecord>;
  startV3Run(runId: string): Promise<V3RunRecord>;
  pauseV3Run(runId: string): Promise<V3RunRecord>;
  resumeV3Run(runId: string): Promise<V3RunRecord>;
  stopV3Run(runId: string): Promise<V3RunRecord>;
  getV3RunStatus(runId: string): Promise<{ run: V3RunRecord; summary: V3Summary; input_status: V3InputStatus }>;
  getV3InputStatus(): Promise<V3InputStatus>;
  getV3FramePumpStatus(): Promise<V3FramePumpStatus>;
  startV3FramePump(payload?: V3FramePumpStartRequest): Promise<V3FramePumpStatus>;
  stopV3FramePump(): Promise<V3FramePumpStatus>;
  openV3InputFolder(): Promise<V3OpenPathResult>;
  getV3Summary(runId: string): Promise<V3Summary>;
  getV3Actions(runId: string): Promise<V3ActionRecord[]>;
  getV3Images(runId: string): Promise<V3ImageRecord[]>;
  getV3ImagePreviewUrl(runId: string, imageId: string): string;
  getV3ImageThumbnailUrl(runId: string, imageId: string): string;
  revealV3Image(runId: string, imageId: string): Promise<V3OpenPathResult>;
  openV3RunFolder(runId: string): Promise<V3OpenPathResult>;
  isUsingMockFallback(): boolean;
}

const defaultBaseUrl = import.meta.env.VITE_MASTER_API_URL || "";
const maxActionHelpText =
  "最大动作数是自动点击或键鼠动作次数，不是截图数量。为了安全，单次任务最多允许 100 次软件动作；游戏动作最多允许 200 次。";

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

  async function requestV3<T>(path: string, options: RequestOptions = {}): Promise<T> {
    const response = await fetcher(`${root}${path}`, {
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      ...options
    });
    if (!response.ok) {
      throw new Error(await formatApiError(response, options.fallbackLabel || path));
    }
    const envelope = (await response.json()) as ApiEnvelope<T>;
    if (!envelope.ok || envelope.data === undefined) {
      throw new Error(formatEnvelopeError(envelope, options.fallbackLabel || path));
    }
    return envelope.data;
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
    getV3Health: () => requestV3<V3Health>("/api/v3/health"),
    getV3ModelHealth: () => requestV3<V3Health>("/api/v3/model/health"),
    getV3ActionHealth: () => requestV3<Record<string, unknown>>("/api/v3/action/health"),
    getV3Defaults: () => requestV3<V3TaskConfig>("/api/v3/config/defaults"),
    listV3Collections: () => requestV3<V3CollectionSummary[]>("/api/v3/collections"),
    createV3Collection: (payload) =>
      requestV3<V3CollectionRecord | { collection: V3CollectionRecord; run: V3RunRecord }>("/api/v3/collections", { method: "POST", body: JSON.stringify(payload) }),
    getV3Collection: (collectionId) => requestV3<V3CollectionRecord>(`/api/v3/collections/${collectionId}`),
    getV3CollectionSummary: (collectionId) => requestV3<V3CollectionSummary>(`/api/v3/collections/${collectionId}/summary`),
    getV3CollectionGallery: (collectionId) => requestV3<V3ImageRecord[]>(`/api/v3/collections/${collectionId}/gallery`),
    continueV3Collection: (collectionId) => requestV3<V3RunRecord>(`/api/v3/collections/${collectionId}/continue`, { method: "POST" }),
    stopV3Collection: (collectionId) => requestV3<V3CollectionRecord>(`/api/v3/collections/${collectionId}/stop`, { method: "POST" }),
    exportV3Collection: (collectionId) => requestV3<V3CollectionExportResult>(`/api/v3/collections/${collectionId}/export`, { method: "POST" }),
    listV3Runs: () => requestV3<V3RunRecord[]>("/api/v3/runs"),
    createV3Run: (payload) => requestV3<V3RunRecord>("/api/v3/runs", { method: "POST", body: JSON.stringify(payload) }),
    startV3Run: (runId) => requestV3<V3RunRecord>(`/api/v3/runs/${runId}/start`, { method: "POST" }),
    pauseV3Run: (runId) => requestV3<V3RunRecord>(`/api/v3/runs/${runId}/pause`, { method: "POST" }),
    resumeV3Run: (runId) => requestV3<V3RunRecord>(`/api/v3/runs/${runId}/resume`, { method: "POST" }),
    stopV3Run: (runId) => requestV3<V3RunRecord>(`/api/v3/runs/${runId}/stop`, { method: "POST" }),
    getV3RunStatus: (runId) => requestV3<{ run: V3RunRecord; summary: V3Summary; input_status: V3InputStatus }>(`/api/v3/runs/${runId}/status`),
    getV3InputStatus: () => requestV3<V3InputStatus>("/api/v3/input/status"),
    getV3FramePumpStatus: () => requestV3<V3FramePumpStatus>("/api/v3/frame-pump/status"),
    startV3FramePump: (payload = { fps: 1, full_screen: true }) =>
      requestV3<V3FramePumpStatus>("/api/v3/frame-pump/start", { method: "POST", body: JSON.stringify(payload) }),
    stopV3FramePump: () => requestV3<V3FramePumpStatus>("/api/v3/frame-pump/stop", { method: "POST", body: JSON.stringify({}) }),
    openV3InputFolder: () => requestV3<V3OpenPathResult>("/api/v3/input/open-folder", { method: "POST", body: JSON.stringify({}) }),
    getV3Summary: (runId) => requestV3<V3Summary>(`/api/v3/runs/${runId}/summary`),
    getV3Actions: (runId) => requestV3<V3ActionRecord[]>(`/api/v3/runs/${runId}/actions`),
    getV3Images: (runId) => requestV3<V3ImageRecord[]>(`/api/v3/runs/${runId}/images`),
    getV3ImagePreviewUrl: (runId, imageId) => `${root}/api/v3/runs/${runId}/images/${imageId}/preview`,
    getV3ImageThumbnailUrl: (runId, imageId) => `${root}/api/v3/runs/${runId}/images/${imageId}/thumbnail`,
    revealV3Image: (runId, imageId) =>
      requestV3<V3OpenPathResult>(
        `/api/v3/runs/${runId}/images/${imageId}/reveal`,
        { method: "POST", body: JSON.stringify({}) }
      ),
    openV3RunFolder: (runId) =>
      requestV3<V3OpenPathResult>(`/api/v3/runs/${runId}/open-folder`, { method: "POST", body: JSON.stringify({}) }),
    isUsingMockFallback: () => usingMockFallback || mockUploads.length > 0
  };
}

export const apiClient = createApiClient();

function mockV3Defaults(): V3TaskConfig {
  return {
    task_name: "新采集任务",
    app_name: "manual_target",
    display_name: "新采集任务",
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
    target_accepted_min: 800,
    target_accepted_soft: 1000,
    target_accepted_max: 2000,
    max_images: 1500,
    max_actions: 20,
    safety_mode: "strict",
    observe_only: true,
    text_priority: true,
    must_have_text: true,
    allow_no_text_fill: false,
    no_text_fill_ratio: 0,
    text_policy: "strict_text",
    game_mode: "menu",
    allow_no_text_gameplay: false,
    max_game_actions: 50,
    game_action_preset: "screenshot_only",
    allow_wasd_mouse: false,
    safe_game_scene_confirmed: false,
    action_interval_ms: 1500
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

async function formatApiError(response: Response, label: string) {
  try {
    const envelope = (await response.json()) as ApiEnvelope<unknown>;
    return formatEnvelopeError(envelope, label, response.status);
  } catch {
    return `${label} 请求失败，状态码 ${response.status}`;
  }
}

function formatEnvelopeError(envelope: ApiEnvelope<unknown>, label: string, status?: number) {
  const detail = Array.isArray(envelope.detail) ? envelope.detail : [];
  if (detail.length > 0) {
    return detail
      .map((item) => {
        if (!item || typeof item !== "object") return String(item);
        const row = item as Record<string, unknown>;
        const field = row.field_label || row.field || "字段";
        const current = row.current_value !== undefined ? `当前值：${String(row.current_value)}。` : "";
        const range = row.allowed_range ? `允许范围：${String(row.allowed_range)}。` : "";
        const isActionLimit = row.field === "max_actions" || row.field === "max_game_actions";
        const message =
          typeof row.message === "string" && row.message.length > 0
            ? row.message
            : isActionLimit
              ? maxActionHelpText
              : "";
        return `${String(field)}不符合要求。${current}${range}${message}`;
      })
      .join("\n");
  }
  if (envelope.error) return envelope.error;
  return status ? `${label} 请求失败，状态码 ${status}` : `${label} 返回异常`;
}
