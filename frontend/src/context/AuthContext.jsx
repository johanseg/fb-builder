import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';

const AuthContext = createContext();
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [accessToken, setAccessToken] = useState(() => localStorage.getItem('accessToken'));
  const [refreshToken, setRefreshToken] = useState(() => localStorage.getItem('refreshToken'));
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const refreshPromiseRef = useRef(null);

  const clearAuth = useCallback(() => {
    setUser(null);
    setAccessToken(null);
    setRefreshToken(null);
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
  }, []);

  const persistTokens = useCallback((tokens) => {
    setAccessToken(tokens.access_token);
    localStorage.setItem('accessToken', tokens.access_token);
    if (tokens.refresh_token) {
      setRefreshToken(tokens.refresh_token);
      localStorage.setItem('refreshToken', tokens.refresh_token);
    }
  }, []);

  const fetchUser = useCallback(async (token) => {
    if (!token) throw new Error('No access token available');
    const response = await fetch(`${API_URL}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok) {
      const authError = new Error('Failed to fetch user');
      authError.status = response.status;
      throw authError;
    }
    const data = await response.json();
    setUser(data);
    return data;
  }, []);

  const refreshAccessToken = useCallback(async () => {
    if (refreshPromiseRef.current) return refreshPromiseRef.current;

    const currentRefreshToken = localStorage.getItem('refreshToken') || refreshToken;
    if (!currentRefreshToken) throw new Error('No refresh token');

    refreshPromiseRef.current = (async () => {
      const response = await fetch(`${API_URL}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: currentRefreshToken }),
      });
      if (!response.ok) {
        const refreshError = new Error('Failed to refresh token');
        refreshError.status = response.status;
        if (response.status === 401 || response.status === 403) clearAuth();
        throw refreshError;
      }
      const tokens = await response.json();
      persistTokens(tokens);
      await fetchUser(tokens.access_token);
      return tokens.access_token;
    })().finally(() => {
      refreshPromiseRef.current = null;
    });

    return refreshPromiseRef.current;
  }, [clearAuth, fetchUser, persistTokens, refreshToken]);

  useEffect(() => {
    const initialise = async () => {
      const token = localStorage.getItem('accessToken');
      if (token) {
        try {
          await fetchUser(token);
        } catch {
          try {
            await refreshAccessToken();
          } catch {
            // Network and 5xx failures retain tokens for a later retry.
          }
        }
      }
      setLoading(false);
    };
    initialise();
  }, [fetchUser, refreshAccessToken]);

  const login = useCallback(async (email, password) => {
    setError(null);
    const response = await fetch(`${API_URL}/auth/login/json`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    if (!response.ok) {
      const data = await response.json();
      const loginError = new Error(data.detail || 'Login failed');
      setError(loginError.message);
      throw loginError;
    }
    const tokens = await response.json();
    persistTokens(tokens);
    await fetchUser(tokens.access_token);
    return tokens;
  }, [fetchUser, persistTokens]);

  const logout = useCallback(async () => {
    const currentAccessToken = localStorage.getItem('accessToken') || accessToken;
    const currentRefreshToken = localStorage.getItem('refreshToken') || refreshToken;
    try {
      if (currentAccessToken && currentRefreshToken) {
        await fetch(`${API_URL}/auth/logout`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${currentAccessToken}` },
          body: JSON.stringify({ refresh_token: currentRefreshToken }),
        });
      }
    } finally {
      clearAuth();
    }
  }, [accessToken, clearAuth, refreshToken]);

  const authFetch = useCallback(async (url, options = {}) => {
    const makeRequest = (token) => fetch(url, {
      ...options,
      headers: { ...options.headers, Authorization: `Bearer ${token}` },
    });
    const token = localStorage.getItem('accessToken') || accessToken;
    if (!token) throw new Error('No access token available');
    let response = await makeRequest(token);
    if (response.status === 401) {
      const refreshedToken = await refreshAccessToken();
      response = await makeRequest(refreshedToken);
    }
    return response;
  }, [accessToken, refreshAccessToken]);

  const hasRole = useCallback((roleName) => user?.is_superuser || user?.roles?.some((role) => role.name === roleName) || false, [user]);
  const hasPermission = useCallback((permissionName) => user?.is_superuser || user?.roles?.some(
    (role) => role.permissions?.some((permission) => permission.name === permissionName),
  ) || false, [user]);

  return (
    <AuthContext.Provider value={{
      user, accessToken, refreshToken, loading, error,
      isAuthenticated: Boolean(user), login, logout, refreshAccessToken, authFetch, hasRole, hasPermission,
    }}>
      {children}
    </AuthContext.Provider>
  );
};
