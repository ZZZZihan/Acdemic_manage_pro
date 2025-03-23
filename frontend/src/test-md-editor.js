// 测试 md-editor-v3 的导入方式
import { MdEditor } from 'md-editor-v3'

console.log('MdEditor:', MdEditor)

// 导出测试结果
export const testResult = {
  mdEditorExists: !!MdEditor,
  mdEditorType: typeof MdEditor
}

// 打印测试结果
console.log('测试结果:', testResult) 