import { ScanText } from "lucide-react";
import { useEffect, useState } from "react";
import { PageHeader } from "../components/layout/page-header";
import { Badge } from "../components/ui/badge";
import { Card } from "../components/ui/card";
import { apiClient } from "../lib/api-client";
import type { OcrStatusRecord } from "../lib/api-types";
import { mockOcrStatus } from "../lib/mock-data";

export function OcrStatusRoute() {
  const [status, setStatus] = useState<OcrStatusRecord>(mockOcrStatus);

  useEffect(() => {
    void apiClient.getOcrStatus().then(setStatus);
  }, []);

  return (
    <div>
      <PageHeader title="OCR 状态" description="展示 OCR runtime、风险命中和 scene hints。真实 PaddleOCR / EasyOCR 仍为 optional，不要求本机存在。" />
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Runtime" eyebrow="ocr_report">
          <div className="grid gap-3">
            <Field label="provider" value={status.provider} />
            <Field label="available" value={status.available ? "available" : "unavailable"} />
            <Field label="status" value={status.status} />
            <Field label="unavailable_reason" value={status.unavailable_reason || "-"} />
          </div>
        </Card>
        <Card title="Optional Provider" eyebrow="runtime check">
          <div className="grid gap-3 sm:grid-cols-2">
            <ProviderStatus name="paddleocr optional" status={status.paddleocr_optional_status} />
            <ProviderStatus name="easyocr optional" status={status.easyocr_optional_status} />
          </div>
          <p className="mt-4 text-sm text-slate-500">缺少真实 OCR 依赖时保持 unavailable/skipped，不影响控制台与测试。</p>
        </Card>
      </div>
      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <Card title="风险命中" eyebrow="risk_hits">
          <TagList items={status.risk_hits} tone="danger" />
        </Card>
        <Card title="场景提示" eyebrow="scene_hints">
          <TagList items={status.scene_hints} tone="info" />
        </Card>
      </div>
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950 px-3 py-2">
      <span className="font-mono text-xs text-slate-500">{label}</span>
      <span className="text-sm text-slate-200">{value}</span>
    </div>
  );
}

function ProviderStatus({ name, status }: { name: string; status: string }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950 p-4">
      <ScanText size={20} className="text-blue-300" />
      <p className="mt-3 text-sm text-slate-300">{name}</p>
      <Badge className={statusClass(status)}>{status}</Badge>
    </div>
  );
}

function TagList({ items, tone }: { items: string[]; tone: "danger" | "info" }) {
  if (!items.length) {
    return <p className="text-sm text-slate-500">暂无记录</p>;
  }
  return (
    <div className="flex flex-wrap gap-2">
      {items.map((item) => (
        <Badge key={item} className={tone === "danger" ? "border-red-500/30 bg-red-500/10 text-red-100" : "border-blue-500/30 bg-blue-500/10 text-blue-100"}>
          {item}
        </Badge>
      ))}
    </div>
  );
}

function statusClass(status: string) {
  if (status === "available") return "mt-3 border-emerald-500/30 bg-emerald-500/10 text-emerald-100";
  if (status === "unavailable") return "mt-3 border-amber-500/30 bg-amber-500/10 text-amber-100";
  return "mt-3 border-slate-700 bg-slate-800 text-slate-200";
}
