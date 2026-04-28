import { marked } from 'marked'
import DOMPurify from 'dompurify'

// 配置 marked
marked.setOptions({
  breaks: true, // 换行符转换
  gfm: true, // GitHub Flavored Markdown
})

// 允许的标签
const allowedTags = [
  'a', 'b', 'blockquote', 'br', 'code', 'del', 'em',
  'h1', 'h2', 'h3', 'h4', 'hr', 'i', 'li', 'ol', 'p',
  'pre', 'strong', 'table', 'tbody', 'td', 'th',
  'thead', 'tr', 'ul', 'img'
]

// 允许的属性
const allowedAttrs = [
  'class', 'href', 'rel', 'target', 'title', 'src', 'alt',
  'style', 'width', 'height'
]

/**
 * 渲染 Markdown 为安全的 HTML
 */
export function renderMarkdown(text: string): string {
  if (!text) return ''

  // 解析 Markdown
  const html = marked.parse(text) as string

  // 清理 HTML，防止 XSS
  // 使用 ALLOW_DATA_ATTR 允许 data URI 图片
  const clean = DOMPurify.sanitize(html, {
    ALLOWED_TAGS: allowedTags,
    ALLOWED_ATTR: allowedAttrs,
    // 允许 data URI（用于 base64 图片）和 http/https 协议
    ALLOWED_URI_REGEXP: /^(?:(?:(?:f|ht)tps?|mailto|tel|callto|sms|cid|xmpp|data):|[^a-z]|[a-z+.\-]+(?:[^a-z+.\-:]|$))/i,
  })

  return clean
}

/**
 * 格式化时间戳
 */
export function formatTime(date: Date): string {
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
  })
}
