import { Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";
import { applyTheme, initializeTheme, readStoredTheme, toggleTheme, writeStoredTheme, type ThemeMode } from "../../lib/theme";

export function ThemeToggle() {
  const [theme, setTheme] = useState<ThemeMode>(() => readStoredTheme());
  const isDark = theme === "dark";
  const nextLabel = isDark ? "切换到白天模式" : "切换到夜间模式";

  useEffect(() => {
    setTheme(initializeTheme());
  }, []);

  function handleToggle() {
    const nextTheme = toggleTheme(theme);
    applyTheme(nextTheme);
    writeStoredTheme(nextTheme);
    setTheme(nextTheme);
  }

  return (
    <button
      type="button"
      aria-label={nextLabel}
      title={nextLabel}
      onClick={handleToggle}
      className="inline-flex min-h-9 items-center gap-2 rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs font-medium text-slate-200 transition hover:border-blue-500/50 hover:text-blue-200 active:translate-y-px"
    >
      {isDark ? <Moon size={14} /> : <Sun size={14} />}
      {isDark ? "夜间模式" : "白天模式"}
    </button>
  );
}
