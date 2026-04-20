import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Sidebar } from '../components/common/Sidebar';
import { useAuthCtx } from '../context/AuthContext';

// Admin Pages
import DashboardPage from '../pages/admin/Dashboard';
import ArticlesPage from '../pages/admin/Articles';
import PendingApprovalsPage from '../pages/admin/PendingApprovals';
import SourcesPage from '../pages/admin/Sources';
import TopNewsPage from '../pages/admin/TopNews';
import CategoriesPage from '../pages/admin/Categories';
import YouTubePage from '../pages/admin/YouTube';
import SchedulerPage from '../pages/admin/Scheduler';
import UsersPage from '../pages/admin/Users';
import PollsPage from '../pages/admin/Polls';
import SurveysPage from '../pages/admin/Surveys';
import WishesPage from '../pages/admin/Wishes';
import SettingsPage from '../pages/admin/Settings';

// Reporter Pages
import ReporterSubmitPage from '../pages/reporter/Submit';
import MySubmissionsPage from '../pages/reporter/MySubmissions';

export function AdminShell() {
  const { doLogout } = useAuthCtx();
  return (
    <div className="app-layout">
      <Sidebar onLogout={doLogout} />
      <div className="main-content">
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/articles" element={<ArticlesPage />} />
          <Route path="/pending" element={<PendingApprovalsPage />} />
          <Route path="/sources" element={<SourcesPage />} />
          <Route path="/top-news" element={<TopNewsPage />} />
          <Route path="/categories" element={<CategoriesPage />} />
          <Route path="/youtube" element={<YouTubePage />} />
          <Route path="/scheduler" element={<SchedulerPage />} />
          <Route path="/users" element={<UsersPage />} />
          <Route path="/polls" element={<PollsPage />} />
          <Route path="/surveys" element={<SurveysPage />} />
          <Route path="/wishes" element={<WishesPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </div>
    </div>
  );
}

export function ReporterShell() {
  const { doLogout } = useAuthCtx();
  return (
    <div className="app-layout">
      <Sidebar onLogout={doLogout} />
      <div className="main-content">
        <Routes>
          <Route path="/" element={<ReporterSubmitPage />} />
          <Route path="/my-submissions" element={<MySubmissionsPage />} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </div>
    </div>
  );
}
