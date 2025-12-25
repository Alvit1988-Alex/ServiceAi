import { API_BASE_URL } from "./config";
import { AuthTokens, PendingLoginResponse, PendingStatusResponse, User } from "./types";

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

export async function createPendingLogin(): Promise<PendingLoginResponse> {
  const response = await fetch(`${API_BASE_URL}/auth/pending`, {
    method: "POST",
  });

  if (!response.ok) {
    throw new Error("Не удалось создать запрос на вход");
  }

  return (await response.json()) as PendingLoginResponse;
}

export async function getPendingStatus(token: string): Promise<PendingStatusResponse> {
  const response = await fetch(`${API_BASE_URL}/auth/pending/${token}/status`);

  if (!response.ok) {
    if (response.status === 404) {
      throw new Error("Запрос входа не найден");
    }
    if (response.status === 410) {
      return {
        status: "expired",
        expires_at: new Date().toISOString(),
        access_token: null,
        refresh_token: null,
      };
    }
    throw new Error("Не удалось получить статус входа");
  }

  return (await response.json()) as PendingStatusResponse;
}
