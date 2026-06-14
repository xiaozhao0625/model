import { ShieldAlert } from "lucide-react";
import { Button } from "../ui/button";

export function CleanupDangerZone({ disabled, onCleanup }: { disabled: boolean; onCleanup: () => void }) {
  return (
    <div className="rounded-[10px] border border-red-500/30 bg-red-500/10 p-4">
      <div className="flex items-start gap-3">
        <ShieldAlert className="text-red-300" size={20} />
        <div>
          <h3 className="text-sm font-semibold text-red-100">本地清理保护</h3>
          <p className="mt-2 text-sm text-red-100/70">
            只有 uploaded_confirmed 后才允许清理。本地必须保留 summary.json、meta.jsonl、upload_manifest.json、upload_record.json、cleanup_record.json 和 run.log。
          </p>
          <Button className="mt-4" variant="danger" disabled={disabled} onClick={onCleanup}>
            清理本地
          </Button>
        </div>
      </div>
    </div>
  );
}
