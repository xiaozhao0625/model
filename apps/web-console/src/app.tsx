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
import { V3ActionsRoute } from "./routes/v3-actions";
import { V3DashboardRoute } from "./routes/v3-dashboard";
import { V3CurrentRunRoute } from "./routes/v3-current-run";
import { V3GalleryRoute } from "./routes/v3-gallery";
import { V3GameRoute } from "./routes/v3-game";
import { V3NewCaptureRoute } from "./routes/v3-new-capture";
import { V3ReportsRoute } from "./routes/v3-reports";
import { WorkersRoute } from "./routes/workers";

export function AppRoutes() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<Navigate to="/v3" replace />} />
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
        <Route path="/v3" element={<V3DashboardRoute />} />
        <Route path="/v3/new" element={<V3NewCaptureRoute />} />
        <Route path="/v3/current" element={<V3CurrentRunRoute />} />
        <Route path="/v3/gallery" element={<V3GalleryRoute />} />
        <Route path="/v3/actions" element={<V3ActionsRoute />} />
        <Route path="/v3/runs/:runId/gallery" element={<V3GalleryRoute />} />
        <Route path="/v3/runs/:runId/actions" element={<V3ActionsRoute />} />
        <Route path="/v3/game" element={<V3GameRoute />} />
        <Route path="/v3/reports" element={<V3ReportsRoute />} />
        <Route path="/settings" element={<SettingsRoute />} />
        <Route path="*" element={<Navigate to="/v3" replace />} />
      </Routes>
    </AppShell>
  );
}
