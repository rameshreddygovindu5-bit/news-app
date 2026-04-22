import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import * as api from '../../services/api';
import { useToast } from '../../hooks/useToast';
import { IC } from '../../components/common/Icons';
import { FlagBadge } from '../../components/common/Badges';
import { CATS } from '../../constants/news';
import ArticleDetailModal from '../../components/modals/ArticleDetailModal';
import CreateArticleModal from '../../components/modals/CreateArticleModal';
import EditArticleModal from '../../components/modals/EditArticleModal';

export default function ArticlesPage() {
  const [searchParams] = useSearchParams();
  const [articles, setArticles] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [tp, setTp] = useState(1);
  const [ld, setLd] = useState(true);
  const [kw, setKw] = useState('');
  const [search, setSearch] = useState(searchParams.get('keyword') || '');
  const [cat, setCat] = useState(searchParams.get('category') || '');
  const [flag, setFlag] = useState(searchParams.get('flag') || '');
  const [srcId, setSrcId] = useState(searchParams.get('source_id') || '');
  const [lang, setLang] = useState(searchParams.get('lang') || '');
  const [sources, setSrc] = useState([]);
  const [showCreate, setShowCreate] = useState(false);
  const [editA, setEditA] = useState(null);
  const [viewA, setViewA] = useState(null);
  const [sel, setSel] = useState([]);
  const { show, ToastContainer } = useToast();
  const debounceRef = useRef(null);

  // Sync state with URL search params
  useEffect(() => {
    setSearch(searchParams.get('keyword') || '');
    setCat(searchParams.get('category') || '');
    setFlag(searchParams.get('flag') || '');
    setSrcId(searchParams.get('source_id') || '');
    setLang(searchParams.get('lang') || '');
    setPage(1);
  }, [searchParams]);

  const load = useCallback(() => {
    setLd(true);
    const p = { page, page_size: 20 };
    if (search) p.keyword = search;
    if (cat) p.category = cat;
    if (flag) p.flag = flag;
    if (srcId) p.source_id = srcId;
    if (lang) p.lang = lang;
    api.getArticles(p).then(r => {
      setArticles(r.data.articles);
      setTotal(r.data.total);
      setTp(r.data.total_pages);
      setSel([]); 
      setLd(false);
    }).catch(() => setLd(false));
  }, [page, search, cat, flag, srcId]);

  const bulkAction = async (action) => {
    if (!sel.length) return;
    if (action === 'delete' && !window.confirm(`Delete ${sel.length} articles?`)) return;
    try {
      if (action === 'delete') await api.bulkDeleteArticles(sel);
      else if (action === 'ai') await api.bulkReprocessArticles(sel);
      show(`${sel.length} articles ${action === 'delete' ? 'deleted' : 'queued for AI'} ✓`);
      load();
    } catch { show('Bulk action failed', 'error'); }
  };

  const toggleSel = (id) => {
    setSel(p => p.includes(id) ? p.filter(x => x !== id) : [...p, id]);
  };
  const toggleAll = () => {
    setSel(sel.length === articles.length ? [] : articles.map(a => a.id));
  };

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => { load(); }, 500);
  }, [search, page, cat, flag, srcId, lang, load]);

  useEffect(() => { 
    api.getSources().then(r => setSrc(r.data)).catch(() => {});
  }, []);

  const trigAI = async (id) => {
    try {
      await api.reprocessArticle(id);
      show('AI queued ✓');
      load();
    } catch (e) {
      show('Failed', 'error');
    }
  };

  const del = async (id) => {
    if (!window.confirm('Delete this article?')) return;
    try {
      await api.deleteArticle(id);
      show('Deleted');
      load();
    } catch (e) {
      show('Failed', 'error');
    }
  };

  return (
    <div>
      <ToastContainer />
      <div className="page-header">
        <h2>Articles <span style={{ fontSize: 14, color: 'var(--text-muted)', fontWeight: 400 }}>({total.toLocaleString()})</span></h2>
        <button className="btn btn-india" onClick={() => setShowCreate(true)}><IC.Plus />Create</button>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <div className="admin-controls card-shadow" style={{ display: 'flex', gap: 16, marginBottom: 20, padding: 16, background: '#fff', borderRadius: 12, alignItems: 'center' }}>
          <div style={{ flex: 1, position: 'relative' }}>
            <input 
              className="form-input" 
              placeholder="Search by title or content..." 
              value={search} 
              onChange={e => { setSearch(e.target.value); setPage(1); }} 
              style={{ margin: 0, paddingLeft: 40 }}
            />
            <IC.Search style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', opacity: 0.4 }} />
          </div>
          <select className="form-select" style={{ width: 150, margin: 0 }} value={cat} onChange={e => { setCat(e.target.value); setPage(1); }}>
              <option value="">All</option>{CATS.map(c => <option key={c}>{c}</option>)}
            </select>
          <div><label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>FLAG</label>
            <select className="form-select" value={flag} onChange={e => { setFlag(e.target.value); setPage(1) }}>
              <option value="">All</option><option value="P">Pending</option><option value="N">New</option><option value="A">AI Done</option><option value="Y">Top</option><option value="D">Deleted</option>
            </select></div>
          <div><label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>SOURCE</label>
            <select className="form-select" value={srcId} onChange={e => { setSrcId(e.target.value); setPage(1) }}>
              <option value="">All</option>{sources.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select></div>
          <div><label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>LANG</label>
            <select className="form-select" value={lang} onChange={e => { setLang(e.target.value); setPage(1) }}>
              <option value="">All</option>
              <option value="en">English</option>
              <option value="te">Telugu</option>
            </select></div>
          <button className="btn btn-india btn-sm" onClick={() => { setPage(1); load() }} style={{ alignSelf: 'flex-end' }}><IC.Ref />Search</button>
          <button className="btn btn-secondary" onClick={() => { setSearch(''); setCat(''); setFlag(''); setSrcId(''); setLang(''); setPage(1) }}>Clear</button>
          <button className="btn btn-secondary" onClick={load}><IC.Ref /></button>
        </div>
      </div>

      {sel.length > 0 && (
        <div className="card" style={{ marginBottom: 12, padding: '10px 16px', background: 'var(--accent-dim)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', animation: 'slideIn .2s' }}>
          <div style={{ fontWeight: 600, color: 'var(--accent)' }}>{sel.length} articles selected</div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="btn btn-sm btn-secondary" style={{ background: '#6200ea', color: '#fff', border: 'none' }} onClick={() => bulkAction('ai')}>Run AI</button>
            <button className="btn btn-sm btn-danger" onClick={() => bulkAction('delete')}>Delete All</button>
            <button className="btn btn-sm btn-secondary" onClick={() => setSel([])}>Cancel</button>
          </div>
        </div>
      )}

      {ld ? <div className="loading"><div className="spinner" /></div> :
        <div className="table-container">
          <table className="table">
            <thead><tr>
              <th style={{ width: 40 }}><input type="checkbox" checked={sel.length > 0 && sel.length === articles.length} onChange={toggleAll} /></th>
              <th>ID</th><th>Title</th><th>Source</th><th>Cat</th><th>Flag</th><th>Telugu</th><th>Actions</th>
            </tr></thead>
            <tbody>
              {articles.map(a => (
                <tr key={a.id} className={sel.includes(a.id) ? 'row-selected' : ''}>
                  <td><input type="checkbox" checked={sel.includes(a.id)} onChange={() => toggleSel(a.id)} /></td>
                  <td style={{ fontFamily: 'var(--mono)', fontSize: 11, display: 'flex', alignItems: 'center', gap: 4 }}>
                    {a.id}
                    {a.ai_error_count > 0 && <span title={`${a.ai_error_count} AI errors`} style={{ display: 'inline-block', width: 6, height: 6, borderRadius: '50%', background: 'var(--india-red)' }} />}
                  </td>
                  <td style={{ maxWidth: 320 }}>
                    <div style={{ fontWeight: 600, cursor: 'pointer', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: 'var(--india-navy)' }} onClick={() => setViewA(a)}>
                      {a.rephrased_title || a.original_title}
                    </div>
                    {a.telugu_title && (
                      <div className="telugu-text" style={{ fontSize: 13, color: 'var(--india-saffron)', marginTop: 4, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {a.telugu_title}
                      </div>
                    )}
                    {a.ai_status === 'failed' && <span style={{ fontSize: 10, color: 'var(--india-red)' }}>AI failed</span>}
                  </td>
                  <td style={{ fontSize: 11 }}>{a.source_name}</td>
                  <td style={{ fontSize: 12 }}>{a.category || '—'}</td>
                  <td><FlagBadge flag={a.flag} /></td>
                  <td style={{ textAlign: 'center' }}>{a.telugu_title ? <span style={{ color: 'var(--india-saffron)', fontWeight: 700, fontSize: 13 }}>తె</span> : <span style={{ color: 'var(--text-muted)', fontSize: 11 }}>—</span>}</td>
                  <td>
                    <div className="btn-group">
                      <button className="btn btn-secondary btn-sm" title="View" onClick={() => setViewA(a)}><IC.Eye /></button>
                      <button className="btn btn-secondary btn-sm" title="Edit" onClick={() => setEditA(a)}>Edit</button>
                      <button className="btn btn-secondary btn-sm" title="Re-run AI" onClick={() => trigAI(a.id)} style={{ background: '#6200ea', color: '#fff', border: 'none' }}>AI</button>
                      <button className="btn btn-danger btn-sm" title="Delete" onClick={() => del(a.id)}>Del</button>
                    </div>
                  </td>
                </tr>
              ))}
              {articles.length === 0 && <tr><td colSpan="7" className="empty-state">No articles found</td></tr>}
            </tbody>
          </table>
        </div>}

      {tp > 1 && <div className="pagination">
        <button disabled={page <= 1} onClick={() => setPage(p => p - 1)}>← Prev</button>
        <span>Page {page} of {tp}</span>
        <button disabled={page >= tp} onClick={() => setPage(p => p + 1)}>Next →</button>
      </div>}

      {showCreate && <CreateArticleModal onClose={() => setShowCreate(false)} onDone={() => { setShowCreate(false); show('Article created ✓'); load() }} sources={sources} />}
      {editA && <EditArticleModal article={editA} onClose={() => setEditA(null)} onDone={() => { setEditA(null); show('Saved ✓'); load() }} />}
      {viewA && <ArticleDetailModal article={viewA} onClose={() => setViewA(null)} />}
    </div>
  );
}
