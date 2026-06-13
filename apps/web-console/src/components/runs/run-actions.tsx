import type { RunRecord } from "../../lib/api-types";
import { actionLabels } from "../../lib/status";
import { Button } from "../ui/button";

interface RunActionsProps {
  run: RunRecord;
  onAction: (action: string) => void;
}

export function RunActions({ run, onAction }: RunActionsProps) {
  const status = run.status;
  return (
    <div aria-label="任务操作" className="grid gap-2">
      <Button disabled={status !== "pending"} onClick={() => onAction("start")}>
        {actionLabels.start}
      </Button>
      <Button disabled={status !== "running"} onClick={() => onAction("manual_seed")}>
        {actionLabels.manual_seed}
      </Button>
      <Button disabled={status !== "running"} variant="danger" onClick={() => onAction("mark_failed")}>
        {actionLabels.mark_failed}
      </Button>
      <Button disabled={status !== "capture_completed"} variant="primary" onClick={() => onAction("upload_manifest")}>
        {actionLabels.upload_manifest}
      </Button>
      <Button disabled={status !== "upload_pending"} onClick={() => onAction("confirm_upload")}>
        {actionLabels.confirm_upload}
      </Button>
      <Button disabled={status !== "uploaded_confirmed"} onClick={() => onAction("cleanup")}>
        {actionLabels.cleanup}
      </Button>
      <Button disabled={status !== "local_deleted"} onClick={() => onAction("finalize")}>
        {actionLabels.finalize}
      </Button>
    </div>
  );
}
