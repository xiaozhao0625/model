import type { ReactNode } from "react";

interface DataTableProps {
  columns: string[];
  children: ReactNode;
}

export function DataTable({ columns, children }: DataTableProps) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[720px] border-separate border-spacing-0 text-left text-sm">
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column} className="border-b border-slate-800 px-3 py-2 text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="[&_td]:border-b [&_td]:border-slate-800/70 [&_td]:px-3 [&_td]:py-3">{children}</tbody>
      </table>
    </div>
  );
}
