import { AlertTriangle, FileText, ShieldCheck } from "lucide-react";
import type { ReactNode } from "react";
import { Card } from "../ui/card";
import { Sidebar } from "./sidebar";
import { Topbar } from "./topbar";

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-[100dvh] bg-[#0B0F14] text-slate-100">
      <div className="flex">
        <Sidebar />
        <div className="min-w-0 flex-1">
          <Topbar />
          <div className="grid min-h-[calc(100dvh-65px)] grid-cols-1 gap-4 p-4 xl:grid-cols-[minmax(0,1fr)_320px]">
            <main className="min-w-0">{children}</main>
            <aside className="space-y-4">
              <Card title="操作提示" eyebrow="operator guide">
                <div className="space-y-3 text-sm text-slate-400">
                  <div className="flex gap-3">
                    <ShieldCheck className="mt-0.5 text-emerald-300" size={17} />
                    <p>真实点击只允许在已通过 Safety Gate 的安全 OCR 候选上执行；结果会写入运行审计。</p>
                  </div>
                  <div className="flex gap-3">
                    <AlertTriangle className="mt-0.5 text-amber-300" size={17} />
                    <p>如果系统状态出现阻塞项，先处理阻塞，再启动新的真实采集任务。</p>
                  </div>
                  <div className="flex gap-3">
                    <FileText className="mt-0.5 text-blue-300" size={17} />
                    <p>采集截图、动作、候选和报告都保存在本机目录，可在结果页复制路径或打开文件夹。</p>
                  </div>
                </div>
              </Card>
              <Card title="高级调试" eyebrow="collapsed">
                <details className="text-sm text-slate-400">
                  <summary className="cursor-pointer text-slate-300">仅开发排查使用</summary>
                  <div className="mt-3 space-y-2">
                    <p>原始日志请查看 run 目录中的 events.jsonl、images.jsonl、meta/actions.jsonl 和 meta/candidates.jsonl。</p>
                    <p>旧平台页面仍可通过侧边栏的高级调试入口访问，主流程不再依赖演示数据兜底。</p>
                  </div>
                </details>
              </Card>
            </aside>
          </div>
        </div>
      </div>
    </div>
  );
}
