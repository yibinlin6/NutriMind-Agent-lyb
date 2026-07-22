import axios from 'axios'
import { ElMessage } from 'element-plus'
import { apiBaseUrl } from './apiUrl'
import { clearNativeAccessToken, getNativeAccessToken } from './authToken'

const request = axios.create({
  baseURL: apiBaseUrl,
  timeout: 30000,
  withCredentials: true,
})

request.interceptors.request.use((config) => {
  const token = getNativeAccessToken()
  if (token) {
    config.headers = config.headers || {}
    if (!config.headers.Authorization) config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const status = error.response?.status
    const detail = error.response?.data?.message || error.response?.data?.detail
    const isSessionProbe = error.config?.url?.includes('/auth/me')
    if (status === 401 && !error.config?.url?.includes('/auth/login')) {
      clearNativeAccessToken()
      localStorage.removeItem('nutrimind_user')
      if (!isSessionProbe && window.location.pathname !== '/login') window.location.assign('/login')
    }
    if (!error.config?.silent) {
      ElMessage.error(detail || (status ? `请求失败（${status}）` : '无法连接后端服务'))
    }
    return Promise.reject(error)
  },
)

export default request
