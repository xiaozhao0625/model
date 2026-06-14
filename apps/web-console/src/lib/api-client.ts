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
  isUsingMockFallback(): boolean;
  getBaseUrl(): string;
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
      const success = envelope.ok === true || envelope.code === 0;
      if (!success || envelope.data === undefined) {
        throw new Error(envelope.error || envelope.message || `${options.fallbackLabel || path} returned an error`);
      }
      usingMockFallback = false;
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
    isUsingMockFallback: () => usingMockFallback,
    getBaseUrl: () => root
  };
}

export const apiClient = createApiClient();
