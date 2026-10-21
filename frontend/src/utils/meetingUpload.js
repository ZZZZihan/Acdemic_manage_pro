import api from './axios'

// Element Plus' default XHR bypasses the shared session refresh/revocation handling.
export async function uploadMeetingAttachment(options) {
  const body = new FormData()
  body.append('file', options.file)
  const response = await api.post('/api/v1/meetings/attachments/upload', body)
  return response.data
}
