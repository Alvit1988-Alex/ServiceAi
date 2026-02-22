import { httpClient } from "./httpClient";

export interface BitrixIntegrationStatus {
  connected: boolean;
  enabled: boolean;
  portal_url?: string | null;
  connected_at?: string | null;
  openline_id?: string | null;
  auto_create_lead_on_first_message: boolean;
}

async function parseError(response: Response, fallback: string): Promise<string> {
  try {
    const data = (await response.json()) as { detail?: string };
    if (data?.detail) {
      return data.detail;
    }
  } catch {
    // ignore parse error
  }
  return fallback;
}

export async function getBitrixIntegration(botId: number): Promise<BitrixIntegrationStatus> {
  const response = await httpClient(`/integrations/bitrix24/status?bot_id=${botId}`);
  if (!response.ok) {
    throw new Error(await parseError(response, "Не удалось получить статус интеграции"));
  }
  return (await response.json()) as BitrixIntegrationStatus;
}

export async function startBitrixConnect(
  botId: number,
  portalUrl: string,
): Promise<{ auth_url: string }> {
  const response = await httpClient("/integrations/bitrix24/connect", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ bot_id: botId, portal_domain: portalUrl }),
  });

  if (!response.ok) {
    throw new Error(await parseError(response, "Не удалось начать подключение Bitrix24"));
  }

  return (await response.json()) as { auth_url: string };
}

export async function disconnectBitrix(botId: number): Promise<BitrixIntegrationStatus> {
  const response = await httpClient("/integrations/bitrix24/disconnect", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ bot_id: botId }),
  });

  if (!response.ok) {
    throw new Error(await parseError(response, "Не удалось отключить Bitrix24"));
  }

  return (await response.json()) as BitrixIntegrationStatus;
}

export async function updateBitrixSettings(
  botId: number,
  settings: {
    openline_id?: string | null;
    auto_create_lead_on_first_message: boolean;
  },
): Promise<BitrixIntegrationStatus> {
  const response = await httpClient("/integrations/bitrix24/settings", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ bot_id: botId, ...settings }),
  });

  if (!response.ok) {
    throw new Error(await parseError(response, "Не удалось сохранить настройки Bitrix24"));
  }

  return (await response.json()) as BitrixIntegrationStatus;
}
