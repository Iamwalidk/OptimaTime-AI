import { useCallback, useEffect, useState } from "react";
import { login, setAuthHandlers, setAuthToken, signupOrLogin } from "../api";

export function useAuth({ onSessionExpired, showToast }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [authLoading, setAuthLoading] = useState(false);

  useEffect(() => {
    setAuthHandlers({
      onRefresh: (data) => {
        setAuthToken(data.access_token);
        setToken(data.access_token);
        setUser(data.user);
      },
      onAuthFailure: () => {
        setAuthToken(null);
        setToken(null);
        setUser(null);
        onSessionExpired?.();
        showToast?.("Session expired. Please log in again.", "error");
      },
    });

    return () =>
      setAuthHandlers({
        onRefresh: null,
        onAuthFailure: null,
      });
  }, [onSessionExpired, showToast]);

  const handleAuth = useCallback(
    async ({ email, name, profile, password, mode }) => {
      setAuthLoading(true);
      try {
        const res =
          mode === "login"
            ? await login({ email, password })
            : await signupOrLogin({ email, name, profile, password });
        setAuthToken(res.access_token);
        setToken(res.access_token);
        setUser(res.user);
        showToast?.(mode === "login" ? "Logged in." : "Welcome to OptimaTime AI.", "success");
      } catch (err) {
        console.error("Auth failed", err);
        showToast?.(
          err?.response?.data?.detail || err?.message || "Unable to sign up/login. Please try again.",
          "error"
        );
        throw err;
      } finally {
        setAuthLoading(false);
      }
    },
    [showToast]
  );

  const logout = useCallback(() => {
    setAuthToken(null);
    setToken(null);
    setUser(null);
    onSessionExpired?.();
  }, [onSessionExpired]);

  return { user, token, authLoading, handleAuth, logout };
}
