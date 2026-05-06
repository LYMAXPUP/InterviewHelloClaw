import api from './index'

export interface InterviewRecord {
  unique_id: string
  company_department: string
  position: string
  start_time: string
  review: string
  status: string
  interview_type: string
  source: string
  created_at: string
  updated_at: string
}

export interface InterviewCreateData {
  company_department: string
  position: string
  start_time: string
  interview_type: string
  review?: string
}

export interface InterviewUpdateData {
  company_department?: string
  position?: string
  start_time?: string
  interview_type?: string
  review?: string
  status?: string
}

export const interviewApi = {
  getAll: async () => {
    return api.get<InterviewRecord[]>('/interviews')
  },

  create: async (data: InterviewCreateData) => {
    return api.post<InterviewRecord>('/interviews', data)
  },

  update: async (uniqueId: string, data: InterviewUpdateData) => {
    return api.put<InterviewRecord>(`/interviews/${encodeURIComponent(uniqueId)}`, data)
  },

  updateReview: async (uniqueId: string, review: string) => {
    return api.put<{ status: string; unique_id: string }>(`/interviews/${encodeURIComponent(uniqueId)}/review`, { review })
  },

  remove: async (uniqueId: string) => {
    return api.delete<{ status: string; unique_id: string }>(`/interviews/${encodeURIComponent(uniqueId)}`)
  },
}
