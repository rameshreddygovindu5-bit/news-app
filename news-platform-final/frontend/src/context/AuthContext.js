import React, { createContext, useContext, useState } from 'react';
import * as api from '../services/api';

export const AuthContext = createContext(null);

export const useAuthCtx = () => useContext(AuthContext);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem('user'));
    } catch {
      return null;
    }
  });
  const [token, setToken] = useState(() => localStorage.getItem('token'));

  const doLogin = async (username, password) => {
    const r = await api.login(username, password);
    const { access_token, username: u, role } = r.data;
    localStorage.setItem('token', access_token);
    localStorage.setItem('user', JSON.stringify({ username: u, role }));
    setToken(access_token);
    setUser({ username: u, role });
  };

  const doLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setToken(null);
    setUser(null);
  };

  const value = {
    user,
    token,
    doLogin,
    doLogout,
    isAuthenticated: !!token,
    isAdmin: user?.role === 'admin'
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}
