const rawEnv =
  (process.env.NEXT_PUBLIC_API_BASE_URL?.trim() ||
   process.env.NEXT_PUBLIC_API_URL?.trim() ||
   "");

const normalizedApiBaseUrl = rawEnv ? rawEnv.replace(/\/$/, "") : "/api";
export const API_BASE_URL = normalizedApiBaseUrl;

export function buildWsUrl(path: string): string {
  const base = API_BASE_URL;
  if (base.startsWith("http://") || base.startsWith("https://")) {
    const wsBase = base.startsWith("https://")
      ? base.replace("https://", "wss://")
      : base.replace("http://", "ws://");
    return `${wsBase}${path}`;
  }

  // relative base like "/api"
  if (typeof window !== "undefined") {
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    return `${proto}://${window.location.host}${path}`;
  }

  return path;
}
