import type { RunStatus } from "../../lib/api-types";
import { statusLabels, statusTone } from "../../lib/status";
import { Badge } from "./badge";

export function StatusPill({ status }: { status: RunStatus }) {
  return <Badge className={statusTone[status]}>{statusLabels[status] || status}</Badge>;
}
