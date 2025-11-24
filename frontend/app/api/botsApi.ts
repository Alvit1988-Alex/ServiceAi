import { httpClient } from "./httpClient";
import { Bot, ListResponse, StatsSummary } from "./types";

export async function fetchBots(): Promise<Bot[]> {
  const response = await httpClient("/bots");

  if (!response.ok) {
    throw new Error("Не удалось загрузить список ботов");
  }

  const data = (await response.json()) as ListResponse<Bot>;
  return data.items;
}

export async function fetchBotStats(botId: number): Promise<StatsSummary> {
  const response = await httpClient(`/bots/${botId}/stats/summary`);

  if (!response.ok) {
    throw new Error("Не удалось загрузить статистику бота");
  }

  return (await response.json()) as StatsSummary;
}
