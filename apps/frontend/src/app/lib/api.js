const API_BASE_URL = (process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");
const LEGACY_API_BASE_URL = (
  process.env.NEXT_PUBLIC_LEGACY_API_BASE_URL || `${API_BASE_URL}/api/v1`
).replace(/\/$/, "");

function buildHeaders(token, isJson = true) {
  const headers = {};
  if (isJson) {
    headers["Content-Type"] = "application/json";
  }
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  return headers;
}

async function parseResponse(response) {
  const rawText = await response.text();
  const payload = rawText ? JSON.parse(rawText) : null;

  if (!response.ok) {
    const message =
      payload?.detail ||
      payload?.message ||
      payload?.error ||
      `Request failed with status ${response.status}`;
    const error = new Error(message);
    error.status = response.status;
    error.payload = payload;
    throw error;
  }

  return payload;
}

async function request(path, options = {}) {
  const { method = "GET", token, body, useLegacyBase = false, isJson = true } = options;
  const baseUrl = useLegacyBase ? LEGACY_API_BASE_URL : API_BASE_URL;
  const response = await fetch(`${baseUrl}${path}`, {
    method,
    headers: buildHeaders(token, isJson),
    body: body === undefined ? undefined : isJson ? JSON.stringify(body) : body,
    cache: "no-store",
  });

  return parseResponse(response);
}

export function getApiBaseUrl() {
  return API_BASE_URL;
}

export function getLegacyApiBaseUrl() {
  return LEGACY_API_BASE_URL;
}

export async function registerUser(payload) {
  return request("/auth/register", {
    method: "POST",
    body: payload,
  });
}

export async function loginUser({ email, password }) {
  const formData = new URLSearchParams();
  formData.set("username", email);
  formData.set("password", password);

  return request("/auth/login", {
    method: "POST",
    body: formData,
    isJson: false,
  });
}

export async function getCurrentUser(token) {
  return request("/auth/me", { token });
}

export async function summarizeText(token, payload) {
  return request("/ai/", {
    method: "POST",
    token,
    body: payload,
  });
}

export async function summarizeLegacy(payload) {
  return request("/summarize", {
    method: "POST",
    useLegacyBase: true,
    body: payload,
  });
}

export async function listConversations(token) {
  return request("/history/conversations", { token });
}

export async function deleteConversation(token, conversationId) {
  return request(`/history/conversations/${conversationId}`, {
    method: "DELETE",
    token,
  });
}

export async function getConversationMessages(token, conversationId) {
  return request(`/ai/conversations/${conversationId}/messages`, { token });
}

export async function getConversationRating(token, conversationId) {
  return request(`/rating/conversation/${conversationId}`, { token });
}

export async function upsertRating(token, payload) {
  return request("/rating/", {
    method: "POST",
    token,
    body: payload,
  });
}

export async function listUsers(token) {
  return request("/admin/users", { token });
}

export async function listLogs(token) {
  return request("/admin/logs", { token });
}

export async function getAdminAnalytics(token) {
  return request("/admin/analytics", { token });
}

export async function updateUserRole(token, userId, role) {
  return request(`/admin/users/${userId}/role`, {
    method: "PATCH",
    token,
    body: { role },
  });
}
