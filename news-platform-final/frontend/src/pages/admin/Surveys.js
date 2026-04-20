import React, { useState, useEffect, useCallback } from 'react';
import * as api from '../../services/api';
import { IC } from '../../components/common/Icons';
import ArticleDetailModal from '../../components/modals/ArticleDetailModal';

export default function SurveysManagementPage() {
  const [arts, setArts] = useState([]);
  const [ld, setLd] = useState(true);
  const [viewA, setViewA] = useState(null);
  const load = useCallback(() => {
    setLd(true);
    api.getArticles({ category: 'Surveys', page_size: 50 }).then(r => {
      setArts(r.data.articles);
      setLd(false);
    }).catch(() => setLd(false));
  }, []);
  useEffect(() => { load(); }, [load]);

  return (
    <div>
      <div className="page-header">
        <h2>Survey Results <span style={{ fontSize: 14, color: 'var(--text-muted)', fontWeight: 400 }}>({arts.length})</span></h2>
        <button className="btn btn-secondary" onClick={load}><IC.Ref />Refresh</button>
      </div>
      {ld ? <div className="loading"><div className="spinner" /></div> : (
        <div className="table-container">
          <table className="table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Survey Title</th>
                <th>Source</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {arts.map(a => (
                <tr key={a.id}>
                  <td style={{ fontSize: 11 }}>{new Date(a.published_at || a.created_at).toLocaleDateString()}</td>
                  <td style={{ fontWeight: 600 }}>{a.rephrased_title || a.original_title}</td>
                  <td style={{ fontSize: 11 }}>{a.source_name}</td>
                  <td><span className="badge badge-enabled">COMPLETED</span></td>
                  <td>
                    <button className="btn btn-secondary btn-sm" onClick={() => setViewA(a)}>View Results</button>
                  </td>
                </tr>
              ))}
              {arts.length === 0 && <tr><td colSpan="5" className="empty-state">No survey data yet</td></tr>}
            </tbody>
          </table>
        </div>
      )}
      {viewA && <ArticleDetailModal article={viewA} onClose={() => setViewA(null)} />}
    </div>
  );
}
