import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { api, getToken, setToken } from './api'

const AuthCtx = createContext(null)
export const useAuth = () => useContext(AuthCtx)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(!!getToken())

  const logout = useCallback(() => { setToken(null); setUser(null) }, [])
  useEffect(() => {
    if (!getToken()) return
    api.get('/auth/me').then((d) => setUser(d.user)).catch(() => setToken(null)).finally(() => setLoading(false))
  }, [])
  useEffect(() => { window.addEventListener('auth:expired', logout); return () => window.removeEventListener('auth:expired', logout) }, [logout])

  const login = async (email, password) => { const d = await api.post('/auth/login', { email, password }); setToken(d.token); setUser(d.user); return d.user }
  const register = async (payload) => { const d = await api.post('/auth/register', payload); setToken(d.token); setUser(d.user); return d.user }
  const can = (code) => !!user?.permissions?.includes(code)
  return <AuthCtx.Provider value={{ user, loading, login, register, logout, can, setUser }}>{children}</AuthCtx.Provider>
}
