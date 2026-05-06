<script setup lang="ts">
import { ref, watch, computed, nextTick, onMounted } from 'vue'
import { Input, Button, message, Tag, Modal, Image } from 'ant-design-vue'
import { SendOutlined, PlusOutlined, StopOutlined, LoadingOutlined } from '@ant-design/icons-vue'
import { useRouter, useRoute } from 'vue-router'
import { sessionApi } from '@/api/session'
import { chatApi } from '@/api/chat'
import { configApi } from '@/api/config'
import { renderMarkdown, formatTime } from '@/utils/markdown'
import { getToolConfig, formatToolArgs, formatToolResult } from '@/utils/toolDisplay'
import LobsterIcon from '@/assets/lobster.svg'

// localStorage key for saving current session
const SESSION_STORAGE_KEY = 'helloclaw.lastSessionId'

// 图片预览相关
const previewImageVisible = ref(false)
const previewImageUrl = ref('')

// 助手名字（从后端获取）
const assistantName = ref('HelloClaw')

// 消息段类型
interface TextSegment {
  type: 'text'
  id: number
  content: string
}

interface ToolSegment {
  type: 'tool'
  id: number
  tool: string
  args: Record<string, unknown>
  result?: string
  status: 'running' | 'done' | 'error'
}

type MessageSegment = TextSegment | ToolSegment

interface Message {
  id: number
  role: 'user' | 'assistant'
  content: string  // 用于从历史加载的消息
  timestamp: Date
  segments?: MessageSegment[]  // 用于流式消息的分段
}

interface MessageGroup {
  role: 'user' | 'assistant'
  messages: Message[]
}

const router = useRouter()
const route = useRoute()
const inputMessage = ref('')
const messages = ref<Message[]>([])
const loading = ref(false)
const currentSessionId = ref<string | null>(null)
const messagesContainer = ref<HTMLElement | null>(null)
const abortController = ref<AbortController | null>(null)
const initializing = ref(true)
const collapsedTools = ref<Set<number>>(new Set())
// 默认所有工具都是展开的（用于新建的工具）
const expandedTools = ref<Set<number>>(new Set())

const quickPrompts = [
  { text: '帮我查一下最近10天的邮件内容', color: '#0047FF', tint: '#E6EEFF' },
  { text: '帮我分析求职进度', color: '#FF5C1A', tint: '#FFEDE3' },
]

// 消息分组（Slack 风格）
const messageGroups = computed<MessageGroup[]>(() => {
  const groups: MessageGroup[] = []

  for (const msg of messages.value) {
    const lastGroup = groups[groups.length - 1]

    if (lastGroup && lastGroup.role === msg.role) {
      lastGroup.messages.push(msg)
    } else {
      groups.push({
        role: msg.role,
        messages: [msg]
      })
    }
  }

  return groups
})

// 是否应该显示加载指示器（底部的独立指示器）
// 只有当助手消息组完全没有可见内容时才显示
const shouldShowLoadingIndicator = computed(() => {
  if (messages.value.length === 0) {
    return true
  }

  const lastMsg = messages.value[messages.value.length - 1]
  if (lastMsg?.role !== 'assistant') {
    return true
  }

  // 只有当完全没有可见内容时才显示底部指示器
  // 如果有工具卡片等可见内容，等待状态会在消息组内部显示
  return !hasVisibleContent(lastMsg)
})

// 检查消息组是否有可见内容
const hasGroupVisibleContent = (group: MessageGroup): boolean => {
  for (const msg of group.messages) {
    if (hasVisibleContent(msg)) {
      return true
    }
  }
  return false
}

// 检查消息组是否有正在执行或已完成的工具（但还没有文本回复）
const hasGroupToolWithoutText = (group: MessageGroup): boolean => {
  if (group.role !== 'assistant') return false
  let hasTool = false
  let hasText = false
  for (const msg of group.messages) {
    if (!msg.segments) continue
    for (const segment of msg.segments) {
      if (segment.type === 'tool' && !getToolConfig(segment.tool).hidden) {
        hasTool = true
      }
      if (segment.type === 'text' && segment.content && segment.content.trim()) {
        hasText = true
      }
    }
  }
  return hasTool && !hasText
}

// 保存当前会话 ID 到 localStorage
const saveCurrentSession = (sessionId: string) => {
  localStorage.setItem(SESSION_STORAGE_KEY, sessionId)
}

// 从 localStorage 读取上次会话 ID
const getLastSession = (): string | null => {
  return localStorage.getItem(SESSION_STORAGE_KEY)
}

// 加载会话历史（按照 OpenAI 标准格式解析）
const loadSessionHistory = async (sessionId: string) => {
  try {
    const res = await sessionApi.getHistory(sessionId)
    const rawMessages = res.messages

    // 用于存储工具调用结果（tool_call_id -> result）
    const toolResults: Map<string, string> = new Map()

    // 第一遍：收集所有 tool 消息的结果
    for (const msg of rawMessages) {
      if (msg.role === 'tool' && msg.tool_call_id && msg.content) {
        toolResults.set(msg.tool_call_id, msg.content)
      }
    }

    // 第二遍：构建显示消息
    const displayMessages: Message[] = []
    let pendingAssistant: Message | null = null

    for (let i = 0; i < rawMessages.length; i++) {
      const msg = rawMessages[i]!

      if (msg.role === 'user') {
        // 如果有待处理的 assistant 消息，先添加
        if (pendingAssistant) {
          displayMessages.push(pendingAssistant)
          pendingAssistant = null
        }
        // 添加 user 消息
        displayMessages.push({
          id: Date.now() + i,
          role: 'user',
          content: msg.content || '',
          timestamp: new Date()
        })
      }
      else if (msg.role === 'assistant') {
        if (msg.tool_calls && msg.tool_calls.length > 0) {
          // 包含工具调用的 assistant 消息
          const segments: MessageSegment[] = []

          // 添加工具调用段
          msg.tool_calls.forEach((tc, tcIndex) => {
            const result = toolResults.get(tc.id)
            segments.push({
              type: 'tool',
              id: Date.now() + i * 1000 + tcIndex,
              tool: tc.function.name,
              args: JSON.parse(tc.function.arguments || '{}'),
              result: result,
              status: result?.startsWith('❌') ? 'error' : 'done'
            })
          })

          // 检查下一个消息是否是最终的 assistant 回答（没有 tool_calls）
          const nextMsg = rawMessages[i + 1]
          if (nextMsg && nextMsg.role === 'assistant' && !nextMsg.tool_calls && nextMsg.content) {
            // 有最终回答，添加文本段
            segments.push({
              type: 'text',
              id: Date.now() + i * 1000 + 100,
              content: nextMsg.content
            })
            i++ // 跳过下一个消息
          }

          pendingAssistant = {
            id: Date.now() + i,
            role: 'assistant',
            content: '',
            timestamp: new Date(),
            segments
          }
        } else if (msg.content) {
          // 普通的 assistant 文本消息
          if (pendingAssistant) {
            // 追加到待处理的 assistant 消息
            if (!pendingAssistant.segments) {
              pendingAssistant.segments = []
            }
            pendingAssistant.segments.push({
              type: 'text',
              id: Date.now() + i,
              content: msg.content
            })
          } else {
            // 新的 assistant 消息
            displayMessages.push({
              id: Date.now() + i,
              role: 'assistant',
              content: msg.content,
              timestamp: new Date()
            })
          }
        }
      }
      // tool 消息在第一遍已经处理，跳过
    }

    // 添加最后的待处理消息
    if (pendingAssistant) {
      displayMessages.push(pendingAssistant)
    }

    messages.value = displayMessages
    await scrollToBottom()
  } catch (error) {
    // 会话不存在或加载失败，清空消息
    messages.value = []
  }
}

// 初始化会话
const initSession = async () => {
  // 获取助手名字
  try {
    const agentInfo = await configApi.getAgentInfo()
    if (agentInfo.name) {
      assistantName.value = agentInfo.name
    }
  } catch (error) {
    // 获取失败时使用默认名字
    console.warn('获取助手名字失败:', error)
  }

  const urlSession = route.query.session as string | undefined

  if (urlSession) {
    // URL 中有 session 参数，使用它
    currentSessionId.value = urlSession
    saveCurrentSession(urlSession)
    await loadSessionHistory(urlSession)
    initializing.value = false
  } else {
    // URL 中没有 session 参数，尝试从 localStorage 读取
    const lastSession = getLastSession()
    if (lastSession) {
      // 有上次会话，设置 session 并加载历史，然后更新 URL
      currentSessionId.value = lastSession
      saveCurrentSession(lastSession)
      await loadSessionHistory(lastSession)
      // 使用 replace 更新 URL（不触发导航）
      window.history.replaceState({}, '', `/?session=${lastSession}`)
      initializing.value = false
    } else {
      // 没有上次会话，创建新会话
      try {
        const res = await sessionApi.create()
        saveCurrentSession(res.session_id)
        currentSessionId.value = res.session_id
        // 使用 replace 更新 URL（不触发导航）
        window.history.replaceState({}, '', `/?session=${res.session_id}`)
        initializing.value = false
      } catch (error) {
        message.error('创建会话失败')
        initializing.value = false
      }
    }
  }
}

// 监听 session 参数变化（处理从其他地方跳转过来的情况）
watch(
  () => route.query.session,
  async (newSession, oldSession) => {
    // 如果正在初始化，跳过
    if (initializing.value) return

    // 如果正在生成消息，跳过（防止切换页面时丢失正在生成的内容）
    if (loading.value) return

    // 如果 session 没有实际变化，跳过
    if (newSession === oldSession) return

    const sessionId = (newSession as string) || null

    // 如果新 session 为空，不做处理（应该由 initSession 处理）
    if (!sessionId) return

    // 切换到新会话
    currentSessionId.value = sessionId
    saveCurrentSession(sessionId)
    inputMessage.value = ''
    await loadSessionHistory(sessionId)
  }
)

// 监听 refresh 参数变化（处理从配置页面初始化后跳转的情况）
watch(
  () => route.query.refresh,
  async (newRefresh) => {
    if (newRefresh) {
      // 重新获取助手名字
      try {
        const agentInfo = await configApi.getAgentInfo()
        if (agentInfo.name) {
          assistantName.value = agentInfo.name
        }
      } catch (error) {
        console.warn('获取助手名字失败:', error)
      }

      // 清除 URL 中的 refresh 参数
      const currentQuery = { ...route.query }
      delete currentQuery.refresh
      router.replace({ query: currentQuery })
    }
  }
)

// 组件挂载时初始化会话
onMounted(async () => {
  await initSession()

  // 为消息容器添加图片点击事件监听
  if (messagesContainer.value) {
    messagesContainer.value.addEventListener('click', handleImageClick)
  }
})

// 处理图片点击事件（事件委托）
const handleImageClick = (event: MouseEvent) => {
  const target = event.target as HTMLElement
  if (target.tagName === 'IMG' && target instanceof HTMLImageElement) {
    // 检查是否是消息中的图片（排除头像等）
    if (target.closest('.message-text')) {
      previewImageUrl.value = target.src
      previewImageVisible.value = true
    }
  }
}

// 滚动到底部
const scrollToBottom = async () => {
  await nextTick()
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

// 切换工具折叠状态
const toggleToolCollapse = (toolId: number) => {
  if (expandedTools.value.has(toolId)) {
    expandedTools.value.delete(toolId)
  } else {
    expandedTools.value.add(toolId)
  }
}

// 检查工具是否展开（默认折叠，只有点击后才展开）
const isToolExpanded = (toolId: number): boolean => {
  return expandedTools.value.has(toolId)
}

// 检查消息是否有可见内容
const hasVisibleContent = (msg: Message): boolean => {
  if (!msg.segments || msg.segments.length === 0) {
    // 没有分段，检查普通内容
    return !!msg.content
  }

  // 有分段，检查是否有可见的段
  for (const segment of msg.segments) {
    if (segment.type === 'text' && segment.content) {
      return true
    }
    if (segment.type === 'tool' && !getToolConfig(segment.tool).hidden) {
      return true
    }
  }
  return false
}

// 检查消息是否有文本内容（用于决定是否显示加载指示器）
const hasTextContent = (msg: Message): boolean => {
  if (!msg.segments || msg.segments.length === 0) {
    return !!msg.content
  }
  // 只检查文本段
  for (const segment of msg.segments) {
    if (segment.type === 'text' && segment.content) {
      return true
    }
  }
  return false
}

// 检查消息是否有可见的工具调用（用于决定是否显示工具卡片而非加载指示器）
const hasVisibleTools = (msg: Message): boolean => {
  if (!msg.segments) return false
  for (const segment of msg.segments) {
    if (segment.type === 'tool' && !getToolConfig(segment.tool).hidden) {
      return true
    }
  }
  return false
}

// 停止生成
const stopGeneration = () => {
  if (abortController.value) {
    abortController.value.abort()
    abortController.value = null
    loading.value = false
  }
}

// 更新消息段（触发 Vue 响应性）
const updateMessageSegments = (msgIndex: number, segments: MessageSegment[]) => {
  if (msgIndex >= 0 && msgIndex < messages.value.length) {
    const existingMsg = messages.value[msgIndex]!
    messages.value[msgIndex] = {
      id: existingMsg.id,
      role: existingMsg.role,
      content: existingMsg.content,
      timestamp: existingMsg.timestamp,
      segments: [...segments]
    }
  }
}

const sendMessage = async () => {
  if (!inputMessage.value.trim()) return

  const userMessage = inputMessage.value
  const userMsg: Message = {
    id: Date.now(),
    role: 'user',
    content: userMessage,
    timestamp: new Date()
  }

  messages.value.push(userMsg)
  inputMessage.value = ''
  loading.value = true

  // 创建 AbortController
  abortController.value = new AbortController()

  // 助手消息的索引和段
  let assistantMsgIndex = -1
  let currentSegments: MessageSegment[] = []
  let currentTextSegmentId = -1

  await scrollToBottom()

  try {
    await chatApi.sendMessageStream(
      userMessage,
      currentSessionId.value || undefined,
      (event) => {
        if (event.type === 'session') {
          // 收到会话 ID
          if (event.session_id) {
            currentSessionId.value = event.session_id
            saveCurrentSession(event.session_id)
          }
        } else if (event.type === 'step_start') {
          // 新步骤开始 - 创建新的文本段
          currentTextSegmentId = Date.now()
          currentSegments.push({
            type: 'text',
            id: currentTextSegmentId,
            content: ''
          })

          // 如果还没有助手消息，创建一个
          if (assistantMsgIndex === -1) {
            assistantMsgIndex = messages.value.length
            messages.value.push({
              id: Date.now(),
              role: 'assistant',
              content: '',
              timestamp: new Date(),
              segments: currentSegments
            })
          } else {
            updateMessageSegments(assistantMsgIndex, currentSegments)
          }
          scrollToBottom()
        } else if (event.type === 'chunk' && event.content) {
          // 更新当前文本段
          const textSegment = currentSegments.find(s => s.type === 'text' && s.id === currentTextSegmentId) as TextSegment | undefined
          if (textSegment) {
            textSegment.content += event.content
            updateMessageSegments(assistantMsgIndex, currentSegments)
          }
          scrollToBottom()
        } else if (event.type === 'tool_start') {
          // 工具调用开始 - 创建工具段
          currentSegments.push({
            type: 'tool',
            id: Date.now(),
            tool: event.tool || '',
            args: event.args || {},
            status: 'running'
          })

          // 如果还没有助手消息，创建一个
          if (assistantMsgIndex === -1) {
            assistantMsgIndex = messages.value.length
            messages.value.push({
              id: Date.now(),
              role: 'assistant',
              content: '',
              timestamp: new Date(),
              segments: currentSegments
            })
          } else {
            updateMessageSegments(assistantMsgIndex, currentSegments)
          }
          scrollToBottom()
        } else if (event.type === 'tool_finish') {
          // 工具调用结束 - 查找或创建工具段
          const lastToolSegment = [...currentSegments].reverse().find(s => s.type === 'tool' && s.status === 'running') as ToolSegment | undefined
          if (lastToolSegment) {
            // 更新现有的运行中工具
            lastToolSegment.result = event.result
            lastToolSegment.status = 'done'
          } else {
            // 没有对应的 tool_start，直接添加为完成的工具
            currentSegments.push({
              type: 'tool',
              id: Date.now(),
              tool: event.tool || '',
              args: {},
              result: event.result,
              status: 'done'
            })
          }
          updateMessageSegments(assistantMsgIndex, currentSegments)
          scrollToBottom()
        } else if (event.type === 'done') {
          // 完成
          if (event.session_id) {
            currentSessionId.value = event.session_id
          }
          // 对话结束后重新获取助手名字（可能在对话中更新了 IDENTITY.md）
          configApi.getAgentInfo().then(agentInfo => {
            if (agentInfo.name) {
              assistantName.value = agentInfo.name
            }
          }).catch(() => {
            // 忽略错误，保持当前名字
          })
        } else if (event.type === 'error') {
          message.error(event.error || '发送消息失败')
        } else if (event.type === 'max_iterations') {
          // 达到最大迭代次数，显示警告
          message.warning(event.message || `已达到最大工具调用次数（${event.max_iterations}次）`)
        }
      },
      abortController.value.signal
    )

    await scrollToBottom()
  } catch (error: unknown) {
    // 如果是用户主动取消，不显示错误
    if (error instanceof Error && error.name === 'AbortError') {
      console.log('用户取消了请求')
      // 取消时保留已生成的内容
    } else {
      console.error('发送消息失败:', error)
      message.error('发送消息失败')
      // 移除用户消息
      messages.value.pop()
    }
  } finally {
    loading.value = false
    abortController.value = null
  }
}

const createNewSession = async () => {
  try {
    const res = await sessionApi.create()
    saveCurrentSession(res.session_id)
    router.push({ name: 'chat', query: { session: res.session_id } })
  } catch (error) {
    message.error('新建会话失败')
  }
}
</script>

<template>
  <div class="chat-view">
    <!-- 消息区域 -->
    <div class="chat-messages" ref="messagesContainer">
      <!-- 初始化加载状态 -->
      <div v-if="initializing" class="empty-state">
        <img :src="LobsterIcon" alt="HelloClaw" class="empty-icon loading" />
        <p class="empty-hint">加载中...</p>
      </div>
      <template v-else-if="messages.length > 0">
        <div
          v-for="(group, groupIndex) in messageGroups"
          :key="groupIndex"
          v-show="group.role !== 'assistant' || hasGroupVisibleContent(group)"
          :class="['message-group', group.role]"
        >
          <!-- 头像 -->
          <div class="group-avatar">
            <img v-if="group.role === 'assistant'" :src="LobsterIcon" alt="HelloClaw" />
            <div v-else class="user-avatar">你</div>
          </div>

          <!-- 消息内容 -->
          <div class="group-content">
            <!-- 遍历每条消息 -->
            <template v-for="(msg, msgIndex) in group.messages" :key="msg.id">
              <!-- 如果有分段，按分段显示 -->
              <template v-if="msg.segments && msg.segments.length > 0">
                <template v-for="segment in msg.segments" :key="segment.id">
                  <!-- 文本段 -->
                  <div v-if="segment.type === 'text' && segment.content" class="message-bubble">
                    <div
                      class="message-text"
                      v-html="renderMarkdown(segment.content)"
                    ></div>
                  </div>
                  <!-- 工具调用段 - 只显示非隐藏的工具 -->
                  <div
                    v-if="segment.type === 'tool' && !getToolConfig(segment.tool).hidden"
                    :class="['tool-card', segment.status]"
                  >
                    <div
                      class="tool-header"
                      @click="segment.status !== 'running' && toggleToolCollapse(segment.id)"
                    >
                      <span class="tool-icon">{{ getToolConfig(segment.tool).icon }}</span>
                      <span class="tool-name">
                        <template v-if="!isToolExpanded(segment.id)">使用了</template>
                        {{ getToolConfig(segment.tool).name }}
                      </span>
                      <Tag v-if="segment.status === 'running'" color="processing" class="tool-tag">
                        <LoadingOutlined /> 执行中
                      </Tag>
                      <Tag v-else-if="segment.status === 'done'" color="success" class="tool-tag">完成</Tag>
                      <Tag v-else-if="segment.status === 'error'" color="error" class="tool-tag">失败</Tag>
                      <span
                        v-if="segment.status !== 'running'"
                        class="collapse-indicator"
                      >
                        {{ isToolExpanded(segment.id) ? '▼' : '▶' }}
                      </span>
                    </div>
                    <!-- 展开后显示入参和结果 -->
                    <div v-if="isToolExpanded(segment.id)" class="tool-details">
                      <!-- 入参 -->
                      <div v-if="segment.args && Object.keys(segment.args).length > 0" class="tool-args">
                        <div class="tool-detail-label">入参</div>
                        <pre class="tool-detail-content">{{ formatToolArgs(segment.args) }}</pre>
                      </div>
                      <!-- 结果 -->
                      <div v-if="segment.result" class="tool-result-wrapper">
                        <div class="tool-detail-label">结果</div>
                        <pre class="tool-detail-content">{{ formatToolResult(segment.result) }}</pre>
                      </div>
                    </div>
                  </div>
                </template>
              </template>
              <!-- 如果没有分段，显示普通内容（历史消息） -->
              <div v-else-if="msg.content" class="message-bubble">
                <div
                  class="message-text"
                  v-html="renderMarkdown(msg.content)"
                ></div>
              </div>
            </template>

            <!-- 消息组内部的等待状态（有工具调用但没有文本回复时） -->
            <div v-if="loading && hasGroupToolWithoutText(group)" class="message-bubble">
              <div class="loading-dots">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>

            <!-- 组底部：名称和时间 -->
            <div class="group-footer">
              <span class="group-name">{{ group.role === 'user' ? '你' : assistantName }}</span>
              <span class="group-time">{{ formatTime(group.messages[group.messages.length - 1]?.timestamp || new Date()) }}</span>
              <!-- 状态图标（仅助手） -->
              <span v-if="group.role === 'assistant' && loading && groupIndex === messageGroups.length - 1" class="msg-status speaking">…</span>
              <span v-else-if="group.role === 'assistant'" class="msg-status done">✓</span>
            </div>
          </div>
        </div>
      </template>

      <!-- 空状态 -->
      <div v-else class="empty-state">
        <img :src="LobsterIcon" alt="HelloClaw" class="empty-icon" />
        <p class="empty-hint">发送消息开始对话</p>
      </div>

      <!-- 加载指示器（助手消息组样式）- 等待响应时显示 -->
      <div v-if="loading && shouldShowLoadingIndicator" class="message-group assistant loading-group">
        <div class="group-avatar">
          <img :src="LobsterIcon" alt="HelloClaw" />
        </div>
        <div class="group-content">
          <div class="message-bubble">
            <div class="loading-dots">
              <span></span>
              <span></span>
              <span></span>
            </div>
            <div class="loading-hint">…</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 快捷提示 -->
    <div class="chat-quick-prompts">
      <div class="quick-prompts-inner">
        <button
          v-for="p in quickPrompts"
          :key="p.text"
          class="quick-prompt-btn"
          @click="() => { inputMessage = p.text }"
        >
          {{ p.text }}
        </button>
      </div>
    </div>

    <!-- 输入区域 -->
    <div class="chat-input-wrapper">
      <div class="chat-input">
        <!-- 输入框 -->
        <Input.TextArea
          v-model:value="inputMessage"
          placeholder="问我任何求职相关的问题…  Enter 发送 / Shift+Enter 换行"
          :auto-size="{ minRows: 1, maxRows: 4 }"
          @press-enter="(e: KeyboardEvent) => { if (!e.shiftKey) { e.preventDefault(); sendMessage() } }"
        />
        <!-- 按钮区域 -->
        <div class="input-actions">
          <!-- 新建会话按钮 -->
          <Button
            class="icon-btn"
            @click="createNewSession"
            title="新建会话"
          >
            <template #icon>
              <PlusOutlined />
            </template>
          </Button>
          <!-- 停止按钮（loading 时显示） -->
          <button
            v-if="loading"
            class="stop-btn"
            @click="stopGeneration"
            title="停止生成"
          >
            <div class="stop-icon"></div>
          </button>
          <!-- 发送按钮（有文字时显示） -->
          <button
            v-else-if="inputMessage.trim()"
            class="send-btn active"
            @click="sendMessage"
            title="发送消息"
          >
            <SendOutlined />
          </button>
        </div>
      </div>
    </div>

    <!-- 图片预览 Modal -->
    <Modal
      v-model:open="previewImageVisible"
      :footer="null"
      width="auto"
      centered
      class="image-preview-modal"
    >
      <img
        :src="previewImageUrl"
        class="preview-image"
        @click="previewImageVisible = false"
      />
    </Modal>
  </div>
</template>

<style scoped>
.chat-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
  box-sizing: border-box;
  background-color: #ffffff;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 32px 48px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  background: #ffffff;
  position: relative;
}

/* 消息组样式 */
.message-group {
  display: flex;
  gap: 16px;
  max-width: 72%;
}

.message-group.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.message-group.assistant {
  align-self: flex-start;
}

/* 头像 */
.group-avatar {
  flex-shrink: 0;
  width: 36px;
  height: 36px;
  margin-top: 2px;
}

.group-avatar img {
  width: 36px;
  height: 36px;
  border-radius: 5px;
}

.user-avatar {
  width: 36px;
  height: 36px;
  border-radius: 5px;
  background: #0047FF;
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 消息组内容 */
.group-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

/* 消息气泡 */
.message-bubble {
  display: inline-block;
  max-width: 100%;
}

.message-text {
  padding: 16px 20px;
  background-color: #ffffff;
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 14px;
  border-top-left-radius: 4px;
  line-height: 1.65;
  word-wrap: break-word;
  font-size: 14px;
  color: #040404;
}

.message-group.user .message-text {
  background: #FFEDE3;
  color: #040404;
  border: none;
  border-radius: 14px;
  border-top-right-radius: 4px;
}

/* Markdown 样式 */
.message-text :deep(p) {
  margin: 0;
}

.message-text :deep(p + p) {
  margin-top: 8px;
}

.message-text :deep(code) {
  background-color: rgba(0, 0, 0, 0.05);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
  font-family: var(--font-family-mono);
}

.message-text :deep(pre) {
  background-color: #1e1e1e;
  color: #d4d4d4;
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 8px 0;
}

.message-text :deep(pre code) {
  background-color: transparent;
  padding: 0;
}

.message-text :deep(ul),
.message-text :deep(ol) {
  margin: 8px 0;
  padding-left: 24px;
}

.message-text :deep(blockquote) {
  border-left: 3px solid var(--color-primary);
  padding-left: 12px;
  margin: 8px 0;
  color: var(--color-text-secondary);
}

.message-text :deep(a) {
  color: var(--color-primary);
  text-decoration: none;
}

.message-text :deep(a:hover) {
  text-decoration: underline;
}

.message-text :deep(strong) {
  font-weight: 600;
  color: #040404;
}

/* 图片样式 */
.message-text :deep(img) {
  max-width: 100%;
  max-height: 400px;
  border-radius: 8px;
  margin: 8px 0;
  display: block;
  cursor: pointer;
  transition: transform 0.15s ease;
}

.message-text :deep(img:hover) {
  transform: scale(1.02);
}

.message-text :deep(p:has(> img:only-child)) {
  margin: 0;
}

/* 组底部 */
.group-footer {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-top: 4px;
  padding-left: 4px;
}

.group-name {
  font-size: 12px;
  font-weight: 600;
  color: #040404;
}

.group-time {
  font-size: 11px;
  color: #A3A3A3;
}

.msg-status {
  margin-left: auto;
  font-size: 14px;
  line-height: 1;
}

.msg-status.speaking {
  color: #A3A3A3;
  font-size: 16px;
  letter-spacing: 2px;
}

.msg-status.done {
  color: #00B86B;
}

/* 空状态 */
.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  position: absolute;
  inset: 0;
}

.empty-icon {
  width: 96px;
  height: 96px;
  opacity: 0.45;
}

.empty-icon.loading {
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 0.25;
    transform: scale(0.95);
  }
  50% {
    opacity: 0.5;
    transform: scale(1);
  }
}

.empty-hint {
  color: #A3A3A3;
  font-size: 14px;
}

/* 加载指示器 */
.loading-group .message-bubble {
  padding: 16px 20px;
  background: #ffffff;
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 14px;
  border-top-left-radius: 4px;
}

.loading-dots {
  display: flex;
  gap: 6px;
  align-items: center;
}

.loading-dots span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background-color: #FF5C1A;
  animation: loading-pulse 0.8s ease-in-out infinite;
}

.loading-dots span:nth-child(2) {
  animation-delay: 0.2s;
}

.loading-dots span:nth-child(3) {
  animation-delay: 0.4s;
}

.loading-hint {
  text-align: right;
  margin-top: 10px;
  font-size: 16px;
  color: #A3A3A3;
  letter-spacing: 2px;
}

@keyframes loading-pulse {
  0%, 100% {
    opacity: 0.35;
    transform: scale(0.75);
  }
  50% {
    opacity: 1;
    transform: scale(1);
  }
}

/* 快捷提示栏 */
.chat-quick-prompts {
  padding: 6px 48px 4px;
  border-top: 1px solid rgba(0, 0, 0, 0.1);
  flex-shrink: 0;
}

.quick-prompts-inner {
  display: flex;
  gap: 6px;
  overflow-x: auto;
  max-width: 1400px;
  width: 100%;
  margin: 0 auto;
}

.quick-prompt-btn {
  flex-shrink: 0;
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 500;
  border-radius: 100px;
  border: none;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.15s ease;
  font-family: var(--font-family-base);
}

.quick-prompt-btn:hover {
  transform: translateY(-1px);
}

.quick-prompt-btn:first-child {
   background: #E6EEFF;
   color: #0047FF;
 }
 
 .quick-prompt-btn:nth-child(2) {
   background: #FFEDE3;
   color: #FF5C1A;
 }

/* 输入区域 */
.chat-input-wrapper {
  padding: 4px 48px 24px;
  flex-shrink: 0;
}

.chat-input {
  display: flex;
  gap: 12px;
  align-items: center;
  max-width: 1400px;
  margin: 0 auto;
  padding: 10px;
  background: #ffffff;
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 10px;
}

.chat-input :deep(.ant-input) {
  flex: 1;
  border: none !important;
  border-radius: 0 !important;
  padding: 0;
  resize: none;
  background: transparent !important;
  font-size: 14px;
  color: #040404;
  line-height: 1.5;
  box-shadow: none !important;
  font-family: var(--font-family-base);
}

.chat-input :deep(.ant-input:focus) {
  box-shadow: none !important;
}

.chat-input :deep(.ant-input::placeholder) {
  color: #A3A3A3;
}

/* 按钮区域 */
.input-actions {
  flex-shrink: 0;
  display: flex;
  gap: 8px;
  align-items: center;
}

/* 新建会话按钮 */
.input-actions .icon-btn {
  width: 32px;
  height: 32px;
  padding: 0;
  border-radius: 5px;
  border: 1px solid rgba(0, 0, 0, 0.1);
  background: #f8fafc;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #A3A3A3;
  transition: all 0.15s ease;
}

.input-actions .icon-btn:hover {
  background: #FFEDE3;
  border-color: #FF5C1A;
  color: #FF5C1A;
}

/* 发送按钮 */
.input-actions .send-btn {
  width: 32px;
  height: 32px;
  padding: 0;
  border-radius: 5px;
  border: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.15s ease;
  color: #A3A3A3;
  background: #E5E5E5;
}

.input-actions .send-btn:disabled {
  cursor: not-allowed;
  background: #E5E5E5;
  color: #A3A3A3;
}

.input-actions .send-btn.active {
  background: #FF5C1A;
  color: #ffffff;
}

.input-actions .send-btn.active:hover {
  background: #E84D0A;
  transform: translateY(-1px);
}

/* 停止按钮 */
.input-actions .stop-btn {
  width: 32px;
  height: 32px;
  padding: 0;
  border: none;
  border-radius: 5px;
  background: #FF5C1A;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.15s ease;
}

.input-actions .stop-btn:hover {
  background: #E84D0A;
  transform: translateY(-1px);
}

.stop-icon {
  width: 14px;
  height: 14px;
  background: #fff;
  border-radius: 4px;
}

/* 工具调用卡片 */
.tool-cards {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 8px;
}

.tool-card {
  background: #ffffff;
  border: 1px solid rgba(0, 0, 0, 0.05);
  border-radius: 8px;
  padding: 8px 12px;
  font-size: 12px;
  transition: all 0.15s ease;
}

.tool-card:hover {
  border-color: rgba(0, 0, 0, 0.1);
}

.tool-card.running {
  border-color: #FF5C1A;
  background: #FFEDE3;
}

.tool-card.running .tool-icon,
.tool-card.running .tool-name {
  color: #FF5C1A;
}

.tool-card.done {
  border-color: rgba(0, 0, 0, 0.05);
  background: #ffffff;
}

.tool-card.error {
  border-color: #ef4444;
  background: #fee2e2;
}

.tool-card.error .tool-icon,
.tool-card.error .tool-name {
  color: #ef4444;
}

.tool-header {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  user-select: none;
}

.tool-header:hover {
  opacity: 0.8;
}

.tool-icon {
  font-size: 14px;
  line-height: 1;
}

.tool-name {
  font-weight: 500;
  color: #040404;
  flex: 1;
}

.tool-tag {
  font-size: 11px;
  padding: 0 6px;
  line-height: 18px;
  border-radius: 4px;
}

.collapse-indicator {
  font-size: 10px;
  color: #A3A3A3;
  margin-left: auto;
}

.tool-details {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed rgba(0, 0, 0, 0.05);
}

.tool-args,
.tool-result-wrapper {
  margin-bottom: 8px;
}

.tool-result-wrapper:last-child {
  margin-bottom: 0;
}

.tool-detail-label {
  font-size: 11px;
  color: #A3A3A3;
  margin-bottom: 4px;
  font-weight: 500;
}

.tool-detail-content {
  margin: 0;
  padding: 8px;
  background: #f8fafc;
  border-radius: 4px;
  font-size: 12px;
  color: #040404;
  max-height: 150px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: var(--font-family-mono);
}

.step-info {
  color: #A3A3A3;
  font-size: 11px;
}

/* 图片预览 Modal */
.preview-image {
  max-width: 90vw;
  max-height: 90vh;
  border-radius: 8px;
  cursor: pointer;
}

.image-preview-modal :deep(.ant-modal-content) {
  background: transparent;
  padding: 0;
}

.image-preview-modal :deep(.ant-modal-body) {
  padding: 0;
}

/* 响应式 */
@media (max-width: 768px) {
  .chat-messages {
    padding: 16px;
    gap: 16px;
  }

  .message-group {
    max-width: 90%;
  }

  .chat-quick-prompts {
    padding: 4px 16px 2px;
  }

  .chat-input-wrapper {
    padding: 12px 16px 20px;
  }
}
</style>
