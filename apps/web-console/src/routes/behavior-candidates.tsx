import { RotateCcw } from "lucide-react";
import { useEffect, useState } from "react";
import { PageHeader } from "../components/layout/page-header";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { DataTable } from "../components/ui/table";
import { apiClient } from "../lib/api-client";
import type { BehaviorCandidateRecord } from "../lib/api-types";
import { mockBehaviorCandidates } from "../lib/mock-data";

export function BehaviorCandidatesRoute() {
  const [candidates, setCandidates] = useState<BehaviorCandidateRecord[]>(mockBehaviorCandidates);

  useEffect(() => {
    void apiClient.listBehaviorCandidates().then(setCandidates);
  }, []);

  async function updateCandidate(candidatePackId: string, action: "approve" | "reject" | "rollback") {
    if (action === "rollback" && !window.confirm("确认回滚该候选行为包？该操作只记录回滚意图，不会自动覆盖线上行为包。")) {
      return;
    }
    const next =
      action === "approve"
        ? await apiClient.approveBehaviorCandidate(candidatePackId)
        : action === "reject"
          ? await apiClient.rejectBehaviorCandidate(candidatePackId)
          : await apiClient.rollbackBehaviorCandidate(candidatePackId);
    setCandidates((items) => items.map((item) => (item.candidate_pack_id === candidatePackId ? next : item)));
  }

  return (
    <div>
      <PageHeader title="行为包候选" description="人工审核 P12 行为包候选。pending_review 才允许 approve/reject，rejected 不可启用，rollback 需要确认。" />
      <Card title="候选列表" eyebrow="behavior_learning candidates">
        <DataTable columns={["candidate_pack_id", "基础包", "类型", "版本", "状态", "来源 run", "回滚目标", "操作"]}>
          {candidates.map((candidate) => {
            const pending = candidate.status === "pending_review";
            return (
              <tr key={candidate.candidate_pack_id}>
                <td className="font-mono text-blue-300">{candidate.candidate_pack_id}</td>
                <td className="font-mono text-slate-300">{candidate.base_pack_id}</td>
                <td>{candidate.game_type}</td>
                <td>{candidate.version}</td>
                <td>
                  <Badge className={candidateStatusClass(candidate.status)}>
                    {candidate.status === "approved" ? "approved / enabled" : candidate.status}
                  </Badge>
                </td>
                <td className="font-mono text-xs text-slate-400">{candidate.created_from_run_id}</td>
                <td className="font-mono text-xs text-slate-400">{candidate.rollback_target}</td>
                <td>
                  <div className="flex flex-wrap gap-2">
                    <Button disabled={!pending} onClick={() => void updateCandidate(candidate.candidate_pack_id, "approve")}>
                      approve
                    </Button>
                    <Button variant="secondary" disabled={!pending} onClick={() => void updateCandidate(candidate.candidate_pack_id, "reject")}>
                      reject
                    </Button>
                    <Button variant="secondary" onClick={() => void updateCandidate(candidate.candidate_pack_id, "rollback")}>
                      <RotateCcw size={14} />
                      rollback
                    </Button>
                  </div>
                </td>
              </tr>
            );
          })}
        </DataTable>
      </Card>
      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        {candidates.map((candidate) => (
          <Card key={`${candidate.candidate_pack_id}-detail`} title={candidate.candidate_pack_id} eyebrow="issues / recommendations">
            <p className="text-sm text-slate-500">rejected 不可启用；approved 仅显示 enabled，不会自动进入 P13。</p>
            <div className="mt-4 grid gap-3">
              <ListBlock title="问题" items={candidate.issues} />
              <ListBlock title="建议" items={candidate.recommendations} />
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}

function ListBlock({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950 p-3">
      <p className="text-xs text-slate-500">{title}</p>
      <ul className="mt-2 space-y-1 text-sm text-slate-300">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

function candidateStatusClass(status: string) {
  if (status === "approved") return "border-emerald-500/30 bg-emerald-500/10 text-emerald-100";
  if (status === "rejected") return "border-red-500/30 bg-red-500/10 text-red-100";
  return "border-amber-500/30 bg-amber-500/10 text-amber-100";
}
