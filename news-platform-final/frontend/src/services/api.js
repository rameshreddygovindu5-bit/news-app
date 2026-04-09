import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_URL || 'http://127.0.0.1:8005';

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/';
    }
    return Promise.reject(err);
  }
);

// Auth
export const login = (username, password) => api.post('/api/auth/login', { username, password });
export const getMe = () => api.get('/api/auth/me');

// User Management (admin only)
export const getUsers = () => api.get('/api/auth/users');
export const createUser = (data) => api.post('/api/auth/users', data);
export const updateUser = (id, data) => api.put(`/api/auth/users/${id}`, data);
export const deleteUser = (id) => api.delete(`/api/auth/users/${id}`);

// Dashboard
export const getDashboardStats = () => api.get('/api/dashboard/stats');

// Articles
export const getArticles = (params) => api.get('/api/articles', { params });
export const getArticle = (id) => api.get(`/api/articles/${id}`);
export const updateArticle = (id, data) => api.put(`/api/articles/${id}`, data);
export const deleteArticle = (id) => api.delete(`/api/articles/${id}`);
export const createManualArticle = (data) => api.post('/api/articles/manual', data);
export const reprocessArticle = (id) => api.post(`/api/articles/${id}/reprocess`);
export const getTopNews = (limit = 100) => api.get('/api/articles/top-news', { params: { limit } });
export const getArticlesByCategory = (category, params) => api.get(`/api/articles/by-category/${category}`, { params });

// Reporter Submission & Approval
export const submitArticle = (data) => api.post('/api/articles/submit', data);
export const getPendingArticles = (params) => api.get('/api/articles/pending', { params });
export const approveArticle = (id, action, note) => api.post(`/api/articles/${id}/approve`, { action, admin_note: note });
export const getMySubmissions = (params) => api.get('/api/articles/my-submissions', { params });

// Sources
export const getSources = () => api.get('/api/sources');
export const getSource = (id) => api.get(`/api/sources/${id}`);
export const createSource = (data) => api.post('/api/sources', data);
export const updateSource = (id, data) => api.put(`/api/sources/${id}`, data);
export const deleteSource = (id) => api.delete(`/api/sources/${id}`);
export const togglePause = (id) => api.post(`/api/sources/${id}/toggle-pause`);
export const toggleEnable = (id) => api.post(`/api/sources/${id}/toggle-enable`);
export const getSourceStats = (id) => api.get(`/api/sources/${id}/stats`);

// Categories
export const getCategories = () => api.get('/api/categories');
export const createCategory = (data) => api.post('/api/categories', data);

// Scheduler
export const getSchedulerLogs = (params) => api.get('/api/scheduler/logs', { params });
export const triggerAction = (action, sourceId) => api.post('/api/scheduler/trigger', { action, source_id: sourceId });
export const getSchedulerConfig = () => api.get('/api/scheduler/config');
export const updateSchedulerConfig = (data) => api.put('/api/scheduler/config', data);

// YouTube Import
export const processYouTube = (url, sourceId) => api.post('/api/youtube/process', { url, source_id: sourceId });
export const saveYouTubeArticle = (data) => api.post('/api/youtube/save', data);

// Social & AWS Status
export const getSocialStatus = () => api.get('/api/scheduler/social-status');

export default api;
