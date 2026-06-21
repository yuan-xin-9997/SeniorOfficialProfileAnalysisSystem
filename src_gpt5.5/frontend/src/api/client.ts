export type Role = "ADMIN" | "USER";

export interface CurrentUser {
  id: string;
  username: string;
  role: Role;
  display_name?: string | null;
}

export interface Official {
  id: string;
  name: string;
  gender?: string | null;
  ethnicity?: string | null;
  birth_date?: string | null;
  birth_date_precision: string;
  current_status?: string | null;
  profile_summary?: string | null;
  data_quality_score?: number | null;
  review_status: string;
  created_at: string;
  updated_at: string;
}

export interface CommitteeTerm {
  id: string;
  term_no: number;
  name: string;
  start_year?: number | null;
  end_year?: number | null;
  is_current: boolean;
  created_at: string;
  updated_at: string;
}

export interface CommitteeImportResult {
  term_id: string;
  created_officials: number;
  updated_officials: number;
  memberships_upserted: number;
  skipped_rows: number;
}

export interface CareerEvent {
  id: string;
  official_id: string;
  event_type: string;
  start_date?: string | null;
  end_date?: string | null;
  start_precision: string;
  end_precision: string;
  organization_name?: string | null;
  position_name?: string | null;
  location_name?: string | null;
  description: string;
  original_text?: string | null;
  confidence: number;
  review_status: string;
}

export interface Relationship {
  id: string;
  subject_official_id: string;
  object_official_id: string;
  subject_name?: string | null;
  object_name?: string | null;
  relationship_type: string;
  strength_score: number;
  confidence: number;
  is_inferred: boolean;
  evidence_summary?: string | null;
  review_status: string;
  created_at: string;
  updated_at: string;
}

export interface SourceConfig {
  id: string;
  name: string;
  base_url: string;
  source_type: string;
  trust_level: string;
  crawl_strategy: string;
  frequency_cron: string;
  request_interval_seconds: number;
  max_retry: number;
  is_enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface SourceDocument {
  id: string;
  source_config_id?: string | null;
  url: string;
  title?: string | null;
  publisher?: string | null;
  fetched_at: string;
  http_status?: number | null;
  content_hash?: string | null;
  raw_html_path?: string | null;
  plain_text_path?: string | null;
  trust_level: string;
  parse_status: string;
  created_at: string;
  plain_text_excerpt?: string | null;
}

export interface SourceParseResult {
  official_id?: string | null;
  official_name?: string | null;
  created_events: number;
  skipped_duplicates: number;
  parsed_candidates: number;
  message: string;
}

export interface AnalysisTask {
  id: string;
  name: string;
  task_type: string;
  status: string;
  parameters?: Record<string, unknown>;
  result_summary?: Record<string, unknown> | null;
  created_at: string;
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

let accessToken = localStorage.getItem("access_token");

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  if (accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
    credentials: "include"
  });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `HTTP ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  setAccessToken(token: string | null) {
    accessToken = token;
    if (token) {
      localStorage.setItem("access_token", token);
    } else {
      localStorage.removeItem("access_token");
    }
  },

  login(username: string, password: string) {
    return request<{ access_token: string; role: Role; username: string }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password })
    });
  },

  me() {
    return request<CurrentUser>("/api/auth/me");
  },

  logout() {
    this.setAccessToken(null);
    return request<{ ok: boolean }>("/api/auth/logout", { method: "POST" });
  },

  listOfficials(q = "") {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    return request<Official[]>(`/api/officials?${params.toString()}`);
  },

  createOfficial(payload: Partial<Official> & { name: string }) {
    return request<Official>("/api/officials", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },

  getOfficial(id: string) {
    return request<Official>(`/api/officials/${id}`);
  },

  listTimeline(officialId: string) {
    return request<CareerEvent[]>(`/api/officials/${officialId}/timeline`);
  },

  createTimelineEvent(
    officialId: string,
    payload: {
      event_type: string;
      start_date?: string | null;
      end_date?: string | null;
      organization_name?: string | null;
      position_name?: string | null;
      location_name?: string | null;
      description: string;
    }
  ) {
    return request<CareerEvent>(`/api/officials/${officialId}/timeline`, {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },

  listCommitteeTerms() {
    return request<CommitteeTerm[]>("/api/committee/terms");
  },

  importCommitteeMembers(payload: {
    term_no: number;
    term_name: string;
    start_year: number;
    end_year?: number | null;
    csv_text: string;
  }) {
    return request<CommitteeImportResult>("/api/committee/import-members", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },

  listRelationships(officialId?: string) {
    const params = new URLSearchParams();
    if (officialId) params.set("official_id", officialId);
    return request<Relationship[]>(`/api/relationships?${params.toString()}`);
  },

  rebuildRelationships() {
    return request<{ generated_relationships: number; relationship_types: number }>(
      "/api/relationships/rebuild",
      { method: "POST" }
    );
  },

  listAnalysisTasks() {
    return request<AnalysisTask[]>("/api/analysis/tasks");
  },

  createAnalysisTask(payload: {
    name: string;
    task_type: string;
    parameters: Record<string, unknown>;
  }) {
    return request<AnalysisTask>("/api/analysis/tasks", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },

  listSourceConfigs() {
    return request<SourceConfig[]>("/api/sources/configs");
  },

  createSourceConfig(payload: Omit<SourceConfig, "id" | "created_at" | "updated_at">) {
    return request<SourceConfig>("/api/sources/configs", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },

  crawlSourceConfig(configId: string) {
    return request<SourceDocument>(`/api/sources/configs/${configId}/crawl`, {
      method: "POST"
    });
  },

  listSourceDocuments(sourceConfigId?: string) {
    const params = new URLSearchParams();
    if (sourceConfigId) params.set("source_config_id", sourceConfigId);
    return request<SourceDocument[]>(`/api/sources/documents?${params.toString()}`);
  },

  parseSourceDocument(documentId: string) {
    return request<SourceParseResult>(`/api/sources/documents/${documentId}/parse-profile`, {
      method: "POST"
    });
  }
};
