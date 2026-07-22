import { isNativeRuntime } from './apiUrl'

const ACCESS_TOKEN_KEY = 'nutrimind_access_token'

function storageAvailable() {
  return typeof localStorage !== 'undefined'
}

// 浏览器站点继续使用 HttpOnly Cookie；原生 WebView 改用 Bearer，避免跨域 Cookie 兼容性问题。
export function getNativeAccessToken() {
  if (!isNativeRuntime || !storageAvailable()) return ''
  return localStorage.getItem(ACCESS_TOKEN_KEY) || ''
}

export function saveNativeAccessToken(token) {
  if (!isNativeRuntime || !storageAvailable()) return
  if (typeof token === 'string' && token.trim()) {
    localStorage.setItem(ACCESS_TOKEN_KEY, token.trim())
  } else {
    localStorage.removeItem(ACCESS_TOKEN_KEY)
  }
}

export function clearNativeAccessToken() {
  if (!isNativeRuntime || !storageAvailable()) return
  localStorage.removeItem(ACCESS_TOKEN_KEY)
}

export function withNativeAuthorization(headers = {}) {
  const token = getNativeAccessToken()
  return token ? { ...headers, Authorization: `Bearer ${token}` } : headers
}
