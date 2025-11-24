export type UserRole = "admin" | "owner" | "operator";

export interface User {
  id: number;
  email: string;
  full_name?: string | null;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type?: string;
}

export interface ListResponse<T> {
  items: T[];
}

export enum ChannelType {
  TELEGRAM = "telegram",
  WHATSAPP_GREEN = "whatsapp_green",
  WHATSAPP_360 = "whatsapp_360",
  WHATSAPP_CUSTOM = "whatsapp_custom",
  AVITO = "avito",
  MAX = "max",
  WEBCHAT = "webchat",
}

export interface BotChannel {
  id: number;
  bot_id: number;
  channel_type: ChannelType;
  config: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Bot {
  id: number;
  name: string;
  description?: string | null;
  account_id: number;
  created_at: string;
  updated_at: string;
  channels?: BotChannel[];
}

export interface BotUpdate {
  name?: string;
  description?: string | null;
}

export interface DialogStatusBreakdown {
  auto: number;
  wait_operator: number;
  wait_user: number;
}

export interface DialogCounts {
  total: number;
  active: number;
  by_status: DialogStatusBreakdown;
}

export interface TimingMetrics {
  average_dialog_duration_seconds: number | null;
  average_time_to_first_message_seconds: number | null;
}

export interface StatsSummary {
  dialogs: DialogCounts;
  timing: TimingMetrics;
}
