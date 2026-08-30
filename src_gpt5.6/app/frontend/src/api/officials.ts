import request from './request'

export interface Career {
  id?: number
  start_date: string
  end_date: string
  organization: string
  position: string
  location: string
  administrative_rank: string
  description: string
  sort_order: number
}

export interface Official {
  id: number
  name: string
  gender: string
  birth_date: string | null
  ethnicity: string
  native_place: string
  education: string
  current_position: string
  organization: string
  administrative_rank: string
  status: string
  party_role: string
  summary: string
  photo_url: string
  source_url: string
  tags: string[]
  careers?: Career[]
  created_at: string
  updated_at: string
}

export interface OfficialPage { items: Official[]; total: number; page: number; page_size: number }
export interface DashboardStats {
  official_count: number; active_count: number; organization_count: number
  career_count: number; relation_count: number; recent_officials: Official[]
}
export interface Relation {
  id: number; source_id: number; target_id: number; source_name: string; target_name: string
  relation_type: string; description: string; created_at: string
}
export interface RelationAnalysis {
  source_id: number; target_id: number; source_name: string; target_name: string
  relation_type: string; summary: string; evidence: string[]; confidence: string
}
export interface TimelineResult { officials: Official[] }
export interface ResumeRefreshResult { run_id: number; status: string }

export const refreshResumesApi = (data: { mode?: 'incremental' | 'full' } = {}) =>
  request.post<unknown, ResumeRefreshResult>('/api/officials/resume-refresh', data)

export const listOfficialsApi = (params: Record<string, unknown> = {}) => request.get<unknown, OfficialPage>('/api/officials', { params })
export const getOfficialApi = (id: number) => request.get<unknown, Official>(`/api/officials/${id}`)
export const createOfficialApi = (data: Partial<Official>) => request.post<unknown, Official>('/api/officials', data)
export const updateOfficialApi = (id: number, data: Partial<Official>) => request.put<unknown, Official>(`/api/officials/${id}`, data)
export const deleteOfficialApi = (id: number) => request.delete(`/api/officials/${id}`)
export const getDashboardApi = () => request.get<unknown, DashboardStats>('/api/officials/dashboard')
export const loadTimelineApi = (official_ids: number[]) => request.post<unknown, TimelineResult>('/api/officials/timeline', { official_ids })
export const listTimelineCandidatesApi = () => request.get<unknown, Official[]>('/api/officials/timeline/candidates')
export const listRelationsApi = () => request.get<unknown, Relation[]>('/api/officials/relations')
export const analyzeRelationApi = (data: { source_id: number; target_id: number }) => request.post<unknown, RelationAnalysis>('/api/officials/relations/analyze', data)
export const createRelationApi = (data: Partial<Relation>) => request.post<unknown, Relation>('/api/officials/relations', data)
export const deleteRelationApi = (id: number) => request.delete(`/api/officials/relations/${id}`)
