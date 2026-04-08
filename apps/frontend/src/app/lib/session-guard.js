"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { getCurrentUser } from "./api";
import { clearStoredSession, getStoredSession, isAdminSession, mergeSessionWithUser, saveSession } from "./session";

async function validateStoredSession() {
  const storedSession = getStoredSession();
  if (!storedSession?.token) {
    return null;
  }

  try {
    const currentUser = await getCurrentUser(storedSession.token);
    const refreshedSession = mergeSessionWithUser(storedSession, currentUser);
    saveSession(refreshedSession);
    return refreshedSession;
  } catch (_error) {
    clearStoredSession();
    return null;
  }
}

export function useSessionGuard({ mode = "protected", requireAdmin = false, fallbackPath = "/" } = {}) {
  const router = useRouter();
  const [session, setSession] = useState(null);
  const [booting, setBooting] = useState(true);
  const lastValidatedRef = useRef({ token: "", at: 0 });

  function sessionsMatch(left, right) {
    if (!left || !right) {
      return false;
    }

    return (
      left.token === right.token &&
      left.email === right.email &&
      left.role === right.role &&
      left.userId === right.userId &&
      left.isActive === right.isActive
    );
  }

  useEffect(() => {
    let cancelled = false;
    let inFlight = false;
    const validationTtlMs = 30000;

    const syncSession = async () => {
      if (inFlight) {
        return;
      }

      const storedSession = getStoredSession();
      const cachedToken = lastValidatedRef.current.token;
      const cacheAge = Date.now() - lastValidatedRef.current.at;
      const token = storedSession?.token || "";

      if (token && token === cachedToken && cacheAge < validationTtlMs) {
        if (cancelled) {
          return;
        }
        setSession((current) => (sessionsMatch(current, storedSession) ? current : storedSession));
        setBooting(false);

        if (mode === "public") {
          if (storedSession) {
            router.replace(isAdminSession(storedSession) ? "/admin" : "/");
          }
        } else if (requireAdmin && !isAdminSession(storedSession)) {
          router.replace(fallbackPath);
        }

        return;
      }

      inFlight = true;
      const refreshedSession = await validateStoredSession();
      lastValidatedRef.current = { token, at: Date.now() };

      if (cancelled) {
        inFlight = false;
        return;
      }

      setSession(refreshedSession);
      setBooting(false);

      if (mode === "public") {
        if (refreshedSession) {
          router.replace(isAdminSession(refreshedSession) ? "/admin" : "/");
        }
      } else if (!refreshedSession) {
        router.replace("/login");
      } else if (requireAdmin && !isAdminSession(refreshedSession)) {
        router.replace(fallbackPath);
      }

      inFlight = false;
    };

    syncSession();

    return () => {
      cancelled = true;
    };
  }, [mode, router]);

  return { session, setSession, booting, setBooting };
}
