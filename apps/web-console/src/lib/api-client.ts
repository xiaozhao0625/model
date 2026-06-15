import type {
  ActionProposal,
  ApiEnvelope,
  AppRecord,
  ArtifactActionResult,
  ArtifactSampleRecord,
  GroundResult,
  BehaviorCandidateRecord,
  ModelDeploymentMatrix,
  OcrStatusRecord,
  P145BatchValidation,
  P145DashboardRecord,
  P145ManualRequiredQueue,
  P145StuckRecovery,
  QualityReportRecord,
  RunArtifactRecord,
  RunListResponse,
  RunRecord,
  RunSummary,
  SceneClassifyResult,
  ToolHealthRecord,
  UploadRecord,
  WorkerRecord
} from "./api-types";
import {
  mockApps,
  mockBehaviorCandidates,
  mockModelDeploymentMatrix,
  mockOcrStatus,
  mockModelProviders,
  mockQualityReports,
  mockRuns,
  mockSummary,
  mockToolHealth,
  mockWorkers
} from "./mock-data";

type Fetcher = typeof fetch;
type RequestOptions = RequestInit & { disableFallback?: boolean; fallbackLabel?: string };

export interface ApiFallbackError {
  api_base_url: string;
  failed_endpoint: string;
  status?: number;
  error: string;
  cors_error: boolean;
}

export interface ApiClient {
  getHealth(): Promise<Record<string, unknown>>;
  listApps(): Promise<AppRecord[]>;
  createApp(app: AppRecord): Promise<AppRecord>;
  listRuns(params?: Record<string, string | number | undefined>): Promise<RunListResponse>;
  createRun(payload: { run_id: string; app_id: string; target_min?: number; target_max?: number }): Promise<RunRecord>;
  getRun(runId: string): Promise<RunRecord>;
  startRun(runId: string): Promise<RunRecord>;
  markRunFailedLowYield(runId: string): Promise<RunRecord>;
  getRunSummary(runId: string): Promise<RunSummary>;
  getRunArtifacts(runId: string): Promise<RunArtifactRecord>;
  getRunArtifactSamples(runId: string, bucket: string, limit?: number): Promise<ArtifactSampleRecord[]>;
  openRunArtifactFolder(runId: string, payload?: { bucket?: string; file_id?: string }): Promise<ArtifactActionResult>;
  packageRunArtifactSample(runId: string, payload?: { buckets?: string[]; limit_per_bucket?: number }): Promise<ArtifactActionResult>;
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
  getModelDeploymentMatrix(): Promise<ModelDeploymentMatrix>;
  listQualityReports(): Promise<QualityReportRecord[]>;
  getOcrStatus(): Promise<OcrStatusRecord>;
  listBehaviorCandidates(): Promise<BehaviorCandidateRecord[]>;
  getBehaviorCandidate(candidatePackId: string): Promise<BehaviorCandidateRecord>;
  approveBehaviorCandidate(candidatePackId: string): Promise<BehaviorCandidateRecord>;
  rejectBehaviorCandidate(candidatePackId: string): Promise<BehaviorCandidateRecord>;
  rollbackBehaviorCandidate(candidatePackId: string): Promise<BehaviorCandidateRecord>;
  getToolHealth(): Promise<ToolHealthRecord>;
  getP145OperatorDashboard(): Promise<P145DashboardRecord>;
  validateP145BatchTasks(payload: { tasks: Array<Record<string, unknown>>; dry_run?: boolean }): Promise<P145BatchValidation>;
  getP145ManualRequired(): Promise<P145ManualRequiredQueue>;
  recoverP145StuckTasks(): Promise<P145StuckRecovery>;
  isUsingMockFallback(): boolean;
  getBaseUrl(): string;
  getFallbackError(): ApiFallbackError | null;
}

function getRuntimeBaseUrl(): string {
  if (typeof window !== "undefined" && window.location.hostname) {
    return `${window.location.protocol}//${window.location.hostname}:8000`;
  }
  return "http://localhost:8000";
}

const defaultBaseUrl = import.meta.env.VITE_MASTER_API_URL || import.meta.env.VITE_API_BASE_URL || getRuntimeBaseUrl();

export function createApiClient(baseUrl = defaultBaseUrl, fetcher: Fetcher = fetch): ApiClient {
  let usingMockFallback = false;
  let fallbackError: ApiFallbackError | null = null;
  const root = baseUrl.replace(/\/$/, "");

  async function request<T>(path: string, fallback: T, options: RequestOptions = {}): Promise<T> {
    let status: number | undefined;
    try {
      const response = await fetcher(`${root}${path}`, {
        headers: { "Content-Type": "application/json", ...(options.headers || {}) },
        ...options
      });
      status = response.status;
      if (!response.ok) {
        throw new Error(`${options.fallbackLabel || path} failed with ${response.status}`);
      }
      const envelope = (await response.json()) as ApiEnvelope<T>;
      const success = envelope.ok === true || envelope.code === 0;
      if (!success || envelope.data === undefined) {
        throw new Error(envelope.error || envelope.message || `${options.fallbackLabel || path} returned an error`);
      }
      usingMockFallback = false;
      fallbackError = null;
      return envelope.data;
    } catch (error) {
      usingMockFallback = true;
      fallbackError = {
        api_base_url: root,
        failed_endpoint: path,
        status,
        error: error instanceof Error ? error.message : String(error),
        cors_error: status === undefined
      };
      if (options.disableFallback) {
        throw error;
      }
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
        disableFallback: true,
        fallbackLabel: "create app"
      }),
    listRuns: async (params = {}) => {
      const query = new URLSearchParams();
      for (const [key, value] of Object.entries(params)) {
        if (value !== undefined && value !== "" && value !== "all") {
          query.set(key, String(value));
        }
      }
      const fallback = {
        items: mockRuns,
        total: mockRuns.length,
        limit: Number(params.limit || 50),
        offset: Number(params.offset || 0),
        sort: String(params.sort || "created_at_desc"),
        filters: {}
      } satisfies RunListResponse;
      const data = await request<RunListResponse | RunRecord[]>(`/api/runs${query.toString() ? `?${query.toString()}` : ""}`, fallback);
      return Array.isArray(data)
        ? { items: data, total: data.length, limit: Number(params.limit || 50), offset: Number(params.offset || 0), sort: String(params.sort || "created_at_desc"), filters: {} }
        : data;
    },
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
        { method: "POST", body: JSON.stringify(payload), disableFallback: true, fallbackLabel: "create run" }
      ),
    getRun: (runId) => request(`/api/runs/${runId}`, mockRuns.find((run) => run.run_id === runId) || mockRuns[0]),
    startRun: (runId) =>
      request(`/api/runs/${runId}/start`, { ...(mockRuns.find((run) => run.run_id === runId) || mockRuns[0]), status: "running" }),
    markRunFailedLowYield: (runId) =>
      request(
        `/api/runs/${runId}/mark-failed-low-yield`,
        { ...(mockRuns.find((run) => run.run_id === runId) || mockRuns[0]), status: "failed_low_yield" },
        {
          method: "POST",
          body: JSON.stringify({ operator_action: "mark_failed_low_yield" }),
          disableFallback: true,
          fallbackLabel: "mark failed low yield"
        }
      ),
    getRunSummary: (runId) =>
      request(`/api/runs/${runId}/summary`, {
        ...mockSummary,
        ...(mockRuns.find((run) => run.run_id === runId) || {})
      }),
    getRunArtifacts: (runId) =>
      request(`/api/runs/${runId}/artifacts`, {
        run_id: runId,
        task_id: runId,
        worker_id: "mock_worker",
        worker_role: "Mock Worker",
        worker_host: "mock",
        artifact_root: "D:\\work\\runs\\<run_id>",
        status: "mock",
        summary: {},
        bucket_counts: {},
        sample_files: [],
        has_meta_jsonl: false,
        has_summary_json: false,
        can_open_folder: false,
        can_download_sample: false
      }),
    getRunArtifactSamples: (runId, bucket, limit = 20) => request(`/api/runs/${runId}/artifacts/samples?bucket=${encodeURIComponent(bucket)}&limit=${limit}`, []),
    openRunArtifactFolder: (runId, payload = {}) =>
      request(
        `/api/runs/${runId}/artifact-actions/open-folder`,
        { run_id: runId, worker_id: "mock_worker", status: "mock_unavailable", desktop_session_required: true },
        { method: "POST", body: JSON.stringify(payload), fallbackLabel: "open artifact folder" }
      ),
    packageRunArtifactSample: (runId, payload = {}) =>
      request(
        `/api/runs/${runId}/artifact-actions/package-sample`,
        { run_id: runId, worker_id: "mock_worker", status: "mock_unavailable", file_count: 0 },
        { method: "POST", body: JSON.stringify(payload), fallbackLabel: "package artifact sample" }
      ),
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
    getModelDeploymentMatrix: () => request("/api/model/deployment-matrix", mockModelDeploymentMatrix),
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
    getP145OperatorDashboard: () =>
      request("/api/p14-5/operator-dashboard", {
        status: "mock",
        run_count: mockRuns.length,
        status_counts: {},
        manual_required: 0,
        disk: { status: "mock", nodes: [], production_scale_capture: false },
        guards: {
          production_scale_capture: false,
          online_inference: false,
          model_action_control: false,
          automatic_upload: false,
          unconfirmed_cleanup: false
        }
      }),
    validateP145BatchTasks: (payload) =>
      request(
        "/api/p14-5/batch-tasks/validate",
        {
          status: "mock",
          dry_run: true,
          production_scale_capture: false,
          online_inference: false,
          model_action_control: false,
          task_count: payload.tasks.length,
          valid_count: 0,
          blocked_count: payload.tasks.length,
          tasks: []
        },
        { method: "POST", body: JSON.stringify({ ...payload, dry_run: payload.dry_run ?? true }) }
      ),
    getP145ManualRequired: () => request("/api/p14-5/manual-required", { status: "mock", count: 0, items: [] }),
    recoverP145StuckTasks: () =>
      request(
        "/api/p14-5/recovery/stuck-tasks",
        { status: "mock", dry_run: true, candidate_count: 0, candidates: [], mutated: false },
        { method: "POST", body: JSON.stringify({ dry_run: true }) }
      ),
    isUsingMockFallback: () => usingMockFallback,
    getBaseUrl: () => root,
    getFallbackError: () => fallbackError
  };
}

export const apiClient = createApiClient();
