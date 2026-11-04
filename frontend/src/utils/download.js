import axios from '@/utils/axios'

function encodedPath(filePath) {
  return String(filePath)
    .split('/')
    .map(segment => encodeURIComponent(segment))
    .join('/')
}

export async function downloadAuthorizedFile(filePath, originalName) {
  const response = await axios.get(`/api/v1/files/download/${encodedPath(filePath)}`, {
    responseType: 'blob'
  })
  const url = URL.createObjectURL(response.data)
  const link = document.createElement('a')
  link.href = url
  link.download = originalName || String(filePath).split('/').pop()
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

export async function authorizedObjectUrl(filePath) {
  const response = await axios.get(`/api/v1/files/download/${encodedPath(filePath)}`, {
    responseType: 'blob'
  })
  return URL.createObjectURL(response.data)
}
