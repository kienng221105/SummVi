function normalizeBaseUrl(value, fallback) {
  return (value || fallback).replace(/\/$/, "");
}

const IS_PROD = typeof window !== "undefined" && !window.location.hostname.includes("localhost");

const getDynamicBaseUrl = (envValue, port, isLegacy = false) => {
  if (typeof window !== "undefined") {
    // In Browser: Route through NextJS rewrites to avoid firewall drops
    // Only trust envValue directly if it's a full absolute external URL (not localhost)
    if (envValue && envValue.startsWith("http") && !envValue.includes("localhost")) {
      return normalizeBaseUrl(envValue, "");
    }
    return isLegacy ? "/api/v1" : "/api";
  }

  // Server-side (SSR / RSC inside Docker or locally):
  // Node.js fetch REQUIRES complete absolute URLs.
  // Prioritize Docker internal network name, user env (if absolute), then fallback.
  const envAbsURL = (envValue && envValue.startsWith("http")) ? envValue : null;
  const ssrBase = (process.env.INTERNAL_BACKEND_URL || envAbsURL || `http://localhost:${port}`).replace(/\/$/, "");
  return isLegacy ? `${ssrBase}/api/v1` : ssrBase;
};

const API_BASE_URL = getDynamicBaseUrl(process.env.NEXT_PUBLIC_API_BASE_URL, 8000, false);
const LEGACY_API_BASE_URL = getDynamicBaseUrl(process.env.NEXT_PUBLIC_LEGACY_API_BASE_URL, 8000, true);

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
  let payload = null;

  if (rawText) {
    try {
      payload = JSON.parse(rawText);
    } catch (_error) {
      payload = { detail: rawText };
    }
  }

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
  try {
    const response = await fetch(`${baseUrl}${path}`, {
      method,
      headers: buildHeaders(token, isJson),
      body: body === undefined ? undefined : isJson ? JSON.stringify(body) : body,
      cache: "no-store",
    });

    return parseResponse(response);
  } catch (error) {
    if (typeof error?.status === "number") {
      throw error;
    }
    throw new Error("Backend chưa sẵn sàng hoặc không thể kết nối. Hãy khởi động backend trước.");
  }
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

export async function uploadDocument(token, file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/ai/upload`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || "Không thể tải tài liệu.");
  }

  return response.json();
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
