import React, { useState, useEffect, useCallback } from 'react';
import * as api from '../../services/api';
import { FlagBadge } from '../../components/common/Badges';

export default function MySubmissionsPage() {
  const [articles, setArticles] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [tp, setTp] = useState(1);
  const [ld, setLd] = useState(true);

  const load = useCallback(() => {
    setLd(true);
    api.getMySubmissions({ page, page_size: 20 }).then(r => {
      setArticles(r.data.articles);
      setTotal(r.data.total);
      setTp(Math.ceil(r.data.total / 20));
      setLd(false);
    }).catch(() => setLd(false))
  }, [page]);

  useEffect(() => { load() }, [load]);

  return (
    <div>
      <div className="page-header"><h2>My Submissions <span style={{ fontSize: 14, color: 'var(--text-muted)', fontWeight: 400 }}>({total})</span></h2></div>
      {ld ? <div className="loading"><div className="spinner" /></div> :
        <div className="table-container"><table className="table">
          <thead><tr><th>ID</th><th>Title</th><th>Category</th><th>Status</th><th>Submitted</th></tr></thead>
          <tbody>
            {articles.map(a => <tr key={a.id}><td style={{ fontFamily: 'var(--mono)', fontSize: 11 }}>{a.id}</td><td style={{ fontWeight: 500 }}>{a.original_title}</td><td>{a.category || '—'}</td><td><FlagBadge flag={a.flag} /></td><td style={{ fontFamily: 'var(--mono)', fontSize: 10 }}>{a.created_at ? new Date(a.created_at).toLocaleString() : '—'}</td></tr>)}
            {articles.length === 0 && <tr><td colSpan="5" className="empty-state">No submissions yet</td></tr>}
          </tbody>
        </table></div>}
      {tp > 1 && <div className="pagination"><button disabled={page <= 1} onClick={() => setPage(p => p - 1)}>← Prev</button><span>{page}/{tp}</span><button disabled={page >= tp} onClick={() => setPage(p => p + 1)}>Next →</button></div>}
    </div>
  );
}
