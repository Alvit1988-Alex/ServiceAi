import { API_BASE_URL } from "./config";
import { AuthTokens, User, YandexAuthStartResponse } from "./types";

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
  const response = await fetch(`${API_BASE_URL}/auth/yandex/start`);

  if (!response.ok) {
    throw new Error("Не удалось начать вход через Яндекс");
  }

  return (await response.json()) as YandexAuthStartResponse;
}

export async function completeYandexLogin(completionToken: string): Promise<AuthTokens> {
  const response = await fetch(`${API_BASE_URL}/auth/yandex/complete`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ completion_token: completionToken }),
  });

  if (!response.ok) {
    throw new Error("Не удалось завершить вход через Яндекс");
  }

  return (await response.json()) as AuthTokens;
}
