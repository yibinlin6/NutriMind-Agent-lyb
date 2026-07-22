import { describe, expect, it } from 'vitest'
import { resolveApiUrl } from './apiUrl'

describe('resolveApiUrl', () => {
  it('keeps relative routes for the browser deployment', () => {
    expect(resolveApiUrl('/api/health', '')).toBe('/api/health')
  })

  it('uses the configured NutriMind origin for native builds', () => {
    expect(resolveApiUrl('/api/health', 'https://nutrimind.chat')).toBe('https://nutrimind.chat/api/health')
    expect(resolveApiUrl('api/health', 'https://nutrimind.chat/')).toBe('https://nutrimind.chat/api/health')
  })

  it('does not rewrite already absolute or blob URLs', () => {
    expect(resolveApiUrl('https://example.com/image.jpg', 'https://nutrimind.chat')).toBe('https://example.com/image.jpg')
    expect(resolveApiUrl('blob:https://app.local/image', 'https://nutrimind.chat')).toBe('blob:https://app.local/image')
  })
})
