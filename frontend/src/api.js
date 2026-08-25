const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

async function request(path, options) {
  const response = await fetch(`${BASE_URL}${path}`, options)
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}))
    throw new Error(payload.detail || 'Something went wrong. Please try again.')
  }
  return response.json()
}

export const api = {
  jobs: () => request('/api/imports'),
  job: (id) => request(`/api/imports/${id}`),
  records: (id, params) => request(`/api/imports/${id}/records?${new URLSearchParams(params)}`),
  upload: (file) => { const body = new FormData(); body.append('file', file); return request('/api/imports', { method: 'POST', body }) },
  validDownloadUrl: (id) => `${BASE_URL}/api/imports/${id}/valid-records.csv`,
}
