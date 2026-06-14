import { AlertTriangle, CheckCircle2, RefreshCw, ShieldAlert } from "lucide-react";
import { useEffect, useState } from "react";
import { PageHeader } from "../components/layout/page-header";
import { Badge } from "../components/ui/badge";
import { Card } from "../components/ui/card";
import { DataTable } from "../components/ui/table";
import { apiClient } from "../lib/api-client";
import type { QualityReportRecord } from "../lib/api-types";

export function QualityReportsRoute() {
  const [reports, setReports] = useState<QualityReportRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    void loadReports();
  }, []);

  async function loadReports() {
    setLoading(true);
    setError("");
    try {
      setReports(await apiClient.listQualityReports());
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setReports([]);
    } finally {
      setLoading(false);
    }
  }

  const report = reports[0] || null;
  const distribution = report?.reject_reason_distribution || {};
  const hasBrowserChrome = (report?.browser_chrome_count || 0) > 0;
  const hasTaskbar = (report?.taskbar_count || 0) > 0;
  const hasDangerousPage = (distribution.dangerous_page || 0) > 0 || (report?.ocr_risk_hit_count || 0) > 0;

  return (
    <div>
      <PageHeader title="Quality Reports" description="Inspect screenshot quality reports, rejection reasons, and contamination checks from the live Master API." />
      {loading ? <Card title="Loading" eyebrow="quality_report.json"><p className="text-sm text-slate-400">Loading quality reports...</p></Card> : null}
      {error ? (
        <Card title="Quality Reports Unavailable" eyebrow="error">
          <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-100">
            <p>{error}</p>
            <button className="mt-3 inline-flex min-h-9 items-center gap-2 rounded-lg border border-red-400/40 px-3 py-2 text-sm" onClick={() => void loadReports()}>
              <RefreshCw size={16} />
              Retry
            </button>
          </div>
        </Card>
      ) : null}
      {!loading && !error && reports.length === 0 ? (
        <Card title="Quality Reports" eyebrow="empty">
          <p className="text-sm text-slate-400">No quality reports have been ingested yet.</p>
        </Card>
      ) : null}
      {report ? (
        <>
          <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
            <Card title="Quality Overview" eyebrow="quality_report.json">
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                <Metric label="Total images" value={report.total_images} />
                <Metric label="clean count" value={report.accepted_count} tone="success" />
                <Metric label="rejected count" value={report.rejected_count} tone="danger" />
                <Metric label="pass rate" value={`${(report.quality_pass_rate * 100).toFixed(1)}%`} />
              </div>
              <div className="mt-4 grid gap-3 md:grid-cols-3">
                <RiskFlag active={hasBrowserChrome} label="browser_chrome_visible" />
                <RiskFlag active={hasTaskbar} label="os_taskbar_visible" />
                <RiskFlag active={hasDangerousPage} label="dangerous_page / ocr_risk_detected" />
              </div>
            </Card>
            <Card title="Reject Reason Distribution" eyebrow="rejected_quality_manifest">
              <div className="space-y-2">
                {Object.keys(distribution).length === 0 ? <p className="text-sm text-slate-400">No rejection reasons reported.</p> : null}
                {Object.entries(distribution).map(([reason, count]) => (
                  <div key={reason} className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950 px-3 py-2">
                    <span className="font-mono text-xs text-slate-300">{reason}</span>
                    <Badge className="border-slate-700 bg-slate-800 text-slate-200">{count}</Badge>
                  </div>
                ))}
              </div>
            </Card>
          </div>
          <Card title="Quality Details" eyebrow="core fields" className="mt-4">
            <DataTable columns={["run_id", "app_id", "black", "white", "blur", "wrong window", "browser chrome", "taskbar", "near duplicate", "OCR risk"]}>
              {reports.map((item) => (
                <tr key={item.run_id}>
                  <td className="font-mono text-blue-300">{item.run_id}</td>
                  <td className="font-mono text-slate-300">{item.app_id}</td>
                  <td>{item.black_screen_count}</td>
                  <td>{item.white_screen_count}</td>
                  <td>{item.blurry_count}</td>
                  <td>{item.wrong_window_count}</td>
                  <td>{item.browser_chrome_count}</td>
                  <td>{item.taskbar_count}</td>
                  <td>{item.near_duplicate_count}</td>
                  <td>{item.ocr_risk_hit_count}</td>
                </tr>
              ))}
            </DataTable>
          </Card>
        </>
      ) : null}
    </div>
  );
}

function Metric({ label, value, tone = "default" }: { label: string; value: string | number; tone?: "default" | "success" | "danger" }) {
  const toneClass = tone === "success" ? "text-emerald-200" : tone === "danger" ? "text-red-200" : "text-slate-100";
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950 p-3">
      <p className="text-xs text-slate-500">{label}</p>
      <p className={`mt-2 text-2xl font-semibold ${toneClass}`}>{value}</p>
    </div>
  );
}

function RiskFlag({ active, label }: { active: boolean; label: string }) {
  return (
    <div className={`rounded-lg border p-3 ${active ? "border-red-500/40 bg-red-500/10" : "border-emerald-500/30 bg-emerald-500/10"}`}>
      <div className="flex items-center gap-2">
        {active ? <ShieldAlert size={18} className="text-red-300" /> : <CheckCircle2 size={18} className="text-emerald-300" />}
        <span className={active ? "text-red-100" : "text-emerald-100"}>{active ? "Detected" : "Clear"}</span>
      </div>
      <p className="mt-2 break-all font-mono text-xs text-slate-400">
        <AlertTriangle size={14} className="mr-1 inline" />
        {label}
      </p>
    </div>
  );
}
