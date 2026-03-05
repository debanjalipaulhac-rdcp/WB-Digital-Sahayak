import axios from 'axios'

const API = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor
API.interceptors.request.use(
  (config) => config,
  (error) => Promise.reject(error)
)

// Response interceptor
API.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 404) {
      error.isNotFound = true
    }
    return Promise.reject(error)
  }
)

export const getScheme = (id) => API.get(`/scheme/${id}`)
export const checkEligibility = (data) => API.post('/check-eligibility', data)
export const getSchemes = () => API.get('/schemes')

export default API
