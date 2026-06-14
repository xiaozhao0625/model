import type { RunStatus } from "../../lib/api-types";
import { StatusPill } from "../ui/status-pill";

const flow: RunStatus[] = ["capture_completed", "upload_pending", "uploaded_confirmed", "local_deleted", "completed"];

export function UploadFlowPanel({ status }: { status: RunStatus }) {
  const activeIndex = flow.indexOf(status);
  return (
    <div className="grid gap-3 md:grid-cols-5">
      {flow.map((step, index) => (
        <div key={step} className={`rounded-lg border p-3 ${index <= activeIndex ? "border-blue-500/30 bg-blue-500/10" : "border-slate-800 bg-slate-950"}`}>
          <StatusPill status={step} />
          <p className="mt-3 text-xs leading-5 text-slate-500">
            {step === "capture_completed" && "capture_completed 不等于最终完成"}
            {step === "upload_pending" && "等待人工确认上传流程"}
            {step === "uploaded_confirmed" && "已确认上传，可进入后续清理"}
            {step === "local_deleted" && "本地大文件已清理"}
            {step === "completed" && "最终完成状态"}
          </p>
        </div>
      ))}
    </div>
  );
}
