const rawEnv =
  (process.env.NEXT_PUBLIC_API_BASE_URL?.trim() ||
   process.env.NEXT_PUBLIC_API_URL?.trim() ||
   "");

const normalizedApiBaseUrl = rawEnv ? rawEnv.replace(/\/$/, "") : "/api";
export const API_BASE_URL = normalizedApiBaseUrl;

function normalizePath(path: string): string {
  if (!path) return "/";
  return path.startsWith("/") ? path : `/${path}`;
}

function normalizeBase(base: string): string {
  if (!base) return "";
  if (base.startsWith("/")) return base.replace(/\/$/, "");
  return `/${base.replace(/\/$/, "")}`;
}

export function buildWsUrl(path: string): string {
  const base = (API_BASE_URL || "").trim();
  const cleanPath = normalizePath(path);

  // Absolute API base (e.g. https://api.example.com or https://example.com/api)
  if (base.startsWith("http://") || base.startsWith("https://")) {
    const wsBase = base.startsWith("https://")
      ? base.replace("https://", "wss://")
      : base.replace("http://", "ws://");
    return `${wsBase}${cleanPath}`;
  }

  // Relative base like "/api"
  if (typeof window !== "undefined") {
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const basePrefix = normalizeBase(base || "/api"); // default to /api if empty
    return `${proto}://${window.location.host}${basePrefix}${cleanPath}`;
  }

  // Server-side fallback (rarely used for WS in browser-only clients)
  const basePrefix = normalizeBase(base || "/api");
  return `${basePrefix}${cleanPath}`;
}
