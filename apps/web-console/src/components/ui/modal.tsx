import type { ReactNode } from "react";

interface ModalProps {
  title: string;
  open: boolean;
  children: ReactNode;
}

export function Modal({ title, open, children }: ModalProps) {
  if (!open) {
    return null;
  }
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/70 p-4">
      <div className="w-full max-w-lg rounded-[10px] border border-slate-700 bg-slate-900 p-4 shadow-2xl">
        <h2 className="text-base font-semibold text-slate-50">{title}</h2>
        <div className="mt-4">{children}</div>
      </div>
    </div>
  );
}
