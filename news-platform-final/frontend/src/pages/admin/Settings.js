import React, { useState, useEffect } from 'react';
import * as api from '../../services/api';
import { useToast } from '../../hooks/useToast';
import { IC } from '../../components/common/Icons';
import { FlagBadge } from '../../components/common/Badges';

export default function SettingsPage() {
  const [cfg, setCfg] = useState(null);
  const [ld, setLd] = useState(true);
  const { show, ToastContainer } = useToast();

  useEffect(() => {
    api.getSchedulerConfig().then(r => {
      setCfg(r.data);
      setLd(false);
    }).catch(() => setLd(false));
  }, []);

  const trig = async (a, l) => {
    try {
      const r = await api.triggerAction(a);
      show(r.data?.message || `${l} triggered`);
    } catch (e) {
      show(e.response?.data?.detail || 'Failed', 'error');
    }
  };

  if (ld) return <div className="loading"><div className="spinner" /></div>;

  return (
    <div>
      <ToastContainer />
      <div className="page-header"><h2>Platform Settings</h2></div>
      <div className="grid-2">
        <div className="card"><div className="card-header"><h3>AI Configuration</h3></div>
          <div style={{ fontSize: 13, lineHeight: 2, padding: '0 4px' }}>
            <div><strong>Provider Chain:</strong> {cfg?.ai_provider_chain?.join(' → ') || 'Not set'}</div>
            <div><strong>Batch Size:</strong> {cfg?.ai_batch_size}</div>
            <div><strong>Workers:</strong> {cfg?.ai_concurrency}</div>
          </div>
        </div>
        <div className="card"><div className="card-header"><h3>Article Flow</h3></div>
          <div style={{ display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap', padding: '8px 0' }}>
            {[{ f: 'P', l: 'Pending' }, { f: 'N', l: 'New' }, { f: 'A', l: 'AI Done' }, { f: 'Y', l: 'Top News' }].map((s, i) => (
              <React.Fragment key={s.f}><div style={{ textAlign: 'center', padding: 8, background: 'var(--bg-input)', borderRadius: 6, minWidth: 72 }}><FlagBadge flag={s.f} /><div style={{ fontSize: 10, marginTop: 4, color: 'var(--text-muted)' }}>{s.l}</div></div>{i < 3 && <span style={{ color: 'var(--text-muted)', fontSize: 18 }}>→</span>}</React.Fragment>
            ))}
          </div>
          <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 8 }}>Reporters submit (P) → Admin approves (N) → AI processes (A) → Rank selects Top 100 (Y)</p>
        </div>
      </div>
      <div className="card" style={{ marginTop: 16 }}>
        <div className="card-header"><h3>Quick Actions</h3></div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button className="btn btn-india" onClick={() => trig('trigger_pipeline', 'Full Pipeline')}><IC.Play />Full Pipeline</button>
          <button className="btn btn-secondary" onClick={() => trig('trigger_scrape', 'Scrape')}><IC.Globe />Scrape All</button>
          <button className="btn btn-sm" style={{ background: '#6200ea', color: '#fff', border: 'none' }} onClick={() => trig('trigger_ai', 'AI')}><IC.Gear />AI Process</button>
          <button className="btn btn-secondary" onClick={() => trig('trigger_ranking', 'Ranking')}><IC.Star />Update Ranking</button>
          <button className="btn btn-sm" style={{ background: '#FF9900', color: '#fff', border: 'none' }} onClick={() => trig('trigger_sync', 'AWS')}>AWS Delta Sync</button>
          <button className="btn btn-sm" style={{ background: '#E65100', color: '#fff', border: 'none' }} onClick={() => trig('trigger_deep_sync', 'Deep Sync')}>AWS Deep Integrity Check</button>
          <button className="btn btn-sm" style={{ background: '#1877F2', color: '#fff', border: 'none' }} onClick={() => trig('trigger_social', 'Social')}><IC.Social />Post Social</button>
          <button className="btn btn-danger" onClick={() => trig('trigger_cleanup', 'Cleanup')}>Cleanup Old</button>
        </div>
      </div>
    </div>
  );
}
