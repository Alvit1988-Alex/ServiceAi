export type UserRole = "admin" | "owner" | "operator";

export interface User {
  id: number;
  email: string;
  full_name?: string | null;
  first_name?: string | null;
  last_name?: string | null;
  account_public_id?: string | null;
  avatar_url?: string | null;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AccountProfile extends User {}

export interface UpdateAccountProfilePayload {
  email: string;
  first_name: string;
  last_name?: string | null;
}

export interface ChangePasswordPayload {
  current_password: string;
  new_password: string;
}

export interface AuthTokens {
  access_token?: string;
  refresh_token?: string;
  token_type?: string;
  requires_profile_completion?: boolean;
}

export interface YandexAuthStartResponse {
  auth_url: string;
}

export interface ListResponse<T> {
  items: T[];
  page: number;
  per_page: number;
  total: number;
  has_next: boolean;
}

export enum ChannelType {
  TELEGRAM = "telegram",
  WHATSAPP_GREEN = "whatsapp_green",
  WHATSAPP_360 = "whatsapp_360",
  WHATSAPP_CUSTOM = "whatsapp_custom",
  AVITO = "avito",
  MAX = "max",
  WEBCHAT = "webchat",
  VK = "vk",
  OK = "ok",
}

export const VISIBLE_CHANNEL_TYPES: ChannelType[] = [
  ChannelType.TELEGRAM,
  ChannelType.WEBCHAT,
  ChannelType.AVITO,
  ChannelType.MAX,
  ChannelType.VK,
  ChannelType.OK,
];

export type WebhookStatus = "ok" | "pending" | "error";

export interface BotChannel {
  id: number;
  bot_id: number;
  channel_type: ChannelType;
  config: Record<string, unknown>;
  webhook_status?: WebhookStatus | null;
  webhook_error?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export type BotAccessRole = "owner" | "superadmin" | "admin" | "account_operator";

export interface Bot {
  id: number;
  name: string;
  description?: string | null;
  operator_handoff_enabled: boolean;
  operator_trigger_phrases: string[];
  account_id: number;
  is_owned?: boolean;
  access_role?: BotAccessRole;
  created_at: string;
  updated_at: string;
  channels?: BotChannel[];
}

export interface BotAdmin {
  id: number;
  bot_id: number;
  user_id: number;
  role: "superadmin" | "admin";
  account_public_id: string;
  first_name?: string | null;
  last_name?: string | null;
}

export interface BotCreate {
  name: string;
  description?: string | null;
  operator_handoff_enabled?: boolean;
  operator_trigger_phrases?: string[];
}

export interface BotUpdate {
  name?: string;
  description?: string | null;
  operator_handoff_enabled?: boolean;
  operator_trigger_phrases?: string[];
}

export interface BotAiInstructions {
  id: number;
  bot_id: number;
  system_prompt: string;
  created_at: string;
  updated_at: string;
}

export interface DialogStatusBreakdown {
  auto: number;
  wait_operator: number;
  wait_user: number;
}

export interface DialogWaitingOperatorCount {
  count: number;
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

export enum DialogStatus {
  AUTO = "auto",
  WAIT_OPERATOR = "wait_operator",
  WAIT_USER = "wait_user",
}

export enum MessageSender {
  USER = "user",
  BOT = "bot",
  OPERATOR = "operator",
}

export interface DialogSearchParams {
  query: string;
  status?: DialogStatus;
  assigned_admin_id?: number;
  channel_type?: ChannelType;
  limit?: number;
  offset?: number;
}

export interface DialogAdminShort {
  id: number;
  first_name: string | null;
  last_name: string | null;
}

export interface Dialog {
  id: number;
  bot_id: number;
  channel_type: ChannelType;
  external_chat_id: string;
  external_user_id: string;
  status: DialogStatus;
  closed: boolean;
  last_message_at: string;
  last_user_message_at: string | null;
  unread_messages_count: number;
  is_locked: boolean;
  locked_until: string | null;
  assigned_admin_id: number | null;
  assigned_admin: DialogAdminShort | null;
  waiting_time_seconds: number;
  created_at: string;
  updated_at: string;
}

export interface DialogMessage {
  id: number;
  dialog_id: number;
  sender: MessageSender;
  text: string | null;
  payload: Record<string, unknown> | null;
  operator_admin_id: number | null;
  operator_admin: DialogAdminShort | null;
  created_at: string;
  updated_at: string;
}

export interface DialogShort extends Dialog {
  last_message?: DialogMessage | null;
}

export type DialogSearchResponse = ListResponse<DialogShort>;

export interface DialogDetail extends Dialog {
  last_message?: DialogMessage | null;
  messages: DialogMessage[];
}

export interface KnowledgeFile {
  id: number;
  bot_id: number;
  file_name: string;
  original_name: string;
  size_bytes: number;
  mime_type?: string;
  chunks_count: number;
  created_at: string;
}

export interface KnowledgeListResponse {
  items: KnowledgeFile[];
}
