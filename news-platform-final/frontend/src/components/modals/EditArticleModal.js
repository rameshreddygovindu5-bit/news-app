import React, { useState } from 'react';
import * as api from '../../services/api';
import { CATS } from '../../constants/news';

export default function EditArticleModal({article:a, onClose, onDone}) {
  const [f, setF] = useState({
    original_title: a.original_title || '',
    original_content: a.original_content || '',
    rephrased_title: a.rephrased_title || '',
    rephrased_content: a.rephrased_content || '',
    telugu_title: a.telugu_title || '',
    telugu_content: a.telugu_content || '',
    category: a.category || 'Home',
    tags: (a.tags || []).join(', '),
    flag: a.flag || 'N',
    image_url: a.image_url || ''
  });
  const [sv, setSv] = useState(false);

  const go = async () => {
    setSv(true);
    try {
      await api.updateArticle(a.id, {
        original_title: f.original_title,
        original_content: f.original_content,
        rephrased_title: f.rephrased_title,
        rephrased_content: f.rephrased_content,
        telugu_title: f.telugu_title,
        telugu_content: f.telugu_content,
        category: f.category,
        tags: f.tags ? f.tags.split(',').map(t => t.trim()) : [],
        flag: f.flag,
        image_url: f.image_url
      });
      onDone();
    } catch {
      setSv(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" style={{maxWidth:760}} onClick={e=>e.stopPropagation()}>
        <h3>Edit #{a.id}</h3>
        <div className="form-group"><label>Original Title</label><input className="form-input" value={f.original_title} onChange={e=>setF({...f, original_title:e.target.value})}/></div>
        <div className="form-group"><label>Rephrased Title</label><input className="form-input" value={f.rephrased_title} onChange={e=>setF({...f, rephrased_title:e.target.value})}/></div>
        <div className="form-group"><label>Telugu Title</label><input className="form-input telugu-text" value={f.telugu_title} onChange={e=>setF({...f, telugu_title:e.target.value})}/></div>
        <div className="form-group"><label>Rephrased Content</label><textarea className="form-textarea" rows={4} value={f.rephrased_content} onChange={e=>setF({...f, rephrased_content:e.target.value})}/></div>
        <div className="form-group"><label>Telugu Content</label><textarea className="form-textarea telugu-text" rows={4} value={f.telugu_content} onChange={e=>setF({...f, telugu_content:e.target.value})}/></div>
        <div className="grid-2">
          <div className="form-group"><label>Category</label><select className="form-select" value={f.category} onChange={e=>setF({...f, category:e.target.value})}>{CATS.map(c=><option key={c}>{c}</option>)}</select></div>
          <div className="form-group"><label>Flag</label><select className="form-select" value={f.flag} onChange={e=>setF({...f, flag:e.target.value})}><option value="P">Pending</option><option value="N">New</option><option value="A">AI Done</option><option value="Y">Top</option><option value="D">Deleted</option></select></div>
        </div>
        <div className="form-group"><label>Tags</label><input className="form-input" value={f.tags} onChange={e=>setF({...f, tags:e.target.value})}/></div>
        <div className="form-group"><label>Image URL</label><input className="form-input" value={f.image_url} onChange={e=>setF({...f, image_url:e.target.value})}/></div>
        <div className="modal-actions"><button className="btn btn-secondary" onClick={onClose}>Cancel</button><button className="btn btn-india" onClick={go} disabled={sv}>{sv?'Saving…':'Save'}</button></div>
      </div>
    </div>
  );
}
