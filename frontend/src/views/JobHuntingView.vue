<script setup lang="ts">
import { ref, onMounted, computed, Teleport, Transition, nextTick } from 'vue'
import { Button, Modal, Form, FormItem, Input, Select, DatePicker, message, Spin, Tag } from 'ant-design-vue'
import { PlusOutlined, ReloadOutlined, ZoomInOutlined, ZoomOutOutlined, DeleteOutlined } from '@ant-design/icons-vue'
import dayjs, { type Dayjs } from 'dayjs'
import { interviewApi, type InterviewRecord, type InterviewCreateData, type InterviewUpdateData } from '@/api/interview'

const interviews = ref<InterviewRecord[]>([])
const loading = ref(true)

const addModalVisible = ref(false)
const addFormRef = ref()
const addFormDate = ref<Dayjs>()
const addForm = ref<InterviewCreateData>({
  company_department: '',
  position: '',
  start_time: '',
  interview_type: '',
  review: '',
})

const reviewModalVisible = ref(false)
const editingInterview = ref<InterviewRecord | null>(null)
const editFormRef = ref()
const editFormDate = ref<Dayjs>()
const editForm = ref<InterviewUpdateData>({
  company_department: '',
  position: '',
  start_time: '',
  interview_type: '',
  review: '',
})

const STAGE_CONFIG: Record<string, { label: string; color: string; bgColor: string }> = {
  '简历筛选': { label: '简历', color: '#94a3b8', bgColor: '#f1f5f9' },
  '笔试': { label: '笔试', color: '#3b82f6', bgColor: '#dbeafe' },
  '一面': { label: '一面', color: '#f59e0b', bgColor: '#fef3c7' },
  '二面': { label: '二面', color: '#f97316', bgColor: '#ffedd5' },
  '三面': { label: '三面', color: '#fb7185', bgColor: '#f3e8ff' },
  '四面': { label: '四面', color: '#a855f7', bgColor: '#faf5ff' },
  'HR面': { label: 'HR面', color: '#06b6d4', bgColor: '#cffafe' },
  'Offer': { label: 'Offer', color: '#10b981', bgColor: '#d1fae5' },
}

const interviewTypeOptions = [
  { label: '简历筛选', value: '简历筛选' },
  { label: '笔试', value: '笔试' },
  { label: '一面', value: '一面' },
  { label: '二面', value: '二面' },
  { label: '三面', value: '三面' },
  { label: '四面', value: '四面' },
  { label: 'HR面', value: 'HR面' },
  { label: 'Offer', value: 'Offer' },
]

const pxPerDay = ref(16)
const MIN_PX_PER_DAY = 8
const MAX_PX_PER_DAY = 32

const hoveredPoint = ref<{ company: string; position: string; stage: InterviewRecord } | null>(null);
const hoveredRow = ref<string | null>(null);
const tooltipPosition = ref({ x: 0, y: 0 });
const editingPosition = ref<{ company: string; value: string } | null>(null);
const positionInputRef = ref<HTMLInputElement | null>(null);

interface CompanyApplication {
  company: string
  position: string
  stages: InterviewRecord[]
}

const companyApplications = computed<CompanyApplication[]>(() => {
  const companyMap = new Map<string, CompanyApplication>()
  
  interviews.value.forEach(interview => {
    const key = interview.company_department
    if (!companyMap.has(key)) {
      companyMap.set(key, {
        company: key,
        position: interview.position,
        stages: []
      })
    }
    companyMap.get(key)!.stages.push(interview)
  })

  return Array.from(companyMap.values()).map(app => ({
    ...app,
    stages: app.stages.sort((a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime())
  })).sort((a, b) => {
    const aDate = a.stages.length > 0 ? new Date(a.stages[0].start_time).getTime() : 0
    const bDate = b.stages.length > 0 ? new Date(b.stages[0].start_time).getTime() : 0
    return aDate - bDate
  })
})

const dateRange = computed(() => {
  const allDates = interviews.value.map(i => new Date(i.start_time).getTime())
  if (allDates.length === 0) {
    const now = new Date()
    return {
      start: new Date(now.getFullYear(), now.getMonth(), 1),
      end: dayjs(now).add(1, 'month').endOf('month').toDate()
    }
  }
  
  const minDate = new Date(Math.min(...allDates))
  const maxDate = new Date(Math.max(...allDates))
  
  return {
    start: dayjs(minDate).subtract(7, 'day').startOf('month').toDate(),
    end: dayjs(maxDate).add(14, 'day').endOf('month').toDate()
  }
})

const totalDays = computed(() => {
  return dayjs(dateRange.value.end).diff(dayjs(dateRange.value.start), 'day') + 1
})

const totalWidth = computed(() => totalDays.value * pxPerDay.value)

const today = new Date('2026-04-30')

const todayX = computed(() => {
  const days = dayjs(today).diff(dayjs(dateRange.value.start), 'day')
  return days * pxPerDay.value + pxPerDay.value / 2
})

const todayInRange = computed(() => {
  return today >= dateRange.value.start && today <= dateRange.value.end
})

const months = computed(() => {
  const result: { date: Date; daysInMonth: number; x: number }[] = []
  let current = new Date(dateRange.value.start)
  while (current <= dateRange.value.end) {
    const x = dayjs(current).diff(dayjs(dateRange.value.start), 'day') * pxPerDay.value
    const daysInMonth = dayjs(current).daysInMonth()
    result.push({ date: new Date(current), daysInMonth, x })
    current = dayjs(current).add(1, 'month').toDate()
  }
  return result
})

function getX(dateStr: string) {
  const days = dayjs(dateStr).diff(dayjs(dateRange.value.start), 'day')
  return days * pxPerDay.value + pxPerDay.value / 2
}

const computedStats = computed(() => {
  const companies = new Set(interviews.value.map(i => i.company_department))
  return {
    passed: interviews.value.filter(r => r.status === 'PASS').length,
    doing: interviews.value.filter(r => r.status === 'DOING' || !r.status).length,
    failed: interviews.value.filter(r => r.status === 'FAIL').length,
    companies: companies.size,
  }
})

async function loadData() {
  loading.value = true
  try {
    interviews.value = await interviewApi.getAll()
  } catch {
    message.error('加载面试数据失败')
  } finally {
    loading.value = false
  }
}

function openReviewModal(interview: InterviewRecord) {
  editingInterview.value = interview
  editForm.value = {
    company_department: interview.company_department,
    position: interview.position,
    start_time: interview.start_time,
    interview_type: interview.interview_type,
    review: interview.review || '',
  }
  if (interview.start_time) {
    editFormDate.value = dayjs(interview.start_time)
  } else {
    editFormDate.value = undefined
  }
  reviewModalVisible.value = true
}

function handleEditDateChange(date: Dayjs | string, dateString: string) {
  editFormDate.value = date instanceof dayjs ? date : (date ? dayjs(date) : undefined)
  editForm.value.start_time = dateString
}

async function saveReview() {
  if (!editingInterview.value) return
  try {
    await editFormRef.value?.validate()
  } catch {
    return
  }

  try {
    const result = await interviewApi.update(editingInterview.value.unique_id, editForm.value)
    const idx = interviews.value.findIndex(i => i.unique_id === editingInterview.value!.unique_id)
    if (idx !== -1) {
      interviews.value[idx] = result
    }
    message.success('已保存')
    reviewModalVisible.value = false
  } catch {
    message.error('保存失败')
  }
}

function openAddModal() {
  addForm.value = {
    company_department: '',
    position: '',
    start_time: '',
    interview_type: '',
    review: '',
  }
  addFormDate.value = undefined
  addModalVisible.value = true
}

async function submitAdd() {
  try {
    await addFormRef.value?.validate()
  } catch {
    return
  }

  try {
    await interviewApi.create(addForm.value)
    message.success('面试流程已添加')
    addModalVisible.value = false
    await loadData()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    if (err?.response?.data?.detail) {
      message.error(err.response.data.detail)
    } else {
      message.error('添加失败')
    }
  }
}

function handleDateChange(date: Dayjs | string, dateString: string) {
  addFormDate.value = date instanceof dayjs ? date : (date ? dayjs(date) : undefined)
  addForm.value.start_time = dateString
}

function getStatusTag(status: string | undefined): { color: string; text: string } {
  if (status === 'PASS') return { color: '#10b981', text: '通过' }
  if (status === 'FAIL') return { color: '#ef4444', text: '未通过' }
  return { color: '#6366f1', text: '待定' }
}

async function deleteInterview(interview: InterviewRecord) {
  try {
    await interviewApi.remove(interview.unique_id)
    interviews.value = interviews.value.filter(i => i.unique_id !== interview.unique_id)
    message.success('已删除')
    reviewModalVisible.value = false
  } catch {
    message.error('删除失败')
  }
}

function onStageMouseEnter(e: MouseEvent, interview: InterviewRecord, app: CompanyApplication) {
  const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
  hoveredPoint.value = {
    company: app.company,
    position: app.position,
    stage: interview
  }
  tooltipPosition.value = { x: rect.left + rect.width / 2, y: rect.top }
}

function onStageMouseLeave() {
  hoveredPoint.value = null
}

function zoomIn() {
  pxPerDay.value = Math.min(MAX_PX_PER_DAY, pxPerDay.value + 4)
}

function zoomOut() {
  pxPerDay.value = Math.max(MIN_PX_PER_DAY, pxPerDay.value - 4)
}

function startEditPosition(company: string, currentPosition: string, e: Event) {
  e.stopPropagation()
  editingPosition.value = { company, value: currentPosition }
  nextTick(() => {
    positionInputRef.value?.focus()
  })
}

async function savePosition(app: CompanyApplication) {
  if (!editingPosition.value || editingPosition.value.company !== app.company) {
    editingPosition.value = null
    return
  }
  
  const newPosition = editingPosition.value.value.trim()
  if (!newPosition) {
    editingPosition.value = null
    return
  }
  
  try {
    const appRecords = interviews.value.filter(i => i.company_department === app.company)
    for (const record of appRecords) {
      await interviewApi.update(record.unique_id, { ...record, position: newPosition })
      record.position = newPosition
    }
    message.success('职位已更新')
  } catch {
    message.error('更新失败')
  } finally {
    editingPosition.value = null
  }
}

function cancelEditPosition() {
  editingPosition.value = null
}

onMounted(async () => {
  await loadData()
})
</script>

<template>
  <div class="job-hunting-view">
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">求职进度</h1>
        <p class="page-subtitle">跟踪和管理各公司的面试流程进展</p>
      </div>
      <div class="header-right">
        <Button class="refresh-btn" @click="loadData" :loading="loading">
          <template #icon><ReloadOutlined /></template>
        </Button>
        <Button type="primary" @click="openAddModal">
          <template #icon><PlusOutlined /></template>
          添加流程
        </Button>
      </div>
    </div>

    <div class="stats-row">
      <div class="stat-card">
        <div class="stat-icon" style="background: #eef2ff; color: #6366f1;">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 2L11 13"></path>
            <path d="M22 2l-7 20-4-9-9-4 20-7z"></path>
          </svg>
        </div>
        <div class="stat-body">
          <div class="stat-value">{{ computedStats.companies }}</div>
          <div class="stat-label">投递公司</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon" style="background: #ecfdf5; color: #10b981;">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
            <polyline points="22,4 12,14.01 9,11.01"></polyline>
          </svg>
        </div>
        <div class="stat-body">
          <div class="stat-value" style="color: #10b981;">{{ computedStats.passed }}</div>
          <div class="stat-label">已通过</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: #eff6ff; color: #6366f1;">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"></circle>
            <polygon points="16.24,7.76 14.12,14.12 7.76,16.24 9.88,9.88 16.24,7.76"></polygon>
          </svg>
        </div>
        <div class="stat-body">
          <div class="stat-value" style="color: #6366f1;">{{ computedStats.doing }}</div>
          <div class="stat-label">进行中</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: #fef2f2; color: #ef4444;">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="15" y1="9" x2="9" y2="15"></line>
            <line x1="9" y1="9" x2="15" y2="15"></line>
          </svg>
        </div>
        <div class="stat-body">
          <div class="stat-value" style="color: #ef4444;">{{ computedStats.failed }}</div>
          <div class="stat-label">未通过</div>
        </div>
      </div>
    </div>

    <div class="chart-section">
      <div class="chart-toolbar">
        <div class="legend">
          <div v-for="(config, type) in STAGE_CONFIG" :key="type" class="legend-item">
            <div class="legend-dot" :style="{ background: config.color }"></div>
            <span class="legend-label">{{ config.label }}</span>
          </div>
        </div>
        <div class="zoom-controls">
          <button class="zoom-btn" @click="zoomOut" :disabled="pxPerDay <= MIN_PX_PER_DAY">
            <ZoomOutOutlined />
          </button>
          <span class="zoom-level">{{ pxPerDay }}px</span>
          <button class="zoom-btn" @click="zoomIn" :disabled="pxPerDay >= MAX_PX_PER_DAY">
            <ZoomInOutlined />
          </button>
        </div>
      </div>

      <div v-if="loading" class="chart-loading">
        <Spin size="large" />
      </div>

      <div v-else class="chart-wrapper">
        <div v-if="companyApplications.length > 0" class="chart-scroll">
          <div class="chart" :style="{ minWidth: `${totalWidth + 196}px` }">
            <div class="chart-header">
              <div class="company-cell sticky-cell">
                <span class="company-label">公司</span>
              </div>
              <div class="timeline-header" :style="{ height: '44px' }">
                <div v-for="month in months" :key="month.date.toISOString()" class="month-label" :style="{ left: `${month.x}px`, width: `${month.daysInMonth * pxPerDay}px` }">
                  <span>{{ dayjs(month.date).format('YYYY年M月') }}</span>
                </div>
                <div v-for="month in months" :key="`line-${month.date.toISOString()}`" class="month-line" :style="{ left: `${month.x}px` }"></div>
              </div>
            </div>

            <div class="chart-body">
              <div v-for="(app, index) in companyApplications" :key="app.company" class="chart-row" :class="{ hover: hoveredRow === app.company }" @mouseenter="hoveredRow = app.company" @mouseleave="hoveredRow = null" :style="{ background: index % 2 === 0 ? '#ffffff' : '#fafafa' }">
                <div class="company-cell sticky-cell">
                  <div class="company-info">
                    <div class="company-name" :title="app.company">{{ app.company }}</div>
                    <div v-if="editingPosition?.company === app.company" class="company-position-edit">
                      <input
                        ref="positionInputRef"
                        v-model="editingPosition.value"
                        class="position-input"
                        @blur="savePosition(app)"
                        @keyup.enter="savePosition(app)"
                        @keyup.escape="cancelEditPosition"
                      />
                    </div>
                    <div v-else class="company-position" @click="startEditPosition(app.company, app.position, $event)">
                      {{ app.position }}
                      <span class="edit-hint">✎</span>
                    </div>
                  </div>
                </div>
                <div class="timeline-row">
                  <div v-for="month in months" :key="`row-line-${month.date.toISOString()}`" class="month-line" :style="{ left: `${month.x}px` }"></div>
                  <div v-if="todayInRange" class="today-line" :style="{ left: `${todayX}px` }"></div>
                  <div v-if="app.stages.length > 1" class="connecting-line" :style="{ left: `${getX(app.stages[0].start_time)}px`, width: `${getX(app.stages[app.stages.length - 1].start_time) - getX(app.stages[0].start_time)}px` }"></div>
                  <div v-for="stage in app.stages" :key="stage.unique_id" class="stage-dot" :style="{ left: `${getX(stage.start_time) - 9}px` }" @click="openReviewModal(stage)" @mouseenter="onStageMouseEnter($event, stage, app)" @mouseleave="onStageMouseLeave">
                    <div v-if="!stage.status || stage.status === 'DOING'" class="pending-ring" :style="{ background: (STAGE_CONFIG[stage.interview_type]?.bgColor || '#f1f5f9'), borderColor: (STAGE_CONFIG[stage.interview_type]?.color || '#94a3b8') }"></div>
                    <div class="dot-main" :style="{ background: stage.status === 'FAIL' ? '#ef4444' : (!stage.status || stage.status === 'DOING' ? '#ffffff' : (STAGE_CONFIG[stage.interview_type]?.color || '#94a3b8')), border: (!stage.status || stage.status === 'DOING' ? `2.5px dashed ${STAGE_CONFIG[stage.interview_type]?.color || '#94a3b8'}` : (stage.status === 'FAIL' ? '2.5px solid #fca5a5' : '2.5px solid white')), boxShadow: `0 0 0 2px ${stage.status === 'FAIL' ? '#fee2e2' : (!stage.status || stage.status === 'DOING' ? (STAGE_CONFIG[stage.interview_type]?.bgColor || '#f1f5f9') : (STAGE_CONFIG[stage.interview_type]?.bgColor || '#f1f5f9'))}` }">
                      <span :style="{ color: (!stage.status || stage.status === 'DOING' ? (STAGE_CONFIG[stage.interview_type]?.color || '#94a3b8') : 'white') }">{{ STAGE_CONFIG[stage.interview_type]?.label?.slice(0, 2) || '面' }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div v-else class="empty-state">
          <div class="empty-icon">📋</div>
          <div class="empty-title">还没有求职记录</div>
          <div class="empty-desc">点击右上角"添加流程"按钮，记录你的第一场面试</div>
          <Button type="primary" @click="openAddModal" size="large">
            <template #icon><PlusOutlined /></template>
            添加第一个流程
          </Button>
        </div>
      </div>
    </div>

    <Teleport to="body">
      <Transition name="tooltip">
        <div v-if="hoveredPoint" class="chart-tooltip" :style="{ position: 'fixed', left: `${tooltipPosition.x}px`, top: `${tooltipPosition.y}px`, transform: 'translate(-50%, -100%)' }">
          <div class="tooltip-content">
            <div class="tooltip-header">
              <div class="tooltip-type" :style="{ background: STAGE_CONFIG[hoveredPoint.stage.interview_type]?.color || '#94a3b8' }"></div>
              <span class="tooltip-stage">{{ STAGE_CONFIG[hoveredPoint.stage.interview_type]?.label || hoveredPoint.stage.interview_type }}</span>
              <Tag :color="getStatusTag(hoveredPoint.stage.status).color" class="tooltip-status">
                {{ getStatusTag(hoveredPoint.stage.status).text }}
              </Tag>
            </div>
            <div class="tooltip-company">{{ hoveredPoint.company }} · {{ hoveredPoint.position }}</div>
            <div class="tooltip-date">📅 {{ dayjs(hoveredPoint.stage.start_time).format('YYYY年M月D日') }}</div>
            <div v-if="hoveredPoint.stage.review" class="tooltip-notes">{{ hoveredPoint.stage.review }}</div>
            <div class="tooltip-arrow"></div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <Modal
      v-model:open="reviewModalVisible"
      title="编辑面试记录"
      :footer="null"
      width="520px"
      destroy-on-close
      class="review-modal"
    >
      <Form
        v-if="editingInterview"
        ref="editFormRef"
        :model="editForm"
        layout="vertical"
        class="edit-form"
      >
        <div class="form-row">
          <FormItem
            label="公司名称（部门）"
            name="company_department"
            :rules="[{ required: true, message: '请输入公司名称' }]"
            class="form-col"
          >
            <Input v-model:value="editForm.company_department" placeholder="如：字节跳动（抖音）" />
          </FormItem>
          <FormItem
            label="应聘职位"
            name="position"
            :rules="[{ required: true, message: '请输入应聘职位' }]"
            class="form-col"
          >
            <Input v-model:value="editForm.position" placeholder="如：前端开发工程师" />
          </FormItem>
        </div>
        <div class="form-row">
          <FormItem
            label="时间节点"
            name="start_time"
            :rules="[{ required: true, message: '请选择时间' }]"
            class="form-col"
          >
            <DatePicker
              :value="editFormDate"
              show-time
              format="YYYY-MM-DD HH:mm:ss"
              placeholder="选择日期时间"
              style="width: 100%"
              @change="handleEditDateChange"
            />
          </FormItem>
          <FormItem
            label="流程类型"
            name="interview_type"
            :rules="[{ required: true, message: '请选择流程类型' }]"
            class="form-col"
          >
            <Select
              v-model:value="editForm.interview_type"
              :options="interviewTypeOptions"
              placeholder="选择流程类型"
            />
          </FormItem>
        </div>
        <FormItem label="复盘总结">
          <Input.TextArea
            v-model:value="editForm.review"
            placeholder="输入面试复盘总结、学到的东西、需要改进的地方..."
            :rows="5"
          />
        </FormItem>
        <div class="edit-form-actions">
          <Button danger @click="deleteInterview(editingInterview)" v-if="editingInterview">
            <template #icon><DeleteOutlined /></template>
            删除记录
          </Button>
          <div class="actions-right">
            <Button @click="reviewModalVisible = false">取消</Button>
            <Button type="primary" @click="saveReview">保存记录</Button>
          </div>
        </div>
      </Form>
    </Modal>

    <Modal
      v-model:open="addModalVisible"
      title="添加面试流程"
      :footer="null"
      width="520px"
      destroy-on-close
      class="add-modal"
    >
      <Form
        ref="addFormRef"
        :model="addForm"
        layout="vertical"
        class="add-form"
      >
        <div class="form-row">
          <FormItem
            label="公司名称（部门）"
            name="company_department"
            :rules="[{ required: true, message: '请输入公司名称' }]"
            class="form-col"
          >
            <Input v-model:value="addForm.company_department" placeholder="如：字节跳动（抖音）" />
          </FormItem>
          <FormItem
            label="应聘职位"
            name="position"
            :rules="[{ required: true, message: '请输入应聘职位' }]"
            class="form-col"
          >
            <Input v-model:value="addForm.position" placeholder="如：前端开发工程师" />
          </FormItem>
        </div>
        <div class="form-row">
          <FormItem
            label="时间节点"
            name="start_time"
            :rules="[{ required: true, message: '请选择时间' }]"
            class="form-col"
          >
            <DatePicker
              :value="addFormDate"
              show-time
              format="YYYY-MM-DD HH:mm:ss"
              placeholder="选择日期时间"
              style="width: 100%"
              @change="handleDateChange"
            />
          </FormItem>
          <FormItem
            label="流程类型"
            name="interview_type"
            :rules="[{ required: true, message: '请选择流程类型' }]"
            class="form-col"
          >
            <Select
              v-model:value="addForm.interview_type"
              :options="interviewTypeOptions"
              placeholder="选择流程类型"
            />
          </FormItem>
        </div>
        <FormItem label="备注">
          <Input.TextArea
            v-model:value="addForm.review"
            placeholder="可选备注信息"
            :rows="3"
          />
        </FormItem>
        <div class="add-form-actions">
          <Button @click="addModalVisible = false">取消</Button>
          <Button type="primary" @click="submitAdd">确认添加</Button>
        </div>
      </Form>
    </Modal>
  </div>
</template>

<style scoped>
.job-hunting-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 48px;
  box-sizing: border-box;
  gap: 24px;
  max-width: 1400px;
  margin: 0 auto;
  background: #ffffff;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  flex-shrink: 0;
}

.header-left {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.page-title {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  color: #040404;
  line-height: 1.3;
}

.page-subtitle {
  margin: 0;
  font-size: 13px;
  color: #575757;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-right :deep(.ant-btn-primary) {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  background: #040404;
  border: none;
  border-radius: 5px;
  font-size: 13px;
  font-weight: 500;
  height: auto;
  box-shadow: none !important;
}

.header-right :deep(.ant-btn-primary:hover) {
  background: #FF5C1A !important;
  transform: translateY(-1px);
}

.refresh-btn {
  border-radius: 5px !important;
  border-color: rgba(0, 0, 0, 0.1) !important;
  background: #f8fafc !important;
  color: #64748b !important;
}

.refresh-btn:hover {
  color: #FF5C1A !important;
  border-color: #FF5C1A !important;
  background: #FFEDE3 !important;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  flex-shrink: 0;
}

.stat-card {
  background: #ffffff;
  border: 1px solid #f1f5f9;
  border-radius: 14px;
  padding: 16px 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  transition: all 0.15s ease;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}

.stat-card:hover {
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.07);
  transform: translateY(-1px);
}

.stat-icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-body {
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: 26px;
  font-weight: 700;
  color: #040404;
  line-height: 1;
  letter-spacing: -0.02em;
}

.stat-label {
  font-size: 13px;
  color: #94a3b8;
  font-weight: 400;
  margin-top: 2px;
}

.chart-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: #ffffff;
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 12px;
  overflow: hidden;
}

.chart-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);
  background: #fafafa;
}

.legend {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.legend-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  flex-shrink: 0;
}

.legend-label {
  font-size: 12px;
  color: #64748b;
}

.zoom-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.zoom-btn {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  color: #64748b;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.15s;
  padding: 0;
}

.zoom-btn:hover:not(:disabled) {
  background: #FF5C1A;
  border-color: #FF5C1A;
  color: white;
}

.zoom-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.zoom-level {
  font-size: 12px;
  color: #94a3b8;
  min-width: 36px;
  text-align: center;
}

.chart-loading {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
}

.chart-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.chart-scroll {
  flex: 1;
  overflow: auto;
  min-height: 0;
}

.chart {
  display: flex;
  flex-direction: column;
}

.chart-header {
  display: flex;
  position: sticky;
  top: 0;
  z-index: 20;
  background: #fafafa;
}

.company-cell {
  width: 196px;
  flex-shrink: 0;
  padding: 0 16px;
  display: flex;
  align-items: center;
  background: #fafafa;
  border-right: 1px solid #e2e8f0;
  z-index: 30;
}

.sticky-cell {
  position: sticky;
  left: 0;
}

.company-label {
  font-size: 12px;
  color: #94a3b8;
  font-weight: 600;
}

.timeline-header {
  flex: 1;
  position: relative;
}

.month-label {
  position: absolute;
  top: 0;
  display: flex;
  align-items: center;
  padding-left: 12px;
  height: 44px;
  font-size: 12px;
  color: #64748b;
  font-weight: 600;
  white-space: nowrap;
}

.month-line {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 1px;
  background: #e2e8f0;
}

.chart-body {
  display: flex;
  flex-direction: column;
}

.chart-row {
  display: flex;
  height: 60px;
  border-bottom: 1px solid #f1f5f9;
  transition: background 0.15s;
}

.chart-row.hover {
  background: #fff8ed !important;
}

.chart-row.hover .company-cell {
  background: #fff8ed !important;
}

.chart-row .company-cell {
  background: inherit;
  border-right: 1px solid #f1f5f9;
}

.company-info {
  flex: 1;
  min-width: 0;
}

.company-name {
  font-size: 13px;
  font-weight: 500;
  color: #1e293b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.company-position {
  font-size: 11px;
  color: #94a3b8;
  margin-top: 1px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  transition: color 0.15s;
}

.company-position:hover {
  color: #64748b;
}

.company-position:hover .edit-hint {
  opacity: 1;
}

.edit-hint {
  font-size: 10px;
  opacity: 0;
  transition: opacity 0.15s;
}

.company-position-edit {
  margin-top: 1px;
}

.position-input {
  width: 100%;
  font-size: 11px;
  padding: 2px 6px;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  outline: none;
  background: white;
  color: #1e293b;
}

.position-input:focus {
  border-color: #FF5C1A;
  box-shadow: 0 0 0 2px rgba(255, 92, 26, 0.1);
}

.timeline-row {
  flex: 1;
  position: relative;
}

.today-line {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 1px;
  background: rgba(250, 152, 25, 0.4);
  z-index: 1;
}

.connecting-line {
  position: absolute;
  top: 29px;
  height: 2px;
  background: linear-gradient(90deg, #e2e8f0, #cbd5e1);
  z-index: 1;
  border-radius: 1px;
}

.stage-dot {
  position: absolute;
  top: 21px;
  width: 18px;
  height: 18px;
  cursor: pointer;
  z-index: 2;
}

.pending-ring {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  border: 2px solid;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.dot-main {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 7px;
  font-weight: 700;
  line-height: 1;
  user-select: none;
}

.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 48px;
}

.empty-icon {
  font-size: 48px;
}

.empty-title {
  font-size: 14px;
  font-weight: 600;
  color: #575757;
  margin: 0;
}

.empty-desc {
  font-size: 12px;
  color: #cbd5e1;
  margin: 0;
  text-align: center;
  line-height: 1.7;
}

.tooltip-enter-active,
.tooltip-leave-active {
  transition: opacity 0.15s ease;
}

.tooltip-enter-from,
.tooltip-leave-to {
  opacity: 0;
}

.chart-tooltip {
  z-index: 1000;
  pointer-events: none;
}

.tooltip-content {
  background: #1e293b;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 12px 16px;
  min-width: 180px;
  max-width: 280px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
}

.tooltip-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.tooltip-type {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.tooltip-stage {
  font-size: 13px;
  font-weight: 600;
  color: white;
}

.tooltip-status {
  margin-left: auto;
  font-size: 11px;
  border-radius: 4px;
  padding: 2px 8px;
  border: none;
  background: transparent;
}

.tooltip-company {
  font-size: 12px;
  color: #94a3b8;
  margin-bottom: 4px;
}

.tooltip-date {
  font-size: 12px;
  color: #64748b;
}

.tooltip-notes {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  font-size: 12px;
  color: #94a3b8;
}

.tooltip-arrow {
  position: absolute;
  bottom: -6px;
  left: 50%;
  transform: translateX(-50%);
  width: 0;
  height: 0;
  border-left: 6px solid transparent;
  border-right: 6px solid transparent;
  border-top: 6px solid #1e293b;
}

.edit-form,
.add-form {
  width: 100%;
}

.form-row {
  display: flex;
  gap: 16px;
}

.form-col {
  flex: 1;
  min-width: 0;
}

.edit-form-actions,
.add-form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 8px;
  padding-top: 16px;
  border-top: 1px solid #f1f5f9;
}

.edit-form-actions {
  justify-content: space-between;
}

.actions-right {
  display: flex;
  gap: 8px;
}

@media (max-width: 1024px) {
  .stats-row {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .job-hunting-view {
    padding: 16px;
    gap: 16px;
  }

  .page-header {
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }

  .header-right {
    width: 100%;
    justify-content: flex-end;
  }

  .stats-row {
    grid-template-columns: repeat(2, 1fr);
    gap: 8px;
  }

  .stat-card {
    padding: 12px;
  }

  .stat-value {
    font-size: 22px;
  }

  .form-row {
    flex-direction: column;
    gap: 0;
  }

  .legend {
    display: none;
  }
}

@media (max-width: 480px) {
  .job-hunting-view {
    padding: 12px;
  }

  .page-title {
    font-size: 18px;
  }

  .stats-row {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
