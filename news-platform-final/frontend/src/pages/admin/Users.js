import React, { useState, useEffect } from 'react';
import * as api from '../../services/api';
import { useToast } from '../../hooks/useToast';
import { IC } from '../../components/common/Icons';

export default function UsersPage() {
  const [users, setUsers] = useState([]);
  const [ld, setLd] = useState(true);
  const [show, setShow] = useState(false);
  const { show: showToast, ToastContainer } = useToast();

  const load = () => {
    setLd(true);
    api.getUsers().then(r => {
      setUsers(r.data);
      setLd(false);
    }).catch(() => setLd(false));
  };

  useEffect(() => { load() }, []);

  return (
    <div>
      <ToastContainer />
      <div className="page-header">
        <h2>Users ({users.length})</h2>
        <button className="btn btn-india" onClick={() => setShow(true)}><IC.Plus />Add User</button>
      </div>
      
      {ld ? <div className="loading"><div className="spinner" /></div> :
        <div className="table-container">
          <table className="table">
            <thead><tr><th>ID</th><th>Username</th><th>Email</th><th>Role</th><th>Active</th><th>Last Login</th><th>Actions</th></tr></thead>
            <tbody>{users.map(u => (
              <tr key={u.id}>
                <td style={{ fontFamily: 'var(--mono)', fontSize: 11 }}>{u.id}</td>
                <td style={{ fontWeight: 600 }}>{u.username}</td>
                <td style={{ fontSize: 12 }}>{u.email || '—'}</td>
                <td><span className={`badge ${u.role === 'admin' ? 'badge-top' : 'badge-new'}`}>{u.role.toUpperCase()}</span></td>
                <td>{u.is_active ? <span className="badge badge-enabled">YES</span> : <span className="badge badge-disabled">NO</span>}</td>
                <td style={{ fontFamily: 'var(--mono)', fontSize: 10 }}>{u.last_login_at ? new Date(u.last_login_at).toLocaleString() : 'Never'}</td>
                <td><div className="btn-group">
                  {u.role === 'reporter' && <button className="btn btn-secondary btn-sm" onClick={async () => { await api.updateUser(u.id, { role: 'admin' }); showToast('Promoted ✓'); load() }}>→Admin</button>}
                  {u.role === 'admin' && u.username !== 'admin' && <button className="btn btn-secondary btn-sm" onClick={async () => { await api.updateUser(u.id, { role: 'reporter' }); showToast('Changed'); load() }}>→Reporter</button>}
                  {u.username !== 'admin' && <button className="btn btn-danger btn-sm" onClick={async () => { if (window.confirm(`Deactivate ${u.username}?`)) { await api.deleteUser(u.id); showToast('Deactivated'); load() } }}>Deactivate</button>}
                </div></td>
              </tr>
            ))}</tbody>
          </table>
        </div>}
      {show && <UserModal onClose={() => setShow(false)} onDone={() => { setShow(false); showToast('User created ✓'); load() }} />}
    </div>
  );
}

function UserModal({ onClose, onDone }) {
  const [f, setF] = useState({ username: '', password: '', email: '', role: 'reporter' });
  const [sv, setSv] = useState(false);

  const go = async () => {
    if (!f.username || !f.password) return;
    setSv(true);
    try {
      await api.createUser(f);
      onDone()
    } catch (e) {
      alert(e.response?.data?.detail || 'Failed');
      setSv(false)
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}><div className="modal" onClick={e => e.stopPropagation()}>
      <h3>Create User</h3>
      <div className="grid-2">
        <div className="form-group"><label>Username *</label><input className="form-input" value={f.username} onChange={e => setF({ ...f, username: e.target.value })} /></div>
        <div className="form-group"><label>Password *</label><input className="form-input" type="password" value={f.password} onChange={e => setF({ ...f, password: e.target.value })} /></div>
      </div>
      <div className="grid-2">
        <div className="form-group"><label>Email</label><input className="form-input" value={f.email} onChange={e => setF({ ...f, email: e.target.value })} /></div>
        <div className="form-group"><label>Role</label><select className="form-select" value={f.role} onChange={e => setF({ ...f, role: e.target.value })}><option value="reporter">Reporter</option><option value="admin">Admin</option></select></div>
      </div>
      <div className="modal-actions"><button className="btn btn-secondary" onClick={onClose}>Cancel</button><button className="btn btn-india" onClick={go} disabled={sv}>{sv ? 'Creating…' : 'Create'}</button></div>
    </div></div>
  );
}
