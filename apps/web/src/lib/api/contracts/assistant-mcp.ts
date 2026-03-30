export type AssistantMcpSummary = {
  id: string;
  file_name: string | null;
  name: string;
  description: string | null;
  enabled: boolean;
  version: string;
  transport: string;
  url: string;
  timeout: number;
  header_count: number;
  updated_at: string | null;
};

export type AssistantMcpDetail = AssistantMcpSummary & {
  headers: Record<string, string>;
};

export type AssistantMcpPayload = {
  name: string;
  description?: string;
  enabled: boolean;
  version: string;
  transport: string;
  url: string;
  headers: Record<string, string>;
  timeout: number;
};
