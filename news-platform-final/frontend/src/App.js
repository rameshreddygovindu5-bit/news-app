import React, { useState, useEffect, useCallback, createContext, useContext, useRef } from 'react';
import { BrowserRouter, Routes, Route, Navigate, Link, useLocation } from 'react-router-dom';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import * as api from './services/api';

// ─── Canonical category list — keep in sync with backend config.py ───
const CATS = ['Home','World','Politics','Business','Tech','Health','Science','Entertainment','Events','Sports','Surveys','Polls'];

const AuthContext = createContext(null);
const useAuthCtx = () => useContext(AuthContext);

// ─── Auth hook ────────────────────────────────────────────────────────
function useAuth() {
  const [user, setUser] = useState(() => { try { return JSON.parse(localStorage.getItem('user')); } catch { return null; } });
  const [token, setToken] = useState(() => localStorage.getItem('token'));
  const doLogin = async (username, password) => {
    const r = await api.login(username, password);
    const { access_token, username: u, role } = r.data;
    localStorage.setItem('token', access_token);
    localStorage.setItem('user', JSON.stringify({ username: u, role }));
    setToken(access_token); setUser({ username: u, role });
  };
  const doLogout = () => { localStorage.removeItem('token'); localStorage.removeItem('user'); setToken(null); setUser(null); };
  return { user, token, doLogin, doLogout, isAuthenticated: !!token, isAdmin: user?.role === 'admin' };
}

// ─── Toast ────────────────────────────────────────────────────────────
function useToast() {
  const [toasts, setToasts] = useState([]);
  const show = (text, type = 'success') => {
    const id = Date.now();
    setToasts(t => [...t, { id, text, type }]);
    setTimeout(() => setToasts(t => t.filter(x => x.id !== id)), 3500);
  };
  const El = () => (
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
  return { show, El };
}

// ─── Icons ────────────────────────────────────────────────────────────
const IC = {
  Dash:()=><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>,
  Doc:()=><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>,
  Globe:()=><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/></svg>,
  Star:()=><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>,
  Clock:()=><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>,
  Gear:()=><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>,
  List:()=><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M4 7h16M4 12h16M4 17h10"/></svg>,
  Out:()=><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>,
  Plus:()=><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>,
  Play:()=><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="5 3 19 12 5 21 5 3"/></svg>,
  Ref:()=><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>,
  Eye:()=><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>,
  Check:()=><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="20 6 9 17 4 12"/></svg>,
  Users:()=><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>,
  YT:()=><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="2" y="4" width="20" height="16" rx="4"/><polygon points="10 8 16 12 10 16 10 8"/></svg>,
  Send:()=><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>,
  TE:()=><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><text x="3" y="18" fontSize="14" fontWeight="bold" fill="currentColor" stroke="none">తె</text></svg>,
  AWS:()=><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M4 17L12 21L20 17"/><path d="M4 12L12 16L20 12"/><path d="M4 7L12 11L20 7L12 3L4 7z"/></svg>,
  Social:()=><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 8h1a4 4 0 0 1 0 8h-1"/><path d="M2 8h16v9a4 4 0 0 1-4 4H6a4 4 0 0 1-4-4V8z"/><line x1="6" y1="1" x2="6" y2="4"/><line x1="10" y1="1" x2="10" y2="4"/><line x1="14" y1="1" x2="14" y2="4"/></svg>,
  Gift:()=><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="20 12 20 22 4 22 4 12"/><rect x="2" y="7" width="20" height="5"/><line x1="12" y1="22" x2="12" y2="7"/><path d="M12 7H7.5a2.5 2.5 0 0 1 0-5C11 2 12 7 12 7z"/><path d="M12 7h4.5a2.5 2.5 0 0 0 0-5C13 2 12 7 12 7z"/></svg>,
  Upload:()=><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>,
};

function FlagBadge({flag}) {
  const m={P:['PENDING','badge-paused'],N:['NEW','badge-new'],A:['AI DONE','badge-processed'],Y:['TOP','badge-top'],D:['DEL','badge-deleted']};
  const [l,cl]=m[flag]||['?',''];
  return <span className={`badge ${cl}`}>{l}</span>;
}

function StatusBadge({status}) {
  const cl = {'DONE':'badge-enabled','completed':'badge-enabled','RUNNING':'badge-new','running':'badge-new','PARTIAL':'badge-paused','FAILED':'badge-deleted','failed':'badge-deleted'}[status]||'badge-new';
  return <span className={`badge ${cl}`}>{status}</span>;
}

const CAT_LOGOS = {
  home: 'https://images.unsplash.com/photo-1504711434969-e33886168d6c?w=400&q=80',
  world: 'https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=400&q=80',
  politics: 'https://images.unsplash.com/photo-1529107386315-e1a2ed48a620?w=400&q=80',
  business: 'https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=400&q=80',
  tech: 'https://images.unsplash.com/photo-1518770660439-4636190af475?w=400&q=80',
  health: 'https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?w=400&q=80',
  science: 'https://images.unsplash.com/photo-1507413245164-6160d8298b31?w=400&q=80',
  entertainment: 'https://images.unsplash.com/photo-1603190287605-e6ade32fa852?w=400&q=80',
  events: 'https://images.unsplash.com/photo-1540575467063-178a50c2df87?w=400&q=80',
  sports: 'https://images.unsplash.com/photo-1461896836934-bd45ba6b0e28?w=400&q=80',
  surveys: 'https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=400&q=80',
  polls: 'https://images.unsplash.com/photo-1540910419892-4a39d20b2944?w=400&q=80',
};
const getImg = (u, c) => u || CAT_LOGOS[(c||'').toLowerCase().trim()] || CAT_LOGOS.home;

// ─── Sidebar ──────────────────────────────────────────────────────────
function Sidebar({onLogout}) {
  const loc = useLocation();
  const {user} = useAuthCtx();
  const isAdmin = user?.role==='admin';
  const adminNav = [
    {p:'/',l:'Dashboard',i:IC.Dash},{p:'/articles',l:'Articles',i:IC.Doc},
    {p:'/pending',l:'Pending Approval',i:IC.Check},{p:'/sources',l:'Sources',i:IC.Globe},
    {p:'/top-news',l:'Top 100 News',i:IC.Star},{p:'/categories',l:'Categories',i:IC.List},
    {p:'/youtube',l:'YouTube Import',i:IC.YT},{p:'/scheduler',l:'Scheduler',i:IC.Clock},
    {p:'/users',l:'Users',i:IC.Users},{p:'/polls',l:'Polls',i:IC.List},{p:'/surveys',l:'Surveys',i:IC.List},{p:'/wishes',l:'Wishes',i:IC.Gift},{p:'/settings',l:'Settings',i:IC.Gear},
  ];
  const reporterNav = [
    {p:'/',l:'Submit Article',i:IC.Send},{p:'/my-submissions',l:'My Submissions',i:IC.Doc},
  ];
  const nav = isAdmin ? adminNav : reporterNav;
  return (
    <div className="sidebar">
      <div className="sidebar-brand">
        <div className="india-tricolor-h"/>
        <h1>NewsAI</h1>
        <span>{isAdmin?'Admin':'Reporter'} · {user?.username}</span>
      </div>
      <nav className="sidebar-nav">
        {nav.map(n=>(
          <Link key={n.p} to={n.p} className={`nav-item ${loc.pathname===n.p?'active':''}`}>
            <n.i/>{n.l}
          </Link>
        ))}
      </nav>
      <div className="sidebar-footer" style={{padding: '16px 0', borderTop: '1px solid var(--border-light)'}}>
        <button className="nav-item logout-btn" onClick={onLogout} style={{width:'100%', border:'none', background:'none', cursor:'pointer', textAlign:'left'}}>
          <IC.Out/>Logout
        </button>
      </div>
    </div>
  );
}

// ─── Login ────────────────────────────────────────────────────────────
function LoginPage({onLogin}) {
  const [u,setU]=useState('');const [p,setP]=useState('');const [e,setE]=useState('');const [ld,setLd]=useState(false);
  const go=async(ev)=>{ev.preventDefault();setLd(true);setE('');try{await onLogin(u,p)}catch(err){setE(err.response?.data?.detail||'Login failed')}setLd(false)};
  return (
    <div className="login-page">
      <div className="login-card">
        <div className="india-tricolor-h" style={{borderRadius:'4px 4px 0 0',marginBottom:24}}/>
        <h2>NewsAI Platform</h2>
        <p style={{color:'var(--text-muted)',marginBottom:24}}>Sign in to continue</p>
        {e&&<div className="error-msg">{e}</div>}
        <form onSubmit={go}>
          <div className="form-group"><label>Username</label><input className="form-input" value={u} onChange={x=>setU(x.target.value)} required autoFocus/></div>
          <div className="form-group"><label>Password</label><input className="form-input" type="password" value={p} onChange={x=>setP(x.target.value)} required/></div>
          <button className="btn btn-india" style={{width:'100%',marginTop:8}} disabled={ld}>{ld?'Signing in…':'Sign In'}</button>
        </form>
        <p style={{marginTop:16,fontSize:11,color:'var(--text-muted)',textAlign:'center'}}>Default: admin / admin123</p>
      </div>
    </div>
  );
}

// ─── Dashboard ────────────────────────────────────────────────────────
function DashboardPage() {
  const [s,setS]=useState(null);const [ld,setLd]=useState(true);const toast=useToast();
  const load=useCallback(()=>{setLd(true);api.getDashboardStats().then(r=>{setS(r.data);setLd(false)}).catch(()=>setLd(false))},[]);
  useEffect(()=>{load();const t=setInterval(load,30000);return()=>clearInterval(t)},[load]);

  const trigger=async(action,label)=>{
    try{const r=await api.triggerAction(action);toast.show(r.data?.message||`${label} triggered`)}
    catch(e){toast.show(e.response?.data?.detail||`${label} failed`,'error')}
  };

  if(ld&&!s)return <div className="loading"><div className="spinner"/>Loading dashboard…</div>;
  if(!s)return <div className="empty-state"><p>Failed to load dashboard</p><button className="btn btn-secondary" onClick={load}><IC.Ref/>Retry</button></div>;
  const CL=['#FF9933','#138808','#000080','#D32F2F','#1565C0','#7B1FA2','#00695C','#AD1457'];

  return (
    <div>
      <toast.El/>
      <div className="page-header">
        <h2>Dashboard</h2>
        <div style={{display:'flex',gap:8,flexWrap:'wrap'}}>
          <span className={`badge ${s.aws?.status==='online'?'badge-enabled':'badge-paused'}`} style={{padding:'8px 14px',fontSize:12}}>
            AWS: {s.aws?.status?.toUpperCase()||'OFFLINE'}
          </span>
          <button className="btn btn-sm btn-secondary" onClick={load}><IC.Ref/>Refresh</button>
        </div>
      </div>

      {/* Pipeline quick-trigger strip */}
      <div className="card" style={{marginBottom:20,padding:'12px 16px'}}>
        <div style={{fontSize:11,color:'var(--text-muted)',marginBottom:10,fontWeight:600,textTransform:'uppercase',letterSpacing:1}}>Quick Pipeline Triggers</div>
        <div style={{display:'flex',gap:8,flexWrap:'wrap'}}>
          <button className="btn btn-india btn-sm" onClick={()=>trigger('trigger_pipeline','Full Pipeline')}><IC.Play/>Full Pipeline</button>
          <button className="btn btn-secondary btn-sm" onClick={()=>trigger('trigger_scrape','Scrape')}><IC.Globe/>Scrape</button>
          <button className="btn btn-secondary btn-sm" style={{background:'#6200ea',color:'#fff',border:'none'}} onClick={()=>trigger('trigger_ai','AI')}><IC.Gear/>AI Process</button>
          <button className="btn btn-secondary btn-sm" onClick={()=>trigger('trigger_ranking','Ranking')}><IC.Star/>Rank</button>
          <button className="btn btn-secondary btn-sm" style={{background:'#FF9900',color:'#fff',border:'none'}} onClick={()=>trigger('trigger_sync','AWS Sync')}><IC.AWS/>AWS Sync</button>
          <button className="btn btn-secondary btn-sm" style={{background:'#1877F2',color:'#fff',border:'none'}} onClick={()=>trigger('trigger_social','Social')}><IC.Social/>Social Post</button>
          <button className="btn btn-secondary btn-sm" onClick={()=>trigger('trigger_categories','Category Counts')}>Cats</button>
          <button className="btn btn-secondary btn-sm" style={{background:'var(--india-red)',color:'#fff',border:'none'}} onClick={()=>trigger('trigger_cleanup','Cleanup')}>Cleanup</button>
        </div>
      </div>

      {/* Stats grid */}
      <div className="grid-2" style={{marginBottom:20}}>
        <div className="card">
          <div className="card-header"><h3 style={{color:'var(--india-saffron)'}}>Local Engine</h3></div>
          <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:12,padding:20}}>
            <div className="stat-card blue"><div className="stat-label">Total Articles</div><div className="stat-value">{(s.local?.total||0).toLocaleString()}</div></div>
            <div className="stat-card green"><div className="stat-label">AI Processed</div><div className="stat-value">{(s.local?.processed||0).toLocaleString()}</div></div>
            <div className="stat-card yellow"><div className="stat-label">AI Pending</div><div className="stat-value">{(s.local?.pending_ai||0).toLocaleString()}</div></div>
            <div className="stat-card purple"><div className="stat-label">Top 100</div><div className="stat-value">{s.local?.top||0}</div></div>
          </div>
        </div>
        <div className="card">
          <div className="card-header"><h3 style={{color:'var(--india-green)'}}>AWS Production</h3></div>
          <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:12,padding:20}}>
            <div className="stat-card blue"><div className="stat-label">AWS Total</div><div className="stat-value">{(s.aws?.total||0).toLocaleString()}</div></div>
            <div className="stat-card green"><div className="stat-label">AWS Processed</div><div className="stat-value">{(s.aws?.processed||0).toLocaleString()}</div></div>
            <div className="stat-card orange"><div className="stat-label">Sync Gap</div><div className="stat-value">{Math.max(0,(s.local?.total||0)-(s.aws?.total||0)).toLocaleString()}</div></div>
            <div className="stat-card purple"><div className="stat-label">AWS Top</div><div className="stat-value">{s.aws?.top||0}</div></div>
          </div>
        </div>
      </div>

      <div className="grid-2" style={{marginBottom:20}}>
        {/* Category pie chart */}
        <div className="card">
          <div className="card-header"><h3>Category Distribution</h3></div>
          <div style={{height:280}}>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={s.category_stats} dataKey="count" nameKey="category" cx="50%" cy="50%" outerRadius={100} label={({category})=>category} labelLine={false}>
                  {(s.category_stats||[]).map((_,i)=><Cell key={i} fill={CL[i%CL.length]}/>)}
                </Pie>
                <Tooltip contentStyle={{background:'#1a2236',border:'none',borderRadius:8,color:'#fff'}}/>
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Pipeline health */}
        <div className="card">
          <div className="card-header"><h3>Pipeline Health</h3></div>
          <div className="table-container">
            <table className="table">
              <thead><tr><th>Job</th><th>Status</th><th>OK / ERR</th></tr></thead>
              <tbody>
                {(s.recent_jobs||s.recent_scrapes||[]).slice(0,8).map(l=>(
                  <tr key={l.id}>
                    <td style={{fontWeight:600,fontSize:12}}>{l.job_name}</td>
                    <td><StatusBadge status={l.status}/></td>
                    <td style={{fontSize:12}}>
                      <span style={{color:'var(--india-green)'}}>{l.rows_ok}</span>
                      <span style={{color:'var(--text-muted)'}}> / </span>
                      <span style={{color:l.rows_err>0?'var(--india-red)':'var(--text-muted)'}}>{l.rows_err}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Article Detail Modal ─────────────────────────────────────────────
function ArticleDetailModal({article:a,onClose}) {
  const [lang,setLang]=useState('en');
  if(!a)return null;
  const hasTE=!!(a.telugu_title&&a.telugu_content);
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" style={{maxWidth:950}} onClick={e=>e.stopPropagation()}>
        <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:12}}>
          <h3>Article #{a.id}</h3>
          <div style={{display:'flex',gap:8,alignItems:'center'}}>
            {hasTE&&(
              <div style={{display:'flex',gap:4}}>
                <button className={`btn btn-sm ${lang==='en'?'btn-primary':'btn-secondary'}`} onClick={()=>setLang('en')}>English</button>
                <button className={`btn btn-sm ${lang==='te'?'btn-primary':'btn-secondary'}`} onClick={()=>setLang('te')}>తెలుగు</button>
              </div>
            )}
            <button className="btn btn-secondary btn-sm" onClick={onClose}>✕</button>
          </div>
        </div>
        <div style={{display:'flex',gap:6,marginBottom:12,flexWrap:'wrap'}}>
          <FlagBadge flag={a.flag}/>
          {a.category&&<span className="badge badge-new">{a.category}</span>}
          {a.source_name&&<span className="badge badge-paused" style={{background:'var(--india-green)',color:'#fff'}}>{a.source_name}</span>}
          {a.submitted_by&&<span className="badge badge-paused">by {a.submitted_by}</span>}
          {a.ai_status&&<span className="badge" style={{background:'#6200ea',color:'#fff'}}>{a.ai_status}</span>}
          {hasTE&&<span className="badge" style={{background:'#FF9933',color:'#fff'}}>తెలుగు ✓</span>}
        </div>
        <div className="grid-2" style={{gap:14}}>
          <div style={{background:'var(--bg-input)',padding:14,borderRadius:8,border:'1px solid var(--border-light)'}}>
            <div style={{fontSize:11,color:'var(--text-muted)',textTransform:'uppercase',marginBottom:8,fontWeight:600}}>Original</div>
            <img src={getImg(a.image_url, a.category)} alt="" style={{width:'100%',borderRadius:4,marginBottom:10,maxHeight:140,objectFit:'cover'}}/>
            <h4 style={{fontSize:14,marginBottom:10,lineHeight:1.4}}>{a.original_title}</h4>
            <div style={{fontSize:12,color:'var(--text-secondary)',lineHeight:1.7,maxHeight:250,overflowY:'auto',whiteSpace:'pre-wrap'}}>{a.original_content?.slice(0,600)||'No content'}</div>
          </div>
          <div style={{background:'var(--bg-input)',padding:14,borderRadius:8,border:'1px solid var(--accent-dim)'}}>
            <div style={{fontSize:11,color:'var(--accent)',textTransform:'uppercase',marginBottom:8,fontWeight:600}}>{lang==='te'?'Telugu Version':'AI Rephrased'}</div>
            <img src={getImg(a.image_url, a.category)} alt="" style={{width:'100%',borderRadius:4,marginBottom:10,maxHeight:140,objectFit:'cover'}}/>
            <h4 style={{fontSize:14,marginBottom:10,lineHeight:1.4,color:'var(--accent)'}}
              dangerouslySetInnerHTML={{__html:lang==='te'?(a.telugu_title||a.rephrased_title||a.original_title):(a.rephrased_title||a.original_title)}}/>
            <div style={{fontSize:12,color:'var(--text-secondary)',lineHeight:1.7,maxHeight:250,overflowY:'auto'}}
              dangerouslySetInnerHTML={{__html:lang==='te'?(a.telugu_content||a.rephrased_content||'Not translated yet'):(a.rephrased_content||'Not processed yet')}}/>
          </div>
        </div>
        {(a.tags||[]).length>0&&<div style={{marginTop:8,display:'flex',gap:4,flexWrap:'wrap'}}>{(a.tags||[]).map(t=><span key={t} className="tag">{t}</span>)}</div>}
      </div>
    </div>
  );
}

// ─── Articles Page ────────────────────────────────────────────────────
function ArticlesPage() {
  const [articles,setArticles]=useState([]);const [total,setTotal]=useState(0);const [page,setPage]=useState(1);const [tp,setTp]=useState(1);const [ld,setLd]=useState(true);
  const [kw,setKw]=useState('');const [cat,setCat]=useState('');const [flag,setFlag]=useState('');const [srcId,setSrcId]=useState('');const [aiStatus,setAiStatus]=useState('');
  const [sources,setSrc]=useState([]);const [showCreate,setShowCreate]=useState(false);const [editA,setEditA]=useState(null);const [viewA,setViewA]=useState(null);const toast=useToast();

  const load=useCallback(()=>{
    setLd(true);
    const p={page,page_size:20};
    if(kw)p.keyword=kw;if(cat)p.category=cat;if(flag)p.flag=flag;if(srcId)p.source_id=srcId;
    api.getArticles(p).then(r=>{setArticles(r.data.articles);setTotal(r.data.total);setTp(r.data.total_pages);setLd(false)}).catch(()=>setLd(false));
  },[page,kw,cat,flag,srcId]);

  useEffect(()=>{load()},[load]);
  useEffect(()=>{api.getSources().then(r=>setSrc(r.data)).catch(()=>{})},[]);

  const trigAI=async(id)=>{try{await api.reprocessArticle(id);toast.show('AI queued ✓');load()}catch(e){toast.show('Failed','error')}};
  const del=async(id)=>{if(!window.confirm('Delete this article?'))return;try{await api.deleteArticle(id);toast.show('Deleted');load()}catch(e){toast.show('Failed','error')}};

  return (
    <div><toast.El/>
      <div className="page-header">
        <h2>Articles <span style={{fontSize:14,color:'var(--text-muted)',fontWeight:400}}>({total.toLocaleString()})</span></h2>
        <button className="btn btn-india" onClick={()=>setShowCreate(true)}><IC.Plus/>Create</button>
      </div>

      {/* Filters */}
      <div className="card" style={{marginBottom:16}}>
        <div style={{display:'flex',gap:10,flexWrap:'wrap',alignItems:'flex-end'}}>
          <div style={{flex:'1 1 180px'}}>
            <label style={{fontSize:11,color:'var(--text-muted)',display:'block',marginBottom:4}}>SEARCH</label>
            <input className="form-input" placeholder="Title, content, Telugu…" value={kw} onChange={e=>setKw(e.target.value)} onKeyDown={e=>e.key==='Enter'&&(setPage(1),load())}/>
          </div>
          <div><label style={{fontSize:11,color:'var(--text-muted)',display:'block',marginBottom:4}}>CATEGORY</label>
            <select className="form-select" value={cat} onChange={e=>{setCat(e.target.value);setPage(1)}}>
              <option value="">All</option>{CATS.map(c=><option key={c}>{c}</option>)}
            </select></div>
          <div><label style={{fontSize:11,color:'var(--text-muted)',display:'block',marginBottom:4}}>FLAG</label>
            <select className="form-select" value={flag} onChange={e=>{setFlag(e.target.value);setPage(1)}}>
              <option value="">All</option><option value="P">Pending</option><option value="N">New</option><option value="A">AI Done</option><option value="Y">Top</option><option value="D">Deleted</option>
            </select></div>
          <div><label style={{fontSize:11,color:'var(--text-muted)',display:'block',marginBottom:4}}>SOURCE</label>
            <select className="form-select" value={srcId} onChange={e=>{setSrcId(e.target.value);setPage(1)}}>
              <option value="">All</option>{sources.map(s=><option key={s.id} value={s.id}>{s.name}</option>)}
            </select></div>
          <button className="btn btn-secondary" onClick={()=>{setKw('');setCat('');setFlag('');setSrcId('');setPage(1)}}>Clear</button>
          <button className="btn btn-secondary" onClick={load}><IC.Ref/></button>
        </div>
      </div>

      {ld?<div className="loading"><div className="spinner"/></div>:
      <div className="table-container">
        <table className="table">
          <thead><tr><th>ID</th><th>Title</th><th>Source</th><th>Cat</th><th>Flag</th><th>Telugu</th><th>Actions</th></tr></thead>
          <tbody>
            {articles.map(a=>(
              <tr key={a.id}>
                <td style={{fontFamily:'var(--mono)',fontSize:11}}>{a.id}</td>
                <td style={{maxWidth:320}}>
                  <div style={{fontWeight:500,cursor:'pointer',overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}} onClick={()=>setViewA(a)}>
                    {a.rephrased_title||a.original_title}
                  </div>
                  {a.ai_status==='failed'&&<span style={{fontSize:10,color:'var(--india-red)'}}>AI failed</span>}
                </td>
                <td style={{fontSize:11}}>{a.source_name}</td>
                <td style={{fontSize:12}}>{a.category||'—'}</td>
                <td><FlagBadge flag={a.flag}/></td>
                <td style={{textAlign:'center'}}>{a.telugu_title?<span style={{color:'var(--india-saffron)',fontWeight:700,fontSize:13}}>తె</span>:<span style={{color:'var(--text-muted)',fontSize:11}}>—</span>}</td>
                <td>
                  <div className="btn-group">
                    <button className="btn btn-secondary btn-sm" title="View" onClick={()=>setViewA(a)}><IC.Eye/></button>
                    <button className="btn btn-secondary btn-sm" title="Edit" onClick={()=>setEditA(a)}>Edit</button>
                    <button className="btn btn-secondary btn-sm" title="Re-run AI" onClick={()=>trigAI(a.id)} style={{background:'#6200ea',color:'#fff',border:'none'}}>AI</button>
                    <button className="btn btn-danger btn-sm" title="Delete" onClick={()=>del(a.id)}>Del</button>
                  </div>
                </td>
              </tr>
            ))}
            {articles.length===0&&<tr><td colSpan="7" className="empty-state">No articles found</td></tr>}
          </tbody>
        </table>
      </div>}

      {tp>1&&<div className="pagination">
        <button disabled={page<=1} onClick={()=>setPage(p=>p-1)}>← Prev</button>
        <span>Page {page} of {tp}</span>
        <button disabled={page>=tp} onClick={()=>setPage(p=>p+1)}>Next →</button>
      </div>}

      {showCreate&&<CreateModal onClose={()=>setShowCreate(false)} onDone={()=>{setShowCreate(false);toast.show('Article created ✓');load()}} sources={sources}/>}
      {editA&&<EditModal article={editA} onClose={()=>setEditA(null)} onDone={()=>{setEditA(null);toast.show('Saved ✓');load()}} sources={sources}/>}
      {viewA&&<ArticleDetailModal article={viewA} onClose={()=>setViewA(null)}/>}
    </div>
  );
}

function CreateModal({onClose,onDone,sources}) {
  const pf = sources.find(s => s.name.toLowerCase() === 'peoples feedback' || s.name.toLowerCase() === 'peoplesfeedback');
  const [f,setF]=useState({title:'',content:'',category:'Home',tags:'',source_id:pf?.id||'',image_url:''});const [sv,setSv]=useState(false);
  const go=async()=>{if(!f.title)return;setSv(true);try{await api.createManualArticle({title:f.title,content:f.content,category:f.category,tags:f.tags?f.tags.split(',').map(t=>t.trim()):[],source_id:parseInt(f.source_id)||undefined,image_url:f.image_url||undefined});onDone()}catch(e){setSv(false);alert(e.response?.data?.detail||'Failed')}};
  return (
    <div className="modal-overlay" onClick={onClose}><div className="modal" onClick={e=>e.stopPropagation()}>
      <h3>Create Article</h3>
      <div className="form-group"><label>Title *</label><input className="form-input" value={f.title} onChange={e=>setF({...f,title:e.target.value})}/></div>
      <div className="form-group"><label>Content</label><textarea className="form-textarea" rows={5} value={f.content} onChange={e=>setF({...f,content:e.target.value})}/></div>
      <div className="grid-2">
        <div className="form-group"><label>Category</label><select className="form-select" value={f.category} onChange={e=>setF({...f,category:e.target.value})}>{CATS.map(c=><option key={c}>{c}</option>)}</select></div>
        <div className="form-group"><label>Source</label><select className="form-select" value={f.source_id} disabled><option value={f.source_id}>{pf?.name || 'Peoples Feedback'}</option></select></div>
      </div>
      <div className="form-group"><label>Tags (comma-separated)</label><input className="form-input" value={f.tags} onChange={e=>setF({...f,tags:e.target.value})} placeholder="tag1, tag2"/></div>
      <div className="form-group"><label>Image URL</label><input className="form-input" value={f.image_url} onChange={e=>setF({...f,image_url:e.target.value})}/></div>
      <div className="modal-actions"><button className="btn btn-secondary" onClick={onClose}>Cancel</button><button className="btn btn-india" onClick={go} disabled={sv}>{sv?'Creating…':'Create + AI'}</button></div>
    </div></div>
  );
}

function EditModal({article:a,onClose,onDone}) {
  const [f,setF]=useState({original_title:a.original_title||'',original_content:a.original_content||'',rephrased_title:a.rephrased_title||'',rephrased_content:a.rephrased_content||'',telugu_title:a.telugu_title||'',telugu_content:a.telugu_content||'',category:a.category||'Home',tags:(a.tags||[]).join(', '),flag:a.flag||'N',image_url:a.image_url||''});
  const [sv,setSv]=useState(false);
  const go=async()=>{setSv(true);try{await api.updateArticle(a.id,{original_title:f.original_title,original_content:f.original_content,rephrased_title:f.rephrased_title,rephrased_content:f.rephrased_content,telugu_title:f.telugu_title,telugu_content:f.telugu_content,category:f.category,tags:f.tags?f.tags.split(',').map(t=>t.trim()):[],flag:f.flag,image_url:f.image_url});onDone()}catch{setSv(false)}};
  return (
    <div className="modal-overlay" onClick={onClose}><div className="modal" style={{maxWidth:760}} onClick={e=>e.stopPropagation()}>
      <h3>Edit #{a.id}</h3>
      <div className="form-group"><label>Original Title</label><input className="form-input" value={f.original_title} onChange={e=>setF({...f,original_title:e.target.value})}/></div>
      <div className="form-group"><label>Rephrased Title</label><input className="form-input" value={f.rephrased_title} onChange={e=>setF({...f,rephrased_title:e.target.value})}/></div>
      <div className="form-group"><label>Telugu Title</label><input className="form-input" style={{fontFamily:'Noto Sans Telugu,sans-serif'}} value={f.telugu_title} onChange={e=>setF({...f,telugu_title:e.target.value})}/></div>
      <div className="form-group"><label>Rephrased Content</label><textarea className="form-textarea" rows={4} value={f.rephrased_content} onChange={e=>setF({...f,rephrased_content:e.target.value})}/></div>
      <div className="form-group"><label>Telugu Content</label><textarea className="form-textarea" rows={4} style={{fontFamily:'Noto Sans Telugu,sans-serif'}} value={f.telugu_content} onChange={e=>setF({...f,telugu_content:e.target.value})}/></div>
      <div className="grid-2">
        <div className="form-group"><label>Category</label><select className="form-select" value={f.category} onChange={e=>setF({...f,category:e.target.value})}>{CATS.map(c=><option key={c}>{c}</option>)}</select></div>
        <div className="form-group"><label>Flag</label><select className="form-select" value={f.flag} onChange={e=>setF({...f,flag:e.target.value})}><option value="P">Pending</option><option value="N">New</option><option value="A">AI Done</option><option value="Y">Top</option><option value="D">Deleted</option></select></div>
      </div>
      <div className="form-group"><label>Tags</label><input className="form-input" value={f.tags} onChange={e=>setF({...f,tags:e.target.value})}/></div>
      <div className="form-group"><label>Image URL</label><input className="form-input" value={f.image_url} onChange={e=>setF({...f,image_url:e.target.value})}/></div>
      <div className="modal-actions"><button className="btn btn-secondary" onClick={onClose}>Cancel</button><button className="btn btn-india" onClick={go} disabled={sv}>{sv?'Saving…':'Save'}</button></div>
    </div></div>
  );
}

// ─── Pending Approvals ────────────────────────────────────────────────
function PendingApprovalsPage() {
  const [articles,setArticles]=useState([]);const [total,setTotal]=useState(0);const [ld,setLd]=useState(true);const [viewA,setViewA]=useState(null);const toast=useToast();
  const load=()=>{setLd(true);api.getPendingArticles({page:1,page_size:50}).then(r=>{setArticles(r.data.articles);setTotal(r.data.total);setLd(false)}).catch(()=>setLd(false))};
  useEffect(()=>{load()},[]);
  const doApprove=async(id,action)=>{try{await api.approveArticle(id,action);toast.show(`Article ${action}d ✓`);load()}catch(e){toast.show(e.response?.data?.detail||'Failed','error')}};
  return (
    <div><toast.El/>
      <div className="page-header"><h2>Pending Approval <span style={{fontSize:14,color:'var(--india-saffron)',fontWeight:400}}>({total})</span></h2><button className="btn btn-secondary" onClick={load}><IC.Ref/>Refresh</button></div>
      {ld?<div className="loading"><div className="spinner"/></div>:articles.length===0?
        <div className="card" style={{textAlign:'center',padding:60,color:'var(--text-muted)'}}><IC.Check/><p style={{marginTop:12}}>No articles pending approval</p></div>:
        <div className="table-container"><table className="table">
          <thead><tr><th>ID</th><th>Title</th><th>Category</th><th>By</th><th>Date</th><th>Actions</th></tr></thead>
          <tbody>{articles.map(a=>(
            <tr key={a.id}>
              <td style={{fontFamily:'var(--mono)',fontSize:11}}>{a.id}</td>
              <td><div style={{fontWeight:500,cursor:'pointer'}} onClick={()=>setViewA(a)}>{a.original_title}</div><div style={{fontSize:11,color:'var(--text-muted)',marginTop:2}}>{a.original_content?.slice(0,100)}…</div></td>
              <td>{a.category||'—'}</td>
              <td><span className="badge badge-new">{a.submitted_by||'—'}</span></td>
              <td style={{fontFamily:'var(--mono)',fontSize:10}}>{a.created_at?new Date(a.created_at).toLocaleString():'—'}</td>
              <td><div className="btn-group">
                <button className="btn btn-success btn-sm" onClick={()=>doApprove(a.id,'approve')}>Approve</button>
                <button className="btn btn-primary btn-sm" onClick={()=>doApprove(a.id,'approve_direct')}>Direct Pub</button>
                <button className="btn btn-danger btn-sm" onClick={()=>doApprove(a.id,'reject')}>Reject</button>
                <button className="btn btn-secondary btn-sm" onClick={()=>setViewA(a)}><IC.Eye/></button>
              </div></td>
            </tr>
          ))}</tbody>
        </table></div>}
      {viewA&&<ArticleDetailModal article={viewA} onClose={()=>setViewA(null)}/>}
    </div>
  );
}

// ─── Sources Page ─────────────────────────────────────────────────────
function SourcesPage() {
  const [src,setSrc]=useState([]);const [ld,setLd]=useState(true);const [show,setShow]=useState(false);const toast=useToast();
  const load=()=>{setLd(true);api.getSources().then(r=>{setSrc(r.data);setLd(false)}).catch(()=>setLd(false))};
  useEffect(()=>{load()},[]);
  const runScrape=async(id,name)=>{try{await api.triggerAction('trigger_scrape',id);toast.show(`Scraping ${name}…`)}catch(e){toast.show('Failed','error')}};
  return (
    <div><toast.El/>
      <div className="page-header"><h2>Sources ({src.length})</h2><button className="btn btn-india" onClick={()=>setShow(true)}><IC.Plus/>Add Source</button></div>
      {ld?<div className="loading"><div className="spinner"/></div>:
      <div className="table-container"><table className="table">
        <thead><tr><th>Name</th><th>Type</th><th>Language</th><th>Interval</th><th>Status</th><th>Last Scraped</th><th>Actions</th></tr></thead>
        <tbody>{src.map(s=>(
          <tr key={s.id}>
            <td style={{fontWeight:600}}>{s.name}</td>
            <td style={{fontFamily:'var(--mono)',fontSize:11}}>{s.scraper_type}</td>
            <td><span className="badge badge-new">{s.language?.toUpperCase()||'EN'}</span></td>
            <td style={{fontSize:12}}>{s.scrape_interval_minutes}m</td>
            <td>{s.is_paused?<span className="badge badge-paused">PAUSED</span>:s.is_enabled?<span className="badge badge-enabled">ACTIVE</span>:<span className="badge badge-disabled">OFF</span>}</td>
            <td style={{fontFamily:'var(--mono)',fontSize:10}}>{s.last_scraped_at?new Date(s.last_scraped_at).toLocaleString():'Never'}</td>
            <td><div className="btn-group">
              <button className="btn btn-secondary btn-sm" title="Scrape now" onClick={()=>runScrape(s.id,s.name)}><IC.Play/></button>
              <button className="btn btn-secondary btn-sm" onClick={async()=>{await api.togglePause(s.id);load()}}>{s.is_paused?'Resume':'Pause'}</button>
              <button className="btn btn-secondary btn-sm" onClick={async()=>{await api.toggleEnable(s.id);load()}}>{s.is_enabled?'Off':'On'}</button>
            </div></td>
          </tr>
        ))}
        {src.length===0&&<tr><td colSpan="7" className="empty-state">No sources configured</td></tr>}
        </tbody>
      </table></div>}
      {show&&<SrcModal onClose={()=>setShow(false)} onDone={()=>{setShow(false);toast.show('Source added ✓');load()}}/>}
    </div>
  );
}

function SrcModal({onClose,onDone}) {
  const [f,setF]=useState({name:'',url:'',language:'en',scraper_type:'rss',scrape_interval_minutes:60,scraper_config:'{}',credibility_score:0.7,priority:0});const [sv,setSv]=useState(false);
  const go=async()=>{if(!f.name||!f.url)return;setSv(true);try{let c={};try{c=JSON.parse(f.scraper_config)}catch{}await api.createSource({...f,scraper_config:c,scrape_interval_minutes:parseInt(f.scrape_interval_minutes),credibility_score:parseFloat(f.credibility_score),priority:parseInt(f.priority)});onDone()}catch(e){setSv(false);alert(e.response?.data?.detail||'Failed')}};
  return (
    <div className="modal-overlay" onClick={onClose}><div className="modal" onClick={e=>e.stopPropagation()}>
      <h3>Add Source</h3>
      <div className="grid-2">
        <div className="form-group"><label>Name *</label><input className="form-input" value={f.name} onChange={e=>setF({...f,name:e.target.value})}/></div>
        <div className="form-group"><label>URL *</label><input className="form-input" value={f.url} onChange={e=>setF({...f,url:e.target.value})}/></div>
      </div>
      <div className="grid-2">
        <div className="form-group"><label>Language</label><select className="form-select" value={f.language} onChange={e=>setF({...f,language:e.target.value})}><option value="en">English</option><option value="te">Telugu</option><option value="hi">Hindi</option></select></div>
        <div className="form-group"><label>Scraper Type</label><select className="form-select" value={f.scraper_type} onChange={e=>setF({...f,scraper_type:e.target.value})}><option value="rss">RSS</option><option value="html">HTML</option><option value="greatandhra">GreatAndhra</option><option value="cnn">CNN</option><option value="manual">Manual</option></select></div>
      </div>
      <div className="grid-2">
        <div className="form-group"><label>Credibility (0–1)</label><input className="form-input" type="number" min="0" max="1" step="0.1" value={f.credibility_score} onChange={e=>setF({...f,credibility_score:e.target.value})}/></div>
        <div className="form-group"><label>Priority</label><input className="form-input" type="number" value={f.priority} onChange={e=>setF({...f,priority:e.target.value})}/></div>
      </div>
      <div className="form-group"><label>Config JSON</label><textarea className="form-textarea" style={{fontFamily:'var(--mono)',fontSize:12}} rows={3} value={f.scraper_config} onChange={e=>setF({...f,scraper_config:e.target.value})}/></div>
      <div className="modal-actions"><button className="btn btn-secondary" onClick={onClose}>Cancel</button><button className="btn btn-india" onClick={go} disabled={sv}>{sv?'Adding…':'Add Source'}</button></div>
    </div></div>
  );
}

// ─── Top News Page ────────────────────────────────────────────────────
function TopNewsPage() {
  const [arts,setArts]=useState([]);const [ld,setLd]=useState(true);const [viewA,setViewA]=useState(null);const toast=useToast();
  const [catFilter,setCatFilter]=useState('');
  const load=()=>{setLd(true);api.getTopNews(200).then(r=>{setArts(r.data);setLd(false)}).catch(()=>setLd(false))};
  useEffect(()=>{load()},[]);
  const rerank=async()=>{try{const r=await api.triggerAction('trigger_ranking');toast.show(r.data?.message||'Ranking triggered');setTimeout(load,3000)}catch(e){toast.show('Failed','error')}};
  const filtered=catFilter?arts.filter(a=>a.category===catFilter):arts;
  // Category coverage stats
  const catStats=CATS.map(c=>({cat:c,count:arts.filter(a=>a.category===c).length}));
  return (
    <div><toast.El/>
      <div className="page-header">
        <h2>Top 100 News <span style={{fontSize:14,color:'var(--text-muted)',fontWeight:400}}>({arts.length} total)</span></h2>
        <div className="btn-group">
          <button className="btn btn-india" onClick={rerank}><IC.Ref/>Re-rank</button>
          <button className="btn btn-secondary" onClick={load}><IC.Ref/>Reload</button>
        </div>
      </div>
      {/* Category coverage */}
      <div className="card" style={{marginBottom:16,padding:'12px 16px'}}>
        <div style={{fontSize:11,color:'var(--text-muted)',marginBottom:8,fontWeight:600}}>CATEGORY COVERAGE</div>
        <div style={{display:'flex',gap:8,flexWrap:'wrap'}}>
          <button className={`btn btn-sm ${!catFilter?'btn-india':'btn-secondary'}`} onClick={()=>setCatFilter('')}>All ({arts.length})</button>
          {catStats.map(({cat,count})=>(
            <button key={cat} className={`btn btn-sm ${catFilter===cat?'btn-india':'btn-secondary'}`} onClick={()=>setCatFilter(cat==='All'?'':cat)}
              style={{borderColor:count<5?'var(--india-red)':count<10?'var(--india-saffron)':''}}>
              {cat} ({count}){count<5&&<span style={{color:'var(--india-red)',marginLeft:4}}>!</span>}
            </button>
          ))}
        </div>
      </div>
      {ld?<div className="loading"><div className="spinner"/></div>:
      <div className="table-container"><table className="table">
        <thead><tr><th>#</th><th>Title</th><th>Category</th><th>Source</th><th>Score</th><th>Telugu</th></tr></thead>
        <tbody>{filtered.map((a,i)=>(
          <tr key={a.id} style={{cursor:'pointer'}} onClick={()=>setViewA(a)}>
            <td style={{fontFamily:'var(--mono)',fontWeight:700,color:i<3?'var(--india-saffron)':i<10?'var(--india-green)':'var(--text-muted)'}}>{i+1}</td>
            <td><div style={{fontWeight:500,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap',maxWidth:320}} dangerouslySetInnerHTML={{__html:a.rephrased_title||a.original_title}}/></td>
            <td><span className="badge badge-new">{a.category}</span></td>
            <td style={{fontSize:11}}>{a.source_name}</td>
            <td style={{fontFamily:'var(--mono)',fontSize:12}}>{a.rank_score?.toFixed(0)}</td>
            <td style={{textAlign:'center'}}>{a.telugu_title?'✓':'—'}</td>
          </tr>
        ))}
        {filtered.length===0&&<tr><td colSpan="6" className="empty-state">No articles found</td></tr>}
        </tbody>
      </table></div>}
      {viewA&&<ArticleDetailModal article={viewA} onClose={()=>setViewA(null)}/>}
    </div>
  );
}

// ─── Categories Page ──────────────────────────────────────────────────
function CategoriesPage() {
  const [cats,setCats]=useState([]);const [ld,setLd]=useState(true);const [nc,setNc]=useState({name:'',slug:'',description:''});const toast=useToast();
  const load=()=>{api.getCategories().then(r=>{setCats(r.data);setLd(false)}).catch(()=>setLd(false))};
  useEffect(()=>{load()},[]);
  const add=async()=>{if(!nc.name)return;try{await api.createCategory({name:nc.name,slug:nc.slug||nc.name.toLowerCase().replace(/\s+/g,'-'),description:nc.description});setNc({name:'',slug:'',description:''});toast.show('Category added ✓');load()}catch(e){toast.show('Failed','error')}};
  const syncCounts=async()=>{try{await api.triggerAction('trigger_categories');toast.show('Counts syncing…')}catch{}};
  return (
    <div><toast.El/>
      <div className="page-header"><h2>Categories</h2><button className="btn btn-secondary" onClick={syncCounts}><IC.Ref/>Sync Counts</button></div>
      <div className="card" style={{marginBottom:16}}>
        <div style={{display:'flex',gap:12,alignItems:'flex-end',flexWrap:'wrap'}}>
          <div style={{flex:1}}><label style={{fontSize:11,color:'var(--text-muted)',display:'block',marginBottom:4}}>NAME</label><input className="form-input" value={nc.name} onChange={e=>setNc({...nc,name:e.target.value})}/></div>
          <div style={{flex:1}}><label style={{fontSize:11,color:'var(--text-muted)',display:'block',marginBottom:4}}>DESCRIPTION</label><input className="form-input" value={nc.description} onChange={e=>setNc({...nc,description:e.target.value})}/></div>
          <button className="btn btn-india" onClick={add}><IC.Plus/>Add</button>
        </div>
      </div>
      {ld?<div className="loading"><div className="spinner"/></div>:
      <div className="table-container"><table className="table">
        <thead><tr><th>Name</th><th>Slug</th><th>Articles</th><th>Active</th></tr></thead>
        <tbody>{cats.map(c=>(
          <tr key={c.id}>
            <td style={{fontWeight:600}}>{c.name}</td>
            <td style={{fontFamily:'var(--mono)',fontSize:11}}>{c.slug}</td>
            <td style={{fontWeight:700,color:c.article_count<5?'var(--india-red)':c.article_count<20?'var(--india-saffron)':'var(--india-green)'}}>{c.article_count}</td>
            <td>{c.is_active?<span className="badge badge-enabled">YES</span>:<span className="badge badge-disabled">NO</span>}</td>
          </tr>
        ))}</tbody>
      </table></div>}
    </div>
  );
}

// ─── Scheduler Page ───────────────────────────────────────────────────
function SchedulerPage() {
  const [logs,setLogs]=useState([]);const [ld,setLd]=useState(true);const [cfg,setCfg]=useState(null);const [running,setRunning]=useState(false);const toast=useToast();
  const loadLogs=useCallback(()=>{setLd(true);api.getSchedulerLogs({limit:60}).then(r=>{setLogs(r.data);setLd(false)}).catch(()=>setLd(false))},[]);
  useEffect(()=>{loadLogs();api.getSchedulerConfig().then(r=>setCfg(r.data)).catch(()=>{});const t=setInterval(loadLogs,15000);return()=>clearInterval(t)},[loadLogs]);

  const trig=async(action,label)=>{
    setRunning(true);
    try{const r=await api.triggerAction(action);toast.show(r.data?.message||`${label} triggered`)}
    catch(e){toast.show(e.response?.data?.detail||`${label} failed`,'error')}
    setRunning(false);setTimeout(loadLogs,2000);
  };

  const toggleFlag=async(field)=>{
    if(!cfg)return;
    const v=!cfg[field];
    try{await api.updateSchedulerConfig({[field]:v});setCfg(p=>({...p,[field]:v}));toast.show(`${field} → ${v?'ON':'OFF'}`)}
    catch{toast.show('Failed','error')}
  };

  return (
    <div><toast.El/>
      <div className="page-header">
        <h2>Scheduler & Pipeline</h2>
        <div className="btn-group" style={{flexWrap:'wrap',gap:6}}>
          <button className="btn btn-india btn-sm" disabled={running} onClick={()=>trig('trigger_pipeline','Full Pipeline')}><IC.Play/>{running?'Running…':'Full Pipeline'}</button>
          <button className="btn btn-secondary btn-sm" onClick={()=>trig('trigger_scrape','Scrape')}><IC.Globe/>Scrape</button>
          <button className="btn btn-sm" style={{background:'#6200ea',color:'#fff',border:'none'}} onClick={()=>trig('trigger_ai','AI')}><IC.Gear/>AI</button>
          <button className="btn btn-secondary btn-sm" onClick={()=>trig('trigger_ranking','Rank')}><IC.Star/>Rank</button>
          <button className="btn btn-sm" style={{background:'#FF9900',color:'#fff',border:'none'}} onClick={()=>trig('trigger_sync','AWS')}><IC.AWS/>AWS</button>
          <button className="btn btn-sm" style={{background:'#1877F2',color:'#fff',border:'none'}} onClick={()=>trig('trigger_social','Social')}><IC.Social/>Social</button>
          <button className="btn btn-secondary btn-sm" onClick={()=>trig('trigger_cleanup','Cleanup')}>Cleanup</button>
          <button className="btn btn-secondary btn-sm" onClick={loadLogs}><IC.Ref/></button>
        </div>
      </div>

      {cfg&&(
        <div className="card" style={{marginBottom:16}}>
          <div className="card-header"><h3>Schedule Config</h3></div>
          <div className="table-container"><table className="table">
            <thead><tr><th>Job</th><th>Status</th><th>Minutes</th><th>Toggle</th></tr></thead>
            <tbody>{[
              {l:'Scrape',f:'scrape_enabled',m:'scrape_minutes'},
              {l:'AI Enrichment',f:'ai_enabled',m:'ai_minutes'},
              {l:'Top-100 Ranking',f:'ranking_enabled',m:'ranking_minutes'},
              {l:'AWS Sync',f:'aws_sync_enabled',m:'aws_sync_minutes'},
              {l:'Category Counts',f:'category_count_enabled',m:'category_minutes'},
              {l:'Cleanup',f:'cleanup_enabled',m:'cleanup_minutes'},
              {l:'Social Posting',f:'social_enabled',m:'social_minutes'},
            ].map(j=>(
              <tr key={j.f}>
                <td style={{fontWeight:600}}>{j.l}</td>
                <td><span className={`badge ${cfg[j.f]?'badge-enabled':'badge-disabled'}`}>{cfg[j.f]?'ON':'OFF'}</span></td>
                <td style={{fontFamily:'var(--mono)',fontSize:12}}>:{cfg[j.m]}</td>
                <td><button className={`btn btn-sm ${cfg[j.f]?'btn-danger':'btn-success'}`} onClick={()=>toggleFlag(j.f)}>{cfg[j.f]?'Disable':'Enable'}</button></td>
              </tr>
            ))}</tbody>
          </table></div>
        </div>
      )}

      <div style={{fontSize:12,color:'var(--text-muted)',marginBottom:8}}>Auto-refreshes every 15s</div>
      {ld&&logs.length===0?<div className="loading"><div className="spinner"/></div>:
      <div className="table-container"><table className="table">
        <thead><tr><th>ID</th><th>Job</th><th>Status</th><th>OK</th><th>ERR</th><th>Duration</th><th>Triggered By</th><th>Started</th></tr></thead>
        <tbody>{logs.map(l=>(
          <tr key={l.id}>
            <td style={{fontFamily:'var(--mono)',fontSize:11}}>{l.id}</td>
            <td style={{fontWeight:600,fontSize:12}}>{l.job_name}</td>
            <td><StatusBadge status={l.status}/></td>
            <td style={{color:'var(--india-green)',fontWeight:600}}>{l.rows_ok}</td>
            <td style={{color:l.rows_err>0?'var(--india-red)':'var(--text-muted)'}}>{l.rows_err}</td>
            <td style={{fontFamily:'var(--mono)',fontSize:11}}>{l.duration_s?(l.duration_s.toFixed(1)+'s'):'—'}</td>
            <td style={{fontSize:11,color:'var(--text-muted)'}}>{l.triggered_by||'cron'}</td>
            <td style={{fontFamily:'var(--mono)',fontSize:10}}>{new Date(l.started_at).toLocaleString()}</td>
          </tr>
        ))}
        {logs.length===0&&<tr><td colSpan="8" className="empty-state">No logs yet</td></tr>}
        </tbody>
      </table></div>}
    </div>
  );
}

// ─── YouTube Page ─────────────────────────────────────────────────────
function YouTubePage() {
  const [url,setUrl]=useState('');const [result,setResult]=useState(null);const [ld,setLd]=useState(false);const [saving,setSaving]=useState(false);const [sources,setSrc]=useState([]);const [srcId,setSrcId]=useState('');const toast=useToast();
  useEffect(()=>{api.getSources().then(r=>setSrc(r.data)).catch(()=>{})},[]);
  const process=async()=>{if(!url){toast.show('Enter a YouTube URL','warn');return;}setLd(true);setResult(null);try{const r=await api.processYouTube(url,parseInt(srcId)||undefined);setResult(r.data);toast.show('Transcript processed ✓')}catch(e){toast.show(e.response?.data?.detail||'Failed','error')}setLd(false)};
  const save=async()=>{if(!result)return;setSaving(true);try{await api.saveYouTubeArticle({video_url:result.video_url,title:result.rephrased_title,content:result.rephrased_content,category:result.category,tags:[],image_url:result.thumbnail_url,source_id:parseInt(srcId)||undefined,telugu_title:result.telugu_title||'',telugu_content:result.telugu_content||''});toast.show('Saved to Top News ✓');setResult(null);setUrl('')}catch(e){toast.show(e.response?.data?.detail||'Failed','error')}setSaving(false)};
  return (
    <div><toast.El/>
      <div className="page-header"><h2>YouTube Import</h2></div>
      <div className="card" style={{marginBottom:16}}>
        <div style={{display:'flex',gap:12,alignItems:'flex-end',flexWrap:'wrap'}}>
          <div style={{flex:1}}><label style={{fontSize:11,color:'var(--text-muted)',display:'block',marginBottom:4}}>YOUTUBE URL</label><input className="form-input" value={url} onChange={e=>setUrl(e.target.value)} placeholder="https://youtube.com/watch?v=…" onKeyDown={e=>e.key==='Enter'&&process()}/></div>
          <div><label style={{fontSize:11,color:'var(--text-muted)',display:'block',marginBottom:4}}>SOURCE</label><select className="form-select" value={srcId} onChange={e=>setSrcId(e.target.value)}><option value="">Default</option>{sources.map(s=><option key={s.id} value={s.id}>{s.name}</option>)}</select></div>
          <button className="btn btn-india" onClick={process} disabled={ld}><IC.Play/>{ld?'Processing…':'Fetch & Process'}</button>
        </div>
        <p style={{fontSize:12,color:'var(--text-muted)',marginTop:8}}>YouTube URL → transcript → AI rephrase (English + Telugu) → save as Top News</p>
      </div>
      {ld&&<div className="loading"><div className="spinner"/>Fetching transcript and running AI…</div>}
      {result&&!result.error&&(
        <div className="card">
          <div className="card-header"><h3>Preview</h3><button className="btn btn-india" onClick={save} disabled={saving}>{saving?'Saving…':'Save to Top News'}</button></div>
          {result.thumbnail_url&&<img src={result.thumbnail_url} alt="" style={{width:'100%',maxWidth:480,borderRadius:8,marginBottom:16}}/>}
          <div style={{marginBottom:12}}><div style={{fontSize:11,color:'var(--text-muted)',marginBottom:4}}>AI TITLE</div><h3 dangerouslySetInnerHTML={{__html:result.rephrased_title}}/></div>
          <div style={{marginBottom:12}}><div style={{fontSize:11,color:'var(--text-muted)',marginBottom:4}}>CATEGORY</div><span className="badge badge-new">{result.category}</span></div>
          <div style={{marginBottom:12}}><div style={{fontSize:11,color:'var(--accent)',marginBottom:4}}>REPHRASED CONTENT</div><div style={{background:'var(--bg-input)',padding:14,borderRadius:8,fontSize:13,lineHeight:1.7,maxHeight:280,overflowY:'auto'}} dangerouslySetInnerHTML={{__html:result.rephrased_content}}/></div>
          {result.telugu_title&&<div style={{marginBottom:12}}><div style={{fontSize:11,color:'var(--india-saffron)',marginBottom:4}}>TELUGU TITLE</div><p style={{fontFamily:'Noto Sans Telugu,sans-serif',fontSize:15}}>{result.telugu_title}</p></div>}
        </div>
      )}
      {result?.error&&<div className="card" style={{borderColor:'var(--india-red)'}}><div style={{color:'var(--india-red)',fontWeight:600}}>Error: {result.error}</div></div>}
    </div>
  );
}

// ─── Users Page ───────────────────────────────────────────────────────
function UsersPage() {
  const [users,setUsers]=useState([]);const [ld,setLd]=useState(true);const [show,setShow]=useState(false);const toast=useToast();
  const load=()=>{setLd(true);api.getUsers().then(r=>{setUsers(r.data);setLd(false)}).catch(()=>setLd(false))};
  useEffect(()=>{load()},[]);
  return (
    <div><toast.El/>
      <div className="page-header"><h2>Users ({users.length})</h2><button className="btn btn-india" onClick={()=>setShow(true)}><IC.Plus/>Add User</button></div>
      {ld?<div className="loading"><div className="spinner"/></div>:
      <div className="table-container"><table className="table">
        <thead><tr><th>ID</th><th>Username</th><th>Email</th><th>Role</th><th>Active</th><th>Last Login</th><th>Actions</th></tr></thead>
        <tbody>{users.map(u=>(
          <tr key={u.id}>
            <td style={{fontFamily:'var(--mono)',fontSize:11}}>{u.id}</td>
            <td style={{fontWeight:600}}>{u.username}</td>
            <td style={{fontSize:12}}>{u.email||'—'}</td>
            <td><span className={`badge ${u.role==='admin'?'badge-top':'badge-new'}`}>{u.role.toUpperCase()}</span></td>
            <td>{u.is_active?<span className="badge badge-enabled">YES</span>:<span className="badge badge-disabled">NO</span>}</td>
            <td style={{fontFamily:'var(--mono)',fontSize:10}}>{u.last_login_at?new Date(u.last_login_at).toLocaleString():'Never'}</td>
            <td><div className="btn-group">
              {u.role==='reporter'&&<button className="btn btn-secondary btn-sm" onClick={async()=>{await api.updateUser(u.id,{role:'admin'});toast.show('Promoted ✓');load()}}>→Admin</button>}
              {u.role==='admin'&&u.username!=='admin'&&<button className="btn btn-secondary btn-sm" onClick={async()=>{await api.updateUser(u.id,{role:'reporter'});toast.show('Changed');load()}}>→Reporter</button>}
              {u.username!=='admin'&&<button className="btn btn-danger btn-sm" onClick={async()=>{if(window.confirm(`Deactivate ${u.username}?`)){await api.deleteUser(u.id);toast.show('Deactivated');load()}}}>Deactivate</button>}
            </div></td>
          </tr>
        ))}</tbody>
      </table></div>}
      {show&&<UserModal onClose={()=>setShow(false)} onDone={()=>{setShow(false);toast.show('User created ✓');load()}}/>}
    </div>
  );
}

function UserModal({onClose,onDone}) {
  const [f,setF]=useState({username:'',password:'',email:'',role:'reporter'});const [sv,setSv]=useState(false);
  const go=async()=>{if(!f.username||!f.password)return;setSv(true);try{await api.createUser(f);onDone()}catch(e){alert(e.response?.data?.detail||'Failed');setSv(false)}};
  return (
    <div className="modal-overlay" onClick={onClose}><div className="modal" onClick={e=>e.stopPropagation()}>
      <h3>Create User</h3>
      <div className="grid-2">
        <div className="form-group"><label>Username *</label><input className="form-input" value={f.username} onChange={e=>setF({...f,username:e.target.value})}/></div>
        <div className="form-group"><label>Password *</label><input className="form-input" type="password" value={f.password} onChange={e=>setF({...f,password:e.target.value})}/></div>
      </div>
      <div className="grid-2">
        <div className="form-group"><label>Email</label><input className="form-input" value={f.email} onChange={e=>setF({...f,email:e.target.value})}/></div>
        <div className="form-group"><label>Role</label><select className="form-select" value={f.role} onChange={e=>setF({...f,role:e.target.value})}><option value="reporter">Reporter</option><option value="admin">Admin</option></select></div>
      </div>
      <div className="modal-actions"><button className="btn btn-secondary" onClick={onClose}>Cancel</button><button className="btn btn-india" onClick={go} disabled={sv}>{sv?'Creating…':'Create'}</button></div>
    </div></div>
  );
}

// ─── Reporter pages ───────────────────────────────────────────────────
function ReporterSubmitPage() {
  const [sources,setSrc]=useState([]);
  const pf = sources.find(s => s.name.toLowerCase() === 'peoples feedback' || s.name.toLowerCase() === 'peoplesfeedback');
  const [f,setF]=useState({title:'',content:'',category:'Home',tags:'',source_id:'',image_url:''});
  const [sv,setSv]=useState(false);const toast=useToast();
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef(null);

  const handleImgUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const r = await api.uploadImage(file);
      setF(prev => ({ ...prev, image_url: r.data.url }));
      toast.show('Image uploaded!');
    } catch(err) { toast.show('Upload failed: ' + (err.response?.data?.detail || err.message), 'error'); }
    setUploading(false);
  };
  
  useEffect(() => {
    if (pf && !f.source_id) setF(prev => ({ ...prev, source_id: pf.id }));
  }, [pf]);

  useEffect(()=>{api.getSources().then(r=>setSrc(r.data)).catch(()=>{})},[]);
  const go=async()=>{if(!f.title||!f.content){toast.show('Title and content required','warn');return;}setSv(true);try{await api.submitArticle({title:f.title,content:f.content,category:f.category,tags:f.tags?f.tags.split(',').map(t=>t.trim()):[],source_id:parseInt(f.source_id)||undefined,image_url:f.image_url||undefined});toast.show('Submitted for review ✓');setF({title:'',content:'',category:'Home',tags:'',source_id:pf?.id||'',image_url:''})}catch(e){toast.show(e.response?.data?.detail||'Failed','error')}setSv(false)};
  return (
    <div><toast.El/>
      <div className="page-header"><h2>Submit Article</h2></div>
      <div className="card" style={{maxWidth:800}}>
        <div style={{padding:'10px 14px',background:'var(--accent-dim)',borderRadius:8,marginBottom:16,fontSize:13,color:'var(--accent)'}}>
          Your article will be reviewed by an admin before publishing.
        </div>
        <div className="form-group"><label>Title *</label><input className="form-input" value={f.title} onChange={e=>setF({...f,title:e.target.value})}/></div>
        <div className="form-group"><label>Content *</label><textarea className="form-textarea" rows={8} value={f.content} onChange={e=>setF({...f,content:e.target.value})}/></div>
        <div className="grid-2">
          <div className="form-group"><label>Category</label><select className="form-select" value={f.category} onChange={e=>setF({...f,category:e.target.value})}>{CATS.map(c=><option key={c}>{c}</option>)}</select></div>
          <div className="form-group"><label>Source</label><select className="form-select" value={f.source_id} disabled><option value={f.source_id}>{pf?.name || 'Peoples Feedback'}</option></select></div>
        </div>
        <div className="grid-2">
          <div className="form-group"><label>Image (URL or Upload)</label>
            <div style={{display:'flex',gap:8,alignItems:'center'}}>
              <input className="form-input" style={{flex:1}} value={f.image_url} onChange={e=>setF({...f,image_url:e.target.value})} placeholder="Paste image URL or click Upload"/>
              <input type="file" ref={fileInputRef} accept="image/*" onChange={handleImgUpload} style={{display:'none'}} />
              <button type="button" className="btn" onClick={()=>fileInputRef.current?.click()} disabled={uploading} style={{whiteSpace:'nowrap',display:'flex',alignItems:'center',gap:4}}>
                <IC.Upload style={{width:14,height:14}}/>{uploading ? 'Uploading...' : 'Upload'}
              </button>
            </div>
            {f.image_url && <img src={f.image_url} alt="Preview" style={{width:100,height:60,objectFit:'cover',borderRadius:8,marginTop:8,border:'2px solid var(--border-light)'}}/>}
          </div>
          <div className="form-group"><label>Tags</label><input className="form-input" value={f.tags} onChange={e=>setF({...f,tags:e.target.value})} placeholder="tag1, tag2"/></div>
        </div>
        <button className="btn btn-india" onClick={go} disabled={sv} style={{marginTop:8}}><IC.Send/>{sv?'Submitting…':'Submit for Review'}</button>
      </div>
    </div>
  );
}

function MySubmissionsPage() {
  const [articles,setArticles]=useState([]);const [total,setTotal]=useState(0);const [page,setPage]=useState(1);const [tp,setTp]=useState(1);const [ld,setLd]=useState(true);
  const load=useCallback(()=>{setLd(true);api.getMySubmissions({page,page_size:20}).then(r=>{setArticles(r.data.articles);setTotal(r.data.total);setTp(Math.ceil(r.data.total/20));setLd(false)}).catch(()=>setLd(false))},[page]);
  useEffect(()=>{load()},[load]);
  return (
    <div>
      <div className="page-header"><h2>My Submissions <span style={{fontSize:14,color:'var(--text-muted)',fontWeight:400}}>({total})</span></h2></div>
      {ld?<div className="loading"><div className="spinner"/></div>:
      <div className="table-container"><table className="table">
        <thead><tr><th>ID</th><th>Title</th><th>Category</th><th>Status</th><th>Submitted</th></tr></thead>
        <tbody>
          {articles.map(a=><tr key={a.id}><td style={{fontFamily:'var(--mono)',fontSize:11}}>{a.id}</td><td style={{fontWeight:500}}>{a.original_title}</td><td>{a.category||'—'}</td><td><FlagBadge flag={a.flag}/></td><td style={{fontFamily:'var(--mono)',fontSize:10}}>{a.created_at?new Date(a.created_at).toLocaleString():'—'}</td></tr>)}
          {articles.length===0&&<tr><td colSpan="5" className="empty-state">No submissions yet</td></tr>}
        </tbody>
      </table></div>}
      {tp>1&&<div className="pagination"><button disabled={page<=1} onClick={()=>setPage(p=>p-1)}>← Prev</button><span>{page}/{tp}</span><button disabled={page>=tp} onClick={()=>setPage(p=>p+1)}>Next →</button></div>}
    </div>
  );
}

// ─── Settings Page ────────────────────────────────────────────────────
function SettingsPage() {
  const [cfg,setCfg]=useState(null);const [ld,setLd]=useState(true);const toast=useToast();
  useEffect(()=>{api.getSchedulerConfig().then(r=>{setCfg(r.data);setLd(false)}).catch(()=>setLd(false))},[]);
  const trig=async(a,l)=>{try{const r=await api.triggerAction(a);toast.show(r.data?.message||`${l} triggered`)}catch(e){toast.show(e.response?.data?.detail||'Failed','error')}};
  if(ld)return <div className="loading"><div className="spinner"/></div>;
  return (
    <div><toast.El/>
      <div className="page-header"><h2>Platform Settings</h2></div>
      <div className="grid-2">
        <div className="card"><div className="card-header"><h3>AI Configuration</h3></div>
          <div style={{fontSize:13,lineHeight:2,padding:'0 4px'}}>
            <div><strong>Provider Chain:</strong> {cfg?.ai_provider_chain?.join(' → ')||'Not set'}</div>
            <div><strong>Batch Size:</strong> {cfg?.ai_batch_size}</div>
            <div><strong>Workers:</strong> {cfg?.ai_concurrency}</div>
          </div>
        </div>
        <div className="card"><div className="card-header"><h3>Article Flow</h3></div>
          <div style={{display:'flex',gap:6,alignItems:'center',flexWrap:'wrap',padding:'8px 0'}}>
            {[{f:'P',l:'Pending'},{f:'N',l:'New'},{f:'A',l:'AI Done'},{f:'Y',l:'Top News'}].map((s,i)=>(
              <React.Fragment key={s.f}><div style={{textAlign:'center',padding:8,background:'var(--bg-input)',borderRadius:6,minWidth:72}}><FlagBadge flag={s.f}/><div style={{fontSize:10,marginTop:4,color:'var(--text-muted)'}}>{s.l}</div></div>{i<3&&<span style={{color:'var(--text-muted)',fontSize:18}}>→</span>}</React.Fragment>
            ))}
          </div>
          <p style={{fontSize:11,color:'var(--text-muted)',marginTop:8}}>Reporters submit (P) → Admin approves (N) → AI processes (A) → Rank selects Top 100 (Y)</p>
        </div>
      </div>
      <div className="card" style={{marginTop:16}}>
        <div className="card-header"><h3>Quick Actions</h3></div>
        <div style={{display:'flex',gap:8,flexWrap:'wrap'}}>
          <button className="btn btn-india" onClick={()=>trig('trigger_pipeline','Full Pipeline')}><IC.Play/>Full Pipeline</button>
          <button className="btn btn-secondary" onClick={()=>trig('trigger_scrape','Scrape')}><IC.Globe/>Scrape All</button>
          <button className="btn btn-sm" style={{background:'#6200ea',color:'#fff',border:'none'}} onClick={()=>trig('trigger_ai','AI')}><IC.Gear/>AI Process</button>
          <button className="btn btn-secondary" onClick={()=>trig('trigger_ranking','Ranking')}><IC.Star/>Update Ranking</button>
          <button className="btn btn-sm" style={{background:'#FF9900',color:'#fff',border:'none'}} onClick={()=>trig('trigger_sync','AWS')}><IC.AWS/>AWS Sync</button>
          <button className="btn btn-sm" style={{background:'#1877F2',color:'#fff',border:'none'}} onClick={()=>trig('trigger_social','Social')}><IC.Social/>Post Social</button>
          <button className="btn btn-danger" onClick={()=>trig('trigger_cleanup','Cleanup')}>Cleanup Old</button>
        </div>
      </div>
    </div>
  );
}

// ─── Polls Management Page ───────────────────────────────────────────
function PollsManagementPage() {
  const [polls, setPolls] = useState([]);
  const [ld, setLd] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const toast = useToast();

  const load = useCallback(() => {
    setLd(true);
    api.getPolls().then(r => {
      setPolls(r.data);
      setLd(false);
    }).catch(() => setLd(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  return (
    <div>
      <toast.El />
      <div className="page-header">
        <h2>Polls Management <span style={{fontSize:14,color:'var(--text-muted)',fontWeight:400}}>({polls.length})</span></h2>
        <button className="btn btn-india" onClick={() => setShowCreate(true)}><IC.Plus />Create Poll</button>
      </div>

      {ld ? <div className="loading"><div className="spinner" /></div> : (
        <div className="grid-2">
          {polls.map(p => (
            <div key={p.id} className="card">
              <div className="card-header">
                <h3>{p.question}</h3>
                <span className={`badge ${p.is_active ? 'badge-enabled' : 'badge-disabled'}`}>
                  {p.is_active ? 'ACTIVE' : 'EXPIRED'}
                </span>
              </div>
              <div style={{padding:16}}>
                <div className="space-y-2">
                  {p.options.map(o => (
                    <div key={o.id} style={{display:'flex',justifyContent:'space-between',fontSize:13,background:'var(--bg-input)',padding:'8px 12px',borderRadius:6}}>
                      <span style={{fontWeight:600}}>{o.option_text}</span>
                      <span style={{color:'var(--accent)',fontFamily:'var(--mono)'}}>{o.votes_count} votes</span>
                    </div>
                  ))}
                </div>
                <div style={{marginTop:16,fontSize:11,color:'var(--text-muted)'}}>
                  Created: {new Date(p.created_at).toLocaleDateString()}
                </div>
              </div>
            </div>
          ))}
          {polls.length === 0 && <div className="empty-state">No polls created yet</div>}
        </div>
      )}

      {showCreate && <CreatePollModal onClose={() => setShowCreate(false)} onDone={() => { setShowCreate(false); toast.show('Poll created ✓'); load(); }} />}
    </div>
  );
}

function CreatePollModal({ onClose, onDone }) {
  const [q, setQ] = useState('');
  const [opts, setOpts] = useState(['', '']);
  const [sv, setSv] = useState(false);

  const go = async () => {
    if (!q || opts.some(o => !o)) return;
    setSv(true);
    try {
      await api.createPoll({
        question: q,
        options: opts.map(o => ({ option_text: o })),
        is_active: true
      });
      onDone();
    } catch { setSv(false); alert('Failed to create poll'); }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <h3>Create New Poll</h3>
        <div className="form-group">
          <label>Question *</label>
          <input className="form-input" value={q} onChange={e => setQ(e.target.value)} placeholder="e.g. Which party will win?" />
        </div>
        <div className="form-group">
          <label>Options *</label>
          <div className="space-y-2">
            {opts.map((o, i) => (
              <div key={i} style={{ display: 'flex', gap: 8 }}>
                <input className="form-input" value={o} onChange={e => {
                  const n = [...opts];
                  n[i] = e.target.value;
                  setOpts(n);
                }} placeholder={`Option ${i + 1}`} />
                {opts.length > 2 && (
                  <button className="btn btn-secondary btn-sm" onClick={() => setOpts(opts.filter((_, idx) => idx !== i))}>✕</button>
                )}
              </div>
            ))}
          </div>
          <button className="btn btn-secondary btn-sm" style={{marginTop:8}} onClick={() => setOpts([...opts, ''])}>+ Add Option</button>
        </div>
        <div className="modal-actions">
          <button className="btn btn-secondary" onClick={onClose}>Cancel</button>
          <button className="btn btn-india" onClick={go} disabled={sv}>
            {sv ? 'Creating…' : 'Create Poll'}
          </button>
        </div>
      </div>
    </div>
  );
}

function SurveysManagementPage() {
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
        <h2>Survey Results <span style={{fontSize:14,color:'var(--text-muted)',fontWeight:400}}>({arts.length})</span></h2>
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
                  <td style={{fontSize:11}}>{new Date(a.published_at||a.created_at).toLocaleDateString()}</td>
                  <td style={{fontWeight:600}}>{a.rephrased_title || a.original_title}</td>
                  <td style={{fontSize:11}}>{a.source_name}</td>
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

// ─── Shells ───────────────────────────────────────────────────────────
function WishesManagementPage() {
  const toast = useToast();
  const [wishes, setWishes] = React.useState([]);
  const [loading, setLoading] = React.useState(true);
  const [showCreate, setShowCreate] = React.useState(false);
  const [form, setForm] = React.useState({title:'',message:'',wish_type:'birthday',person_name:'',image_url:'',display_on_home:false,occasion_date:'',expires_at:''});
  const [uploading, setUploading] = React.useState(false);
  const fileRef = React.useRef(null);

  const load = async () => {
    try { const r = await api.getWishes(); setWishes(r.data); } catch(e) { toast.show('Failed to load wishes','error'); }
    setLoading(false);
  };
  React.useEffect(() => { load(); }, []);

  const handleImageUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const r = await api.uploadImage(file);
      setForm(f => ({...f, image_url: r.data.url}));
      toast.show('Image uploaded!');
    } catch(err) {
      toast.show('Upload failed: ' + (err.response?.data?.detail || err.message), 'error');
    }
    setUploading(false);
  };

  const handleCreate = async () => {
    if (!form.title.trim()) { toast.show('Title required','error'); return; }
    try {
      const payload = {...form};
      if (!payload.occasion_date) delete payload.occasion_date;
      if (!payload.expires_at) delete payload.expires_at;
      await api.createWish(payload);
      toast.show('Wish created!');
      setShowCreate(false);
      setForm({title:'',message:'',wish_type:'birthday',person_name:'',image_url:'',display_on_home:false,occasion_date:'',expires_at:''});
      load();
    } catch(e) { toast.show('Failed: ' + (e.response?.data?.detail || e.message), 'error'); }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Deactivate this wish?')) return;
    try { await api.deleteWish(id); toast.show('Wish deactivated'); load(); } catch(e) { toast.show('Failed','error'); }
  };

  const typeColors = {birthday:'#e91e63',festival:'#ff9800',anniversary:'#f44336',custom:'#673ab7'};

  return (
    <div className="page">
      <toast.El/>
      <div className="page-header">
        <div><h2>Wishes & Greetings</h2><p>Birthday, festival, and special occasion wishes</p></div>
        <button className="btn btn-primary" onClick={()=>setShowCreate(!showCreate)}><IC.Plus style={{width:16,height:16}}/> Create Wish</button>
      </div>

      {showCreate && (
        <div className="card" style={{marginBottom:24}}>
          <div style={{padding:20}}>
            <h3 style={{margin:'0 0 16px',fontSize:16,fontWeight:700}}>New Wish</h3>
            <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:12}}>
              <div><label style={{fontSize:11,fontWeight:700,textTransform:'uppercase',letterSpacing:1,color:'var(--text-muted)'}}>Title *</label>
                <input className="input" value={form.title} onChange={e=>setForm(f=>({...f,title:e.target.value}))} placeholder="Happy Birthday to..." /></div>
              <div><label style={{fontSize:11,fontWeight:700,textTransform:'uppercase',letterSpacing:1,color:'var(--text-muted)'}}>Person Name</label>
                <input className="input" value={form.person_name} onChange={e=>setForm(f=>({...f,person_name:e.target.value}))} placeholder="Name of the person" /></div>
              <div><label style={{fontSize:11,fontWeight:700,textTransform:'uppercase',letterSpacing:1,color:'var(--text-muted)'}}>Type</label>
                <select className="input" value={form.wish_type} onChange={e=>setForm(f=>({...f,wish_type:e.target.value}))}>
                  <option value="birthday">Birthday</option><option value="festival">Festival</option>
                  <option value="anniversary">Anniversary</option><option value="custom">Custom / Special</option>
                </select></div>
              <div><label style={{fontSize:11,fontWeight:700,textTransform:'uppercase',letterSpacing:1,color:'var(--text-muted)'}}>Occasion Date</label>
                <input className="input" type="datetime-local" value={form.occasion_date} onChange={e=>setForm(f=>({...f,occasion_date:e.target.value}))} /></div>
              <div style={{gridColumn:'1/-1'}}><label style={{fontSize:11,fontWeight:700,textTransform:'uppercase',letterSpacing:1,color:'var(--text-muted)'}}>Message</label>
                <textarea className="input" rows={3} value={form.message} onChange={e=>setForm(f=>({...f,message:e.target.value}))} placeholder="Write your heartfelt message..." /></div>
              <div><label style={{fontSize:11,fontWeight:700,textTransform:'uppercase',letterSpacing:1,color:'var(--text-muted)'}}>Image</label>
                <div style={{display:'flex',gap:8,alignItems:'center'}}>
                  <input className="input" value={form.image_url} onChange={e=>setForm(f=>({...f,image_url:e.target.value}))} placeholder="Image URL or upload" style={{flex:1}} />
                  <input type="file" ref={fileRef} accept="image/*" onChange={handleImageUpload} style={{display:'none'}} />
                  <button className="btn" onClick={()=>fileRef.current?.click()} disabled={uploading} style={{whiteSpace:'nowrap'}}>
                    {uploading ? 'Uploading...' : 'Upload'}
                  </button>
                </div>
                {form.image_url && <img src={form.image_url} alt="" style={{width:80,height:60,objectFit:'cover',borderRadius:8,marginTop:8,border:'2px solid var(--border-light)'}} />}
              </div>
              <div><label style={{fontSize:11,fontWeight:700,textTransform:'uppercase',letterSpacing:1,color:'var(--text-muted)'}}>Expires At</label>
                <input className="input" type="datetime-local" value={form.expires_at} onChange={e=>setForm(f=>({...f,expires_at:e.target.value}))} /></div>
              <div style={{gridColumn:'1/-1',display:'flex',alignItems:'center',gap:8}}>
                <input type="checkbox" checked={form.display_on_home} onChange={e=>setForm(f=>({...f,display_on_home:e.target.checked}))} id="wish-home" />
                <label htmlFor="wish-home" style={{fontSize:13,fontWeight:600}}>Display on Homepage</label>
              </div>
            </div>
            <div style={{display:'flex',gap:8,marginTop:16}}>
              <button className="btn btn-primary" onClick={handleCreate}>Create Wish</button>
              <button className="btn" onClick={()=>setShowCreate(false)}>Cancel</button>
            </div>
          </div>
        </div>
      )}

      {loading ? <div style={{textAlign:'center',padding:40,color:'var(--text-muted)'}}>Loading...</div> : (
        <div className="card">
          <table className="data-table" style={{width:'100%'}}>
            <thead><tr>
              <th>Image</th><th>Title</th><th>Type</th><th>Person</th><th>Home</th><th>Status</th><th>Actions</th>
            </tr></thead>
            <tbody>
              {wishes.map(w => (
                <tr key={w.id}>
                  <td>{w.image_url ? <img src={w.image_url} alt="" style={{width:48,height:36,objectFit:'cover',borderRadius:6}} /> : <span style={{color:'var(--text-muted)',fontSize:11}}>No image</span>}</td>
                  <td style={{fontWeight:700}}>{w.title}</td>
                  <td><span style={{background:typeColors[w.wish_type]||'#666',color:'#fff',padding:'2px 10px',borderRadius:20,fontSize:10,fontWeight:700,textTransform:'uppercase'}}>{w.wish_type}</span></td>
                  <td>{w.person_name || '—'}</td>
                  <td>{w.display_on_home ? <span className="badge badge-enabled">YES</span> : <span className="badge">NO</span>}</td>
                  <td>{w.is_active ? <span className="badge badge-enabled">Active</span> : <span className="badge badge-deleted">Inactive</span>}</td>
                  <td><button className="btn" style={{fontSize:11,padding:'4px 12px'}} onClick={()=>handleDelete(w.id)}>Deactivate</button></td>
                </tr>
              ))}
              {wishes.length===0 && <tr><td colSpan={7} style={{textAlign:'center',padding:30,color:'var(--text-muted)'}}>No wishes created yet</td></tr>}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function AdminShell({auth}) {
  return (
    <div className="app-layout">
      <Sidebar onLogout={auth.doLogout}/>
      <div className="main-content">
        <Routes>
          <Route path="/" element={<DashboardPage/>}/>
          <Route path="/articles" element={<ArticlesPage/>}/>
          <Route path="/pending" element={<PendingApprovalsPage/>}/>
          <Route path="/sources" element={<SourcesPage/>}/>
          <Route path="/top-news" element={<TopNewsPage/>}/>
          <Route path="/categories" element={<CategoriesPage/>}/>
          <Route path="/youtube" element={<YouTubePage/>}/>
          <Route path="/scheduler" element={<SchedulerPage/>}/>
          <Route path="/users" element={<UsersPage/>}/>
          <Route path="/polls" element={<PollsManagementPage/>}/>
          <Route path="/surveys" element={<SurveysManagementPage/>}/>
          <Route path="/wishes" element={<WishesManagementPage/>}/>
          <Route path="/settings" element={<SettingsPage/>}/>
          <Route path="*" element={<Navigate to="/"/>}/>
        </Routes>
      </div>
    </div>
  );
}

function ReporterShell({auth}) {
  return (
    <div className="app-layout">
      <Sidebar onLogout={auth.doLogout}/>
      <div className="main-content">
        <Routes>
          <Route path="/" element={<ReporterSubmitPage/>}/>
          <Route path="/my-submissions" element={<MySubmissionsPage/>}/>
          <Route path="*" element={<Navigate to="/"/>}/>
        </Routes>
      </div>
    </div>
  );
}

export default function App() {
  const auth = useAuth();
  return (
    <AuthContext.Provider value={auth}>
      <BrowserRouter basename={process.env.PUBLIC_URL || ''}>
        {!auth.isAuthenticated
          ? <Routes><Route path="*" element={<LoginPage onLogin={auth.doLogin}/>}/></Routes>
          : auth.isAdmin ? <AdminShell auth={auth}/> : <ReporterShell auth={auth}/>}
      </BrowserRouter>
    </AuthContext.Provider>
  );
}
