import React, { useState, useEffect, useRef } from 'react';
import * as api from '../../services/api';
import { useToast } from '../../hooks/useToast';
import { IC } from '../../components/common/Icons';
import { CATS } from '../../constants/news';

export default function ReporterSubmitPage() {
  const [sources, setSrc] = useState([]);
  const pf = sources.find(s => s.name.toLowerCase() === 'peoples feedback' || s.name.toLowerCase() === 'peoplesfeedback');
  const [f, setF] = useState({ title: '', content: '', category: 'Home', tags: '', source_id: '', image_url: '' });
  const [sv, setSv] = useState(false);
  const [suggesting, setSuggesting] = useState(false);
  const { show, ToastContainer } = useToast();
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef(null);

  const handleImgUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const r = await api.uploadImage(file);
      setF(prev => ({ ...prev, image_url: r.data.url }));
      show('Image uploaded!');
    } catch (err) { show('Upload failed: ' + (err.response?.data?.detail || err.message), 'error'); }
    setUploading(false);
  };

  const suggest = async () => {
    if (!f.title || !f.content) { show('Provide title and content first', 'warn'); return; }
    setSuggesting(true);
    try {
      const r = await api.suggestMetadata({ title: f.title, content: f.content });
      setF(prev => ({ 
        ...prev, 
        category: r.data.suggested_category || prev.category,
        tags: r.data.suggested_tags?.join(', ') || prev.tags
      }));
      show('AI suggestions applied! ✓');
    } catch { show('AI suggestion failed', 'error'); }
    setSuggesting(false);
  };

  useEffect(() => {
    if (pf && !f.source_id) setF(prev => ({ ...prev, source_id: pf.id }));
  }, [pf, f.source_id]);

  useEffect(() => { api.getSources().then(r => setSrc(r.data)).catch(() => { }) }, []);

  const go = async () => {
    if (!f.title || !f.content) { show('Title and content required', 'warn'); return; }
    setSv(true);
    try {
      await api.submitArticle({
        title: f.title,
        content: f.content,
        category: f.category,
        tags: f.tags ? f.tags.split(',').map(t => t.trim()) : [],
        source_id: parseInt(f.source_id) || undefined,
        image_url: f.image_url || undefined
      });
      show('Submitted for review ✓');
      setF({ title: '', content: '', category: 'Home', tags: '', source_id: pf?.id || '', image_url: '' })
    } catch (e) { show(e.response?.data?.detail || 'Failed', 'error') }
    setSv(false)
  };

  return (
    <div>
      <ToastContainer />
      <div className="page-header"><h2>Submit Article</h2></div>
      <div className="card" style={{ maxWidth: 800 }}>
        <div style={{ padding: '10px 14px', background: 'var(--accent-dim)', borderRadius: 8, marginBottom: 16, fontSize: 13, color: 'var(--accent)' }}>
          Your article will be reviewed by an admin before publishing.
        </div>
        <div className="form-group"><label>Title *</label><input className="form-input" value={f.title} onChange={e => setF({ ...f, title: e.target.value })} /></div>
        <div className="form-group"><label>Content *</label><textarea className="form-textarea" rows={8} value={f.content} onChange={e => setF({ ...f, content: e.target.value })} /></div>
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 16 }}>
          <button className="btn btn-sm btn-secondary" style={{ background: '#6200ea', color: '#fff', border: 'none' }} onClick={suggest} disabled={suggesting || sv}>
            <IC.Gear style={{ width: 14, height: 14 }} /> {suggesting ? 'Analyzing...' : 'AI Suggest Category & Tags'}
          </button>
        </div>
        <div className="grid-2">
          <div className="form-group"><label>Category</label><select className="form-select" value={f.category} onChange={e => setF({ ...f, category: e.target.value })}>{CATS.map(c => <option key={c}>{c}</option>)}</select></div>
          <div className="form-group"><label>Source</label><select className="form-select" value={f.source_id} disabled><option value={f.source_id}>{pf?.name || 'Peoples Feedback'}</option></select></div>
        </div>
        <div className="grid-2">
          <div className="form-group"><label>Image (URL or Upload)</label>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <input className="form-input" style={{ flex: 1 }} value={f.image_url} onChange={e => setF({ ...f, image_url: e.target.value })} placeholder="Paste image URL or click Upload" />
              <input type="file" ref={fileInputRef} accept="image/*" onChange={handleImgUpload} style={{ display: 'none' }} />
              <button type="button" className="btn" onClick={() => fileInputRef.current?.click()} disabled={uploading} style={{ whiteSpace: 'nowrap', display: 'flex', alignItems: 'center', gap: 4 }}>
                <IC.Upload style={{ width: 14, height: 14 }} />{uploading ? 'Uploading...' : 'Upload'}
              </button>
            </div>
            {f.image_url && <img src={f.image_url} alt="Preview" style={{ width: 100, height: 60, objectFit: 'cover', borderRadius: 8, marginTop: 8, border: '2px solid var(--border-light)' }} />}
          </div>
          <div className="form-group"><label>Tags</label><input className="form-input" value={f.tags} onChange={e => setF({ ...f, tags: e.target.value })} placeholder="tag1, tag2" /></div>
        </div>
        <button className="btn btn-india" onClick={go} disabled={sv} style={{ marginTop: 8 }}><IC.Send />{sv ? 'Submitting…' : 'Submit for Review'}</button>
      </div>
    </div>
  );
}
