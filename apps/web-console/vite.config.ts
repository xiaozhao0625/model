import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

function parseList(value?: string): string[] {
  return (
    value
      ?.split(",")
      .map((item) => item.trim())
      .filter(Boolean) ?? []
  );
}

function optionalNumber(value?: string): number | undefined {
  if (!value) {
    return undefined;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : undefined;
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const host = env.WEB_CONSOLE_HOST || "0.0.0.0";
  const port = optionalNumber(env.WEB_CONSOLE_PORT) ?? 5173;
  const apiProxyTarget = env.WEB_CONSOLE_API_PROXY_TARGET || "http://127.0.0.1:8000";
  const allowedHosts = parseList(env.WEB_CONSOLE_ALLOWED_HOSTS);
  const hmrHost = env.WEB_CONSOLE_HMR_HOST;
  const hmrClientPort = optionalNumber(env.WEB_CONSOLE_HMR_CLIENT_PORT);
  const hmrProtocol = env.WEB_CONSOLE_HMR_PROTOCOL as "ws" | "wss" | undefined;

  return {
    plugins: [react()],
    server: {
      host,
      port,
      strictPort: true,
      allowedHosts,
      hmr:
        hmrHost || hmrClientPort || hmrProtocol
          ? {
              host: hmrHost,
              clientPort: hmrClientPort,
              protocol: hmrProtocol
            }
          : undefined,
      proxy: {
        "/api/health": {
          target: apiProxyTarget,
          changeOrigin: true,
          rewrite: () => "/health"
        },
        "/api": {
          target: apiProxyTarget,
          changeOrigin: true
        }
      }
    }
  };
});
