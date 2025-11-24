import { httpClient } from "./httpClient";
import { BotAiInstructions } from "./types";

async function getErrorMessage(response: Response, fallback: string): Promise<string> {
  try {
    const data = (await response.json()) as { detail?: string };
    if (data?.detail) {
      return data.detail;
    }
  } catch (error) {
    console.error("Failed to parse AI API error", error);
  }

  return fallback;
}

export async function getBotAiInstructions(botId: number): Promise<BotAiInstructions> {
  const response = await httpClient(`/bots/${botId}/ai/instructions`);

  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Не удалось загрузить инструкции ИИ"));
  }

  return (await response.json()) as BotAiInstructions;
}

export async function updateBotAiInstructions(
  botId: number,
  system_prompt: string,
): Promise<BotAiInstructions> {
  const response = await httpClient(`/bots/${botId}/ai/instructions`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ system_prompt }),
  });

  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Не удалось обновить инструкции ИИ"));
  }

  return (await response.json()) as BotAiInstructions;
}
