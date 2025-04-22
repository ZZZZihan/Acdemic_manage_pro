/**
 * 日期格式化工具函数
 */

/**
 * 格式化日期
 * @param {Date|string|number} date 要格式化的日期
 * @param {string} format 格式化模式，支持YYYY-MM-DD HH:mm:ss
 * @returns {string} 格式化后的日期字符串
 */
export function formatDate(date, format = 'YYYY-MM-DD') {
  if (!date) return ''
  
  const d = new Date(date)
  
  if (isNaN(d.getTime())) {
    console.error('Invalid date:', date)
    return ''
  }
  
  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const hours = String(d.getHours()).padStart(2, '0')
  const minutes = String(d.getMinutes()).padStart(2, '0')
  const seconds = String(d.getSeconds()).padStart(2, '0')
  
  return format
    .replace('YYYY', year)
    .replace('MM', month)
    .replace('DD', day)
    .replace('HH', hours)
    .replace('mm', minutes)
    .replace('ss', seconds)
}

/**
 * 相对时间格式，如 "3分钟前"，"1小时前"，"昨天10:30" 等
 * @param {Date|string|number} date 要格式化的日期
 * @returns {string} 相对时间字符串
 */
export function formatRelativeTime(date) {
  if (!date) return ''
  
  const d = new Date(date)
  const now = new Date()
  const diff = now - d
  
  // 时间差（毫秒）
  const minute = 60 * 1000
  const hour = 60 * minute
  const day = 24 * hour
  const month = 30 * day
  const year = 365 * day
  
  if (diff < minute) {
    return '刚刚'
  } else if (diff < hour) {
    return `${Math.floor(diff / minute)}分钟前`
  } else if (diff < day) {
    return `${Math.floor(diff / hour)}小时前`
  } else if (diff < 2 * day) {
    return `昨天 ${formatDate(d, 'HH:mm')}`
  } else if (diff < 3 * day) {
    return `前天 ${formatDate(d, 'HH:mm')}`
  } else if (diff < 7 * day) {
    return `${Math.floor(diff / day)}天前`
  } else if (diff < year) {
    return formatDate(d, 'MM-DD HH:mm')
  } else {
    return formatDate(d, 'YYYY-MM-DD')
  }
} 