<template>
  <div class="markdown-renderer" v-html="renderedContent"></div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { marked } from 'marked'

const props = defineProps({
  content: {
    type: String,
    default: ''
  }
})

const renderedContent = computed(() => {
  try {
    if (!props.content) return '<div class="empty-content">暂无内容</div>'
    return marked(props.content)
  } catch (error) {
    console.error('Markdown渲染错误:', error)
    return `<div class="error-content">渲染错误: ${error.message}</div>`
  }
})
</script>

<style scoped>
.markdown-renderer {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
  font-size: 16px;
  line-height: 1.8;
  color: #333;
}

.markdown-renderer :deep(h1) {
  font-size: 28px;
  margin-top: 28px;
  margin-bottom: 16px;
  font-weight: 600;
  line-height: 1.3;
}

.markdown-renderer :deep(h2) {
  font-size: 24px;
  margin-top: 24px;
  margin-bottom: 14px;
  font-weight: 600;
  line-height: 1.3;
}

.markdown-renderer :deep(h3) {
  font-size: 20px;
  margin-top: 20px;
  margin-bottom: 12px;
  font-weight: 600;
  line-height: 1.3;
}

.markdown-renderer :deep(p) {
  margin-bottom: 16px;
  line-height: 1.7;
}

.markdown-renderer :deep(ul), .markdown-renderer :deep(ol) {
  padding-left: 24px;
  margin-bottom: 16px;
}

.markdown-renderer :deep(li) {
  margin-bottom: 6px;
}

.markdown-renderer :deep(code) {
  background-color: rgba(135, 131, 120, 0.15);
  color: #eb5757;
  padding: 2px 4px;
  border-radius: 3px;
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
  font-size: 0.9em;
}

.markdown-renderer :deep(pre) {
  margin-bottom: 16px;
  border-radius: 4px;
  padding: 16px;
  background-color: #f6f8fa;
  overflow: auto;
}

.markdown-renderer :deep(pre code) {
  background-color: transparent;
  color: #333;
  padding: 0;
}

.markdown-renderer :deep(blockquote) {
  border-left: 3px solid #dfe2e5;
  padding: 0.6em 1.2em;
  color: #6a737d;
  margin: 0 0 16px;
  background-color: #f6f8fa;
  border-radius: 0 4px 4px 0;
}

.markdown-renderer :deep(table) {
  border-collapse: collapse;
  margin-bottom: 16px;
  width: 100%;
  border-radius: 4px;
  overflow: hidden;
}

.markdown-renderer :deep(table th), .markdown-renderer :deep(table td) {
  border: 1px solid #dfe2e5;
  padding: 8px 12px;
}

.markdown-renderer :deep(table th) {
  background-color: #f6f8fa;
  font-weight: 600;
}

.markdown-renderer :deep(table tr:nth-child(2n)) {
  background-color: #f8f8f8;
}

.markdown-renderer :deep(a) {
  color: #0366d6;
  text-decoration: none;
}

.markdown-renderer :deep(a:hover) {
  text-decoration: underline;
}

.markdown-renderer :deep(img) {
  max-width: 100%;
  border-radius: 4px;
  margin: 16px 0;
}

.markdown-renderer :deep(hr) {
  height: 1px;
  background-color: #e1e4e8;
  border: none;
  margin: 24px 0;
}

.empty-content {
  color: #999;
  font-style: italic;
  padding: 20px 0;
}

.error-content {
  color: #ff4d4f;
  font-style: italic;
  padding: 20px 0;
}
</style> 