<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Card, List, Input, Button, message, Empty, Tag, Modal, Checkbox, Tabs } from 'ant-design-vue'
import { configApi, type ConfigFile } from '@/api/config'
import { skillApi, type SkillInfo, type SkillContent } from '@/api/skill'
import { SaveOutlined, FileTextOutlined, ReloadOutlined, ToolOutlined, PlusOutlined, DeleteOutlined } from '@ant-design/icons-vue'

const router = useRouter()

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

const skills = ref<SkillInfo[]>([])
const selectedSkill = ref<SkillContent | null>(null)
const skillEditingContent = ref('')
const skillsLoading = ref(false)
const skillSaving = ref(false)

const showCreateSkillModal = ref(false)
const newSkillName = ref('')
const newSkillDescription = ref('')
const skillCreating = ref(false)

const showDeleteSkillModal = ref(false)
const skillToDelete = ref<SkillInfo | null>(null)
const skillDeleting = ref(false)

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
    await loadSkills()
  } catch (error: any) {
    const errorMsg = error?.response?.data?.detail || error?.message || '保存失败'
    message.error(errorMsg)
  } finally {
    skillSaving.value = false
  }
}

const confirmReset = () => {
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
    if (resetOptions.value.reset_sessions) {
      localStorage.removeItem('helloclaw.lastSessionId')
    }
    await loadConfigs()
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
    await selectSkill(name)
  } catch (error: any) {
    const errorMsg = error?.response?.data?.detail || error?.message || '创建失败'
    message.error(errorMsg)
  } finally {
    skillCreating.value = false
  }
}

const confirmDeleteSkill = (skill: SkillInfo, event: MouseEvent) => {
  event.stopPropagation()
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
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">配置管理</h1>
        <p class="page-subtitle">管理 Agent 的配置文件、身份信息和 Skills</p>
      </div>
    </div>

    <Tabs v-model:activeKey="activeTab" class="config-tabs">
      <Tabs.TabPane key="configs" tab="配置文件">
        <div class="config-content">
          <div class="config-list">
            <Card :loading="loading" class="list-card" :bordered="false">
              <template #title>
                <div class="card-title-row">
                  <FileTextOutlined class="card-title-icon" />
                  <span>配置文件</span>
                </div>
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

          <div class="config-editor">
            <Card v-if="selectedConfig" class="editor-card" :bordered="false">
              <template #title>
                <div class="editor-title-row">
                  <span class="editor-name">{{ selectedConfig.name }}</span>
                  <Tag color="green">{{ getConfigExtension(selectedConfig.name) }}</Tag>
                </div>
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

            <Card v-else class="empty-card" :bordered="false">
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
          <div class="config-list">
            <Card :loading="skillsLoading" class="list-card" :bordered="false">
              <template #title>
                <div class="card-title-row">
                  <ToolOutlined class="card-title-icon" />
                  <span>Skills</span>
                </div>
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

          <div class="config-editor">
            <Card v-if="selectedSkill" class="editor-card" :bordered="false">
              <template #title>
                <div class="editor-title-row">
                  <span class="editor-name">{{ selectedSkill.name }}</span>
                  <Tag color="purple">SKILL.md</Tag>
                </div>
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

            <Card v-else class="empty-card" :bordered="false">
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
        <p class="reset-warning-title">⚠️ 警告：此操作不可撤销！</p>
        <p>初始化将把所有配置文件恢复为默认模板，包括：</p>
        <ul>
          <li>AGENTS.md - 工作空间规则</li>
          <li>IDENTITY.md - 身份信息</li>
          <li>USER.md - 用户信息</li>
          <li>SOUL.md - 人格模板</li>
          <li>MEMORY.md - 长期记忆</li>
          <li>HEARTBEAT.md - 心跳任务</li>
          <li>BOOTSTRAP.md - 初始化引导</li>
        </ul>

        <div class="reset-options">
          <p class="reset-options-title">额外清除选项：</p>
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

        <p class="reset-confirm-text">您确定要继续吗？</p>
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
        <p class="delete-warning-title">⚠️ 警告：此操作不可撤销！</p>
        <p>即将删除 Skill <strong>{{ skillToDelete?.name }}</strong></p>
        <p class="delete-warning-hint">该 Skill 的目录及所有文件将被永久删除。</p>
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

.config-item {
  cursor: pointer;
  padding: 12px 16px;
  transition: all 0.15s ease;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

.config-item:last-child {
  border-bottom: none;
}

.config-item:hover {
  background-color: #f8fafc;
}

.config-item.active {
  background-color: #FFEDE3;
  border-left: 3px solid #FF5C1A;
}

.config-item-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
  width: 100%;
}

.config-name {
  font-weight: 500;
  font-size: 12px;
  color: #040404;
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
  background: #ffffff;
  border: 1px solid rgba(0, 0, 0, 0.1) !important;
  border-radius: 14px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
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

.editor-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.editor-name {
  font-weight: 600;
  font-size: 14px;
  color: #040404;
}

.editor-textarea {
  flex: 1;
  width: 100%;
  font-family: var(--font-family-mono);
  font-size: 12px;
  line-height: 1.7;
  resize: none;
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

.reset-btn {
  padding: 4px 12px;
  font-size: 12px;
  border: none;
  border-radius: 5px;
  background: #ef4444;
  color: #fff;
  cursor: pointer;
  transition: all 0.15s ease;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-weight: 500;
}

.reset-btn:hover {
  background: #f87171;
  transform: translateY(-1px);
}

.reset-warning {
  padding: 8px 0;
}

.reset-warning-title,
.delete-warning-title {
  color: #ef4444;
  font-weight: 600;
  margin-bottom: 12px;
}

.reset-warning ul {
  margin: 12px 0;
  padding-left: 24px;
}

.reset-warning li {
  margin: 4px 0;
  color: #575757;
  font-size: 12px;
}

.reset-options {
  margin-top: 16px;
  padding: 12px;
  background: #f8fafc;
  border-radius: 5px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.reset-options-title,
.reset-confirm-text {
  font-weight: 500;
  color: #040404;
}

.reset-confirm-text {
  margin-top: 16px;
}

.skill-description {
  font-size: 12px;
  color: #A3A3A3;
  line-height: 1.5;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.skill-path-info {
  padding: 8px 12px;
  background: #f8fafc;
  border-radius: 4px;
  margin-bottom: 12px;
  font-size: 12px;
}

.path-label {
  color: #A3A3A3;
  margin-right: 8px;
}

.path-value {
  color: #040404;
}

.skill-item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.add-btn {
  padding: 4px 8px;
  font-size: 12px;
  border: none;
  border-radius: 5px;
  background: #10b981;
  color: #fff;
  cursor: pointer;
  transition: all 0.15s ease;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.add-btn:hover {
  background: #73d13d;
  transform: translateY(-1px);
}

.delete-btn {
  padding: 2px 6px;
  font-size: 12px;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: #ef4444;
  cursor: pointer;
  transition: all 0.15s ease;
  display: inline-flex;
  align-items: center;
}

.delete-btn:hover {
  background: #ef4444;
  color: #fff;
}

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
  color: #040404;
}

.required {
  color: #ef4444;
}

.form-hint {
  font-size: 10px;
  color: #A3A3A3;
  margin-top: 4px;
}

.delete-warning {
  padding: 8px 0;
}

.delete-warning p {
  margin: 8px 0;
}

.delete-warning strong {
  color: #FF5C1A;
}

.delete-warning-hint {
  color: #A3A3A3;
  font-size: 12px;
}

@media (max-width: 768px) {
  .config-view {
    padding: 16px;
  }

  .config-content {
    flex-direction: column;
    gap: 16px;
  }

  .config-list {
    width: 100%;
    max-height: 260px;
  }

  .page-title {
    font-size: 18px;
  }
}
</style>
