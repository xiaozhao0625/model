import { ShieldAlert } from "lucide-react";
import { Button } from "../ui/button";

export function CleanupDangerZone({ disabled, onCleanup }: { disabled: boolean; onCleanup: () => void }) {
  return (
    <div className="rounded-[10px] border border-red-500/30 bg-red-500/10 p-4">
      <div className="flex items-start gap-3">
        <ShieldAlert className="text-red-300" size={20} />
        <div>
          <h3 className="text-sm font-semibold text-red-100">Local cleanup guard</h3>
          <p className="mt-2 text-sm text-red-100/70">
            Cleanup is only enabled after uploaded_confirmed. The platform keeps summary.json, meta.jsonl, upload_manifest.json, upload_record.json,
            cleanup_record.json, and run.log.
          </p>
          <Button className="mt-4" variant="danger" disabled={disabled} onClick={onCleanup}>
            Cleanup Local
          </Button>
        </div>
      </div>
    </div>
  );
}
