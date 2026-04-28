<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Card, List, Input, Button, message, Empty, Tag, Modal, Checkbox, Tabs } from 'ant-design-vue'
import { configApi, type ConfigFile } from '@/api/config'
import { skillApi, type SkillInfo, type SkillContent } from '@/api/skill'
import { SaveOutlined, FileTextOutlined, ReloadOutlined, ToolOutlined, PlusOutlined, DeleteOutlined } from '@ant-design/icons-vue'

const router = useRouter()

// 配置文件相关
const configs = ref<string[]>([])
const selectedConfig = ref<ConfigFile | null>(null)
const editingContent = ref('')
const loading = ref(false)
const saving = ref(false)
const resetting = ref(false)
const showResetModal = ref(false)
const resetOptions = ref({
  reset_sessions: true,
  reset_memory: true,
  reset_global_config: false,
})

// Skills 相关
const skills = ref<SkillInfo[]>([])
const selectedSkill = ref<SkillContent | null>(null)
const skillEditingContent = ref('')
const skillsLoading = ref(false)
const skillSaving = ref(false)

// 创建 Skill 相关
const showCreateSkillModal = ref(false)
const newSkillName = ref('')
const newSkillDescription = ref('')
const skillCreating = ref(false)

// 删除 Skill 相关
const showDeleteSkillModal = ref(false)
const skillToDelete = ref<SkillInfo | null>(null)
const skillDeleting = ref(false)

// 当前激活的标签页
const activeTab = ref('configs')

const configDescriptions: Record<string, string> = {
  CONFIG: '全局配置',
  IDENTITY: '身份定义',
  USER: '用户信息',
  SOUL: '人格模板',
  MEMORY: '长期记忆',
  AGENTS: '工作空间规则',
  HEARTBEAT: '心跳任务',
  BOOTSTRAP: '初始化引导',
}

// 获取配置文件的后缀
const getConfigExtension = (name: string): string => {
  return name === 'CONFIG' ? '.json' : '.md'
}

const loadConfigs = async () => {
  loading.value = true
  try {
    const res = await configApi.list()
    configs.value = res.configs
  } catch (error) {
    message.error('加载配置列表失败')
  } finally {
    loading.value = false
  }
}

const loadSkills = async () => {
  skillsLoading.value = true
  try {
    const res = await skillApi.list()
    skills.value = res.skills
  } catch (error) {
    message.error('加载 Skills 列表失败')
  } finally {
    skillsLoading.value = false
  }
}

const selectConfig = async (name: string) => {
  try {
    const res = await configApi.get(name)
    selectedConfig.value = res
    editingContent.value = res.content
  } catch (error) {
    message.error('加载配置失败')
  }
}

const selectSkill = async (skillName: string) => {
  try {
    const res = await skillApi.get(skillName)
    selectedSkill.value = res
    skillEditingContent.value = res.content
  } catch (error) {
    message.error('加载 Skill 失败')
  }
}

const saveConfig = async () => {
  if (!selectedConfig.value) return

  saving.value = true
  try {
    await configApi.update(selectedConfig.value.name, editingContent.value)
    message.success('保存成功')
  } catch (error: any) {
    // 透传后端错误信息
    const errorMsg = error?.response?.data?.detail || error?.message || '保存失败'
    message.error(errorMsg)
  } finally {
    saving.value = false
  }
}

const saveSkill = async () => {
  if (!selectedSkill.value) return

  skillSaving.value = true
  try {
    const res = await skillApi.update(selectedSkill.value.name, skillEditingContent.value)
    message.success(res.message)
    // 重新加载 Skills 列表以获取更新后的信息
    await loadSkills()
  } catch (error: any) {
    const errorMsg = error?.response?.data?.detail || error?.message || '保存失败'
    message.error(errorMsg)
  } finally {
    skillSaving.value = false
  }
}

const confirmReset = () => {
  // 重置选项为默认值
  resetOptions.value = {
    reset_sessions: true,
    reset_memory: true,
    reset_global_config: false,
  }
  showResetModal.value = true
}

const handleReset = async () => {
  resetting.value = true
  try {
    const res = await configApi.reset(resetOptions.value)
    message.success(res.message)
    showResetModal.value = false
    selectedConfig.value = null
    editingContent.value = ''

    // 如果清除了会话历史，也要清除 localStorage 中的上次会话 ID
    if (resetOptions.value.reset_sessions) {
      localStorage.removeItem('helloclaw.lastSessionId')
    }

    await loadConfigs()

    // 导航到聊天页面并传递刷新参数，让 ChatView 重新获取 agent 信息
    router.push({ name: 'chat', query: { refresh: Date.now().toString() } })
  } catch (error) {
    message.error('重置失败')
  } finally {
    resetting.value = false
  }
}

const openCreateSkillModal = () => {
  newSkillName.value = ''
  newSkillDescription.value = ''
  showCreateSkillModal.value = true
}

const handleCreateSkill = async () => {
  const name = newSkillName.value.trim()
  if (!name) {
    message.error('Skill 名称不能为空')
    return
  }

  skillCreating.value = true
  try {
    const res = await skillApi.create(name, newSkillDescription.value)
    message.success(res.message)
    showCreateSkillModal.value = false
    await loadSkills()
    // 自动选中新创建的 Skill
    await selectSkill(name)
  } catch (error: any) {
    const errorMsg = error?.response?.data?.detail || error?.message || '创建失败'
    message.error(errorMsg)
  } finally {
    skillCreating.value = false
  }
}

const confirmDeleteSkill = (skill: SkillInfo, event: MouseEvent) => {
  event.stopPropagation() // 阻止触发选择事件
  skillToDelete.value = skill
  showDeleteSkillModal.value = true
}

const handleDeleteSkill = async () => {
  if (!skillToDelete.value) return

  skillDeleting.value = true
  try {
    const res = await skillApi.delete(skillToDelete.value.name)
    message.success(res.message)
    showDeleteSkillModal.value = false
    // 如果删除的是当前选中的 Skill，清除选中状态
    if (selectedSkill.value?.name === skillToDelete.value.name) {
      selectedSkill.value = null
      skillEditingContent.value = ''
    }
    await loadSkills()
  } catch (error: any) {
    const errorMsg = error?.response?.data?.detail || error?.message || '删除失败'
    message.error(errorMsg)
  } finally {
    skillDeleting.value = false
    skillToDelete.value = null
  }
}

onMounted(() => {
  loadConfigs()
  loadSkills()
})
</script>

<template>
  <div class="config-view">
    <div class="config-header">
      <h1>配置管理</h1>
      <p>管理 Agent 的配置文件、身份信息和 Skills</p>
    </div>

    <Tabs v-model:activeKey="activeTab" class="config-tabs">
      <Tabs.TabPane key="configs" tab="配置文件">
        <div class="config-content">
          <!-- 配置列表 -->
          <div class="config-list">
            <Card :loading="loading" class="list-card">
              <template #title>
                <FileTextOutlined /> 配置文件
              </template>
              <template #extra>
                <button
                  class="reset-btn"
                  @click="confirmReset"
                  title="重置为初始模板"
                >
                  <ReloadOutlined /> 初始化
                </button>
              </template>
              <List :data-source="configs" :locale="{ emptyText: '暂无配置文件' }">
                <template #renderItem="{ item }">
                  <List.Item
                    @click="selectConfig(item)"
                    :class="['config-item', { active: selectedConfig?.name === item }]"
                  >
                    <div class="config-item-content">
                      <span class="config-name">{{ item }}</span>
                      <Tag color="blue" v-if="configDescriptions[item]">
                        {{ configDescriptions[item] }}
                      </Tag>
                    </div>
                  </List.Item>
                </template>
              </List>
            </Card>
          </div>

          <!-- 编辑区域 -->
          <div class="config-editor">
            <Card v-if="selectedConfig" class="editor-card">
              <template #title>
                <span>{{ selectedConfig.name }}</span>
                <Tag color="green" style="margin-left: 8px">{{ getConfigExtension(selectedConfig.name) }}</Tag>
              </template>
              <template #extra>
                <Button
                  type="primary"
                  :loading="saving"
                  @click="saveConfig"
                >
                  <SaveOutlined /> 保存
                </Button>
              </template>
              <Input.TextArea
                v-model:value="editingContent"
                :auto-size="{ minRows: 18, maxRows: 30 }"
                class="editor-textarea"
              />
            </Card>

            <Card v-else class="empty-card">
              <Empty
                description="请从左侧选择一个配置文件"
                :image-style="{ height: '80px' }"
              />
            </Card>
          </div>
        </div>
      </Tabs.TabPane>

      <Tabs.TabPane key="skills" tab="Skills">
        <div class="config-content">
          <!-- Skills 列表 -->
          <div class="config-list">
            <Card :loading="skillsLoading" class="list-card">
              <template #title>
                <ToolOutlined /> Skills
              </template>
              <template #extra>
                <button
                  class="add-btn"
                  @click="openCreateSkillModal"
                  title="新建 Skill"
                >
                  <PlusOutlined />
                </button>
              </template>
              <List :data-source="skills" :locale="{ emptyText: '暂无 Skills' }">
                <template #renderItem="{ item }">
                  <List.Item
                    @click="selectSkill(item.name)"
                    :class="['config-item', { active: selectedSkill?.name === item.name }]"
                  >
                    <div class="config-item-content">
                      <div class="skill-item-header">
                        <span class="config-name">{{ item.name }}</span>
                        <button
                          class="delete-btn"
                          @click="(e: MouseEvent) => confirmDeleteSkill(item, e)"
                          title="删除 Skill"
                        >
                          <DeleteOutlined />
                        </button>
                      </div>
                      <Tag color="purple" v-if="item.has_scripts">
                        有脚本
                      </Tag>
                      <div class="skill-description">{{ item.description }}</div>
                    </div>
                  </List.Item>
                </template>
              </List>
            </Card>
          </div>

          <!-- Skills 编辑区域 -->
          <div class="config-editor">
            <Card v-if="selectedSkill" class="editor-card">
              <template #title>
                <span>{{ selectedSkill.name }}</span>
                <Tag color="purple" style="margin-left: 8px">SKILL.md</Tag>
              </template>
              <template #extra>
                <Button
                  type="primary"
                  :loading="skillSaving"
                  @click="saveSkill"
                >
                  <SaveOutlined /> 保存
                </Button>
              </template>
              <div class="skill-path-info">
                <span class="path-label">路径:</span>
                <span class="path-value">{{ selectedSkill.path }}</span>
              </div>
              <Input.TextArea
                v-model:value="skillEditingContent"
                :auto-size="{ minRows: 18, maxRows: 30 }"
                class="editor-textarea"
              />
            </Card>

            <Card v-else class="empty-card">
              <Empty
                description="请从左侧选择一个 Skill"
                :image-style="{ height: '80px' }"
              />
            </Card>
          </div>
        </div>
      </Tabs.TabPane>
    </Tabs>

    <!-- 重置确认弹窗 -->
    <Modal
      v-model:open="showResetModal"
      title="确认初始化"
      :confirm-loading="resetting"
      @ok="handleReset"
      okText="确认初始化"
      cancelText="取消"
      okType="danger"
    >
      <div class="reset-warning">
        <p style="color: #ff4d4f; font-weight: 500;">⚠️ 警告：此操作不可撤销！</p>
        <p>初始化将把所有配置文件恢复为默认模板，包括：</p>
        <ul>
          <li>AGENTS.md - 工作空间规则</li>
          <li>IDENTITY.md - 身份信息</li>
          <li>USER.md - 用户信息</li>
          <li>SOUL.md - 人格模板</li>
          <li>MEMORY.md - 期记忆</li>
          <li>HEARTBEAT.md - 心跳任务</li>
          <li>BOOTSTRAP.md - 初始化引导</li>
        </ul>

        <div class="reset-options">
          <p style="font-weight: 500; margin-bottom: 8px;">额外清除选项：</p>
          <Checkbox v-model:checked="resetOptions.reset_sessions">
            清除所有会话历史
          </Checkbox>
          <Checkbox v-model:checked="resetOptions.reset_memory">
            清除每日记忆文件
          </Checkbox>
          <Checkbox v-model:checked="resetOptions.reset_global_config">
            重置全局配置（LLM、Agent 设置等）
          </Checkbox>
        </div>

        <p style="margin-top: 16px;">您确定要继续吗？</p>
      </div>
    </Modal>

    <!-- 创建 Skill 弹窗 -->
    <Modal
      v-model:open="showCreateSkillModal"
      title="新建 Skill"
      :confirm-loading="skillCreating"
      @ok="handleCreateSkill"
      okText="创建"
      cancelText="取消"
    >
      <div class="create-skill-form">
        <div class="form-item">
          <label class="form-label">Skill 名称 <span class="required">*</span></label>
          <Input
            v-model:value="newSkillName"
            placeholder="例如: my-skill-name"
            :maxlength="50"
          />
          <div class="form-hint">只能包含字母、数字、下划线和横线</div>
        </div>
        <div class="form-item">
          <label class="form-label">描述</label>
          <Input.TextArea
            v-model:value="newSkillDescription"
            placeholder="简短描述这个 Skill 的用途"
            :auto-size="{ minRows: 2, maxRows: 4 }"
            :maxlength="200"
          />
        </div>
      </div>
    </Modal>

    <!-- 删除 Skill 弹窗 -->
    <Modal
      v-model:open="showDeleteSkillModal"
      title="确认删除"
      :confirm-loading="skillDeleting"
      @ok="handleDeleteSkill"
      okText="确认删除"
      cancelText="取消"
      okType="danger"
    >
      <div class="delete-warning">
        <p style="color: #ff4d4f; font-weight: 500;">⚠️ 警告：此操作不可撤销！</p>
        <p>即将删除 Skill <strong>{{ skillToDelete?.name }}</strong></p>
        <p style="color: #666;">该 Skill 的目录及所有文件将被永久删除。</p>
      </div>
    </Modal>
  </div>
</template>

<style scoped>
.config-view {
  min-height: 100%;
  width: 100%;
  display: flex;
  flex-direction: column;
  padding: 24px;
  box-sizing: border-box;
}

.config-header {
  flex-shrink: 0;
  margin-bottom: 24px;
}

.config-header h1 {
  margin: 0 0 8px;
  font-size: 24px;
  font-weight: 500;
}

.config-header p {
  margin: 0;
  color: #999;
}

.config-content {
  display: flex;
  gap: 24px;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.config-list {
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
}

.list-card :deep(.ant-card-body) {
  flex: 1;
  padding: 0;
  overflow-y: auto;
}

.config-item {
  cursor: pointer;
  padding: 12px 16px;
  transition: all 0.2s;
  border-bottom: 1px solid #f0f0f0;
}

.config-item:hover {
  background-color: #f5f5f5;
}

.config-item.active {
  background-color: #fff1f0;
  border-left: 3px solid #ff4d4f;
}

.config-item-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.config-name {
  font-weight: 500;
}

.config-editor {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.editor-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.editor-card :deep(.ant-card-head) {
  flex-shrink: 0;
}

.editor-card :deep(.ant-card-body) {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.editor-textarea {
  flex: 1;
  width: 100%;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 13px;
  line-height: 1.6;
  resize: none;
}

.empty-card {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 初始化按钮 - 纯红色背景 + 白色字体（可操作） */
.reset-btn {
  padding: 4px 12px;
  font-size: 13px;
  border: none;
  border-radius: 6px;
  background: #ff4d4f;
  color: #fff;
  cursor: pointer;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.reset-btn:hover {
  background: #ff7875;
}

.reset-warning {
  padding: 8px 0;
}

.reset-warning ul {
  margin: 12px 0;
  padding-left: 24px;
}

.reset-warning li {
  margin: 4px 0;
  color: #666;
}

.reset-options {
  margin-top: 16px;
  padding: 12px;
  background: #fafafa;
  border-radius: 6px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* Skills 相关样式 */
.skill-description {
  font-size: 12px;
  color: #666;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.skill-path-info {
  padding: 8px 12px;
  background: #f5f5f5;
  border-radius: 4px;
  margin-bottom: 12px;
  font-size: 12px;
}

.path-label {
  color: #666;
  margin-right: 8px;
}

.path-value {
  color: #333;
}

/* Skill 头部操作按钮组 */
.skill-header-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

/* 新建按钮 - 绿色 */
.add-btn {
  padding: 4px 10px;
  font-size: 13px;
  border: none;
  border-radius: 6px;
  background: #52c41a;
  color: #fff;
  cursor: pointer;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.add-btn:hover {
  background: #73d13d;
}

/* Skill 列表项头部 */
.skill-item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

/* 删除按钮 - 红色 */
.delete-btn {
  padding: 2px 6px;
  font-size: 12px;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: #ff4d4f;
  cursor: pointer;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
}

.delete-btn:hover {
  background: #ff4d4f;
  color: #fff;
}

/* Tabs 样式调整 */
.config-tabs {
  flex: 1;
  min-height: 0;
}

.config-tabs :deep(.ant-tabs-content) {
  height: 100%;
}

.config-tabs :deep(.ant-tabs-tabpane) {
  height: 100%;
}

/* 创建 Skill 表单样式 */
.create-skill-form {
  padding: 8px 0;
}

.form-item {
  margin-bottom: 16px;
}

.form-label {
  display: block;
  font-weight: 500;
  margin-bottom: 8px;
}

.required {
  color: #ff4d4f;
}

.form-hint {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
}

/* 删除警告样式 */
.delete-warning {
  padding: 8px 0;
}

.delete-warning p {
  margin: 8px 0;
}

.delete-warning strong {
  color: #722ed1;
}
</style>
