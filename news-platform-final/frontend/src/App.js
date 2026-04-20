import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider, useAuthCtx } from './context/AuthContext';
import LoginPage from './pages/auth/Login';
import { AdminShell, ReporterShell } from './layouts/Shells';
import './styles/index.css';

function AppContent() {
  const { isAuthenticated, isAdmin } = useAuthCtx();

  if (!isAuthenticated) {
    return (
      <Routes>
        <Route path="*" element={<LoginPage />} />
      </Routes>
    );
  }

  return isAdmin ? <AdminShell /> : <ReporterShell />;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter basename={process.env.PUBLIC_URL || ''}>
        <AppContent />
      </BrowserRouter>
    </AuthProvider>
  );
}
