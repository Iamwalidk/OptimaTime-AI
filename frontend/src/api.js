import axios from "axios";

const defaultHost = typeof window !== "undefined" ? window.location.hostname : "localhost";
const defaultBase = `http://${defaultHost}:8000/api/v1`;
export const apiBase = import.meta.env.VITE_API_BASE || defaultBase;

const api = axios.create({
  baseURL: apiBase,
  timeout: 20000, // allow slower responses (model load, cold start)
});
api.defaults.withCredentials = true;

export function setAuthToken(token) {
  if (token) {
    api.defaults.headers.common["Authorization"] = `Bearer ${token}`;
  } else {
    delete api.defaults.headers.common["Authorization"];
  }
}

export async function signup({ email, name, profile, password }) {
  const res = await api.post("/auth/signup", { email, name, profile, password });
  return res.data;
}

export async function signupOrLogin({ email, name, profile, password }) {
  try {
    return await signup({ email, name, profile, password });
  } catch (err) {
    const status = err?.response?.status;
    if (status === 409 || status === 400 || status === 401 || status === 404) {
      return await login({ email, password });
    }
    throw err;
  }
}

export async function login({ email, password }) {
  const res = await api.post("/auth/login", { email, password });
  return res.data;
}

export async function createTask(task) {
  const res = await api.post(`/tasks/`, task);
  return res.data;
}

export async function getTasks() {
  const res = await api.get(`/tasks/`);
  return res.data;
}

export async function generatePlan(dateString) {
  const res = await api.post("/planning/plan", {
    date: dateString,
  });
  return res.data;
}

export async function getPlan(dateString) {
  const res = await api.get(`/planning/plan`, { params: { plan_date: dateString } });
  return res.data;
}

export async function getCalendarRange(startDate, endDate) {
  const res = await api.get("/planning/calendar", { params: { start_date: startDate, end_date: endDate } });
  return res.data;
}

export async function updatePlanItem(planItemId, start, end) {
  const res = await api.patch(`/planning/item/${planItemId}`, null, { params: { start, end } });
  return res.data;
}

export async function deletePlanItem(planItemId) {
  const res = await api.delete(`/planning/item/${planItemId}`);
  return res.data;
}

export async function logFeedback({ taskId, outcome, note }) {
  const res = await api.post("/feedback/", {
    task_id: taskId,
    outcome,
    note,
  });
  return res.data;
}

export async function refreshAccessToken() {
  const res = await api.post("/auth/refresh");
  return res.data;
}

export async function getNotes() {
  const res = await api.get("/notes/");
  return res.data;
}

export async function addNote({ title, body }) {
  const res = await api.post("/notes/", { title, body });
  return res.data;
}

let isRefreshing = false;
let pendingRequests = [];

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          pendingRequests.push({ resolve, reject });
        })
          .then(() => api(originalRequest))
          .catch((err) => Promise.reject(err));
      }
      originalRequest._retry = true;
      isRefreshing = true;
      try {
        const refreshed = await refreshAccessToken();
        setAuthToken(refreshed.access_token);
        pendingRequests.forEach((p) => p.resolve());
        pendingRequests = [];
        return api(originalRequest);
      } catch (err) {
        pendingRequests.forEach((p) => p.reject(err));
        pendingRequests = [];
        return Promise.reject(err);
      } finally {
        isRefreshing = false;
      }
    }
    return Promise.reject(error);
  }
);
