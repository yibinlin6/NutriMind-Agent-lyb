import request from '@/utils/request'

const KNOWLEDGE_ASK_TIMEOUT = 120000
// 图片资料上传要跑「多模态描述 + 向量化 + 食物实体抽取」多段模型调用，
// 远超默认 30s；给足时长，避免前端提前超时误报「无法连接后端」。
const KNOWLEDGE_UPLOAD_TIMEOUT = 300000

export function uploadDocumentApi(file) {
  const data = new FormData()
  data.append('file', file)
  return request.post('/knowledge/upload', data, { timeout: KNOWLEDGE_UPLOAD_TIMEOUT })
}

export const searchKnowledgeApi = (params) => request.get('/knowledge/search', { params })
export const askKnowledgeApi = (params, config = {}) => request.get('/knowledge/ask', {
  params,
  timeout: KNOWLEDGE_ASK_TIMEOUT,
  silent: true,
  ...config,
})
export const deleteDocumentApi = (source) => request.delete('/knowledge/', { params: { source } })
export const getKnowledgeStatsApi = () => request.get('/knowledge/stats')
export const getKnowledgeGraphApi = (config = {}) => request.get('/knowledge/graph', config)
// 用新抽取规则对已上传资料重跑图谱抽取（回填历史资料，如把成品菜肴补成节点）。
// 后端改为后台任务：此接口立即返回，用 status 接口轮询进度。
export const rebuildKnowledgeGraphApi = (config = {}) => request.post(
  '/knowledge/graph/rebuild', null, { silent: true, ...config },
)
export const getRebuildStatusApi = (config = {}) => request.get(
  '/knowledge/graph/rebuild/status', { silent: true, ...config },
)
