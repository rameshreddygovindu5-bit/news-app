import React, { useState, useEffect } from 'react';
import * as api from '../../services/api';
import { useToast } from '../../hooks/useToast';
import { IC } from '../../components/common/Icons';

export default function SourcesPage() {
  const [src, setSrc] = useState([]);
  const [ld, setLd] = useState(true);
  const [show, setShow] = useState(false);
  const { show: showToast, ToastContainer } = useToast();

  const load = () => {
    setLd(true);
    api.getSources().then(r => {
      setSrc(r.data);
      setLd(false);
    }).catch(() => setLd(false));
  };

  useEffect(() => { load() }, []);

  const runScrape = async (id, name) => {
    try {
      await api.triggerAction('trigger_scrape', id);
      showToast(`Scraping ${name}…`);
    } catch (e) {
      showToast('Failed', 'error');
    }
  };

  return (
    <div>
      <ToastContainer />
      <div className="page-header">
        <h2>Sources ({src.length})</h2>
        <button className="btn btn-india" onClick={() => setShow(true)}><IC.Plus />Add Source</button>
      </div>
      
      {ld ? <div className="loading"><div className="spinner" /></div> :
        <div className="table-container">
          <table className="table">
            <thead><tr><th>Name</th><th>Type</th><th>Language</th><th>Interval</th><th>Status</th><th>Last Scraped</th><th>Actions</th></tr></thead>
            <tbody>{src.map(s => (
              <tr key={s.id}>
                <td style={{ fontWeight: 600 }}>{s.name}</td>
                <td style={{ fontFamily: 'var(--mono)', fontSize: 11 }}>{s.scraper_type}</td>
                <td><span className="badge badge-new">{s.language?.toUpperCase() || 'EN'}</span></td>
                <td style={{ fontSize: 12 }}>{s.scrape_interval_minutes}m</td>
                <td>{s.is_paused ? <span className="badge badge-paused">PAUSED</span> : s.is_enabled ? <span className="badge badge-enabled">ACTIVE</span> : <span className="badge badge-disabled">OFF</span>}</td>
                <td style={{ fontFamily: 'var(--mono)', fontSize: 10 }}>{s.last_scraped_at ? new Date(s.last_scraped_at).toLocaleString() : 'Never'}</td>
                <td><div className="btn-group">
                  <button className="btn btn-secondary btn-sm" title="Scrape now" onClick={() => runScrape(s.id, s.name)}><IC.Play /></button>
                  <button className="btn btn-secondary btn-sm" onClick={async () => { await api.togglePause(s.id); load() }}>{s.is_paused ? 'Resume' : 'Pause'}</button>
                  <button className="btn btn-secondary btn-sm" onClick={async () => { await api.toggleEnable(s.id); load() }}>{s.is_enabled ? 'Off' : 'On'}</button>
                </div></td>
              </tr>
            ))}
            {src.length === 0 && <tr><td colSpan="7" className="empty-state">No sources configured</td></tr>}
            </tbody>
          </table>
        </div>}
      {show && <SrcModal onClose={() => setShow(false)} onDone={() => { setShow(false); showToast('Source added ✓'); load() }} />}
    </div>
  );
}

function SrcModal({ onClose, onDone }) {
  const [f, setF] = useState({ name: '', url: '', language: 'en', scraper_type: 'rss', scrape_interval_minutes: 60, scraper_config: '{}', credibility_score: 0.7, priority: 0 });
  const [sv, setSv] = useState(false);

  const go = async () => {
    if (!f.name || !f.url) return;
    setSv(true);
    try {
      let c = {};
      try { c = JSON.parse(f.scraper_config) } catch { }
      await api.createSource({ ...f, scraper_config: c, scrape_interval_minutes: parseInt(f.scrape_interval_minutes), credibility_score: parseFloat(f.credibility_score), priority: parseInt(f.priority) });
      onDone()
    } catch (e) {
      setSv(false);
      alert(e.response?.data?.detail || 'Failed')
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}><div className="modal" onClick={e => e.stopPropagation()}>
      <h3>Add Source</h3>
      <div className="grid-2">
        <div className="form-group"><label>Name *</label><input className="form-input" value={f.name} onChange={e => setF({ ...f, name: e.target.value })} /></div>
        <div className="form-group"><label>URL *</label><input className="form-input" value={f.url} onChange={e => setF({ ...f, url: e.target.value })} /></div>
      </div>
      <div className="grid-2">
        <div className="form-group"><label>Language</label><select className="form-select" value={f.language} onChange={e => setF({ ...f, language: e.target.value })}><option value="en">English</option><option value="te">Telugu</option><option value="hi">Hindi</option></select></div>
        <div className="form-group"><label>Scraper Type</label><select className="form-select" value={f.scraper_type} onChange={e => setF({ ...f, scraper_type: e.target.value })}><option value="rss">RSS</option><option value="html">HTML</option><option value="greatandhra">GreatAndhra</option><option value="cnn">CNN</option><option value="manual">Manual</option></select></div>
      </div>
      <div className="grid-2">
        <div className="form-group"><label>Credibility (0–1)</label><input className="form-input" type="number" min="0" max="1" step="0.1" value={f.credibility_score} onChange={e => setF({ ...f, credibility_score: e.target.value })} /></div>
        <div className="form-group"><label>Priority</label><input className="form-input" type="number" value={f.priority} onChange={e => setF({ ...f, priority: e.target.value })} /></div>
      </div>
      <div className="form-group"><label>Config JSON</label><textarea className="form-textarea" style={{ fontFamily: 'var(--mono)', fontSize: 12 }} rows={3} value={f.scraper_config} onChange={e => setF({ ...f, scraper_config: e.target.value })} /></div>
      <div className="modal-actions"><button className="btn btn-secondary" onClick={onClose}>Cancel</button><button className="btn btn-india" onClick={go} disabled={sv}>{sv ? 'Adding…' : 'Add Source'}</button></div>
    </div></div>
  );
}
