<template>
  <div class="rich-text-editor">
    <div style="border: 1px solid #ccc; z-index: 100;">
      <Toolbar
        style="border-bottom: 1px solid #ccc"
        :editor="editorRef"
        :defaultConfig="toolbarConfig"
        :mode="mode"
      />
      <Editor
        style="height: 400px; overflow-y: hidden;"
        v-model="valueHtml"
        :defaultConfig="editorConfig"
        :mode="mode"
        @onCreated="handleCreated"
        @onChange="handleChange"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, shallowRef, onBeforeUnmount, watch } from 'vue'
import '@wangeditor/editor/dist/css/style.css'
import { Editor, Toolbar } from '@wangeditor/editor-for-vue'

const props = defineProps({
  modelValue: {
    type: String,
    default: ''
  },
  placeholder: {
    type: String,
    default: '请输入内容...'
  },
  height: {
    type: Number,
    default: 400
  }
})

const emit = defineEmits(['update:modelValue', 'change'])

// 编辑器实例，必须用 shallowRef
const editorRef = shallowRef()

// 内容 HTML
const valueHtml = ref('')

// 模式
const mode = ref('default') // 或 'simple'

// 工具栏配置
const toolbarConfig = {
  excludeKeys: []
}

// 编辑器配置
const editorConfig = {
  placeholder: props.placeholder,
  MENU_CONF: {}
}

// 初始化编辑器内容
watch(() => props.modelValue, (newValue) => {
  if (newValue !== valueHtml.value) {
    valueHtml.value = newValue
  }
}, { immediate: true })

// 监听内容变化，向父组件发送更新
watch(() => valueHtml.value, (newValue) => {
  emit('update:modelValue', newValue)
  emit('change', newValue)
})

// 组件销毁时，也销毁编辑器
onBeforeUnmount(() => {
  const editor = editorRef.value
  if (editor == null) return
  editor.destroy()
})

// 编辑器创建完成时的回调
const handleCreated = (editor) => {
  editorRef.value = editor // 记录 editor 实例
}

// 编辑器内容变化时的回调
const handleChange = (editor) => {
  emit('update:modelValue', editor.getHtml())
  emit('change', editor.getHtml())
}
</script>

<style scoped>
.rich-text-editor {
  width: 100%;
  margin-bottom: 20px;
}
</style> 