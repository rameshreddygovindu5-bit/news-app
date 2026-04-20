import React, { useState } from 'react';
import { useAuthCtx } from '../../context/AuthContext';

export default function LoginPage() {
  const [u, setU] = useState('');
  const [p, setP] = useState('');
  const [ld, setLd] = useState(false);
  const [err, setErr] = useState('');
  const { doLogin } = useAuthCtx();

  const go = async (e) => {
    e.preventDefault();
    if (!u || !p) return;
    setLd(true);
    setErr('');
    try {
      await doLogin(u, p);
    } catch (e) {
      setErr(e.response?.data?.detail || 'Invalid credentials');
      setLd(false);
    }
  };

  return (
    <div className="login-screen">
      <div className="login-card">
        <div className="india-tricolor-h" />
        <div className="login-header">
          <h2>NewsAI Admin</h2>
          <p>Sign in to manage news platform</p>
        </div>
        <form onSubmit={go}>
          <div className="form-group"><label>Username</label><input required className="form-input" value={u} onChange={e => setU(e.target.value)} placeholder="Enter username" /></div>
          <div className="form-group"><label>Password</label><input required className="form-input" type="password" value={p} onChange={e => setP(e.target.value)} placeholder="••••••••" /></div>
          {err && <div className="login-error">{err}</div>}
          <button type="submit" className="login-btn" disabled={ld}>{ld ? 'Signing in…' : 'Sign In'}</button>
        </form>
        <div className="login-footer">© 2026 People's Feedback · Multi-lingual Engine</div>
      </div>
    </div>
  );
}
