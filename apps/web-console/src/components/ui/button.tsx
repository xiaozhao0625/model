import type { ButtonHTMLAttributes, ReactNode } from "react";

type ButtonVariant = "primary" | "secondary" | "danger" | "ghost";

const variantClass: Record<ButtonVariant, string> = {
  primary: "border-blue-500 bg-blue-500 text-white hover:bg-blue-400",
  secondary: "border-slate-700 bg-slate-900 text-slate-100 hover:border-slate-500",
  danger: "border-red-500 bg-red-500/15 text-red-100 hover:bg-red-500/25",
  ghost: "border-transparent bg-transparent text-slate-300 hover:bg-slate-800"
};

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  icon?: ReactNode;
}

export function Button({ className = "", variant = "secondary", icon, children, ...props }: ButtonProps) {
  return (
    <button
      className={`inline-flex min-h-9 items-center justify-center gap-2 rounded-lg border px-3 py-2 text-sm font-medium transition active:translate-y-px disabled:cursor-not-allowed disabled:opacity-45 ${variantClass[variant]} ${className}`}
      {...props}
    >
      {icon}
      {children}
    </button>
  );
}
