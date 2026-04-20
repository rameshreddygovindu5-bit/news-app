import React, { useState } from 'react';

export function useToast() {
  const [toasts, setToasts] = useState([]);

  const show = (text, type = 'success') => {
    const id = Date.now();
    setToasts(t => [...t, { id, text, type }]);
    setTimeout(() => setToasts(t => t.filter(x => x.id !== id)), 3500);
  };

  const ToastContainer = () => (
    <div style={{ position:'fixed', top:16, right:16, zIndex:9999, display:'flex', flexDirection:'column', gap:8 }}>
      {toasts.map(t => (
        <div key={t.id} style={{
          background: t.type==='error' ? 'var(--india-red)' : t.type==='warn' ? 'var(--india-saffron)' : 'var(--india-green)',
          color:'#fff', padding:'10px 20px', borderRadius:8, fontWeight:600, fontSize:13,
          boxShadow:'0 8px 24px rgba(0,0,0,.25)', animation:'slideIn .2s ease'
        }}>{t.text}</div>
      ))}
    </div>
  );

  return { show, ToastContainer };
}
