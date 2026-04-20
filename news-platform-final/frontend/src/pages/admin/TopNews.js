import React, { useState, useEffect } from 'react';
import * as api from '../../services/api';
import { useToast } from '../../hooks/useToast';
import { IC } from '../../components/common/Icons';
import { CATS } from '../../constants/news';
import ArticleDetailModal from '../../components/modals/ArticleDetailModal';

export default function TopNewsPage() {
  const [arts, setArts] = useState([]);
  const [ld, setLd] = useState(true);
  const [viewA, setViewA] = useState(null);
  const { show, ToastContainer } = useToast();
  const [catFilter, setCatFilter] = useState('');

  const load = () => {
    setLd(true);
    api.getTopNews(200).then(r => {
      setArts(r.data);
      setLd(false);
    }).catch(() => setLd(false));
  };

  useEffect(() => { load() }, []);

  const rerank = async () => {
    try {
      const r = await api.triggerAction('trigger_ranking');
      show(r.data?.message || 'Ranking triggered');
      setTimeout(load, 3000);
    } catch (e) {
      show('Failed', 'error');
    }
  };

  const filtered = catFilter ? arts.filter(a => a.category === catFilter) : arts;
  const catStats = CATS.map(c => ({ cat: c, count: arts.filter(a => a.category === c).length }));

  return (
    <div>
      <ToastContainer />
      <div className="page-header">
        <h2>Top 100 News <span style={{ fontSize: 14, color: 'var(--text-muted)', fontWeight: 400 }}>({arts.length} total)</span></h2>
        <div className="btn-group">
          <button className="btn btn-india" onClick={rerank}><IC.Ref />Re-rank</button>
          <button className="btn btn-secondary" onClick={load}><IC.Ref />Reload</button>
        </div>
      </div>
      
      <div className="card" style={{ marginBottom: 16, padding: '12px 16px' }}>
        <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 8, fontWeight: 600 }}>CATEGORY COVERAGE</div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button className={`btn btn-sm ${!catFilter ? 'btn-india' : 'btn-secondary'}`} onClick={() => setCatFilter('')}>All ({arts.length})</button>
          {catStats.map(({ cat, count }) => (
            <button key={cat} className={`btn btn-sm ${catFilter === cat ? 'btn-india' : 'btn-secondary'}`} onClick={() => setCatFilter(cat === 'All' ? '' : cat)}
              style={{ borderColor: count < 5 ? 'var(--india-red)' : count < 10 ? 'var(--india-saffron)' : '' }}>
              {cat} ({count}){count < 5 && <span style={{ color: 'var(--india-red)', marginLeft: 4 }}>!</span>}
            </button>
          ))}
        </div>
      </div>

      {ld ? <div className="loading"><div className="spinner" /></div> :
        <div className="table-container">
          <table className="table">
            <thead><tr><th>#</th><th>Title</th><th>Category</th><th>Source</th><th>Score</th><th>Telugu</th></tr></thead>
            <tbody>{filtered.map((a, i) => (
              <tr key={a.id} style={{ cursor: 'pointer' }} onClick={() => setViewA(a)}>
                <td style={{ fontFamily: 'var(--mono)', fontWeight: 700, color: i < 3 ? 'var(--india-saffron)' : i < 10 ? 'var(--india-green)' : 'var(--text-muted)' }}>{i + 1}</td>
                <td><div style={{ fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 320 }} dangerouslySetInnerHTML={{ __html: a.rephrased_title || a.original_title }} /></td>
                <td><span className="badge badge-new">{a.category}</span></td>
                <td style={{ fontSize: 11 }}>{a.source_name}</td>
                <td style={{ fontFamily: 'var(--mono)', fontSize: 12 }}>{a.rank_score?.toFixed(0)}</td>
                <td style={{ textAlign: 'center' }}>{a.telugu_title ? '✓' : '—'}</td>
              </tr>
            ))}
            {filtered.length === 0 && <tr><td colSpan="6" className="empty-state">No articles found</td></tr>}
            </tbody>
          </table>
        </div>}
      {viewA && <ArticleDetailModal article={viewA} onClose={() => setViewA(null)} />}
    </div>
  );
}
