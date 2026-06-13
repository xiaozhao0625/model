export type ThemeMode = "dark" | "light";

export const themeStorageKey = "web-console-theme";
export const defaultTheme: ThemeMode = "dark";

function isThemeMode(value: string | null): value is ThemeMode {
  return value === "dark" || value === "light";
}

export function readStoredTheme(storage: Storage | undefined = globalThis.localStorage): ThemeMode {
  try {
    const stored = storage?.getItem(themeStorageKey) ?? null;
    return isThemeMode(stored) ? stored : defaultTheme;
  } catch {
    return defaultTheme;
  }
}

export function writeStoredTheme(theme: ThemeMode, storage: Storage | undefined = globalThis.localStorage): void {
  try {
    storage?.setItem(themeStorageKey, theme);
  } catch {
    // Theme persistence is best-effort so private browsing does not break UI rendering.
  }
}

export function applyTheme(theme: ThemeMode, root: HTMLElement = document.documentElement): void {
  root.dataset.theme = theme;
  root.style.colorScheme = theme === "light" ? "light" : "dark";
}

export function initializeTheme(): ThemeMode {
  const theme = readStoredTheme();
  applyTheme(theme);
  return theme;
}

export function toggleTheme(theme: ThemeMode): ThemeMode {
  return theme === "dark" ? "light" : "dark";
}
