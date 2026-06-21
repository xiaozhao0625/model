import { Copy, FolderOpen } from "lucide-react";
import { useState } from "react";
import { PageHeader } from "../components/layout/page-header";
import { Card } from "../components/ui/card";

const reports = [
  {
    title: "运行摘要",
    tech: "summary.json",
    path: "D:\\work\\app-shot\\runs\\v3\\<run_id>\\summary.json",
    stats: "processed / accepted / rejected / failed / quarantined / action_count"
  },
  {
    title: "重复帧解释报告",
    tech: "duplicate explanation report",
    path: "D:\\work\\app-shot\\reports\\duplicate_explain_<run_id>.md",
    stats: "exact_duplicate_count / near_duplicate_count / action_representative_accepted_count"
  },
  {
    title: "批量采集报告",
    tech: "batch capture report",
    path: "D:\\work\\app-shot\\reports\\v3_batch_capture_report.md",
    stats: "每个软件 accepted/rejected/action_count/风险结论"
  },
  {
    title: "系统自检报告",
    tech: "self check report",
    path: "D:\\work\\app-shot\\reports\\v3_self_check_report.md",
    stats: "PaddleOCR GPU / ShowUI / input gateway / full_auto_capture_ready"
  }
];

export function V3ReportsRoute() {
  const [message, setMessage] = useState("报告中心只展示本地路径，文件内容由采集脚本持续生成。");

  async function copyPath(path: string) {
    await navigator.clipboard?.writeText(path);
    setMessage(`已复制路径：${path}`);
  }

  async function openFolder(path: string) {
    const folder = path.includes("<run_id>") ? "D:\\work\\app-shot\\runs\\v3" : "D:\\work\\app-shot\\reports";
    await navigator.clipboard?.writeText(folder);
    setMessage(`已复制可打开文件夹路径：${folder}`);
  }

  return (
    <div>
      <PageHeader title="报告中心" description="集中查看运行摘要、重复帧解释报告、批量采集报告和系统自检报告。" />
      <div className="grid gap-4 xl:grid-cols-2">
        {reports.map((report) => (
          <Card key={report.title} title={report.title} eyebrow={report.tech}>
            <div className="space-y-3 text-sm">
              <Detail label="报告路径" value={report.path} />
              <Detail label="核心统计" value={report.stats} />
              <div className="flex flex-wrap gap-2">
                <button className="rounded-lg border border-blue-500/40 px-3 py-2 text-sm text-blue-100" onClick={() => void copyPath(report.path)}>
                  <Copy size={15} className="mr-1 inline" />
                  复制路径
                </button>
                <button className="rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200" onClick={() => void openFolder(report.path)}>
                  <FolderOpen size={15} className="mr-1 inline" />
                  打开文件夹
                </button>
              </div>
            </div>
          </Card>
        ))}
      </div>
      <p className="mt-4 text-sm text-slate-400">{message}</p>
    </div>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-slate-500">{label}</p>
      <p className="break-all font-mono text-xs text-slate-300">{value}</p>
    </div>
  );
}
