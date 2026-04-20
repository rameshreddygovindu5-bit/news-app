import React, { useState } from 'react';
import * as api from '../../services/api';
import { CATS } from '../../constants/news';

export default function CreateArticleModal({onClose, onDone, sources}) {
  const pf = sources.find(s => s.name.toLowerCase() === 'peoples feedback' || s.name.toLowerCase() === 'peoplesfeedback');
  const [f, setF] = useState({title:'', content:'', category:'Home', tags:'', source_id:pf?.id||'', image_url:''});
  const [sv, setSv] = useState(false);

  const go = async () => {
    if(!f.title) return;
    setSv(true);
    try {
      await api.createManualArticle({
        title: f.title,
        content: f.content,
        category: f.category,
        tags: f.tags ? f.tags.split(',').map(t => t.trim()) : [],
        source_id: parseInt(f.source_id) || undefined,
        image_url: f.image_url || undefined
      });
      onDone();
    } catch(e) {
      setSv(false);
      alert(e.response?.data?.detail || 'Failed');
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e=>e.stopPropagation()}>
        <h3>Create Article</h3>
        <div className="form-group"><label>Title *</label><input className="form-input" value={f.title} onChange={e=>setF({...f, title:e.target.value})}/></div>
        <div className="form-group"><label>Content</label><textarea className="form-textarea" rows={5} value={f.content} onChange={e=>setF({...f, content:e.target.value})}/></div>
        <div className="grid-2">
          <div className="form-group"><label>Category</label><select className="form-select" value={f.category} onChange={e=>setF({...f, category:e.target.value})}>{CATS.map(c=><option key={c}>{c}</option>)}</select></div>
          <div className="form-group"><label>Source</label><select className="form-select" value={f.source_id} disabled><option value={f.source_id}>{pf?.name || 'Peoples Feedback'}</option></select></div>
        </div>
        <div className="form-group"><label>Tags (comma-separated)</label><input className="form-input" value={f.tags} onChange={e=>setF({...f, tags:e.target.value})} placeholder="tag1, tag2"/></div>
        <div className="form-group"><label>Image URL</label><input className="form-input" value={f.image_url} onChange={e=>setF({...f, image_url:e.target.value})}/></div>
        <div className="modal-actions"><button className="btn btn-secondary" onClick={onClose}>Cancel</button><button className="btn btn-india" onClick={go} disabled={sv}>{sv?'Creating…':'Create + AI'}</button></div>
      </div>
    </div>
  );
}
