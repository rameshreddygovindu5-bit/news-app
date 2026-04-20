import React, { useState, useEffect } from 'react';
import * as api from '../../services/api';
import { useToast } from '../../hooks/useToast';
import { IC } from '../../components/common/Icons';

export default function YouTubePage() {
  const [url, setUrl] = useState('');
  const [result, setResult] = useState(null);
  const [ld, setLd] = useState(false);
  const [saving, setSaving] = useState(false);
  const [sources, setSrc] = useState([]);
  const [srcId, setSrcId] = useState('');
  const { show, ToastContainer } = useToast();

  useEffect(() => { 
    api.getSources().then(r => setSrc(r.data)).catch(() => { });
  }, []);

  const process = async () => {
    if (!url) { show('Enter a YouTube URL', 'warn'); return; }
    setLd(true);
    setResult(null);
    try {
      const r = await api.processYouTube(url, parseInt(srcId) || undefined);
      setResult(r.data);
      show('Transcript processed ✓')
    } catch (e) {
      show(e.response?.data?.detail || 'Failed', 'error')
    }
    setLd(false);
  };

  const save = async () => {
    if (!result) return;
    setSaving(true);
    try {
      await api.saveYouTubeArticle({
        video_url: result.video_url,
        title: result.rephrased_title,
        content: result.rephrased_content,
        category: result.category,
        tags: [],
        image_url: result.thumbnail_url,
        source_id: parseInt(srcId) || undefined,
        telugu_title: result.telugu_title || '',
        telugu_content: result.telugu_content || ''
      });
      show('Saved to Top News ✓');
      setResult(null);
      setUrl('');
    } catch (e) {
      show(e.response?.data?.detail || 'Failed', 'error')
    }
    setSaving(false);
  };

  return (
    <div>
      <ToastContainer />
      <div className="page-header"><h2>YouTube Import</h2></div>
      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', gap: 12, alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <div style={{ flex: 1 }}>
            <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>YOUTUBE URL</label>
            <input className="form-input" value={url} onChange={e => setUrl(e.target.value)} placeholder="https://youtube.com/watch?v=…" onKeyDown={e => e.key === 'Enter' && process()} />
          </div>
          <div><label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>SOURCE</label><select className="form-select" value={srcId} onChange={e => setSrcId(e.target.value)}><option value="">Default</option>{sources.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}</select></div>
          <button className="btn btn-india" onClick={process} disabled={ld}><IC.Play />{ld ? 'Processing…' : 'Fetch & Process'}</button>
        </div>
        <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 8 }}>YouTube URL → transcript → AI rephrase (English + Telugu) → save as Top News</p>
      </div>
      {ld && <div className="loading"><div className="spinner" />Fetching transcript and running AI…</div>}
      {result && !result.error && (
        <div className="card">
          <div className="card-header"><h3>Preview</h3><button className="btn btn-india" onClick={save} disabled={saving}>{saving ? 'Saving…' : 'Save to Top News'}</button></div>
          {result.thumbnail_url && <img src={result.thumbnail_url} alt="" style={{ width: '100%', maxWidth: 480, borderRadius: 8, marginBottom: 16 }} />}
          <div style={{ marginBottom: 12 }}><div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>AI TITLE</div><h3 className="telugu-text" dangerouslySetInnerHTML={{ __html: result.telugu_title || result.rephrased_title }} /></div>
          <div style={{ marginBottom: 12 }}><div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>CATEGORY</div><span className="badge badge-new">{result.category}</span></div>
          <div style={{ marginBottom: 12 }}><div style={{ fontSize: 11, color: 'var(--accent)', marginBottom: 4 }}>REPHRASED CONTENT</div><div className="news-premium-content telugu-text" style={{ background: 'var(--bg-input)', padding: 14, borderRadius: 8, maxHeight: 280, overflowY: auto }} dangerouslySetInnerHTML={{ __html: result.telugu_content || result.rephrased_content }} /></div>
          {result.telugu_title && <div style={{ marginBottom: 12 }}><div style={{ fontSize: 11, color: 'var(--india-saffron)', marginBottom: 4 }}>TELUGU TITLE ✓</div></div>}
        </div>
      )}
      {result?.error && <div className="card" style={{ borderColor: 'var(--india-red)' }}><div style={{ color: 'var(--india-red)', fontWeight: 600 }}>Error: {result.error}</div></div>}
    </div>
  );
}
