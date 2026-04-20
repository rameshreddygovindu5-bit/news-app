import React, { useState, useEffect, useRef } from 'react';
import * as api from '../../services/api';
import { useToast } from '../../hooks/useToast';
import { IC } from '../../components/common/Icons';
import { getImg } from '../../constants/news';

export default function WishesManagementPage() {
  const { show, ToastContainer } = useToast();
  const [wishes, setWishes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ title: '', message: '', wish_type: 'birthday', person_name: '', image_url: '', display_on_home: false, occasion_date: '', expires_at: '' });
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef(null);

  const load = async () => {
    try { const r = await api.getWishes(); setWishes(r.data); } catch (e) { show('Failed to load wishes', 'error'); }
    setLoading(false);
  };
  useEffect(() => { load(); }, []);

  const handleImageUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const r = await api.uploadImage(file);
      const url = r.data.url;
      setForm(f => ({ ...f, image_url: url }));
      show('Image uploaded!');
    } catch (err) {
      show('Upload failed: ' + (err.response?.data?.detail || err.message), 'error');
    }
    setUploading(false);
  };

  const handleCreate = async () => {
    if (!form.title.trim()) { show('Title required', 'error'); return; }
    try {
      const payload = { ...form };
      if (!payload.occasion_date) delete payload.occasion_date;
      if (!payload.expires_at) delete payload.expires_at;
      await api.createWish(payload);
      show('Wish created!');
      setShowCreate(false);
      setForm({ title: '', message: '', wish_type: 'birthday', person_name: '', image_url: '', display_on_home: false, occasion_date: '', expires_at: '' });
      load();
    } catch (e) { show('Failed: ' + (e.response?.data?.detail || e.message), 'error'); }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Deactivate this wish?')) return;
    try { await api.deleteWish(id); show('Wish deactivated'); load(); } catch (e) { show('Failed', 'error'); }
  };

  const typeColors = { birthday: '#e91e63', festival: '#ff9800', anniversary: '#f44336', custom: '#673ab7' };

  return (
    <div className="page">
      <ToastContainer />
      <div className="page-header">
        <div><h2>Wishes & Greetings</h2><p>Birthday, festival, and special occasion wishes</p></div>
        <button className="btn btn-primary" onClick={() => setShowCreate(!showCreate)}><IC.Plus style={{ width: 16, height: 16 }} /> Create Wish</button>
      </div>

      {showCreate && (
        <div className="card" style={{ marginBottom: 24 }}>
          <div style={{ padding: 20 }}>
            <h3 style={{ margin: '0 0 16px', fontSize: 16, fontWeight: 700 }}>New Wish</h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <div><label style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 1, color: 'var(--text-muted)' }}>Title *</label>
                <input className="input" value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))} placeholder="Happy Birthday to..." /></div>
              <div><label style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 1, color: 'var(--text-muted)' }}>Person Name</label>
                <input className="input" value={form.person_name} onChange={e => setForm(f => ({ ...f, person_name: e.target.value }))} placeholder="Name of the person" /></div>
              <div><label style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 1, color: 'var(--text-muted)' }}>Type</label>
                <select className="input" value={form.wish_type} onChange={e => setForm(f => ({ ...f, wish_type: e.target.value }))}>
                  <option value="birthday">Birthday</option><option value="festival">Festival</option>
                  <option value="anniversary">Anniversary</option><option value="custom">Custom / Special</option>
                </select></div>
              <div><label style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 1, color: 'var(--text-muted)' }}>Occasion Date</label>
                <input className="input" type="datetime-local" value={form.occasion_date} onChange={e => setForm(f => ({ ...f, occasion_date: e.target.value }))} /></div>
              <div style={{ gridColumn: '1/-1' }}><label style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 1, color: 'var(--text-muted)' }}>Message</label>
                <textarea className="input" rows={3} value={form.message} onChange={e => setForm(f => ({ ...f, message: e.target.value }))} placeholder="Write your heartfelt message..." /></div>
              <div><label style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 1, color: 'var(--text-muted)' }}>Image</label>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  <input className="input" value={form.image_url} onChange={e => setForm(f => ({ ...f, image_url: e.target.value }))} placeholder="Image URL or upload" style={{ flex: 1 }} />
                  <input type="file" ref={fileRef} accept="image/*" onChange={handleImageUpload} style={{ display: 'none' }} />
                  <button className="btn" onClick={() => fileRef.current?.click()} disabled={uploading} style={{ whiteSpace: 'nowrap', background: 'var(--india-green)', color: '#fff', border: 'none' }}>
                    <IC.Upload style={{ width: 14, height: 14, marginRight: 4 }} />{uploading ? 'Uploading...' : 'Upload'}
                  </button>
                </div>
                {form.image_url && <img src={getImg(form.image_url)} alt="" style={{ width: 80, height: 60, objectFit: 'cover', borderRadius: 8, marginTop: 8, border: '2px solid var(--india-green)' }} />}
              </div>
              <div><label style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 1, color: 'var(--text-muted)' }}>Expires At</label>
                <input className="input" type="datetime-local" value={form.expires_at} onChange={e => setForm(f => ({ ...f, expires_at: e.target.value }))} /></div>
              <div style={{ gridColumn: '1/-1', display: 'flex', alignItems: 'center', gap: 8 }}>
                <input type="checkbox" checked={form.display_on_home} onChange={e => setForm(f => ({ ...f, display_on_home: e.target.checked }))} id="wish-home" />
                <label htmlFor="wish-home" style={{ fontSize: 13, fontWeight: 600 }}>Display on Homepage</label>
              </div>
            </div>
            <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
              <button className="btn btn-primary" onClick={handleCreate}>Create Wish</button>
              <button className="btn" onClick={() => setShowCreate(false)}>Cancel</button>
            </div>
          </div>
        </div>
      )}

      {loading ? <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>Loading...</div> : (
        <div className="card">
          <table className="data-table" style={{ width: '100%' }}>
            <thead><tr>
              <th>Image</th><th>Title</th><th>Type</th><th>Person</th><th>Home</th><th>Status</th><th>Actions</th>
            </tr></thead>
            <tbody>
              {wishes.map(w => (
                <tr key={w.id}>
                  <td>{w.image_url ? <img src={getImg(w.image_url)} alt="" style={{ width: 48, height: 36, objectFit: 'cover', borderRadius: 6, border: '1px solid var(--border-light)' }} /> : <span style={{ color: 'var(--text-muted)', fontSize: 11 }}>No image</span>}</td>
                  <td style={{ fontWeight: 700 }}>{w.title}</td>
                  <td><span style={{ background: typeColors[w.wish_type] || '#666', color: '#fff', padding: '2px 10px', borderRadius: 20, fontSize: 10, fontWeight: 700, textTransform: 'uppercase' }}>{w.wish_type}</span></td>
                  <td>{w.person_name || '—'}</td>
                  <td>{w.display_on_home ? <span className="badge badge-enabled">YES</span> : <span className="badge">NO</span>}</td>
                  <td>{w.is_active ? <span className="badge badge-enabled">Active</span> : <span className="badge badge-deleted">Inactive</span>}</td>
                  <td><button className="btn" style={{ fontSize: 11, padding: '4px 12px' }} onClick={() => handleDelete(w.id)}>Deactivate</button></td>
                </tr>
              ))}
              {wishes.length === 0 && <tr><td colSpan={7} style={{ textAlign: 'center', padding: 30, color: 'var(--text-muted)' }}>No wishes created yet</td></tr>}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
