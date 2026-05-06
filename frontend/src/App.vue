<script setup lang="ts">
import { RouterLink, RouterView, useRoute } from 'vue-router'
import { ConfigProvider } from 'ant-design-vue'

const route = useRoute()

const customTheme = {
  token: {
    colorPrimary: '#FF5C1A',
    colorPrimaryHover: '#FF7A3D',
    colorPrimaryActive: '#E84D0A',
    colorPrimaryBg: '#FFEDE3',
    colorPrimaryBgHover: 'rgba(255, 92, 26, 0.14)',
    borderRadius: 5,
    fontFamily: "'Rethink Sans', -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif",
  },
}

const navItems = [
  { name: 'chat', to: '/', num: '01', label: '聊天' },
  { name: 'sessions', to: '/sessions', num: '02', label: '会话' },
  { name: 'memory', to: '/memory', num: '03', label: '记忆' },
  { name: 'job-hunting', to: '/job-hunting', num: '04', label: '求职' },
  { name: 'config', to: '/config', num: '05', label: '配置' },
]
</script>

<template>
  <ConfigProvider :theme="{ token: customTheme.token }">
    <div class="app-container">
      <aside class="sidebar">
        <div class="sidebar-brand">
          <div class="logo-area">
            <div class="logo-mark">
              <span class="logo-letter">H</span>
            </div>
            <div class="logo-text-group">
              <span class="logo-text">HelloClaw</span>
              <span class="logo-subtitle">JOB · TRACKER</span>
            </div>
          </div>
        </div>

        <nav class="sidebar-nav">
          <RouterLink
            v-for="item in navItems"
            :key="item.name"
            :to="item.to"
            class="nav-item"
            :class="{ active: route.name === item.name }"
          >
            <span class="nav-num" :class="{ 'num-active': route.name === item.name }">
              {{ item.num }}
            </span>
            <span class="nav-label">{{ item.label }}</span>
            <span v-if="route.name === item.name" class="nav-dot" />
          </RouterLink>
        </nav>
      </aside>

      <main class="main-content">
        <RouterView v-slot="{ Component }">
          <transition name="page-fade" mode="out-in">
            <keep-alive include="ChatView">
              <component :is="Component" />
            </keep-alive>
          </transition>
        </RouterView>
      </main>
    </div>
  </ConfigProvider>
</template>

<style scoped>
.app-container {
  display: flex;
  height: 100vh;
  overflow: hidden;
  background: #ffffff;
}

/* ===== 侧边栏 - 白色极简风格 ===== */
.sidebar {
  width: var(--sidebar-width);
  background: #ffffff;
  border-right: 1px solid var(--sidebar-border);
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  user-select: none;
}

/* ===== 品牌区域 ===== */
.sidebar-brand {
  padding: 24px 24px;
  border-bottom: 1px solid var(--sidebar-border);
  flex-shrink: 0;
}

.logo-area {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-mark {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--sidebar-accent);
  border-radius: 5px;
  flex-shrink: 0;
}

.logo-letter {
  color: #ffffff;
  font-weight: 700;
  font-size: 15px;
}

.logo-text-group {
  display: flex;
  flex-direction: column;
  line-height: 1;
}

.logo-text {
  font-family: var(--font-family-display);
  font-size: 20px;
  color: var(--sidebar-logo-color);
  letter-spacing: -0.01em;
}

.logo-subtitle {
  font-size: 10px;
  color: #575757;
  margin-top: 4px;
  letter-spacing: 0.12em;
}

/* ===== 导航菜单 ===== */
.sidebar-nav {
  flex: 1;
  padding: 16px 12px;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}

.nav-item {
  display: flex;
  align-items: baseline;
  gap: 16px;
  padding: 12px 12px;
  color: #575757;
  text-decoration: none;
  font-size: 14px;
  font-weight: 400;
  transition: color 0.15s ease;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

.nav-item:hover {
  color: #040404;
}

.nav-item.active {
  color: #040404;
  font-weight: 600;
}

.nav-num {
  font-family: var(--font-family-display);
  font-size: 13px;
  color: #A3A3A3;
  width: 20px;
  flex-shrink: 0;
}

.nav-num.num-active {
  color: var(--sidebar-accent);
}

.nav-label {
  flex: 1;
}

.nav-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--sidebar-accent);
  flex-shrink: 0;
}

/* ===== 主内容区 ===== */
.main-content {
  flex: 1;
  overflow: auto;
  height: 100vh;
  background: #ffffff;
}

/* ===== 页面切换动画 ===== */
.page-fade-enter-active,
.page-fade-leave-active {
  transition: opacity var(--transition-base), transform var(--transition-base);
}

.page-fade-enter-from {
  opacity: 0;
  transform: translateY(6px);
}

.page-fade-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

/* ===== 响应式 ===== */
@media (max-width: 768px) {
  .sidebar {
    width: 60px;
  }

  .nav-label,
  .logo-text-group,
  .nav-dot {
    display: none;
  }

  .sidebar-brand {
    padding: 16px 12px;
    display: flex;
    justify-content: center;
  }

  .sidebar-nav {
    padding: 12px 4px;
  }

  .nav-item {
    justify-content: center;
    padding: 12px 0;
    border-bottom: none;
    gap: 0;
  }
}
</style>
