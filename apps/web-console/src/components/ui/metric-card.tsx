import type { ReactNode } from "react";

interface MetricCardProps {
  label: string;
  value: string | number;
  detail?: string;
  icon?: ReactNode;
  tone?: "blue" | "green" | "amber" | "red" | "slate";
}

const toneClass = {
  blue: "text-blue-300 bg-blue-500/10 border-blue-500/30",
  green: "text-emerald-300 bg-emerald-500/10 border-emerald-500/30",
  amber: "text-amber-300 bg-amber-500/10 border-amber-500/30",
  red: "text-red-300 bg-red-500/10 border-red-500/30",
  slate: "text-slate-300 bg-slate-800/60 border-slate-700"
};

export function MetricCard({ label, value, detail, icon, tone = "slate" }: MetricCardProps) {
  return (
    <div className="rounded-[10px] border border-slate-800 bg-slate-900/80 p-4">
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm text-slate-400">{label}</p>
        {icon && <span className={`rounded-lg border p-2 ${toneClass[tone]}`}>{icon}</span>}
      </div>
      <p className="mt-4 text-2xl font-semibold text-slate-50">{value}</p>
      {detail && <p className="mt-1 text-xs text-slate-500">{detail}</p>}
    </div>
  );
}
