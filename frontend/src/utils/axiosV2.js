import { createAuthenticatedClient } from './axios'

export default createAuthenticatedClient(import.meta.env.VITE_API_V2_URL || '', 30000)
