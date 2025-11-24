import { httpClient } from "./httpClient";
import { KnowledgeFile, KnowledgeListResponse } from "./types";

async function getErrorMessage(response: Response, fallback: string): Promise<string> {
  try {
    const data = (await response.json()) as { detail?: string };
    if (data?.detail) {
      return data.detail;
    }
  } catch (error) {
    console.error("Failed to parse knowledge API error", error);
  }

  return fallback;
}

export async function getKnowledgeItems(botId: number): Promise<KnowledgeListResponse> {
  const response = await httpClient(`/bots/${botId}/ai/knowledge`);

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(response, "Не удалось загрузить список файлов базы знаний"),
    );
  }

  return (await response.json()) as KnowledgeListResponse;
}

export async function uploadKnowledgeItem(
  botId: number,
  file: File,
): Promise<KnowledgeFile> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await httpClient(`/bots/${botId}/ai/knowledge/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(response, "Не удалось загрузить файл в базу знаний"),
    );
  }

  return (await response.json()) as KnowledgeFile;
}

export async function deleteKnowledgeItem(botId: number, fileId: number): Promise<void> {
  const response = await httpClient(`/bots/${botId}/ai/knowledge/${fileId}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Не удалось удалить файл базы знаний"));
  }
}
