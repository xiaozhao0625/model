import type { RunRecord } from "../../lib/api-types";
import { Button } from "../ui/button";

interface RunActionsProps {
  run: RunRecord;
  onAction: (action: string) => void;
}

export function RunActions({ run, onAction }: RunActionsProps) {
  const status = run.status;
  return (
    <div aria-label="Run actions" className="grid gap-2">
      <Button disabled={status !== "pending"} onClick={() => onAction("start")}>
        Start
      </Button>
      <Button disabled={status !== "running"} onClick={() => onAction("manual_seed")}>
        Manual Seed
      </Button>
      <Button disabled={status !== "running"} variant="danger" onClick={() => onAction("mark_failed")}>
        Mark Failed
      </Button>
      <Button disabled={status !== "capture_completed"} variant="primary" onClick={() => onAction("upload_manifest")}>
        Generate Upload Manifest
      </Button>
      <Button disabled={status !== "upload_pending"} onClick={() => onAction("confirm_upload")}>
        Confirm Upload
      </Button>
      <Button disabled={status !== "uploaded_confirmed"} onClick={() => onAction("cleanup")}>
        Cleanup Local
      </Button>
      <Button disabled={status !== "local_deleted"} onClick={() => onAction("finalize")}>
        Finalize
      </Button>
    </div>
  );
}
