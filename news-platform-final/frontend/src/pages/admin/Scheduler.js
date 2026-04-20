import React, { useState, useEffect, useCallback } from 'react';
import * as api from '../../services/api';
import { useToast } from '../../hooks/useToast';
import { IC } from '../../components/common/Icons';
import { StatusBadge } from '../../components/common/Badges';

export default function SchedulerPage() {
  const [logs, setLogs] = useState([]);
  const [ld, setLd] = useState(true);
  const [cfg, setCfg] = useState(null);
  const [running, setRunning] = useState(false);
  const [srcErrors, setSrcErrors] = useState([]);
  const [postErrors, setPostErrors] = useState([]);
  const [exp, setExp] = useState(null); // Expanded log ID
  const { show, ToastContainer } = useToast();

  const loadLogs = useCallback(() => {
    setLd(true);
    api.getSchedulerLogs({ limit: 60 }).then(r => {
      setLogs(r.data);
      setLd(false);
    }).catch(() => setLd(false));
    api.getSourceErrors({ limit: 10 }).then(r => setSrcErrors(r.data)).catch(() => { });
    api.getPostErrors({ limit: 10 }).then(r => setPostErrors(r.data)).catch(() => { });
  }, []);

  useEffect(() => {
    loadLogs();
    api.getSchedulerConfig().then(r => setCfg(r.data)).catch(() => { });
    const t = setInterval(loadLogs, 15000);
    return () => clearInterval(t);
  }, [loadLogs]);

  const trig = async (action, label) => {
    setRunning(true);
    try {
      const r = await api.triggerAction(action);
      show(r.data?.message || `${label} triggered`);
    } catch (e) {
      show(e.response?.data?.detail || `${label} failed`, 'error');
    }
    setRunning(false);
    setTimeout(loadLogs, 2000);
  };

  const toggleFlag = async (field) => {
    if (!cfg) return;
    const v = !cfg[field];
    try {
      await api.updateSchedulerConfig({ [field]: v });
      setCfg(p => ({ ...p, [field]: v }));
      show(`${field} → ${v ? 'ON' : 'OFF'}`);
    } catch {
      show('Failed', 'error');
    }
  };

  return (
    <div>
      <ToastContainer />
      <div className="page-header">
        <h2>Scheduler & Pipeline</h2>
        <div className="btn-group" style={{ flexWrap: 'wrap', gap: 6 }}>
          <button className="btn btn-india btn-sm" disabled={running} onClick={() => trig('trigger_pipeline', 'Full Pipeline')}><IC.Play />{running ? 'Running…' : 'Full Pipeline'}</button>
          <button className="btn btn-secondary btn-sm" onClick={() => trig('trigger_scrape', 'Scrape')}><IC.Globe />Scrape</button>
          <button className="btn btn-sm" style={{ background: '#6200ea', color: '#fff', border: 'none' }} onClick={() => trig('trigger_ai', 'AI')}><IC.Gear />AI</button>
          <button className="btn btn-secondary btn-sm" onClick={() => trig('trigger_ranking', 'Rank')}><IC.Star />Rank</button>
          <button className="btn btn-sm" style={{ background: '#FF9900', color: '#fff', border: 'none' }} onClick={() => trig('trigger_sync', 'AWS')}><IC.AWS />AWS</button>
          <button className="btn btn-sm" style={{ background: '#1877F2', color: '#fff', border: 'none' }} onClick={() => trig('trigger_social', 'Social')}><IC.Social />Social</button>
          <button className="btn btn-secondary btn-sm" onClick={() => trig('trigger_cleanup', 'Cleanup')}>Cleanup</button>
          <button className="btn btn-secondary btn-sm" onClick={loadLogs}><IC.Ref /></button>
        </div>
      </div>

      {cfg && (
        <div className="card" style={{ marginBottom: 16 }}>
          <div className="card-header"><h3>Schedule Config</h3></div>
          <div className="table-container"><table className="table">
            <thead><tr><th>Job</th><th>Status</th><th>Minutes</th><th>Toggle</th></tr></thead>
            <tbody>{[
              { l: 'Scrape', f: 'scrape_enabled', m: 'scrape_minutes' },
              { l: 'AI Enrichment', f: 'ai_enabled', m: 'ai_minutes' },
              { l: 'Top-100 Ranking', f: 'ranking_enabled', m: 'ranking_minutes' },
              { l: 'AWS Sync', f: 'aws_sync_enabled', m: 'aws_sync_minutes' },
              { l: 'Category Counts', f: 'category_count_enabled', f_minutes: 'category_minutes' }, // fix key
              { l: 'Cleanup', f: 'cleanup_enabled', m: 'cleanup_minutes' },
              { l: 'Social Posting', f: 'social_enabled', m: 'social_minutes' },
            ].map(j => (
              <tr key={j.f}>
                <td style={{ fontWeight: 600 }}>{j.l}</td>
                <td><span className={`badge ${cfg[j.f] ? 'badge-enabled' : 'badge-disabled'}`}>{cfg[j.f] ? 'ON' : 'OFF'}</span></td>
                <td style={{ fontFamily: 'var(--mono)', fontSize: 12 }}>:{cfg[j.m || j.f_minutes]}</td>
                <td><button className={`btn btn-sm ${cfg[j.f] ? 'btn-danger' : 'btn-success'}`} onClick={() => toggleFlag(j.f)}>{cfg[j.f] ? 'Disable' : 'Enable'}</button></td>
              </tr>
            ))}</tbody>
          </table></div>
        </div>
      )}

      <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8 }}>Auto-refreshes every 15s</div>
      {ld && logs.length === 0 ? <div className="loading"><div className="spinner" /></div> :
        <div className="table-container shadow-sm"><table className="table">
          <thead><tr><th>ID</th><th>Job</th><th>Status</th><th>OK</th><th>ERR</th><th>Duration</th><th>Action</th></tr></thead>
          <tbody>{logs.map(l => (
            <React.Fragment key={l.id}>
              <tr>
                <td style={{ fontFamily: 'var(--mono)', fontSize: 11 }}>{l.id}</td>
                <td style={{ fontWeight: 600, fontSize: 12 }}>{l.job_name}</td>
                <td><StatusBadge status={l.status} /></td>
                <td style={{ color: 'var(--india-green)', fontWeight: 600 }}>{l.rows_ok}</td>
                <td style={{ color: l.rows_err > 0 ? 'var(--india-red)' : 'var(--text-muted)' }}>{l.rows_err}</td>
                <td style={{ fontFamily: 'var(--mono)', fontSize: 11 }}>{l.duration_s ? (l.duration_s.toFixed(1) + 's') : '—'}</td>
                <td><button className="btn btn-sm btn-secondary" onClick={() => setExp(exp === l.id ? null : l.id)}>{exp === l.id ? 'Hide' : 'View'}</button></td>
              </tr>
              {exp === l.id && (
                <tr><td colSpan="7" style={{ background: 'var(--bg-input)', padding: 12 }}>
                  <div style={{ fontSize: 11, marginBottom: 4, color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>Execution Details</div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 8 }}>
                    <div><span style={{ color: 'var(--text-muted)' }}>Triggered By:</span> {l.triggered_by || 'cron'}</div>
                    <div><span style={{ color: 'var(--text-muted)' }}>Started:</span> {new Date(l.started_at).toLocaleString()}</div>
                  </div>
                  {l.error_summary && (
                    <div style={{ background: '#fff1f0', padding: 10, borderRadius: 6, border: '1px solid #ffa39e', color: '#cf1322', fontSize: 12, fontFamily: 'var(--mono)', whiteSpace: 'pre-wrap' }}>
                      <strong>Error Summary:</strong><br />{l.error_summary}
                    </div>
                  )}
                  {!l.error_summary && l.status === 'DONE' && <div style={{ color: 'var(--india-green)', fontSize: 12 }}>Job completed successfully with no errors.</div>}
                </td></tr>
              )}
            </React.Fragment>
          ))}
          {logs.length === 0 && <tr><td colSpan="7" className="empty-state">No logs yet</td></tr>}
          </tbody>
        </table></div>}

      <div className="grid-2" style={{ marginTop: 24 }}>
        <div className="card">
          <div className="card-header"><h3 style={{ color: 'var(--india-red)' }}>Recent Scraper Failures</h3></div>
          <div className="table-container" style={{ maxHeight: 300, overflowY: 'auto' }}>
            <table className="table">
              <thead><tr><th>Source ID</th><th>Error</th><th>Time</th></tr></thead>
              <tbody>
                {srcErrors.map(e => (
                  <tr key={e.id}>
                    <td>{e.source_id}</td>
                    <td style={{ fontSize: 11, maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis' }} title={e.error_message}>{e.error_message}</td>
                    <td style={{ fontSize: 10 }}>{new Date(e.created_at).toLocaleTimeString()}</td>
                  </tr>
                ))}
                {srcErrors.length === 0 && <tr><td colSpan="3" style={{ textAlign: 'center', padding: 20, color: 'var(--text-muted)' }}>No recent failures</td></tr>}
              </tbody>
            </table>
          </div>
        </div>

        <div className="card">
          <div className="card-header"><h3 style={{ color: 'var(--india-saffron)' }}>Social Media Issues</h3></div>
          <div className="table-container" style={{ maxHeight: 300, overflowY: 'auto' }}>
            <table className="table">
              <thead><tr><th>Platform</th><th>Msg</th><th>Time</th></tr></thead>
              <tbody>
                {postErrors.map(e => (
                  <tr key={e.id}>
                    <td><span className="badge badge-paused">{e.platform.toUpperCase()}</span></td>
                    <td style={{ fontSize: 11, maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis' }} title={e.error_message}>{e.error_message}</td>
                    <td style={{ fontSize: 10 }}>{new Date(e.created_at).toLocaleTimeString()}</td>
                  </tr>
                ))}
                {postErrors.length === 0 && <tr><td colSpan="3" style={{ textAlign: 'center', padding: 20, color: 'var(--text-muted)' }}>No recent issues</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
