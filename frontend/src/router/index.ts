import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'chat',
      component: () => import('../views/ChatView.vue'),
    },
    {
      path: '/sessions',
      name: 'sessions',
      component: () => import('../views/SessionsView.vue'),
    },
    {
      path: '/memory',
      name: 'memory',
      component: () => import('../views/MemoryView.vue'),
    },
    {
      path: '/config',
      name: 'config',
      component: () => import('../views/ConfigView.vue'),
    },
    {
      path: '/job-hunting',
      name: 'job-hunting',
      component: () => import('../views/JobHuntingView.vue'),
    },
  ],
})

export default router
