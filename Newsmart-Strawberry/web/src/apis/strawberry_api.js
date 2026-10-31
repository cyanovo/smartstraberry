const TOKEN_KEY = 'strawberry-admin-token'

export const getToken = () => sessionStorage.getItem(TOKEN_KEY)
export const setToken = (token) => sessionStorage.setItem(TOKEN_KEY, token)
export const clearToken = () => sessionStorage.removeItem(TOKEN_KEY)

export async function request(path, options = {}) {
  const headers = { ...options.headers }
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`
  if (options.body && !(options.body instanceof FormData)) headers['Content-Type'] = 'application/json'
  const response = await fetch(`/legacy${path}`, { ...options, headers })
  if (!response.ok) throw new Error(`服务请求失败 (${response.status})`)
  const result = await response.json()
  if (result.code && result.code !== 200) {
    if (result.code === 401) clearToken()
    throw new Error(result.msg || '请求失败')
  }
  return result
}

export const getCaptcha = () => request('/captchaImage')
export const login = (data) => request('/login', { method: 'POST', body: JSON.stringify(data) })
export const getUser = () => request('/getInfo')
export const logout = () => request('/logout', { method: 'POST' })
export const list = (resource, params = {}) => {
  const query = new URLSearchParams(params)
  return request(`/system/${resource}/list?${query}`)
}
