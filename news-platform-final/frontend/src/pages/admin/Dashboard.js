import React, { useState, useEffect, useCallback } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import * as api from '../../services/api';
import { useToast } from '../../hooks/useToast';
import { IC } from '../../components/common/Icons';
import { StatusBadge } from '../../components/common/Badges';

export default function DashboardPage() {
  const [s, setS] = useState(null);
  const [ld, setLd] = useState(true);
  const { show, ToastContainer } = useToast();

  const load = useCallback(() => {
    setLd(true);
    api.getDashboardStats().then(r => {
      setS(r.data);
      setLd(false);
    }).catch(() => setLd(false));
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(load, 30000);
    return () => clearInterval(t);
  }, [load]);

  const trigger = async (action, label) => {
    try {
      const r = await api.triggerAction(action);
      show(r.data?.message || `${label} triggered`);
    } catch (e) {
      show(e.response?.data?.detail || `${label} failed`, 'error');
    }
  };

  if (ld && !s) return <div className="loading"><div className="spinner" />Loading dashboard…</div>;
  if (!s) return <div className="empty-state"><p>Failed to load dashboard</p><button className="btn btn-secondary" onClick={load}><IC.Ref />Retry</button></div>;

  const CL = ['#FF9933', '#138808', '#000080', '#D32F2F', '#1565C0', '#7B1FA2', '#00695C', '#AD1457'];

  return (
    <div>
      <ToastContainer />
      <div className="page-header">
        <h2>Dashboard</h2>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <span className={`badge ${s.aws?.status === 'online' ? 'badge-enabled' : 'badge-paused'}`} style={{ padding: '8px 14px', fontSize: 12 }}>
            AWS: {s.aws?.status?.toUpperCase() || 'OFFLINE'}
          </span>
          <button className="btn btn-sm btn-secondary" onClick={load}><IC.Ref />Refresh</button>
        </div>
      </div>

      <div className="card" style={{ marginBottom: 20, padding: '12px 16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: 1 }}>Quick Pipeline Triggers</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <div style={{ width: 8, height: 8, background: '#4CAF50', borderRadius: '50%', animation: 'pulse 2s infinite' }} />
            <span style={{ fontSize: 10, color: '#4CAF50', fontWeight: 700, letterSpacing: 1 }}>AUTO-SYNC ACTIVE</span>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button className="btn btn-india btn-sm" onClick={() => trigger('trigger_pipeline', 'Full Pipeline')}><IC.Play />Full Pipeline</button>
          <button className="btn btn-secondary btn-sm" onClick={() => trigger('trigger_scrape', 'Scrape')}><IC.Globe />Scrape</button>
          <button className="btn btn-secondary btn-sm" style={{ background: '#6200ea', color: '#fff', border: 'none' }} onClick={() => trigger('trigger_ai', 'AI')}><IC.Gear />AI Process</button>
          <button className="btn btn-secondary btn-sm" onClick={() => trigger('trigger_ranking', 'Ranking')}><IC.Star />Rank</button>
          <button className="btn btn-secondary btn-sm" style={{ background: '#FF9900', color: '#fff', border: 'none' }} onClick={() => trigger('trigger_sync', 'AWS Sync')}><IC.AWS />AWS Sync</button>
          <button className="btn btn-secondary btn-sm" style={{ background: '#1877F2', color: '#fff', border: 'none' }} onClick={() => trigger('trigger_social', 'Social')}><IC.Social />Social Post</button>
          <button className="btn btn-secondary btn-sm" onClick={() => trigger('trigger_categories', 'Category Counts')}>Cats</button>
          <button className="btn btn-secondary btn-sm" style={{ background: 'var(--india-red)', color: '#fff', border: 'none' }} onClick={() => trigger('trigger_cleanup', 'Cleanup')}>Cleanup</button>
        </div>
      </div>

      <div className="grid-2" style={{ marginBottom: 20 }}>
        <div className="card">
          <div className="card-header"><h3 style={{ color: 'var(--india-saffron)' }}>Local Engine</h3></div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, padding: 20 }}>
            <div className="stat-card blue"><div className="stat-label">Total Articles</div><div className="stat-value">{(s.local?.total || 0).toLocaleString()}</div></div>
            <div className="stat-card green"><div className="stat-label">AI Processed</div><div className="stat-value">{(s.local?.processed || 0).toLocaleString()}</div></div>
            <div className="stat-card yellow"><div className="stat-label">AI Pending</div><div className="stat-value">{(s.local?.pending_ai || 0).toLocaleString()}</div></div>
            <div className="stat-card purple"><div className="stat-label">Top 100</div><div className="stat-value">{s.local?.top || 0}</div></div>
          </div>
        </div>
        <div className="card">
          <div className="card-header"><h3 style={{ color: 'var(--india-green)' }}>AWS Production</h3></div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, padding: 20 }}>
            <div className="stat-card blue"><div className="stat-label">AWS Total</div><div className="stat-value">{(s.aws?.total || 0).toLocaleString()}</div></div>
            <div className="stat-card green"><div className="stat-label">AWS Processed</div><div className="stat-value">{(s.aws?.processed || 0).toLocaleString()}</div></div>
            <div className="stat-card orange"><div className="stat-label">Sync Gap</div><div className="stat-value">{Math.max(0, (s.local?.total || 0) - (s.aws?.total || 0)).toLocaleString()}</div></div>
            <div className="stat-card purple"><div className="stat-label">AWS Top</div><div className="stat-value">{s.aws?.top || 0}</div></div>
          </div>
        </div>
      </div>

      <div className="grid-2" style={{ marginBottom: 20 }}>
        <div className="card">
          <div className="card-header"><h3>Category Distribution</h3></div>
          <div style={{ height: 280 }}>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={s.category_stats} dataKey="count" nameKey="category" cx="50%" cy="50%" outerRadius={100} label={({ category }) => category} labelLine={false}>
                  {(s.category_stats || []).map((_, i) => <Cell key={i} fill={CL[i % CL.length]} />)}
                </Pie>
                <Tooltip contentStyle={{ background: '#1a2236', border: 'none', borderRadius: 8, color: '#fff' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card">
          <div className="card-header"><h3>Source Distribution</h3></div>
          <div style={{ height: 280, padding: '0 10px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={s.source_stats} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={false} stroke="#2a3246" />
                <XAxis type="number" hide />
                <YAxis dataKey="source" type="category" width={100} tick={{ fill: '#fff', fontSize: 10 }} />
                <Tooltip cursor={{ fill: '#2a3246' }} contentStyle={{ background: '#1a2236', border: 'none', borderRadius: 8, color: '#fff' }} />
                <Bar dataKey="count" fill="var(--india-saffron)" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="grid-2" style={{ marginBottom: 20 }}>
        <div className="card">
          <div className="card-header"><h3>Source Wise News Numbers</h3></div>
          <div className="table-container" style={{ maxHeight: 300, overflowY: 'auto' }}>
            <table className="table">
              <thead><tr><th>Source Channel</th><th style={{ textAlign: 'right' }}>Articles</th></tr></thead>
              <tbody>
                {(s.source_stats || []).map((src, i) => (
                  <tr key={i}>
                    <td style={{ fontWeight: 600 }}>{src.source}</td>
                    <td style={{ textAlign: 'right', color: 'var(--india-green)', fontWeight: 700 }}>{src.count.toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="card">
          <div className="card-header"><h3>Pipeline Health</h3></div>
          <div className="table-container">
            <table className="table">
              <thead><tr><th>Job</th><th>Status</th><th>OK / ERR</th></tr></thead>
              <tbody>
                {(s.recent_jobs || s.recent_scrapes || []).slice(0, 8).map(l => (
                  <tr key={l.id}>
                    <td style={{ fontWeight: 600, fontSize: 12 }}>{l.job_name}</td>
                    <td><StatusBadge status={l.status} /></td>
                    <td style={{ fontSize: 12 }}>
                      <span style={{ color: 'var(--india-green)' }}>{l.rows_ok}</span>
                      <span style={{ color: 'var(--text-muted)' }}> / </span>
                      <span style={{ color: l.rows_err > 0 ? 'var(--india-red)' : 'var(--text-muted)' }}>{l.rows_err}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
