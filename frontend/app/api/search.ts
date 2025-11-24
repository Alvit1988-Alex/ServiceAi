import { httpClient } from "./httpClient";
import { DialogSearchParams, DialogShort, ListResponse } from "./types";

function buildQueryString(params: DialogSearchParams): string {
  const searchParams = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      searchParams.append(key, String(value));
    }
  });

  const queryString = searchParams.toString();
  return queryString ? `?${queryString}` : "";
}

export async function searchDialogs(
  botId: number,
  params: DialogSearchParams,
): Promise<ListResponse<DialogShort>> {
  const query = buildQueryString(params);
  const response = await httpClient(`/bots/${botId}/search${query}`);

  if (!response.ok) {
    throw new Error("Не удалось выполнить поиск диалогов");
  }

  return (await response.json()) as ListResponse<DialogShort>;
}
