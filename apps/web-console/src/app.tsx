import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./components/layout/app-shell";
import { RouteBoundary } from "./components/layout/route-boundary";
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
  const route = (element: JSX.Element) => <RouteBoundary>{element}</RouteBoundary>;
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={route(<DashboardRoute />)} />
        <Route path="/dashboard" element={route(<DashboardRoute />)} />
        <Route path="/apps" element={route(<AppsRoute />)} />
        <Route path="/runs" element={route(<RunsRoute />)} />
        <Route path="/runs/:runId" element={route(<RunDetailRoute />)} />
        <Route path="/workers" element={route(<WorkersRoute />)} />
        <Route path="/upload" element={route(<UploadRoute />)} />
        <Route path="/model-gateway" element={route(<ModelGatewayRoute />)} />
        <Route path="/quality-reports" element={route(<QualityReportsRoute />)} />
        <Route path="/ocr-status" element={route(<OcrStatusRoute />)} />
        <Route path="/behavior-candidates" element={route(<BehaviorCandidatesRoute />)} />
        <Route path="/tool-health" element={route(<ToolHealthRoute />)} />
        <Route path="/settings" element={route(<SettingsRoute />)} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppShell>
  );
}
