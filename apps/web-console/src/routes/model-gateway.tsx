import { Bot, Cpu, ShieldX } from "lucide-react";
import { useEffect, useState } from "react";
import { PageHeader } from "../components/layout/page-header";
import { Badge } from "../components/ui/badge";
import { Card } from "../components/ui/card";
import { DataTable } from "../components/ui/table";
import { apiClient } from "../lib/api-client";
import type { ModelDeploymentMatrix } from "../lib/api-types";
import { mockModelDeploymentMatrix, mockModelProviders } from "../lib/mock-data";
import { providerTypeLabels } from "../lib/status";

export function ModelGatewayRoute() {
  const [matrix, setMatrix] = useState<ModelDeploymentMatrix>(mockModelDeploymentMatrix);
  const blocked = mockModelProviders.reduce((total, provider) => total + provider.blocked_count, 0);

  useEffect(() => {
    void apiClient.getModelDeploymentMatrix().then(setMatrix);
  }, []);

  return (
    <div>
      <PageHeader
        title="模型网关"
        description="展示模型 Provider 边界与 P13.5 分布式 OCR / 模型部署矩阵。本阶段只做计划，不下载模型，不安装 OCR，不启用在线推理。"
      />
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Provider 注册表" eyebrow="能力声明">
          <DataTable columns={["provider", "类型", "启用", "场景识别", "定位", "动作建议"]}>
            {mockModelProviders.map((provider) => (
              <tr key={provider.provider_name}>
                <td className="font-mono text-blue-300">{provider.provider_name}</td>
                <td className="text-slate-300">{providerTypeLabels[provider.provider_type] || provider.provider_type}</td>
                <td>
                  <Badge className={provider.enabled ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200" : "border-slate-700 bg-slate-800 text-slate-300"}>
                    {provider.enabled ? "启用" : "停用"}
                  </Badge>
                </td>
                <td className="text-slate-400">{provider.supports_scene_classify ? "支持" : "不支持"}</td>
                <td className="text-slate-400">{provider.supports_ground ? "支持" : "不支持"}</td>
                <td className="text-slate-400">{provider.supports_act ? "支持" : "不支持"}</td>
              </tr>
            ))}
          </DataTable>
        </Card>
        <Card title="安全边界" eyebrow="P13.5">
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4">
              <ShieldX className="text-red-300" size={22} />
              <p className="mt-3 text-2xl font-semibold text-red-100">{blocked}</p>
              <p className="mt-1 text-sm text-red-100/70">已拦截高风险意图</p>
            </div>
            <div className="rounded-lg border border-blue-500/30 bg-blue-500/10 p-4">
              <Bot className="text-blue-300" size={22} />
              <p className="mt-3 text-2xl font-semibold text-blue-100">{matrix.status}</p>
              <p className="mt-1 text-sm text-blue-100/70">模型/OCR 仍为计划状态</p>
            </div>
          </div>
          <div className="mt-4 grid gap-2 text-sm text-slate-400">
            <Field label="online_inference_enabled" value={String(matrix.online_inference_enabled)} />
            <Field label="model_downloaded" value={String(matrix.model_downloaded)} />
            <Field label="ocr_installed" value={String(matrix.ocr_installed)} />
          </div>
        </Card>
      </div>

      <Card title="ShowUI Provider 计划" eyebrow="P13.5.4 - P13.5.6" className="mt-4">
        <DataTable columns={["Provider", "目标节点", "下载", "Hash", "Health", "Enabled", "Online", "显存", "最新检查"]}>
          {(matrix.providers || []).map((provider) => (
            <tr key={provider.provider}>
              <td>
                <div className="font-mono text-blue-300">{provider.provider}</div>
                <div className="mt-1 font-mono text-xs text-slate-500">{provider.model_dir}</div>
              </td>
              <td className="text-slate-300">
                <div className="font-mono">{provider.target_node}</div>
                <div className="mt-1 text-xs text-slate-500">{provider.candidate_nodes.join(", ") || "-"}</div>
              </td>
              <td className="text-slate-400">{provider.download_status}</td>
              <td className="text-slate-400">{provider.hash_verification}</td>
              <td>
                <Badge className={provider.health_status === "inference_ok" ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-100" : "border-amber-500/30 bg-amber-500/10 text-amber-100"}>
                  {provider.health_status}
                </Badge>
              </td>
              <td className="font-mono text-xs text-slate-400">{String(provider.enabled)}</td>
              <td className="font-mono text-xs text-slate-400">{String(provider.online_inference_enabled)}</td>
              <td className="font-mono text-xs text-slate-400">{provider.estimated_vram_gb}</td>
              <td className="font-mono text-xs text-slate-500">{provider.last_health_at || "-"}</td>
            </tr>
          ))}
        </DataTable>
      </Card>

      <Card title="分布式 OCR / 模型部署矩阵" eyebrow="M0 / W1 / W2 / W3" className="mt-4">
        <DataTable columns={["节点", "GPU/显存", "目录", "计划能力", "预计显存", "采集影响", "启用"]}>
          {matrix.nodes.map((node) => (
            <tr key={node.role}>
              <td>
                <div className="font-mono text-blue-300">{node.role}</div>
                <div className="mt-1 font-mono text-xs text-slate-500">{node.ip}</div>
              </td>
              <td className="text-slate-300">
                <Cpu size={14} className="mr-1 inline text-blue-300" />
                {node.gpu} / {node.vram_gb}GB
              </td>
              <td className="font-mono text-xs text-slate-500">
                <div>{node.models_dir}</div>
                <div>{node.ocr_dir}</div>
                <div>{node.runtime_dir}</div>
              </td>
              <td className="text-xs text-slate-300">
                <div>{node.capabilities.join(", ")}</div>
                <div className="mt-1 text-slate-500">{node.planned_components.join(", ")}</div>
              </td>
              <td className="font-mono text-xs text-slate-400">{node.estimated_vram_gb}</td>
              <td className="text-xs text-slate-400">{node.capture_impact}</td>
              <td>
                <Badge className={node.enabled ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-100" : "border-slate-700 bg-slate-800 text-slate-300"}>
                  {node.enabled ? "enabled" : "planned"}
                </Badge>
              </td>
            </tr>
          ))}
        </DataTable>
      </Card>
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950 px-3 py-2">
      <span className="font-mono text-xs text-slate-500">{label}</span>
      <span className="font-mono text-xs text-slate-200">{value}</span>
    </div>
  );
}
