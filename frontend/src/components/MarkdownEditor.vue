<template>
  <div class="markdown-editor">
    <md-editor
      v-model="content"
      :style="{ height: height + 'px' }"
      :placeholder="placeholder"
      :toolbars="toolbars"
      :preview="true"
      :previewOnly="false"
      previewTheme="github"
      codeTheme="github"
      @onChange="handleChange"
      :editorId="editorId"
      :tabWidth="2"
      :noMermaid="false"
      :noKatex="false"
      :noIframe="false"
      :autoDetectCode="true"
      :showCodeRowNumber="true"
      :footers="[]"
    />
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import MdEditor from 'md-editor-v3'
import 'md-editor-v3/lib/style.css'

const props = defineProps({
  modelValue: {
    type: String,
    default: ''
  },
  placeholder: {
    type: String,
    default: '请输入内容，支持Markdown格式'
  },
  height: {
    type: Number,
    default: 500
  }
})

const emit = defineEmits(['update:modelValue', 'change'])

// 生成唯一的编辑器ID
const editorId = `md-editor-${Date.now()}`

// 编辑器内容
const content = ref(props.modelValue || '')

// 工具栏配置 - 更简洁的工具栏，类似Notion
const toolbars = [
  'bold', 'italic', 'strikethrough', 
  'title', 'sub', 'sup', 
  'quote', 'unorderedList', 'orderedList', 
  'codeRow', 'code', 
  'link', 'image', 'table', 
  'revoke', 'next', 
  'save', 'preview'
]

// 监听父组件传入的值变化
watch(() => props.modelValue, (newValue) => {
  if (newValue !== content.value) {
    content.value = newValue
  }
}, { immediate: true })

// 监听内容变化，向父组件发送更新
watch(() => content.value, (newValue) => {
  emit('update:modelValue', newValue)
})

// 内容变化处理函数
const handleChange = (value) => {
  emit('change', value)
}

// 组件挂载后的处理
onMounted(() => {
  // 可以在这里添加额外的初始化逻辑
})
</script>

<style scoped>
.markdown-editor {
  width: 100%;
  margin-bottom: 20px;
}

:deep(.md-editor) {
  border-radius: 4px;
  border: 1px solid #dcdfe6;
  transition: border-color 0.2s;
}

:deep(.md-editor:hover) {
  border-color: #c0c4cc;
}

:deep(.md-editor-content) {
  font-size: 15px;
  line-height: 1.6;
}

:deep(.md-editor-preview-wrapper) {
  padding: 16px 24px;
  background-color: #fafafa;
  border-left: 1px solid #eaeaea;
}

:deep(.md-editor-preview) {
  font-size: 15px;
  line-height: 1.6;
}

:deep(.md-editor-toolbar) {
  border-bottom: 1px solid #eaeaea;
  background-color: #f5f7fa;
}

:deep(.md-editor-toolbar-item) {
  color: #606266;
}

:deep(.md-editor-toolbar-item:hover) {
  color: #409eff;
  background-color: #ecf5ff;
}

:deep(.md-editor-input) {
  padding: 16px 24px;
}
</style> 