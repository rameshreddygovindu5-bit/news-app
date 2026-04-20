import React, { useState, useEffect } from 'react';
import * as api from '../../services/api';
import { useToast } from '../../hooks/useToast';
import { IC } from '../../components/common/Icons';

export default function CategoriesPage() {
  const [cats, setCats] = useState([]);
  const [ld, setLd] = useState(true);
  const [nc, setNc] = useState({ name: '', slug: '', description: '' });
  const { show, ToastContainer } = useToast();

  const load = () => {
    api.getCategories().then(r => {
      setCats(r.data);
      setLd(false);
    }).catch(() => setLd(false));
  };

  useEffect(() => { load() }, []);

  const add = async () => {
    if (!nc.name) return;
    try {
      await api.createCategory({
        name: nc.name,
        slug: nc.slug || nc.name.toLowerCase().replace(/\s+/g, '-'),
        description: nc.description
      });
      setNc({ name: '', slug: '', description: '' });
      show('Category added ✓');
      load();
    } catch (e) {
      show('Failed', 'error');
    }
  };

  const syncCounts = async () => {
    try {
      await api.triggerAction('trigger_categories');
      show('Counts syncing…');
    } catch { }
  };

  return (
    <div>
      <ToastContainer />
      <div className="page-header">
        <h2>Categories</h2>
        <button className="btn btn-secondary" onClick={syncCounts}><IC.Ref />Sync Counts</button>
      </div>
      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', gap: 12, alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <div style={{ flex: 1 }}><label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>NAME</label><input className="form-input" value={nc.name} onChange={e => setNc({ ...nc, name: e.target.value })} /></div>
          <div style={{ flex: 1 }}><label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>DESCRIPTION</label><input className="form-input" value={nc.description} onChange={e => setNc({ ...nc, description: e.target.value })} /></div>
          <button className="btn btn-india" onClick={add}><IC.Plus />Add</button>
        </div>
      </div>
      {ld ? <div className="loading"><div className="spinner" /></div> :
        <div className="table-container">
          <table className="table">
            <thead><tr><th>Name</th><th>Slug</th><th>Articles</th><th>Active</th></tr></thead>
            <tbody>{cats.map(c => (
              <tr key={c.id}>
                <td style={{ fontWeight: 600 }}>{c.name}</td>
                <td style={{ fontFamily: 'var(--mono)', fontSize: 11 }}>{c.slug}</td>
                <td style={{ fontWeight: 700, color: c.article_count < 5 ? 'var(--india-red)' : c.article_count < 20 ? 'var(--india-saffron)' : 'var(--india-green)' }}>{c.article_count}</td>
                <td>{c.is_active ? <span className="badge badge-enabled">YES</span> : <span className="badge badge-disabled">NO</span>}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>}
    </div>
  );
}
