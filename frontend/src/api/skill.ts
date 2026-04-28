import api from './index'

export interface SkillInfo {
  name: string
  description: string
  path: string
  has_scripts: boolean
}

export interface SkillContent {
  name: string
  path: string
  content: string
  has_scripts: boolean
}

export interface SkillListResponse {
  skills: SkillInfo[]
  total: number
}

export const skillApi = {
  list: async () => {
    return api.get<SkillListResponse>('/skills/list')
  },
  get: async (skillName: string) => {
    return api.get<SkillContent>(`/skills/${skillName}`)
  },
  update: async (skillName: string, content: string) => {
    return api.put<{ name: string; status: string; message: string }>(
      `/skills/${skillName}`,
      { content }
    )
  },
  create: async (name: string, description: string = '') => {
    return api.post<{ name: string; path: string; status: string; message: string }>(
      '/skills/create',
      { name, description }
    )
  },
  delete: async (skillName: string) => {
    return api.delete<{ name: string; status: string; message: string }>(
      `/skills/${skillName}`
    )
  },
}