import { reactive } from 'vue'

function storedUser() {
  try {
    const value = JSON.parse(localStorage.getItem('user') || 'null')
    return value && typeof value === 'object' && !Array.isArray(value) ? value : null
  } catch {
    localStorage.removeItem('user')
    return null
  }
}

export const authSession = reactive({
  token: localStorage.getItem('token') || '',
  refreshToken: localStorage.getItem('refreshToken') || '',
  user: storedUser(),
  validated: false,
})
let epoch = 0
export const sessionEpoch = () => epoch

export function updateAuthData(data) {
  if (data.access_token) {
    authSession.token = data.access_token
    localStorage.setItem('token', data.access_token)
  }
  if (data.refresh_token) {
    authSession.refreshToken = data.refresh_token
    localStorage.setItem('refreshToken', data.refresh_token)
  }
  if (data.user) {
    authSession.user = data.user
    authSession.validated = true
    localStorage.setItem('user', JSON.stringify(data.user))
  }
}

export function startSession(data) {
  clearAuthData()
  updateAuthData(data)
}

export function clearAuthData() {
  epoch += 1
  authSession.token = ''
  authSession.refreshToken = ''
  authSession.user = null
  authSession.validated = false
  for (const key of ['token', 'refreshToken', 'user']) localStorage.removeItem(key)
}

// A logout/account switch in another tab must not leave an old privileged UI active.
window.addEventListener('storage', (event) => {
  if (event.key === null || ['token', 'refreshToken', 'user'].includes(event.key)) {
    epoch += 1
    authSession.token = localStorage.getItem('token') || ''
    authSession.refreshToken = localStorage.getItem('refreshToken') || ''
    authSession.user = storedUser()
    authSession.validated = false
    if (!authSession.token) window.dispatchEvent(new Event('auth:expired'))
  }
})
