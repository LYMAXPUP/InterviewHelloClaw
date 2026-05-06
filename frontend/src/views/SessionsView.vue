<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Button, Empty, message } from 'ant-design-vue'
import { sessionApi, type Session } from '@/api/session'
import { useRouter } from 'vue-router'
import { PlusOutlined, MessageOutlined, ClockCircleOutlined, DeleteOutlined, ArrowRightOutlined } from '@ant-design/icons-vue'

const router = useRouter()
const sessions = ref<Session[]>([])
const listLoading = ref(false)
const createLoading = ref(false)

const loadSessions = async () => {
  listLoading.value = true
  try {
    const res = await sessionApi.list()
    sessions.value = res.sessions
  } catch (error) {
    message.error('加载会话列表失败')
  } finally {
    listLoading.value = false
  }
}

const createSession = async () => {
  createLoading.value = true
  try {
    const res = await sessionApi.create()
    message.success('创建会话成功')
    await loadSessions()
    router.push({ name: 'chat', query: { session: res.session_id } })
  } catch (error) {
    message.error('创建会话失败')
  } finally {
    createLoading.value = false
  }
}

const deleteSession = async (id: string) => {
  try {
    await sessionApi.delete(id)
    message.success('删除成功')
    await loadSessions()
  } catch (error) {
    message.error('删除失败')
  }
}

const formatDate = (timestamp: number) => {
  return new Date(timestamp * 1000).toLocaleString('zh-CN')
}

onMounted(() => {
  loadSessions()
})
</script>

<template>
  <div class="sessions-view">
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">会话管理</h1>
        <p class="page-subtitle">查看和管理你与 AI 的全部对话历史，按时间倒序排列。</p>
      </div>
      <button class="add-btn" @click="createSession" :disabled="createLoading">
        <PlusOutlined />
        新建会话
      </button>
    </div>

    <div class="sessions-content">
      <!-- Sessions list -->
      <div class="sessions-list" v-if="sessions.length > 0">
        <div
          v-for="(s, i) in sessions"
          :key="s.id"
          class="session-item"
        >
          <span class="session-num">{{ String(i + 1).padStart(2, '0') }}</span>

          <div class="session-icon-wrap">
            <MessageOutlined class="session-icon" />
          </div>

          <div class="session-body">
            <div class="session-title">{{ s.id }}</div>
            <div class="session-meta">
              <span class="session-id">#{{ s.id.slice(0, 8) }}</span>
              <span>·</span>
              <span class="session-time">
                <ClockCircleOutlined />
                {{ formatDate(s.updated_at) }}
              </span>
            </div>
          </div>

          <div class="session-actions">
            <button
              class="open-btn"
              @click="router.push({ name: 'chat', query: { session: s.id } })"
            >
              打开
              <ArrowRightOutlined />
            </button>
            <button
              class="delete-btn"
              @click="deleteSession(s.id)"
              title="删除"
            >
              <DeleteOutlined />
            </button>
          </div>
        </div>
      </div>

      <!-- Empty state -->
      <div v-else class="empty-wrap">
        <Empty description="暂无会话记录">
          <Button type="primary" @click="createSession">
            <template #icon><PlusOutlined /></template>
            创建第一个会话
          </Button>
        </Empty>
      </div>
    </div>
  </div>
</template>

<style scoped>
.sessions-view {
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
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 32px;
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

.add-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  background: #040404;
  color: #ffffff;
  border-radius: 5px;
  font-size: 13px;
  font-weight: 500;
  border: none;
  cursor: pointer;
  transition: background 0.15s ease;
  font-family: var(--font-family-base);
  flex-shrink: 0;
}

.add-btn:hover {
  background: #FF5C1A;
}

.add-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.sessions-content {
  flex: 1;
  overflow-y: auto;
}

.sessions-list {
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 14px;
  overflow: hidden;
  background: #ffffff;
}

.session-item {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 20px 24px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
  transition: background 0.15s ease;
}

.session-item:last-child {
  border-bottom: none;
}

.session-item:hover {
  background: #FFEDE3;
}

.session-num {
  font-family: var(--font-family-display);
  font-size: 14px;
  color: #A3A3A3;
  width: 28px;
  flex-shrink: 0;
}

.session-icon-wrap {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #FFEDE3;
  border-radius: 8px;
  flex-shrink: 0;
}

.session-icon {
  font-size: 15px;
  color: #FF5C1A;
}

.session-body {
  flex: 1;
  min-width: 0;
}

.session-title {
  font-size: 14px;
  font-weight: 500;
  color: #040404;
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #A3A3A3;
}

.session-id {
  font-family: monospace;
}

.session-time {
  display: flex;
  align-items: center;
  gap: 4px;
}

.session-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.open-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: #ffffff;
  border: 1px solid rgba(0, 0, 0, 0.1);
  color: #040404;
  font-size: 12px;
  font-weight: 500;
  border-radius: 5px;
  cursor: pointer;
  transition: all 0.15s ease;
  font-family: var(--font-family-base);
}

.open-btn:hover {
  background: #040404;
  color: #ffffff;
}

.delete-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 5px;
  background: transparent;
  color: #A3A3A3;
  cursor: pointer;
  transition: all 0.15s ease;
}

.delete-btn:hover {
  background: #FFE3EC;
  color: #FF2D6E;
}

.empty-wrap {
  margin: 80px auto;
  text-align: center;
  max-width: 480px;
}

@media (max-width: 768px) {
  .sessions-view {
    padding: 16px;
  }

  .page-header {
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }

  .page-title {
    font-size: 18px;
  }

  .session-item {
    padding: 16px;
    gap: 12px;
  }

  .session-actions {
    flex-direction: column;
    gap: 4px;
  }
}
</style>
