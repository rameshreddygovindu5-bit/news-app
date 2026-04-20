import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_URL || '';

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
  timeout: 120000,
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
export const bulkDeleteArticles = (ids) => api.post('/api/articles/bulk-delete', { ids });
export const bulkReprocessArticles = (ids) => api.post('/api/articles/bulk-reprocess', { ids });

// Reporter Submission & Approval
export const submitArticle = (data) => api.post('/api/articles/submit', data);
export const suggestMetadata = (data) => api.post('/api/articles/suggest', data);
export const getPendingArticles = (params) => api.get('/api/articles/pending', { params });
export const approveArticle = (id, action, note) => api.post(`/api/articles/${id}/approve`, { action, admin_note: note });
export const bulkApproveArticles = (ids, action) => api.post('/api/articles/bulk-approve', { ids, action });
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
export const getSourceErrors = (params) => api.get('/api/scheduler/source-errors', { params });
export const getPostErrors = (params) => api.get('/api/scheduler/post-errors', { params });
export const triggerAction = (action, sourceId) => api.post('/api/scheduler/trigger', { action, source_id: sourceId });
export const getSchedulerConfig = () => api.get('/api/scheduler/config');
export const updateSchedulerConfig = (data) => api.put('/api/scheduler/config', data);

// YouTube Import
export const processYouTube = (url, sourceId) => api.post('/api/youtube/process', { url, source_id: sourceId });
export const saveYouTubeArticle = (data) => api.post('/api/youtube/save', data);

// File Upload
export const uploadImage = (file) => {
  const formData = new FormData();
  formData.append('file', file);
  return api.post('/api/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
};

// Wishes / Greetings
export const getWishes = (params) => api.get('/api/wishes', { params });
export const getActiveWishes = (params) => api.get('/api/wishes/active', { params });
export const createWish = (data) => api.post('/api/wishes', data);
export const updateWish = (id, data) => api.put(`/api/wishes/${id}`, data);
export const deleteWish = (id) => api.delete(`/api/wishes/${id}`);

// Polls
export const getPolls = () => api.get('/api/polls');
export const createPoll = (data) => api.post('/api/polls', data);

// Social & AWS Status
export const getSocialStatus = () => api.get('/api/scheduler/social-status');

export default api;
