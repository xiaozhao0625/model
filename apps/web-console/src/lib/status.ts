import type { RunStatus } from "./api-types";

export const statusLabels: Record<RunStatus, string> = {
  pending: "Pending",
  launching: "Launching",
  waiting_manual: "Waiting Manual",
  profiling: "Profiling",
  running: "Running",
  capture_completed: "Capture Completed",
  upload_pending: "Upload Pending",
  uploaded_confirmed: "Uploaded Confirmed",
  local_deleted: "Local Deleted",
  completed: "Completed",
  needs_manual_seed: "Needs Manual Seed",
  failed_low_yield: "Failed Low Yield",
  skipped_risk: "Skipped Risk"
};

export const statusTone: Record<RunStatus, string> = {
  pending: "border-slate-500/40 bg-slate-500/10 text-slate-300",
  launching: "border-blue-500/40 bg-blue-500/10 text-blue-300",
  waiting_manual: "border-amber-500/40 bg-amber-500/10 text-amber-300",
  profiling: "border-cyan-500/40 bg-cyan-500/10 text-cyan-300",
  running: "border-emerald-500/40 bg-emerald-500/10 text-emerald-300",
  capture_completed: "border-emerald-400/50 bg-emerald-400/10 text-emerald-200",
  upload_pending: "border-amber-400/50 bg-amber-400/10 text-amber-200",
  uploaded_confirmed: "border-blue-400/50 bg-blue-400/10 text-blue-200",
  local_deleted: "border-purple-400/50 bg-purple-400/10 text-purple-200",
  completed: "border-slate-400/50 bg-slate-400/10 text-slate-200",
  needs_manual_seed: "border-orange-400/50 bg-orange-400/10 text-orange-200",
  failed_low_yield: "border-red-400/50 bg-red-400/10 text-red-200",
  skipped_risk: "border-red-400/50 bg-red-400/10 text-red-200"
};

export const lifecycleSteps: RunStatus[] = [
  "pending",
  "launching",
  "profiling",
  "running",
  "capture_completed",
  "upload_pending",
  "uploaded_confirmed",
  "local_deleted",
  "completed"
];

export function isTerminalStatus(status: RunStatus): boolean {
  return status === "completed" || status === "failed_low_yield" || status === "skipped_risk";
}
