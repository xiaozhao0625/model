import type { ReactNode } from "react";

interface TabsProps {
  items: Array<{ key: string; label: string; content: ReactNode }>;
}

export function Tabs({ items }: TabsProps) {
  return (
    <div>
      <div className="flex gap-1 rounded-lg border border-slate-800 bg-slate-950 p-1">
        {items.map((item) => (
          <span key={item.key} className="rounded-md px-3 py-1.5 text-xs font-medium text-slate-300 first:bg-slate-800 first:text-slate-100">
            {item.label}
          </span>
        ))}
      </div>
      <div className="mt-4">{items[0]?.content}</div>
    </div>
  );
}
