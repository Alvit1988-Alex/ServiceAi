import { API_BASE_URL } from "./config";
import { AuthTokens, User, YandexAuthStartResponse } from "./types";

async function parseAuthError(response: Response, fallbackMessage: string): Promise<never> {
  let detail: string | undefined;

  try {
    const payload = await response.clone().json();
    if (payload && typeof payload === "object" && "detail" in payload) {
      const rawDetail = (payload as { detail?: unknown }).detail;
      if (typeof rawDetail === "string") {
        detail = rawDetail;
      } else if (rawDetail != null) {
        detail = String(rawDetail);
      }
    } else if (payload != null) {
      detail = JSON.stringify(payload);
    }
  } catch {
    try {
      const text = await response.text();
      detail = text || undefined;
    } catch {
      detail = undefined;
    }
  }

  throw new Error(detail || fallbackMessage || String(response.status));
}

export async function login(email: string, password: string): Promise<AuthTokens> {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) {
    throw new Error("Invalid email or password");
  }

  return (await response.json()) as AuthTokens;
}

export async function refreshToken(refresh_token: string): Promise<AuthTokens> {
  const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ refresh_token }),
  });

  if (!response.ok) {
    throw new Error("Unable to refresh session");
  }

  return (await response.json()) as AuthTokens;
}

export async function getCurrentUser(accessToken: string): Promise<User> {
  const response = await fetch(`${API_BASE_URL}/auth/me`, {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });

  if (!response.ok) {
    throw new Error("Unable to fetch current user");
  }

  return (await response.json()) as User;
}

export async function startYandexLogin(): Promise<YandexAuthStartResponse> {
  const response = await fetch(`${API_BASE_URL}/auth/yandex/start?ts=${Date.now()}`, {
    cache: "no-store",
    headers: {
      "Cache-Control": "no-store",
      Pragma: "no-cache",
    },
  });

  if (!response.ok) {
    await parseAuthError(response, "Не удалось начать вход через Яндекс");
  }

  return (await response.json()) as YandexAuthStartResponse;
}

export async function completeYandexLogin(completionToken: string): Promise<AuthTokens> {
  const response = await fetch(`${API_BASE_URL}/auth/yandex/complete`, {
    method: "POST",
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      "Cache-Control": "no-store",
      Pragma: "no-cache",
    },
    body: JSON.stringify({ completion_token: completionToken }),
  });

  if (!response.ok) {
    await parseAuthError(response, "Не удалось завершить вход через Яндекс");
  }

  return (await response.json()) as AuthTokens;
}
