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
  // If WS is routed via dedicated nginx "/ws/" location, don't prefix with API_BASE_URL ("/api")
  if (cleanPath.startsWith("/ws/")) {
    if (typeof window !== "undefined") {
      const proto = window.location.protocol === "https:" ? "wss" : "ws";
      return `${proto}://${window.location.host}${cleanPath}`;
    }
    return cleanPath;
  }

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
    // Prevent double-prefixing when callers pass already-prefixed paths like "/api/ws/..."
    const fullPath =
      cleanPath === basePrefix || cleanPath.startsWith(`${basePrefix}/`)
        ? cleanPath
        : `${basePrefix}${cleanPath}`;

    return `${proto}://${window.location.host}${fullPath}`;
  }

  // Server-side fallback (rarely used for WS in browser-only clients)
  const basePrefix = normalizeBase(base || "/api");
  // Prevent double-prefixing in SSR fallbacks
  const fullPath =
    cleanPath === basePrefix || cleanPath.startsWith(`${basePrefix}/`)
      ? cleanPath
      : `${basePrefix}${cleanPath}`;

  return fullPath;
}
