import { httpClient } from "./httpClient";
import { Bot, BotUpdate, ListResponse, StatsSummary } from "./types";

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

export async function getBotStatsSummary(botId: number): Promise<StatsSummary> {
  const response = await httpClient(`/bots/${botId}/stats/summary`);

  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Не удалось загрузить статистику бота"));
  }

  return (await response.json()) as StatsSummary;
}
