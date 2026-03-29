import { httpClient } from "./httpClient";
import { Bot, BotAdmin, BotCreate, BotUpdate, ListResponse, StatsSummary } from "./types";

async function getErrorMessage(response: Response, fallback: string): Promise<string> {
  try {
    const data = (await response.json()) as { detail?: string };
    if (data?.detail) {
      return data.detail;
    }
  } catch (error) {
    console.error("Failed to parse bots API error", error);
  }

  return fallback;
}

export async function listBots(): Promise<Bot[]> {
  const response = await httpClient("/bots");

  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Не удалось загрузить список ботов"));
  }

  const data = (await response.json()) as ListResponse<Bot>;
  return data.items;
}

export async function createBot(payload: BotCreate): Promise<Bot> {
  const { name, description } = payload;
  const response = await httpClient("/bots", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ name, description }),
  });

  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Не удалось создать бота"));
  }

  return (await response.json()) as Bot;
}

export async function getBot(botId: number): Promise<Bot> {
  const response = await httpClient(`/bots/${botId}`);

  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Не удалось загрузить бота"));
  }

  return (await response.json()) as Bot;
}

export async function updateBot(botId: number, payload: BotUpdate): Promise<Bot> {
  const response = await httpClient(`/bots/${botId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Не удалось обновить данные бота"));
  }

  return (await response.json()) as Bot;
}

export async function listBotAdmins(botId: number): Promise<BotAdmin[]> {
  const response = await httpClient(`/bots/${botId}/admins`);
  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Не удалось загрузить администраторов"));
  }
  const data = (await response.json()) as ListResponse<BotAdmin>;
  return data.items;
}

export async function addBotAdmin(botId: number, accountPublicId: string, role: "superadmin" | "admin"): Promise<BotAdmin> {
  const response = await httpClient(`/bots/${botId}/admins`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ account_public_id: accountPublicId, role }),
  });
  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Не удалось добавить администратора"));
  }
  return (await response.json()) as BotAdmin;
}

export async function removeBotAdmin(botId: number, userId: number): Promise<void> {
  const response = await httpClient(`/bots/${botId}/admins`, {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId }),
  });
  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Не удалось удалить администратора"));
  }
}

export async function getBotStatsSummary(botId: number): Promise<StatsSummary> {
  const response = await httpClient(`/bots/${botId}/stats/summary`);

  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Не удалось загрузить статистику бота"));
  }

  return (await response.json()) as StatsSummary;
}
