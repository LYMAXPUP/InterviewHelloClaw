<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Card, List, Empty, message, Tag } from 'ant-design-vue'
import { memoryApi, type MemoryEntry } from '@/api/memory'
import { FileTextOutlined, CalendarOutlined } from '@ant-design/icons-vue'

const memories = ref<MemoryEntry[]>([])
const selectedMemory = ref<MemoryEntry | null>(null)
const loading = ref(false)

const loadMemories = async () => {
  loading.value = true
  try {
    const res = await memoryApi.list()
    memories.value = res.memories
  } catch (error) {
    message.error('加载记忆列表失败')
  } finally {
    loading.value = false
  }
}

const selectMemory = (memory: MemoryEntry) => {
  selectedMemory.value = memory
}

const formatDate = (dateStr: string) => {
  const date = new Date(dateStr)
  const today = new Date()
  const yesterday = new Date(today)
  yesterday.setDate(yesterday.getDate() - 1)

  if (dateStr === today.toISOString().split('T')[0]) {
    return '今天'
  } else if (dateStr === yesterday.toISOString().split('T')[0]) {
    return '昨天'
  }
  return dateStr
}

const isToday = (dateStr: string) => {
  return dateStr === new Date().toISOString().split('T')[0]
}

const formatMarkdown = (content: string): string => {
  return content
    .replace(/^## (.+)$/gm, '<h3>$1</h3>')
    .replace(/^# (.+)$/gm, '<h2>$1</h2>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>')
}

onMounted(() => {
  loadMemories()
})
</script>

<template>
  <div class="memory-view">
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">工作记忆</h1>
        <p class="page-subtitle">查看每日工作记录与记忆</p>
      </div>
    </div>

    <div class="memory-content">
      <!-- 记忆列表 -->
      <div class="memory-list">
        <Card :loading="loading" class="list-card" :bordered="false">
          <template #title>
            <div class="card-title-row">
              <FileTextOutlined class="card-title-icon" />
              <span>每日记录</span>
            </div>
          </template>
          <List :data-source="memories" :locale="{ emptyText: '暂无工作记忆' }">
            <template #renderItem="{ item }">
              <List.Item
                @click="selectMemory(item)"
                :class="['memory-item', { active: selectedMemory?.filename === item.filename }]"
              >
                <div class="memory-item-content">
                  <div class="memory-date">
                    <CalendarOutlined class="date-icon" />
                    <span>{{ formatDate(item.date) }}</span>
                    <Tag v-if="isToday(item.date)" color="error" size="small">今天</Tag>
                  </div>
                  <div class="memory-preview">{{ item.preview }}</div>
                </div>
              </List.Item>
            </template>
          </List>
        </Card>
      </div>

      <!-- 记忆详情 -->
      <div class="memory-detail">
        <Card v-if="selectedMemory" class="detail-card" :bordered="false">
          <template #title>
            <div class="detail-header">
              <span class="detail-date">{{ selectedMemory.date }}</span>
              <Tag v-if="isToday(selectedMemory.date)" color="error" style="margin-left: 8px">今天</Tag>
            </div>
          </template>
          <div class="memory-content-text" v-html="formatMarkdown(selectedMemory.content)"></div>
        </Card>

        <Card v-else class="empty-card" :bordered="false">
          <Empty
            description="请从左侧选择一条记忆"
            :image-style="{ height: '80px' }"
          />
        </Card>
      </div>
    </div>
  </div>
</template>

<style scoped>
.memory-view {
  min-height: 100%;
  width: 100%;
  display: flex;
  flex-direction: column;
  padding: 48px;
  box-sizing: border-box;
  max-width: 1400px;
  margin: 0 auto;
  background: #ffffff;
}

.page-header {
  flex-shrink: 0;
  margin-bottom: 24px;
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

.memory-content {
  display: flex;
  gap: 24px;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.memory-list {
  width: 280px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
}

.list-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #ffffff;
  border: 1px solid rgba(0, 0, 0, 0.1) !important;
  border-radius: 14px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}

.list-card :deep(.ant-card-body) {
  flex: 1;
  padding: 0;
  overflow-y: auto;
}

.card-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

.card-title-icon {
  color: #FF5C1A;
  font-size: 14px;
}

.memory-item {
  cursor: pointer;
  padding: 12px 16px;
  transition: all 0.15s ease;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

.memory-item:last-child {
  border-bottom: none;
}

.memory-item:hover {
  background-color: #f8fafc;
}

.memory-item.active {
  background-color: #FFEDE3;
  border-left: 3px solid #FF5C1A;
}

.memory-item-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
  width: 100%;
}

.memory-date {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
  color: #040404;
  font-size: 12px;
}

.date-icon {
  color: #FF5C1A;
  font-size: 12px;
}

.memory-preview {
  font-size: 12px;
  color: #A3A3A3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.memory-detail {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.detail-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #ffffff;
  border: 1px solid rgba(0, 0, 0, 0.1) !important;
  border-radius: 14px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}

.detail-card :deep(.ant-card-head) {
  flex-shrink: 0;
}

.detail-card :deep(.ant-card-body) {
  flex: 1;
  overflow-y: auto;
}

.detail-header {
  display: flex;
  align-items: center;
}

.detail-date {
  font-weight: 600;
  font-size: 14px;
  color: #040404;
}

.memory-content-text {
  font-size: 14px;
  line-height: 1.7;
  color: #040404;
}

.memory-content-text :deep(h2) {
  font-size: 18px;
  margin: 16px 0 12px;
  color: #040404;
  font-weight: 600;
}

.memory-content-text :deep(h3) {
  font-size: 15px;
  margin: 12px 0 8px;
  color: #FF5C1A;
  font-weight: 600;
}

.memory-content-text :deep(strong) {
  color: #040404;
  font-weight: 600;
}

.empty-card {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #ffffff;
  border: 1px solid rgba(0, 0, 0, 0.1) !important;
  border-radius: 14px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}

@media (max-width: 768px) {
  .memory-view {
    padding: 16px;
  }

  .memory-content {
    flex-direction: column;
    gap: 16px;
  }

  .memory-list {
    width: 100%;
    max-height: 260px;
  }

  .page-title {
    font-size: 18px;
  }
}
</style>
