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
            {step === "capture_completed" && "capture_completed is not completed"}
            {step === "upload_pending" && "upload_pending waits for manual Baidu Netdisk upload"}
            {step === "uploaded_confirmed" && "uploaded_confirmed only allows cleanup later"}
            {step === "local_deleted" && "local_deleted means local heavy files were removed"}
            {step === "completed" && "completed is the final state"}
          </p>
        </div>
      ))}
    </div>
  );
}
