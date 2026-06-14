import { Link } from "react-router-dom";
import { formatNumber, formatPercent } from "../../lib/format";
import { mockRuns } from "../../lib/mock-data";
import { bucketLabels } from "../../lib/status";
import { StatusPill } from "../ui/status-pill";
import { DataTable } from "../ui/table";

export function ActiveRuns() {
  const active = mockRuns.filter((run) => run.status !== "completed").slice(0, 6);
  return (
    <DataTable columns={["任务", "应用", "状态", "有效数", "分档结构", "Worker"]}>
      {active.map((run) => (
        <tr key={run.run_id}>
          <td>
            <Link className="font-mono text-blue-300 hover:text-blue-200" to={`/runs/${run.run_id}`}>
              {run.run_id}
            </Link>
          </td>
          <td className="text-slate-300">{run.app_id}</td>
          <td>
            <StatusPill status={run.status} />
          </td>
          <td className="text-slate-300">{formatNumber(run.valid_total)}</td>
          <td className="text-slate-400">
            {bucketLabels.low} {formatPercent(run.low_count, run.valid_total)} / {bucketLabels.high} {formatPercent(run.high_count, run.valid_total)}
          </td>
          <td className="font-mono text-xs text-slate-500">{run.executed_by || run.assigned_worker_id || run.worker_id || "未分配"}</td>
        </tr>
      ))}
    </DataTable>
  );
}
