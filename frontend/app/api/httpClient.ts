import { AUTH_STORAGE_KEY, useAuthStore } from "@/store/auth.store";

import { API_BASE_URL } from "./config";

interface HttpClientOptions extends RequestInit {
  skipAuthRefresh?: boolean;
}

function readStoredTokens(): { accessToken: string | null; refreshToken: string | null } {
  const { accessToken, refreshToken } = useAuthStore.getState();

  if (accessToken && refreshToken) {
    return { accessToken, refreshToken };
  }

  if (typeof window === "undefined") {
    return { accessToken: null, refreshToken: null };
  }

  const raw = window.localStorage.getItem(AUTH_STORAGE_KEY);
  if (!raw) {
    return { accessToken: null, refreshToken: null };
  }

  try {
    const parsed = JSON.parse(raw) as { access_token?: string; refresh_token?: string };
    return {
      accessToken: parsed.access_token ?? null,
      refreshToken: parsed.refresh_token ?? null,
    };
  } catch (error) {
    console.error("Failed to read stored tokens", error);
    return { accessToken: null, refreshToken: null };
  }
}

async function refreshAccessToken(): Promise<string | null> {
  const { setTokens, logout } = useAuthStore.getState();
  const { refreshToken } = readStoredTokens();

  if (!refreshToken) {
    return null;
  }

  try {
    const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!response.ok) {
      return null;
    }

    const data = (await response.json()) as {
      access_token: string;
      refresh_token: string;
    };

    setTokens(data.access_token, data.refresh_token);
    return data.access_token;
  } catch (error) {
    console.error("Failed to refresh token", error);
    logout();
    return null;
  }
}

export async function httpClient(
  path: string,
  options: HttpClientOptions = {},
  hasRetried = false,
): Promise<Response> {
  const { accessToken } = readStoredTokens();
  const { logout } = useAuthStore.getState();
  const headers = new Headers(options.headers || {});

  if (accessToken && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (
    response.status === 401 &&
    !options.skipAuthRefresh &&
    !hasRetried
  ) {
    const newAccessToken = await refreshAccessToken();

    if (newAccessToken) {
      const retryHeaders = new Headers(options.headers || {});
      retryHeaders.set("Authorization", `Bearer ${newAccessToken}`);

      return httpClient(
        path,
        {
          ...options,
          headers: retryHeaders,
          skipAuthRefresh: true,
        },
        true,
      );
    }

    logout();
  }

  return response;
}
