// 浏览器站点沿用相对路径；原生壳通过 VITE_API_ORIGIN 指向线上服务。
const configuredOrigin = import.meta.env.VITE_API_ORIGIN?.trim() || ''
const apiOrigin = configuredOrigin.replace(/\/+$/, '')
const absoluteUrlPattern = /^(?:[a-z][a-z\d+.-]*:|\/\/)/i

export function resolveApiUrl(path, origin = apiOrigin) {
  if (typeof path !== 'string') return path
  const source = path.trim()
  const normalizedOrigin = typeof origin === 'string' ? origin.replace(/\/+$/, '') : ''
  if (!source || !normalizedOrigin || absoluteUrlPattern.test(source)) return source
  return `${normalizedOrigin}${source.startsWith('/') ? source : `/${source}`}`
}

export function apiUrl(path) {
  return resolveApiUrl(path)
}

export const apiBaseUrl = apiUrl('/api')

export const isNativeRuntime = import.meta.env.VITE_APP_RUNTIME === 'native'
