const BASE = import.meta.env.VITE_API_URL || ''

export class ApiError extends Error {
  constructor(message, status, data) { super(message); this.status = status; this.data = data; this.fields = data?.fields || {} }
}

export const getToken = () => { try { return localStorage.getItem('token') } catch { return null } }
export const setToken = (t) => { try { t ? localStorage.setItem('token', t) : localStorage.removeItem('token') } catch { /* storage unavailable */ } }

async function request(method, path, body, { raw } = {}) {
  const headers = {}
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`
  let payload
  if (body instanceof FormData) payload = body
  else if (body !== undefined) { headers['Content-Type'] = 'application/json'; payload = JSON.stringify(body) }
  let res
  try { res = await fetch(`${BASE}/api${path}`, { method, headers, body: payload }) }
  catch { throw new ApiError('Cannot reach the server. Is the backend running?', 0, {}) }
  if (raw && res.ok) return res
  let data = {}
  try { data = await res.json() } catch { /* non-JSON */ }
  if (!res.ok) {
    if (res.status === 401 && token) window.dispatchEvent(new Event('auth:expired'))
    throw new ApiError(data.error || `Request failed (${res.status})`, res.status, data)
  }
  return data
}

export const api = {
  get: (p) => request('GET', p),
  post: (p, b) => request('POST', p, b ?? {}),
  put: (p, b) => request('PUT', p, b ?? {}),
  download: async (p, filename) => {
    const res = await request('GET', p, undefined, { raw: true })
    const url = URL.createObjectURL(await res.blob())
    const a = Object.assign(document.createElement('a'), { href: url, download: filename })
    document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url)
  },
}

export const qs = (obj) => {
  const p = new URLSearchParams()
  Object.entries(obj).forEach(([k, v]) => { if (v !== '' && v !== undefined && v !== null) p.set(k, v) })
  const s = p.toString()
  return s ? `?${s}` : ''
}
