import axios from 'axios';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const api = axios.create({
  baseURL: `${API_URL}/api`,
});

// Add token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Projects
export const getProjects = () => api.get('/projects');
export const getProject = (id) => api.get(`/projects/${id}`);
export const createProject = (data) => api.post('/projects', data);
export const updateProject = (id, data) => api.put(`/projects/${id}`, data);
export const deleteProject = (id) => api.delete(`/projects/${id}`);

// Risk Analysis
export const analyzeProject = (projectId) => api.post(`/projects/${projectId}/analyze`);
export const getProjectAssessments = (projectId) => api.get(`/projects/${projectId}/assessments`);
export const getLatestAssessments = () => api.get('/assessments/latest');

// Data Uploads
export const uploadData = (formData) => api.post('/uploads', formData, {
  headers: { 'Content-Type': 'multipart/form-data' }
});
export const getUploads = (projectId) => api.get('/uploads', { params: { project_id: projectId } });

// Manual Entries
export const createEntry = (data) => api.post('/entries', data);
export const getEntries = (projectId) => api.get('/entries', { params: { project_id: projectId } });

// Notifications
export const getNotifications = () => api.get('/notifications');
export const markNotificationRead = (id) => api.put(`/notifications/${id}/read`);
export const markAllNotificationsRead = () => api.put('/notifications/read-all');

// Dashboard
export const getDashboardStats = () => api.get('/dashboard/stats');

// Settings - Jira
export const saveJiraConfig = (data) => api.post('/settings/jira', data);
export const getJiraConfig = () => api.get('/settings/jira');

// Settings - ClickUp
export const saveClickUpConfig = (data) => api.post('/settings/clickup', data);
export const getClickUpConfig = () => api.get('/settings/clickup');
export const testClickUpConnection = () => api.post('/clickup/test-connection');
export const getClickUpTeams = () => api.get('/clickup/teams');
export const getClickUpSpaces = (teamId) => api.get(`/clickup/spaces/${teamId}`);
export const getClickUpLists = (spaceId) => api.get(`/clickup/lists/${spaceId}`);
export const syncClickUp = (data) => api.post('/clickup/sync', data);
export const getClickUpSyncHistory = (projectId) => api.get(`/clickup/sync-history/${projectId}`);

export default api;
