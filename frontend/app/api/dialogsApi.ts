import { httpClient } from "./httpClient";
import {
  ChannelType,
  DialogDetail,
  DialogMessage,
  DialogShort,
  DialogStatus,
  ListResponse,
} from "./types";

interface ListDialogsParams {
  status?: DialogStatus;
  channel_type?: ChannelType;
  assigned_admin_id?: number;
  external_chat_id?: string;
  closed?: boolean;
  is_locked?: boolean;
  page?: number;
  per_page?: number;
}

interface SearchDialogsParams {
  query?: string;
  status?: DialogStatus;
  assigned_admin_id?: number;
  channel_type?: ChannelType;
  limit?: number;
  offset?: number;
}

interface OperatorMessagePayload {
  text?: string | null;
  payload?: Record<string, unknown> | null;
}

async function getErrorMessage(response: Response, fallback: string): Promise<string> {
  try {
    const data = (await response.json()) as { detail?: string };
    if (data?.detail) {
      return data.detail;
    }
  } catch (error) {
    console.error("Failed to parse dialogs API error", error);
  }

  return fallback;
}

function buildQueryString(params: Record<string, unknown>): string {
  const searchParams = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      searchParams.append(key, String(value));
    }
  });

  const queryString = searchParams.toString();
  return queryString ? `?${queryString}` : "";
}

export async function listDialogs(
  botId: number,
  params: ListDialogsParams = {},
): Promise<ListResponse<DialogShort>> {
  const query = buildQueryString(params);
  const response = await httpClient(`/bots/${botId}/dialogs${query}`);

  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Не удалось загрузить список диалогов"));
  }

  return (await response.json()) as ListResponse<DialogShort>;
}

export async function searchDialogs(
  botId: number,
  params: SearchDialogsParams = {},
): Promise<ListResponse<DialogShort>> {
  const query = buildQueryString(params);
  const response = await httpClient(`/bots/${botId}/search${query}`);

  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Не удалось выполнить поиск диалогов"));
  }

  return (await response.json()) as ListResponse<DialogShort>;
}

export async function getDialog(botId: number, dialogId: number): Promise<DialogDetail> {
  const response = await httpClient(`/bots/${botId}/dialogs/${dialogId}`);

  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Не удалось загрузить диалог"));
  }

  return (await response.json()) as DialogDetail;
}

export async function closeDialog(botId: number, dialogId: number): Promise<DialogDetail> {
  const response = await httpClient(`/bots/${botId}/dialogs/${dialogId}/close`, {
    method: "POST",
  });

  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Не удалось закрыть диалог"));
  }

  return (await response.json()) as DialogDetail;
}

export async function lockDialog(botId: number, dialogId: number): Promise<DialogDetail> {
  const response = await httpClient(`/bots/${botId}/dialogs/${dialogId}/lock`, {
    method: "POST",
  });

  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Не удалось заблокировать диалог"));
  }

  return (await response.json()) as DialogDetail;
}

export async function unlockDialog(botId: number, dialogId: number): Promise<DialogDetail> {
  const response = await httpClient(`/bots/${botId}/dialogs/${dialogId}/unlock`, {
    method: "POST",
  });

  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Не удалось разблокировать диалог"));
  }

  return (await response.json()) as DialogDetail;
}

export async function sendOperatorMessage(
  botId: number,
  dialogId: number,
  payload: OperatorMessagePayload,
): Promise<DialogMessage> {
  const response = await httpClient(`/bots/${botId}/dialogs/${dialogId}/message`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Не удалось отправить сообщение"));
  }

  return (await response.json()) as DialogMessage;
}
