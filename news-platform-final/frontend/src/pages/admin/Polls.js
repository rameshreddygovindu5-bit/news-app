import React, { useState, useEffect, useCallback } from 'react';
import * as api from '../../services/api';
import { useToast } from '../../hooks/useToast';
import { IC } from '../../components/common/Icons';

export default function PollsManagementPage() {
  const [polls, setPolls] = useState([]);
  const [ld, setLd] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const { show, ToastContainer } = useToast();

  const load = useCallback(() => {
    setLd(true);
    api.getPolls().then(r => {
      setPolls(r.data);
      setLd(false);
    }).catch(() => setLd(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  return (
    <div>
      <ToastContainer />
      <div className="page-header">
        <h2>Polls Management <span style={{ fontSize: 14, color: 'var(--text-muted)', fontWeight: 400 }}>({polls.length})</span></h2>
        <button className="btn btn-india" onClick={() => setShowCreate(true)}><IC.Plus />Create Poll</button>
      </div>

      {ld ? <div className="loading"><div className="spinner" /></div> : (
        <div className="grid-2">
          {polls.map(p => (
            <div key={p.id} className="card">
              <div className="card-header">
                <h3>{p.question}</h3>
                <span className={`badge ${p.is_active ? 'badge-enabled' : 'badge-disabled'}`}>
                  {p.is_active ? 'ACTIVE' : 'EXPIRED'}
                </span>
              </div>
              <div style={{ padding: 16 }}>
                <div className="space-y-2">
                  {p.options.map(o => (
                    <div key={o.id} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, background: 'var(--bg-input)', padding: '8px 12px', borderRadius: 6 }}>
                      <span style={{ fontWeight: 600 }}>{o.option_text}</span>
                      <span style={{ color: 'var(--accent)', fontFamily: 'var(--mono)' }}>{o.votes_count} votes</span>
                    </div>
                  ))}
                </div>
                <div style={{ marginTop: 16, fontSize: 11, color: 'var(--text-muted)' }}>
                  Created: {new Date(p.created_at).toLocaleDateString()}
                </div>
              </div>
            </div>
          ))}
          {polls.length === 0 && <div className="empty-state">No polls created yet</div>}
        </div>
      )}

      {showCreate && <CreatePollModal onClose={() => setShowCreate(false)} onDone={() => { setShowCreate(false); show('Poll created ✓'); load(); }} />}
    </div>
  );
}

function CreatePollModal({ onClose, onDone }) {
  const [q, setQ] = useState('');
  const [opts, setOpts] = useState(['', '']);
  const [sv, setSv] = useState(false);

  const go = async () => {
    if (!q || opts.some(o => !o)) return;
    setSv(true);
    try {
      await api.createPoll({
        question: q,
        options: opts.map(o => ({ option_text: o })),
        is_active: true
      });
      onDone();
    } catch { setSv(false); alert('Failed to create poll'); }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <h3>Create New Poll</h3>
        <div className="form-group">
          <label>Question *</label>
          <input className="form-input" value={q} onChange={e => setQ(e.target.value)} placeholder="e.g. Which party will win?" />
        </div>
        <div className="form-group">
          <label>Options *</label>
          <div className="space-y-2">
            {opts.map((o, i) => (
              <div key={i} style={{ display: 'flex', gap: 8 }}>
                <input className="form-input" value={o} onChange={e => {
                  const n = [...opts];
                  n[i] = e.target.value;
                  setOpts(n);
                }} placeholder={`Option ${i + 1}`} />
                {opts.length > 2 && (
                  <button className="btn btn-secondary btn-sm" onClick={() => setOpts(opts.filter((_, idx) => idx !== i))}>✕</button>
                )}
              </div>
            ))}
          </div>
          <button className="btn btn-secondary btn-sm" style={{ marginTop: 8 }} onClick={() => setOpts([...opts, ''])}>+ Add Option</button>
        </div>
        <div className="modal-actions">
          <button className="btn btn-secondary" onClick={onClose}>Cancel</button>
          <button className="btn btn-india" onClick={go} disabled={sv}>
            {sv ? 'Creating…' : 'Create Poll'}
          </button>
        </div>
      </div>
    </div>
  );
}
