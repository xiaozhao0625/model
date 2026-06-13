import type { HTMLAttributes, ReactNode } from "react";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  title?: string;
  eyebrow?: string;
  action?: ReactNode;
}

export function Card({ title, eyebrow, action, children, className = "", ...props }: CardProps) {
  return (
    <section className={`rounded-[10px] border border-slate-800 bg-slate-900/80 shadow-xl shadow-black/10 ${className}`} {...props}>
      {(title || eyebrow || action) && (
        <div className="flex items-start justify-between gap-4 border-b border-slate-800 px-4 py-3">
          <div>
            {eyebrow && <p className="text-xs font-medium uppercase tracking-[0.16em] text-slate-500">{eyebrow}</p>}
            {title && <h2 className="mt-1 text-base font-semibold text-slate-100">{title}</h2>}
          </div>
          {action}
        </div>
      )}
      <div className="p-4">{children}</div>
    </section>
  );
}
