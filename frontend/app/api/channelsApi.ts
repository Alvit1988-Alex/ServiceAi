import { httpClient } from "./httpClient";
import { BotChannel, ChannelType, ListResponse } from "./types";

interface BotChannelCreatePayload {
  channel_type: ChannelType;
  config: Record<string, unknown>;
  is_active?: boolean;
}

interface BotChannelUpdatePayload {
  config?: Record<string, unknown>;
  is_active?: boolean;
}

async function getErrorMessage(response: Response, fallback: string): Promise<string> {
  try {
    const data = (await response.json()) as { detail?: string };
    if (data?.detail) {
      return data.detail;
    }
  } catch (error) {
    console.error("Failed to parse channels API error", error);
  }

  return fallback;
}

export async function listChannels(botId: number): Promise<BotChannel[]> {
  const response = await httpClient(`/bots/${botId}/channels`);

  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Не удалось загрузить список каналов"));
  }

  const data = (await response.json()) as ListResponse<BotChannel>;
  return data.items;
}

export async function getChannel(botId: number, channelId: number): Promise<BotChannel> {
  const response = await httpClient(`/bots/${botId}/channels/${channelId}`);

  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Не удалось загрузить канал"));
  }

  return (await response.json()) as BotChannel;
}

export async function createChannel(
  botId: number,
  payload: BotChannelCreatePayload,
): Promise<BotChannel> {
  const response = await httpClient(`/bots/${botId}/channels`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Не удалось создать канал"));
  }

  return (await response.json()) as BotChannel;
}

export async function updateChannel(
  botId: number,
  channelId: number,
  payload: BotChannelUpdatePayload,
): Promise<BotChannel> {
  const response = await httpClient(`/bots/${botId}/channels/${channelId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Не удалось обновить канал"));
  }

  return (await response.json()) as BotChannel;
}

export async function deleteChannel(botId: number, channelId: number): Promise<void> {
  const response = await httpClient(`/bots/${botId}/channels/${channelId}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Не удалось удалить канал"));
  }
}
