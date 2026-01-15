import { httpClient } from "./httpClient";
import {
  AccountProfile,
  ChangePasswordPayload,
  UpdateAccountProfilePayload,
} from "./types";

async function getErrorMessage(response: Response, fallback: string): Promise<string> {
  try {
    const data = (await response.json()) as { detail?: string };
    if (data?.detail) {
      return data.detail;
    }
  } catch (error) {
    console.error("Failed to parse account API error", error);
  }

  return fallback;
}

export async function getCurrentAccount(): Promise<AccountProfile> {
  const response = await httpClient("/auth/me");

  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Не удалось загрузить профиль"));
  }

  return (await response.json()) as AccountProfile;
}

export async function updateAccountProfile(
  userId: number,
  payload: UpdateAccountProfilePayload,
): Promise<AccountProfile> {
  const response = await httpClient(`/users/${userId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Не удалось обновить профиль"));
  }

  return (await response.json()) as AccountProfile;
}

export async function changePassword(payload: ChangePasswordPayload): Promise<AccountProfile> {
  const response = await httpClient("/auth/change-password", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Не удалось изменить пароль"));
  }

  return (await response.json()) as AccountProfile;
}

export async function uploadAvatar(file: File): Promise<AccountProfile> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await httpClient("/auth/me/avatar", {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Не удалось загрузить аватар"));
  }

  return (await response.json()) as AccountProfile;
}

export async function deleteAvatar(): Promise<AccountProfile> {
  const response = await httpClient("/auth/me/avatar", {
    method: "DELETE",
  });

  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Не удалось удалить аватар"));
  }

  return (await response.json()) as AccountProfile;
}
