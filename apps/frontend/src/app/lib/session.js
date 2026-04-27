const SESSION_KEY = "summvi-session";

function decodeJwtSegment(segment) {
  /**
   * Decode một segment của JWT token (base64url).
   *
   * JWT format: header.payload.signature
   * Mỗi segment là base64url encoded JSON
   */
  if (!segment) {
    return null;
  }

  try {
    const normalized = segment.replace(/-/g, "+").replace(/_/g, "/");
    const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, "=");
    return JSON.parse(window.atob(padded));
  } catch (_error) {
    return null;
  }
}

function decodeToken(token) {
  /**
   * Decode JWT token để lấy payload (claims).
   * Không verify signature - chỉ extract thông tin.
   */
  if (!token) {
    return null;
  }
  const parts = token.split(".");
  const payload = parts.length >= 3 ? parts[1] : parts[0];
  return decodeJwtSegment(payload);
}

export function createSession(accessToken, email) {
  /**
   * Tạo session object từ access token.
   * Extract user info từ JWT claims.
   */
  const claims = decodeToken(accessToken) || {};
  return {
    token: accessToken,
    email: email || claims.email || "",
    userId: claims.sub || "",
    role: claims.role || "user",
    issuedAt: new Date().toISOString(),
  };
}

export function mergeSessionWithUser(session, user) {
  return {
    ...session,
    email: user?.email || session?.email || "",
    userId: user?.id || session?.userId || "",
    role: user?.role || session?.role || "user",
    isActive: user?.is_active ?? session?.isActive ?? true,
  };
}

export function saveSession(session) {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(SESSION_KEY, JSON.stringify(session));
}

export function getStoredSession() {
  if (typeof window === "undefined") {
    return null;
  }

  try {
    const raw = window.localStorage.getItem(SESSION_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch (_error) {
    return null;
  }
}

export function clearStoredSession() {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.removeItem(SESSION_KEY);
}

export function isAdminSession(session) {
  return session?.role === "admin";
}

export function clearSessionAndRedirect(target = "/login") {
  clearStoredSession();

  if (typeof window === "undefined") {
    return;
  }

  window.location.replace(target);
}
