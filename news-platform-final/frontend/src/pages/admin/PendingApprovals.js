import React, { useState, useEffect } from 'react';
import * as api from '../../services/api';
import { useToast } from '../../hooks/useToast';
import { IC } from '../../components/common/Icons';
import ArticleDetailModal from '../../components/modals/ArticleDetailModal';

export default function PendingApprovalsPage() {
  const [articles, setArticles] = useState([]);
  const [total, setTotal] = useState(0);
  const [ld, setLd] = useState(true);
  const [viewA, setViewA] = useState(null);
  const [sel, setSel] = useState([]);
  const { show, ToastContainer } = useToast();

  const load = () => {
    setLd(true);
    api.getPendingArticles({ page: 1, page_size: 50 })
      .then(r => {
        setArticles(r.data.articles);
        setTotal(r.data.total);
        setSel([]);
        setLd(false);
      })
      .catch(() => setLd(false));
  };

  useEffect(() => { load() }, []);

  const doApprove = async (id, action) => {
    try {
      await api.approveArticle(id, action);
      show(`Article ${action}d ✓`);
      load();
    } catch (e) {
      show(e.response?.data?.detail || 'Failed', 'error');
    }
  };

  const bulkApprove = async (action) => {
    if (!sel.length) return;
    try {
      await api.bulkApproveArticles(sel, action);
      show(`${sel.length} articles ${action}d ✓`);
      load();
    } catch { show('Bulk action failed', 'error'); }
  };

  const toggleSel = (id) => {
    setSel(p => p.includes(id) ? p.filter(x => x !== id) : [...p, id]);
  };
  const toggleAll = () => {
    setSel(sel.length === articles.length ? [] : articles.map(a => a.id));
  };

  return (
    <div>
      <ToastContainer />
      <div className="page-header">
        <h2>Pending Approval <span style={{ fontSize: 14, color: 'var(--india-saffron)', fontWeight: 400 }}>({total})</span></h2>
        <button className="btn btn-secondary" onClick={load}><IC.Ref />Refresh</button>
      </div>

      {sel.length > 0 && (
        <div className="card" style={{ marginBottom: 12, padding: '10px 16px', background: 'var(--accent-dim)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', animation: 'slideIn .2s' }}>
          <div style={{ fontWeight: 600, color: 'var(--accent)' }}>{sel.length} items selected</div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="btn btn-sm btn-success" onClick={() => bulkApprove('approve')}>Approve All</button>
            <button className="btn btn-sm btn-primary" onClick={() => bulkApprove('approve_direct')}>Pub Direct</button>
            <button className="btn btn-sm btn-danger" onClick={() => bulkApprove('reject')}>Reject All</button>
            <button className="btn btn-sm btn-secondary" onClick={() => setSel([])}>Cancel</button>
          </div>
        </div>
      )}
      
      {ld ? <div className="loading"><div className="spinner" /></div> : articles.length === 0 ?
        <div className="card" style={{ textAlign: 'center', padding: 60, color: 'var(--text-muted)' }}><IC.Check /><p style={{ marginTop: 12 }}>No articles pending approval</p></div> :
        <div className="table-container">
          <table className="table">
            <thead><tr>
              <th style={{ width: 40 }}><input type="checkbox" checked={sel.length > 0 && sel.length === articles.length} onChange={toggleAll} /></th>
              <th>ID</th><th>Title</th><th>Category</th><th>By</th><th>Date</th><th>Actions</th>
            </tr></thead>
            <tbody>{articles.map(a => (
              <tr key={a.id} className={sel.includes(a.id) ? 'row-selected' : ''}>
                <td><input type="checkbox" checked={sel.includes(a.id)} onChange={() => toggleSel(a.id)} /></td>
                <td style={{ fontFamily: 'var(--mono)', fontSize: 11 }}>{a.id}</td>
                <td><div style={{ fontWeight: 500, cursor: 'pointer' }} onClick={() => setViewA(a)}>{a.original_title}</div><div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>{a.original_content?.slice(0, 100)}…</div></td>
                <td>{a.category || '—'}</td>
                <td><span className="badge badge-new">{a.submitted_by || '—'}</span></td>
                <td style={{ fontFamily: 'var(--mono)', fontSize: 10 }}>{a.created_at ? new Date(a.created_at).toLocaleString() : '—'}</td>
                <td><div className="btn-group">
                  <button className="btn btn-success btn-sm" onClick={() => doApprove(a.id, 'approve')}>Approve</button>
                  <button className="btn btn-primary btn-sm" onClick={() => doApprove(a.id, 'approve_direct')}>Direct Pub</button>
                  <button className="btn btn-danger btn-sm" onClick={() => doApprove(a.id, 'reject')}>Reject</button>
                  <button className="btn btn-secondary btn-sm" onClick={() => setViewA(a)}><IC.Eye /></button>
                </div></td>
              </tr>
            ))}</tbody>
          </table>
        </div>}
      {viewA && <ArticleDetailModal article={viewA} onClose={() => setViewA(null)} />}
    </div>
  );
}
