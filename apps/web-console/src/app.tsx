import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./components/layout/app-shell";
import { AppsRoute } from "./routes/apps";
import { DashboardRoute } from "./routes/dashboard";
import { ModelGatewayRoute } from "./routes/model-gateway";
import { RunDetailRoute } from "./routes/run-detail";
import { RunsRoute } from "./routes/runs";
import { SettingsRoute } from "./routes/settings";
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
        <Route path="/settings" element={<SettingsRoute />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppShell>
  );
}
