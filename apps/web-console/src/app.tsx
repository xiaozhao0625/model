import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./components/layout/app-shell";
import { AppsRoute } from "./routes/apps";
import { BehaviorCandidatesRoute } from "./routes/behavior-candidates";
import { DashboardRoute } from "./routes/dashboard";
import { ModelGatewayRoute } from "./routes/model-gateway";
import { OcrStatusRoute } from "./routes/ocr-status";
import { QualityReportsRoute } from "./routes/quality-reports";
import { RunDetailRoute } from "./routes/run-detail";
import { RunsRoute } from "./routes/runs";
import { SettingsRoute } from "./routes/settings";
import { ToolHealthRoute } from "./routes/tool-health";
import { UploadRoute } from "./routes/upload";
import { WorkersRoute } from "./routes/workers";

export function AppRoutes() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<DashboardRoute />} />
        <Route path="/dashboard" element={<DashboardRoute />} />
        <Route path="/apps" element={<AppsRoute />} />
        <Route path="/runs" element={<RunsRoute />} />
        <Route path="/runs/:runId" element={<RunDetailRoute />} />
        <Route path="/workers" element={<WorkersRoute />} />
        <Route path="/upload" element={<UploadRoute />} />
        <Route path="/model-gateway" element={<ModelGatewayRoute />} />
        <Route path="/quality-reports" element={<QualityReportsRoute />} />
        <Route path="/ocr-status" element={<OcrStatusRoute />} />
        <Route path="/behavior-candidates" element={<BehaviorCandidatesRoute />} />
        <Route path="/tool-health" element={<ToolHealthRoute />} />
        <Route path="/settings" element={<SettingsRoute />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppShell>
  );
}
