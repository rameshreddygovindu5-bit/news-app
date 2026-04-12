import React, { useState, useEffect, useCallback, createContext, useContext } from 'react';
import { BrowserRouter, Routes, Route, Navigate, Link, useLocation } from 'react-router-dom';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import * as api from './services/api';

const CATS = ['Home','World','Politics','Business','Tech','Health','Science','Entertainment','Events'];
const AuthContext = createContext(null);
const useAuthCtx = () => useContext(AuthContext);

function useAuth() {
  const [user, setUser] = useState(() => { try { return JSON.parse(localStorage.getItem('user')); } catch { return null; } });
  const [token, setToken] = useState(() => localStorage.getItem('token'));
  const doLogin = async (username, password) => {
    const r = await api.login(username, password);
    const { access_token, username: u, role } = r.data;
    localStorage.setItem('token', access_token); localStorage.setItem('user', JSON.stringify({ username: u, role }));
    setToken(access_token); setUser({ username: u, role });
  };
  const doLogout = () => { localStorage.removeItem('token'); localStorage.removeItem('user'); setToken(null); setUser(null); };
  return { user, token, doLogin, doLogout, isAuthenticated: !!token, isAdmin: user?.role === 'admin' };
}

function useToast() {
  const [msg, setMsg] = useState('');
  const show = (text) => { setMsg(text); setTimeout(() => setMsg(''), 3000); };
  const El = () => msg ? <div style={{ position:'fixed',top:20,right:20,zIndex:9999,background:'var(--green)',color:'#fff',padding:'12px 24px',borderRadius:8,fontWeight:600,fontSize:13,boxShadow:'0 8px 32px rgba(0,0,0,.4)' }}>{msg}</div> : null;
  return { show, El };
}

// ===== ICONS =====
const IC = {
  Dash:()=><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>,
  Doc:()=><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>,
  Globe:()=><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/></svg>,
  Star:()=><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>,
  Clock:()=><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>,
  Gear:()=><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>,
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
};

function FlagBadge({flag}) {
  const m={P:['PENDING','badge-paused'],N:['NEW','badge-new'],A:['AI DONE','badge-processed'],Y:['TOP','badge-top'],D:['DEL','badge-deleted']};
  const [l,c]=m[flag]||['?','']; return <span className={`badge ${c}`}>{l}</span>;
}

// ===== SIDEBAR (role-aware) =====
function Sidebar({onLogout}) {
  const loc = useLocation();
  const {user} = useAuthCtx();
  const isAdmin = user?.role === 'admin';

  const adminNav = [
    {p:'/',l:'Dashboard',i:IC.Dash},{p:'/articles',l:'Articles',i:IC.Doc},{p:'/pending',l:'Pending Approval',i:IC.Check},
    {p:'/sources',l:'Sources',i:IC.Globe},{p:'/top-news',l:'Top 100 News',i:IC.Star},{p:'/categories',l:'Categories',i:IC.List},
    {p:'/youtube',l:'YouTube Import',i:IC.YT},{p:'/scheduler',l:'Scheduler',i:IC.Clock},
    {p:'/users',l:'Users',i:IC.Users},{p:'/settings',l:'Settings',i:IC.Gear},
  ];
  const reporterNav = [
    {p:'/',l:'Submit Article',i:IC.Send},{p:'/my-submissions',l:'My Submissions',i:IC.Doc},
  ];

  const nav = isAdmin ? adminNav : reporterNav;
  return (<div className="sidebar"><div className="sidebar-brand"><h1>NewsAI</h1><span>{isAdmin?'Admin':'Reporter'} • {user?.username}</span></div>
    <nav className="sidebar-nav">{nav.map(n=><Link key={n.p} to={n.p} className={`nav-item ${loc.pathname===n.p?'active':''}`}><n.i/>{n.l}</Link>)}</nav>
    <div className="sidebar-footer"><button className="nav-item" onClick={onLogout}><IC.Out/>Logout</button></div></div>);
}

// ===== LOGIN =====
function LoginPage({onLogin}) {
  const [u,setU]=useState('');const [p,setP]=useState('');const [e,setE]=useState('');const [ld,setLd]=useState(false);
  const go=async(ev)=>{ev.preventDefault();setLd(true);setE('');try{await onLogin(u,p)}catch(err){setE(err.response?.data?.detail||'Login failed')}setLd(false)};
  return (<div className="login-page"><div className="login-card"><h2>NewsAI Platform</h2><p>Sign in to continue</p>
    {e&&<div className="error-msg">{e}</div>}
    <form onSubmit={go}><div className="form-group"><label>Username</label><input className="form-input" value={u} onChange={x=>setU(x.target.value)} required/></div>
    <div className="form-group"><label>Password</label><input className="form-input" type="password" value={p} onChange={x=>setP(x.target.value)} required/></div>
    <button className="btn btn-primary" style={{width:'100%',marginTop:8}} disabled={ld}>{ld?'Signing in...':'Sign In'}</button></form>
    <p style={{marginTop:20,fontSize:12,color:'var(--text-muted)'}}>Admin: admin/admin123 | Reporters: contact admin for access</p></div></div>);
}

// ===== DASHBOARD (admin) =====
function DashboardPage() {
  const [s,setS]=useState(null);const [ld,setLd]=useState(true);
  useEffect(()=>{api.getDashboardStats().then(r=>{setS(r.data);setLd(false)}).catch(()=>setLd(false))},[]);
  if(ld) return <div className="loading"><div className="spinner"/>Loading...</div>;
  if(!s) return <div className="empty-state"><p>Failed to load</p></div>;
  const CL=['#3b82f6','#10b981','#f59e0b','#ef4444','#8b5cf6','#f97316','#06b6d4','#ec4899'];

  return (
    <div className="dashboard-root">
      <div className="page-header">
        <h2>Sync Monitor Dashboard</h2>
        <div style={{display:'flex',gap:8}}>
          <span className={`badge ${s.aws?.status==='online'?'badge-enabled':'badge-paused'}`} style={{padding:'8px 16px',fontSize:12}}>
            AWS PRODUCTION: {s.aws?.status?.toUpperCase() || 'UNKNOWN'}
          </span>
          <button className="btn btn-secondary" onClick={()=>window.location.reload()}><IC.Ref/>Refresh</button>
        </div>
      </div>
      
      <div className="grid-2" style={{marginBottom:24}}>
        <div className="card">
          <div className="card-header"><h3 style={{color:'var(--accent)'}}>Local Engine (Source)</h3></div>
          <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:12,padding:20}}>
            <div className="stat-card blue"><div className="stat-label">Total News</div><div className="stat-value">{s.local?.total || 0}</div></div>
            <div className="stat-card green"><div className="stat-label">AI Processed</div><div className="stat-value">{s.local?.processed || 0}</div></div>
            <div className="stat-card yellow"><div className="stat-label">AI Pending</div><div className="stat-value">{s.local?.pending_ai || 0}</div></div>
            <div className="stat-card purple"><div className="stat-label">Top 100</div><div className="stat-value">{s.local?.top || 0}</div></div>
          </div>
        </div>
        
        <div className="card">
          <div className="card-header"><h3 style={{color:'var(--green)'}}>AWS Production (Live)</h3></div>
          <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:12,padding:20}}>
            <div className="stat-card blue"><div className="stat-label">AWS Total</div><div className="stat-value">{s.aws?.total || 0}</div></div>
            <div className="stat-card green"><div className="stat-label">AWS Processed</div><div className="stat-value">{s.aws?.processed || 0}</div></div>
            <div className="stat-card orange"><div className="stat-label">Sync Gap</div><div className="stat-value">{(s.local?.total || 0) - (s.aws?.total || 0)}</div></div>
            <div className="stat-card purple"><div className="stat-label">AWS Top News</div><div className="stat-value">{s.aws?.top || 0}</div></div>
          </div>
        </div>
      </div>

      <div className="grid-2" style={{marginBottom:24}}>
        <div className="card">
          <div className="card-header"><h3>Category Distribution</h3></div>
          <div style={{height:300}}>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={s.category_stats} dataKey="count" nameKey="category" cx="50%" cy="50%" outerRadius={100} label={({category})=>category}>
                  {s.category_stats?.map((_, i) => <Cell key={i} fill={CL[i % CL.length]} />)}
                </Pie>
                <Tooltip contentStyle={{background:'#1a2236',border:'none',borderRadius:8,color:'#fff'}}/>
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="card">
          <div className="card-header"><h3>Pipeline Health</h3></div>
          <div className="table-container">
            <table className="table">
              <thead><tr><th>Job</th><th>Status</th><th>OK/ERR</th></tr></thead>
              <tbody>
                {s.recent_scrapes?.slice(0,6).map(l=><tr key={l.id}>
                  <td style={{fontWeight:600}}>{l.job_name}</td>
                  <td><span className={`badge ${l.status==='DONE'?'badge-enabled':l.status==='RUNNING'?'badge-new':'badge-paused'}`}>{l.status}</span></td>
                  <td>{l.rows_ok}/{l.rows_err}</td>
                </tr>)}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header"><h3>Raw Debug Data (Temporary)</h3></div>
        <pre style={{fontSize:10,background:'#111',padding:10,overflow:'auto',maxHeight:200,color:'#0f0'}}>
          {JSON.stringify(s, null, 2)}
        </pre>
      </div>
    </div>
  );
}

// ===== REPORTER: SUBMIT ARTICLE =====
function ReporterSubmitPage() {
  const [f,setF]=useState({title:'',content:'',category:'General',tags:'',source_id:'',image_url:''});
  const [sources,setSrc]=useState([]);const [sv,setSv]=useState(false);const toast=useToast();
  useEffect(()=>{api.getSources().then(r=>setSrc(r.data)).catch(()=>{})},[]);

  const go=async()=>{
    if(!f.title||!f.content){toast.show('Title and content are required');return;}
    setSv(true);
    try{
      const r=await api.submitArticle({title:f.title,content:f.content,category:f.category,tags:f.tags?f.tags.split(',').map(t=>t.trim()):[],source_id:parseInt(f.source_id)||undefined,image_url:f.image_url||undefined});
      toast.show(r.data.message||'Article submitted!');
      setF({title:'',content:'',category:'General',tags:'',source_id:'',image_url:''});
    }catch(e){toast.show(e.response?.data?.detail||'Failed to submit')}
    setSv(false);
  };

  return (<div><toast.El/>
    <div className="page-header"><h2>Submit Article</h2></div>
    <div className="card" style={{maxWidth:800}}>
      <div style={{padding:'12px 16px',background:'var(--accent-dim)',borderRadius:8,marginBottom:20,fontSize:13,color:'var(--accent)'}}>
        Your article will be reviewed by an admin before publishing. Once approved, it goes through AI processing and gets published.
      </div>
      <div className="form-group"><label>Title *</label><input className="form-input" value={f.title} onChange={e=>setF({...f,title:e.target.value})} placeholder="Enter article headline"/></div>
      <div className="form-group"><label>Content *</label><textarea className="form-textarea" rows={8} value={f.content} onChange={e=>setF({...f,content:e.target.value})} placeholder="Write the full article content..."/></div>
      <div className="grid-2">
        <div className="form-group"><label>Category</label><select className="form-select" value={f.category} onChange={e=>setF({...f,category:e.target.value})}>{CATS.map(c=><option key={c}>{c}</option>)}<option>General</option></select></div>
        <div className="form-group"><label>Source</label><select className="form-select" value={f.source_id} onChange={e=>setF({...f,source_id:e.target.value})}><option value="">— Select —</option>{sources.map(s=><option key={s.id} value={s.id}>{s.name}</option>)}</select></div>
      </div>
      <div className="grid-2">
        <div className="form-group"><label>Image URL (optional)</label><input className="form-input" value={f.image_url} onChange={e=>setF({...f,image_url:e.target.value})}/></div>
        <div className="form-group"><label>Tags (comma-separated)</label><input className="form-input" value={f.tags} onChange={e=>setF({...f,tags:e.target.value})} placeholder="politics, india"/></div>
      </div>
      <button className="btn btn-primary" onClick={go} disabled={sv} style={{marginTop:8}}><IC.Send/>{sv?'Submitting...':'Submit for Review'}</button>
    </div>
  </div>);
}

// ===== REPORTER: MY SUBMISSIONS =====
function MySubmissionsPage() {
  const [articles,setArticles]=useState([]);const [total,setTotal]=useState(0);const [page,setPage]=useState(1);const [tp,setTp]=useState(1);const [ld,setLd]=useState(true);
  const load=useCallback(()=>{setLd(true);api.getMySubmissions({page,page_size:20}).then(r=>{setArticles(r.data.articles);setTotal(r.data.total);setTp(Math.ceil(r.data.total/20));setLd(false)}).catch(()=>setLd(false))},[page]);
  useEffect(()=>{load()},[load]);
  return (<div>
    <div className="page-header"><h2>My Submissions <span style={{fontSize:14,color:'var(--text-muted)',fontWeight:400}}>({total})</span></h2></div>
    {ld?<div className="loading"><div className="spinner"/></div>:<div className="table-container"><table><thead><tr><th>ID</th><th>Title</th><th>Category</th><th>Status</th><th>Submitted</th></tr></thead><tbody>
      {articles.map(a=><tr key={a.id}><td style={{fontFamily:'var(--mono)',fontSize:12}}>{a.id}</td><td style={{fontWeight:500,maxWidth:400}}>{a.original_title}</td><td>{a.category||'—'}</td><td><FlagBadge flag={a.flag}/></td><td style={{fontFamily:'var(--mono)',fontSize:11}}>{a.created_at?new Date(a.created_at).toLocaleString():'—'}</td></tr>)}
      {articles.length===0&&<tr><td colSpan="5" className="empty-state">No submissions yet. Submit your first article!</td></tr>}
    </tbody></table></div>}
    {tp>1&&<div className="pagination"><button disabled={page<=1} onClick={()=>setPage(p=>p-1)}>Prev</button><span>Page {page} of {tp}</span><button disabled={page>=tp} onClick={()=>setPage(p=>p+1)}>Next</button></div>}
  </div>);
}

// ===== ADMIN: PENDING APPROVAL QUEUE =====
function PendingApprovalsPage() {
  const [articles,setArticles]=useState([]);const [total,setTotal]=useState(0);const [ld,setLd]=useState(true);const [viewA,setViewA]=useState(null);const toast=useToast();
  const load=()=>{setLd(true);api.getPendingArticles({page:1,page_size:50}).then(r=>{setArticles(r.data.articles);setTotal(r.data.total);setLd(false)}).catch(()=>setLd(false))};
  useEffect(()=>{load()},[]);

  const doApprove=async(id,action)=>{
    try{await api.approveArticle(id,action);toast.show(`Article ${action}d!`);load()}catch(e){toast.show(e.response?.data?.detail||'Failed')}
  };

  return (<div><toast.El/>
    <div className="page-header"><h2>Pending Approval <span style={{fontSize:14,color:'var(--yellow)',fontWeight:400}}>({total} articles)</span></h2><button className="btn btn-secondary" onClick={load}><IC.Ref/>Refresh</button></div>
    {ld?<div className="loading"><div className="spinner"/></div>:
    articles.length===0?<div className="card" style={{textAlign:'center',padding:60,color:'var(--text-muted)'}}><IC.Check/><p style={{marginTop:12,fontSize:15}}>No articles pending approval</p></div>:
    <div className="table-container"><table><thead><tr><th>ID</th><th>Title</th><th>Category</th><th>Submitted By</th><th>Date</th><th>Actions</th></tr></thead><tbody>
      {articles.map(a=><tr key={a.id}>
        <td style={{fontFamily:'var(--mono)',fontSize:12}}>{a.id}</td>
        <td><div style={{fontWeight:500,cursor:'pointer',color:'var(--text-primary)'}} onClick={()=>setViewA(a)}>{a.original_title}</div><div className="truncate" style={{fontSize:11,color:'var(--text-muted)',marginTop:2,maxWidth:400}}>{a.original_content?.slice(0,120)}...</div></td>
        <td>{a.category||'—'}</td>
        <td><span className="badge badge-new">{a.submitted_by||'—'}</span></td>
        <td style={{fontFamily:'var(--mono)',fontSize:11}}>{a.created_at?new Date(a.created_at).toLocaleString():'—'}</td>
        <td><div className="btn-group">
          <button className="btn btn-success btn-sm" onClick={()=>doApprove(a.id,'approve')} title="Approve → AI Pipeline">Approve</button>
          <button className="btn btn-primary btn-sm" onClick={()=>doApprove(a.id,'approve_direct')} title="Approve → Direct to Top News">Direct Publish</button>
          <button className="btn btn-danger btn-sm" onClick={()=>doApprove(a.id,'reject')}>Reject</button>
          <button className="btn btn-secondary btn-sm" onClick={()=>setViewA(a)}><IC.Eye/></button>
        </div></td>
      </tr>)}
    </tbody></table></div>}
    {viewA&&<ArticleDetailModal article={viewA} onClose={()=>setViewA(null)}/>}
  </div>);
}

// ===== ARTICLE DETAIL MODAL =====
function ArticleDetailModal({article:a,onClose}) {
  if(!a)return null;
  return (<div className="modal-overlay" onClick={onClose}><div className="modal" style={{maxWidth:900}} onClick={e=>e.stopPropagation()}>
    <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:16}}><h3>Article #{a.id}</h3><button className="btn btn-secondary btn-sm" onClick={onClose}>✕</button></div>
    <div style={{display:'flex',gap:4,marginBottom:16,flexWrap:'wrap'}}><FlagBadge flag={a.flag}/>{a.category&&<span className="badge badge-new">{a.category}</span>}{a.submitted_by&&<span className="badge badge-paused">by {a.submitted_by}</span>}{(a.tags||[]).map(t=><span key={t} className="tag">{t}</span>)}</div>
    <div className="grid-2" style={{gap:16}}>
      <div style={{background:'var(--bg-input)',padding:16,borderRadius:8,border:'1px solid var(--border-light)'}}>
        <div style={{fontSize:11,color:'var(--text-muted)',textTransform:'uppercase',letterSpacing:1,marginBottom:8,fontWeight:600}}>Original</div>
        {a.image_url && <img src={a.image_url} alt="" style={{width:'100%',borderRadius:4,marginBottom:12,maxHeight:150,objectFit:'cover'}}/>}
        <h4 style={{fontSize:15,marginBottom:12,lineHeight:1.4}}>{a.original_title}</h4>
        <div style={{fontSize:13,color:'var(--text-secondary)',lineHeight:1.7,maxHeight:300,overflowY:'auto',whiteSpace:'pre-wrap'}}>{a.original_content||'No content'}</div></div>
      <div style={{background:'var(--bg-input)',padding:16,borderRadius:8,border:'1px solid var(--accent-dim)'}}>
        <div style={{fontSize:11,color:'var(--accent)',textTransform:'uppercase',letterSpacing:1,marginBottom:8,fontWeight:600}}>AI Rephrased</div>
        {a.image_url && <img src={a.image_url} alt="" style={{width:'100%',borderRadius:4,marginBottom:12,maxHeight:150,objectFit:'cover'}}/>}
        <h4 style={{fontSize:15,marginBottom:12,lineHeight:1.4,color:'var(--accent)'}} dangerouslySetInnerHTML={{__html:a.rephrased_title||a.original_title}}/>
        <div style={{fontSize:13,color:'var(--text-secondary)',lineHeight:1.7,maxHeight:300,overflowY:'auto'}} dangerouslySetInnerHTML={{__html:a.rephrased_content||'Not processed yet'}}/></div>
    </div>
    <div style={{marginTop:12,fontSize:11,color:'var(--text-muted)',background:'var(--bg-card)',padding:8,borderRadius:4}}>
        {a.original_url && <div><strong>Source URL:</strong> <a href={a.original_url} target="_blank" rel="noreferrer" style={{color:'var(--accent)'}}>{a.original_url}</a></div>}
        {a.image_url && <div style={{marginTop:4}}><strong>Image URL:</strong> <a href={a.image_url} target="_blank" rel="noreferrer" style={{color:'var(--accent)'}}>{a.image_url}</a></div>}
    </div>
  </div></div>);
}

// ===== ADMIN: ARTICLES PAGE =====
function ArticlesPage() {
  const [articles,setArticles]=useState([]);const [total,setTotal]=useState(0);const [page,setPage]=useState(1);const [tp,setTp]=useState(1);const [ld,setLd]=useState(true);
  const [kw,setKw]=useState('');const [cat,setCat]=useState('');const [flag,setFlag]=useState('');const [sources,setSrc]=useState([]);const [srcId,setSrcId]=useState('');
  const [showCreate,setShowCreate]=useState(false);const [editA,setEditA]=useState(null);const [viewA,setViewA]=useState(null);const toast=useToast();

  const load=useCallback(()=>{setLd(true);const p2={page,page_size:20};if(kw)p2.keyword=kw;if(cat)p2.category=cat;if(flag)p2.flag=flag;if(srcId)p2.source_id=srcId;
    api.getArticles(p2).then(r=>{setArticles(r.data.articles);setTotal(r.data.total);setTp(r.data.total_pages);setLd(false)}).catch(()=>setLd(false))},[page,kw,cat,flag,srcId]);
  useEffect(()=>{load()},[load]);
  useEffect(()=>{api.getSources().then(r=>setSrc(r.data))},[]);

  return (<div><toast.El/>
    <div className="page-header"><h2>Articles ({total})</h2><button className="btn btn-primary" onClick={()=>setShowCreate(true)}><IC.Plus/>Create</button></div>
    <div className="card" style={{marginBottom:20}}><div style={{display:'flex',gap:12,flexWrap:'wrap',alignItems:'flex-end'}}>
      <div style={{flex:'1 1 200px'}}><label style={{fontSize:11,color:'var(--text-muted)',display:'block',marginBottom:4}}>SEARCH</label><input className="form-input" placeholder="Search..." value={kw} onChange={e=>setKw(e.target.value)} onKeyDown={e=>e.key==='Enter'&&(setPage(1)||load())}/></div>
      <div><label style={{fontSize:11,color:'var(--text-muted)',display:'block',marginBottom:4}}>CATEGORY</label><select className="form-select" value={cat} onChange={e=>{setCat(e.target.value);setPage(1)}}><option value="">All</option>{CATS.map(c=><option key={c}>{c}</option>)}</select></div>
      <div><label style={{fontSize:11,color:'var(--text-muted)',display:'block',marginBottom:4}}>FLAG</label><select className="form-select" value={flag} onChange={e=>{setFlag(e.target.value);setPage(1)}}><option value="">All</option><option value="P">Pending</option><option value="N">New</option><option value="A">AI Done</option><option value="Y">Top</option><option value="D">Deleted</option></select></div>
      <div><label style={{fontSize:11,color:'var(--text-muted)',display:'block',marginBottom:4}}>SOURCE</label><select className="form-select" value={srcId} onChange={e=>{setSrcId(e.target.value);setPage(1)}}><option value="">All</option>{sources.map(s=><option key={s.id} value={s.id}>{s.name}</option>)}</select></div>
      <button className="btn btn-secondary" onClick={()=>{setKw('');setCat('');setFlag('');setSrcId('');setPage(1)}}>Clear</button>
    </div></div>
    {ld?<div className="loading"><div className="spinner"/></div>:<div className="table-container"><table><thead><tr><th>ID</th><th>Title</th><th>Source</th><th>Cat</th><th>Flag</th><th>By</th><th>Actions</th></tr></thead><tbody>
      {articles.map(a=><tr key={a.id}><td style={{fontFamily:'var(--mono)',fontSize:12}}>{a.id}</td>
        <td><div className="truncate" style={{color:'var(--text-primary)',fontWeight:500,cursor:'pointer'}} onClick={()=>setViewA(a)}>{a.rephrased_title||a.original_title}</div></td>
        <td style={{fontSize:12}}>{a.source_name}</td><td>{a.category||'—'}</td><td><FlagBadge flag={a.flag}/></td><td style={{fontSize:11}}>{a.submitted_by||'—'}</td>
        <td><div className="btn-group"><button className="btn btn-secondary btn-sm" onClick={()=>setViewA(a)}><IC.Eye/></button><button className="btn btn-secondary btn-sm" onClick={()=>setEditA(a)}>Edit</button><button className="btn btn-secondary btn-sm" onClick={async()=>{await api.reprocessArticle(a.id);toast.show('AI queued');load()}}>AI</button><button className="btn btn-danger btn-sm" onClick={async()=>{if(window.confirm('Delete?')){await api.deleteArticle(a.id);toast.show('Deleted');load()}}}>Del</button></div></td></tr>)}
      {articles.length===0&&<tr><td colSpan="7" className="empty-state">No articles</td></tr>}
    </tbody></table></div>}
    {tp>1&&<div className="pagination"><button disabled={page<=1} onClick={()=>setPage(p=>p-1)}>Prev</button><span>{page}/{tp}</span><button disabled={page>=tp} onClick={()=>setPage(p=>p+1)}>Next</button></div>}
    {showCreate&&<CreateModal onClose={()=>setShowCreate(false)} onDone={()=>{setShowCreate(false);toast.show('Created');load()}} sources={sources}/>}
    {editA&&<EditModal article={editA} onClose={()=>setEditA(null)} onDone={()=>{setEditA(null);toast.show('Updated');load()}} sources={sources}/>}
    {viewA&&<ArticleDetailModal article={viewA} onClose={()=>setViewA(null)}/>}
  </div>);
}

function CreateModal({onClose,onDone,sources}) {
  const [f,setF]=useState({title:'',content:'',category:'General',tags:'',source_id:'',image_url:''});const [sv,setSv]=useState(false);
  const go=async()=>{if(!f.title)return;setSv(true);try{await api.createManualArticle({title:f.title,content:f.content,category:f.category,tags:f.tags?f.tags.split(',').map(t=>t.trim()):[],source_id:parseInt(f.source_id)||undefined,image_url:f.image_url||undefined});onDone()}catch(e){setSv(false);alert(e.response?.data?.detail||'Failed to create article')}};
  return (<div className="modal-overlay" onClick={onClose}><div className="modal" onClick={e=>e.stopPropagation()}>
    <h3>Create Article (Admin)</h3>
    <div className="form-group"><label>Title *</label><input className="form-input" value={f.title} onChange={e=>setF({...f,title:e.target.value})}/></div>
    <div className="form-group"><label>Content</label><textarea className="form-textarea" rows={5} value={f.content} onChange={e=>setF({...f,content:e.target.value})}/></div>
    <div className="grid-2"><div className="form-group"><label>Category</label><select className="form-select" value={f.category} onChange={e=>setF({...f,category:e.target.value})}>{CATS.map(c=><option key={c}>{c}</option>)}<option>General</option></select></div>
    <div className="form-group"><label>Source</label><select className="form-select" value={f.source_id} onChange={e=>setF({...f,source_id:e.target.value})}><option value="">— Select —</option>{sources.map(s=><option key={s.id} value={s.id}>{s.name}</option>)}</select></div></div>
    <div className="form-group"><label>Tags</label><input className="form-input" value={f.tags} onChange={e=>setF({...f,tags:e.target.value})} placeholder="tag1, tag2"/></div>
    <div className="form-group"><label>Image URL</label><input className="form-input" value={f.image_url} onChange={e=>setF({...f,image_url:e.target.value})} placeholder="https://example.com/image.jpg"/></div>
    <div className="modal-actions"><button className="btn btn-secondary" onClick={onClose}>Cancel</button><button className="btn btn-primary" onClick={go} disabled={sv}>{sv?'Creating...':'Create'}</button></div>
  </div></div>);
}

function EditModal({article:a,onClose,onDone}) {
  const [f,setF]=useState({
    original_title:a.original_title||'',
    original_content:a.original_content||'',
    rephrased_title:a.rephrased_title||'',
    rephrased_content:a.rephrased_content||'',
    category:a.category||'General',
    tags:(a.tags||[]).join(', '),
    flag:a.flag||'N',
    image_url:a.image_url||''
  });
  const [sv,setSv]=useState(false);
  const go=async()=>{setSv(true);try{await api.updateArticle(a.id,{original_title:f.original_title,original_content:f.original_content,rephrased_title:f.rephrased_title,rephrased_content:f.rephrased_content,category:f.category,tags:f.tags?f.tags.split(',').map(t=>t.trim()):[],flag:f.flag,image_url:f.image_url});onDone()}catch{setSv(false)}};
  return (<div className="modal-overlay" onClick={onClose}><div className="modal" style={{maxWidth:720}} onClick={e=>e.stopPropagation()}>
    <h3>Edit #{a.id}</h3>
    <div className="form-group"><label>Original Title</label><input className="form-input" value={f.original_title} onChange={e=>setF({...f,original_title:e.target.value})}/></div>
    <div className="form-group"><label>Original Content</label><textarea className="form-textarea" rows={3} value={f.original_content} onChange={e=>setF({...f,original_content:e.target.value})}/></div>
    <div className="form-group"><label>Rephrased Title</label><input className="form-input" value={f.rephrased_title} onChange={e=>setF({...f,rephrased_title:e.target.value})}/></div>
    <div className="form-group"><label>Rephrased Content</label><textarea className="form-textarea" rows={5} value={f.rephrased_content} onChange={e=>setF({...f,rephrased_content:e.target.value})}/></div>
    <div className="grid-2"><div className="form-group"><label>Category</label><select className="form-select" value={f.category} onChange={e=>setF({...f,category:e.target.value})}>{CATS.map(c=><option key={c}>{c}</option>)}</select></div>
    <div className="form-group"><label>Flag</label><select className="form-select" value={f.flag} onChange={e=>setF({...f,flag:e.target.value})}><option value="P">Pending</option><option value="N">New</option><option value="A">AI Done</option><option value="Y">Top</option><option value="D">Deleted</option></select></div></div>
    <div className="form-group"><label>Tags</label><input className="form-input" value={f.tags} onChange={e=>setF({...f,tags:e.target.value})}/></div>
    <div className="form-group"><label>Image URL</label><input className="form-input" value={f.image_url} onChange={e=>setF({...f,image_url:e.target.value})} placeholder="https://example.com/image.jpg"/></div>
    <div className="modal-actions"><button className="btn btn-secondary" onClick={onClose}>Cancel</button><button className="btn btn-primary" onClick={go} disabled={sv}>{sv?'Saving...':'Save'}</button></div>
  </div></div>);
}

// ===== SOURCES, TOP NEWS, CATEGORIES — compact =====
function SourcesPage() {
  const [src,setSrc]=useState([]);const [ld,setLd]=useState(true);const [show,setShow]=useState(false);const toast=useToast();
  const load=()=>{setLd(true);api.getSources().then(r=>{setSrc(r.data);setLd(false)}).catch(()=>setLd(false))};
  useEffect(()=>{load()},[]);
  return (<div><toast.El/>
    <div className="page-header"><h2>Sources</h2><button className="btn btn-primary" onClick={()=>setShow(true)}><IC.Plus/>Add</button></div>
    {ld?<div className="loading"><div className="spinner"/></div>:<div className="table-container"><table><thead><tr><th>Name</th><th>Type</th><th>Interval</th><th>Status</th><th>Actions</th></tr></thead><tbody>
      {src.map(s=><tr key={s.id}><td style={{fontWeight:600}}>{s.name}</td><td style={{fontFamily:'var(--mono)',fontSize:12}}>{s.scraper_type}</td><td>{s.scrape_interval_minutes}m</td><td>{s.is_paused?<span className="badge badge-paused">PAUSED</span>:s.is_enabled?<span className="badge badge-enabled">ACTIVE</span>:<span className="badge badge-disabled">OFF</span>}</td>
        <td><div className="btn-group"><button className="btn btn-secondary btn-sm" onClick={async()=>{await api.triggerAction('trigger_scrape',s.id);toast.show('Scraping')}}><IC.Play/></button><button className="btn btn-secondary btn-sm" onClick={async()=>{await api.togglePause(s.id);load()}}>{s.is_paused?'Resume':'Pause'}</button><button className="btn btn-secondary btn-sm" onClick={async()=>{await api.toggleEnable(s.id);load()}}>{s.is_enabled?'Off':'On'}</button></div></td></tr>)}
    </tbody></table></div>}
    {show&&<SrcModal onClose={()=>setShow(false)} onDone={()=>{setShow(false);toast.show('Added');load()}}/>}
  </div>);
}
function SrcModal({onClose,onDone}) {
  const [f,setF]=useState({name:'',url:'',language:'en',scraper_type:'rss',scrape_interval_minutes:60,scraper_config:'{}'});const [sv,setSv]=useState(false);
  const go=async()=>{if(!f.name||!f.url)return;setSv(true);try{let c={};try{c=JSON.parse(f.scraper_config)}catch{}await api.createSource({...f,scraper_config:c,scrape_interval_minutes:parseInt(f.scrape_interval_minutes)});onDone()}catch(e){setSv(false);alert(e.response?.data?.detail||'Failed to add source')}};
  return (<div className="modal-overlay" onClick={onClose}><div className="modal" onClick={e=>e.stopPropagation()}>
    <h3>Add Source</h3>
    <div className="grid-2"><div className="form-group"><label>Name *</label><input className="form-input" value={f.name} onChange={e=>setF({...f,name:e.target.value})}/></div><div className="form-group"><label>URL *</label><input className="form-input" value={f.url} onChange={e=>setF({...f,url:e.target.value})}/></div></div>
    <div className="grid-2"><div className="form-group"><label>Language</label><select className="form-select" value={f.language} onChange={e=>setF({...f,language:e.target.value})}><option value="en">English</option><option value="te">Telugu</option></select></div><div className="form-group"><label>Type</label><select className="form-select" value={f.scraper_type} onChange={e=>setF({...f,scraper_type:e.target.value})}><option value="rss">RSS</option><option value="html">HTML</option><option value="manual">Manual</option></select></div></div>
    <div className="form-group"><label>Config JSON</label><textarea className="form-textarea" style={{fontFamily:'var(--mono)',fontSize:12}} value={f.scraper_config} onChange={e=>setF({...f,scraper_config:e.target.value})}/></div>
    <div className="modal-actions"><button className="btn btn-secondary" onClick={onClose}>Cancel</button><button className="btn btn-primary" onClick={go} disabled={sv}>{sv?'Adding...':'Add'}</button></div>
  </div></div>);
}

function TopNewsPage() {
  const [arts,setArts]=useState([]);const [ld,setLd]=useState(true);const [viewA,setViewA]=useState(null);const toast=useToast();
  useEffect(()=>{api.getTopNews(100).then(r=>{setArts(r.data);setLd(false)}).catch(()=>setLd(false))},[]);
  return (<div><toast.El/>
    <div className="page-header"><h2>Top 100 News</h2><button className="btn btn-primary" onClick={async()=>{try{const r=await api.triggerAction('trigger_ranking');toast.show(r.data?.message||'Ranking triggered')}catch(e){toast.show(e.response?.data?.detail||'Failed')}}}><IC.Ref/>Refresh</button></div>
    {ld?<div className="loading"><div className="spinner"/></div>:<div className="table-container"><table><thead><tr><th>#</th><th>Title</th><th>Category</th><th>Source</th><th>Score</th></tr></thead><tbody>
      {arts.map((a,i)=><tr key={a.id} style={{cursor:'pointer'}} onClick={()=>setViewA(a)}><td style={{fontFamily:'var(--mono)',fontWeight:700,color:i<3?'var(--yellow)':'var(--text-muted)'}}>{i+1}</td><td><div style={{fontWeight:500}} dangerouslySetInnerHTML={{__html:a.rephrased_title||a.original_title}}/></td><td><span className="badge badge-new">{a.category}</span></td><td style={{fontSize:12}}>{a.source_name}</td><td style={{fontFamily:'var(--mono)'}}>{a.rank_score?.toFixed(0)}</td></tr>)}
      {arts.length===0&&<tr><td colSpan="5" className="empty-state">No top news</td></tr>}
    </tbody></table></div>}
    {viewA&&<ArticleDetailModal article={viewA} onClose={()=>setViewA(null)}/>}
  </div>);
}

function CategoriesPage() {
  const [cats,setCats]=useState([]);const [ld,setLd]=useState(true);const [nc,setNc]=useState({name:'',slug:'',description:''});const toast=useToast();
  const load=()=>{api.getCategories().then(r=>{setCats(r.data);setLd(false)}).catch(()=>setLd(false))};
  useEffect(()=>{load()},[]);
  const add=async()=>{if(!nc.name)return;await api.createCategory({name:nc.name,slug:nc.slug||nc.name.toLowerCase().replace(/\s+/g,'-'),description:nc.description});setNc({name:'',slug:'',description:''});toast.show('Added');load()};
  return (<div><toast.El/>
    <div className="page-header"><h2>Categories</h2></div>
    <div className="card" style={{marginBottom:20}}><div style={{display:'flex',gap:12,alignItems:'flex-end',flexWrap:'wrap'}}>
      <div style={{flex:1}}><label style={{fontSize:11,color:'var(--text-muted)',display:'block',marginBottom:4}}>NAME</label><input className="form-input" value={nc.name} onChange={e=>setNc({...nc,name:e.target.value})}/></div>
      <div style={{flex:1}}><label style={{fontSize:11,color:'var(--text-muted)',display:'block',marginBottom:4}}>DESC</label><input className="form-input" value={nc.description} onChange={e=>setNc({...nc,description:e.target.value})}/></div>
      <button className="btn btn-primary" onClick={add}><IC.Plus/>Add</button>
    </div></div>
    {ld?<div className="loading"><div className="spinner"/></div>:<div className="table-container"><table><thead><tr><th>Name</th><th>Slug</th><th>Articles</th><th>Active</th></tr></thead><tbody>
      {cats.map(c=><tr key={c.id}><td style={{fontWeight:600}}>{c.name}</td><td style={{fontFamily:'var(--mono)',fontSize:12}}>{c.slug}</td><td>{c.article_count}</td><td>{c.is_active?<span className="badge badge-enabled">YES</span>:<span className="badge badge-disabled">NO</span>}</td></tr>)}
    </tbody></table></div>}
  </div>);
}

// ===== YOUTUBE IMPORT PAGE =====
function YouTubePage() {
  const [url,setUrl]=useState('');const [result,setResult]=useState(null);const [ld,setLd]=useState(false);const [saving,setSaving]=useState(false);
  const [sources,setSrc]=useState([]);const [srcId,setSrcId]=useState('');const toast=useToast();
  useEffect(()=>{api.getSources().then(r=>setSrc(r.data)).catch(()=>{})},[]);

  const process=async()=>{
    if(!url){toast.show('Enter a YouTube URL');return;}
    setLd(true);setResult(null);
    try{const r=await api.processYouTube(url);setResult(r.data);toast.show('Transcript processed!')}catch(e){toast.show(e.response?.data?.detail||'Failed to process')}
    setLd(false);
  };

  const save=async()=>{
    if(!result)return;setSaving(true);
    try{
      await api.saveYouTubeArticle({video_url:result.video_url,title:result.rephrased_title,content:result.rephrased_content,category:result.category,tags:[],image_url:result.thumbnail_url,source_id:parseInt(srcId)||undefined});
      toast.show('Saved to Top News!');setResult(null);setUrl('');
    }catch(e){toast.show(e.response?.data?.detail||'Failed to save')}
    setSaving(false);
  };

  return (<div><toast.El/>
    <div className="page-header"><h2><IC.YT/> YouTube Import</h2></div>
    <div className="card" style={{marginBottom:20}}>
      <div style={{display:'flex',gap:12,alignItems:'flex-end'}}>
        <div style={{flex:1}}><label style={{fontSize:11,color:'var(--text-muted)',display:'block',marginBottom:4}}>YOUTUBE URL</label>
          <input className="form-input" value={url} onChange={e=>setUrl(e.target.value)} placeholder="https://www.youtube.com/watch?v=..." onKeyDown={e=>e.key==='Enter'&&process()}/></div>
        <div><label style={{fontSize:11,color:'var(--text-muted)',display:'block',marginBottom:4}}>SOURCE</label>
          <select className="form-select" value={srcId} onChange={e=>setSrcId(e.target.value)}><option value="">Default</option>{sources.map(s=><option key={s.id} value={s.id}>{s.name}</option>)}</select></div>
        <button className="btn btn-primary" onClick={process} disabled={ld}><IC.Play/>{ld?'Processing...':'Fetch & Process'}</button>
      </div>
      <div style={{marginTop:12,fontSize:12,color:'var(--text-muted)'}}>Paste a YouTube link → fetches captions → translates to English → AI rephrases → saves as news article</div>
    </div>

    {ld&&<div className="loading"><div className="spinner"/>Fetching transcript and running AI...</div>}

    {result&&!result.error&&(<div className="card">
      <div className="card-header"><h3>Preview</h3><button className="btn btn-primary" onClick={save} disabled={saving}>{saving?'Saving...':'Save to Top News'}</button></div>
      {result.thumbnail_url&&<img src={result.thumbnail_url} alt="" style={{width:'100%',maxWidth:480,borderRadius:8,marginBottom:16}}/>}

      <div style={{marginBottom:16}}>
        <div style={{fontSize:11,color:'var(--text-muted)',textTransform:'uppercase',marginBottom:4}}>AI Title</div>
        <h3 dangerouslySetInnerHTML={{__html:result.rephrased_title}}/>
      </div>

      <div style={{marginBottom:16}}>
        <div style={{fontSize:11,color:'var(--text-muted)',textTransform:'uppercase',marginBottom:4}}>Category</div>
        <span className="badge badge-new">{result.category}</span>
      </div>

      <div style={{marginBottom:16}}>
        <div style={{fontSize:11,color:'var(--accent)',textTransform:'uppercase',marginBottom:4}}>AI Rephrased Content</div>
        <div style={{background:'var(--bg-input)',padding:16,borderRadius:8,fontSize:13,lineHeight:1.7,maxHeight:300,overflowY:'auto'}} dangerouslySetInnerHTML={{__html:result.rephrased_content}}/>
      </div>

      <details style={{marginTop:12}}>
        <summary style={{cursor:'pointer',fontSize:12,color:'var(--text-muted)'}}>View Raw Transcript ({result.transcript_language})</summary>
        <div style={{background:'var(--bg-input)',padding:12,borderRadius:8,fontSize:12,lineHeight:1.6,marginTop:8,maxHeight:200,overflowY:'auto',whiteSpace:'pre-wrap'}}>{result.raw_transcript}</div>
      </details>
      {result.translated_text!==result.raw_transcript&&<details style={{marginTop:8}}>
        <summary style={{cursor:'pointer',fontSize:12,color:'var(--text-muted)'}}>View English Translation</summary>
        <div style={{background:'var(--bg-input)',padding:12,borderRadius:8,fontSize:12,lineHeight:1.6,marginTop:8,maxHeight:200,overflowY:'auto',whiteSpace:'pre-wrap'}}>{result.translated_text}</div>
      </details>}
    </div>)}

    {result&&result.error&&<div className="card" style={{borderColor:'var(--red)'}}><div style={{color:'var(--red)',fontWeight:600}}>Error: {result.error}</div></div>}
  </div>);
}

// ===== USER MANAGEMENT (admin) =====
function UsersPage() {
  const [users,setUsers]=useState([]);const [ld,setLd]=useState(true);const [show,setShow]=useState(false);const toast=useToast();
  const load=()=>{setLd(true);api.getUsers().then(r=>{setUsers(r.data);setLd(false)}).catch(()=>setLd(false))};
  useEffect(()=>{load()},[]);

  return (<div><toast.El/>
    <div className="page-header"><h2>User Management</h2><button className="btn btn-primary" onClick={()=>setShow(true)}><IC.Plus/>Add User</button></div>
    <div style={{padding:'12px 16px',background:'var(--accent-dim)',borderRadius:8,marginBottom:20,fontSize:13,color:'var(--accent)'}}>
      <strong>Admin</strong> users have full platform access. <strong>Reporter</strong> users can only submit articles and view their submissions. Reporter articles require admin approval before publishing.
    </div>
    {ld?<div className="loading"><div className="spinner"/></div>:<div className="table-container"><table><thead><tr><th>ID</th><th>Username</th><th>Email</th><th>Role</th><th>Active</th><th>Last Login</th><th>Actions</th></tr></thead><tbody>
      {users.map(u=><tr key={u.id}><td style={{fontFamily:'var(--mono)',fontSize:12}}>{u.id}</td><td style={{fontWeight:600}}>{u.username}</td><td style={{fontSize:12}}>{u.email||'—'}</td>
        <td><span className={`badge ${u.role==='admin'?'badge-top':'badge-new'}`}>{u.role.toUpperCase()}</span></td>
        <td>{u.is_active?<span className="badge badge-enabled">YES</span>:<span className="badge badge-disabled">NO</span>}</td>
        <td style={{fontFamily:'var(--mono)',fontSize:11}}>{u.last_login_at?new Date(u.last_login_at).toLocaleString():'Never'}</td>
        <td><div className="btn-group">
          {u.role==='reporter'&&<button className="btn btn-secondary btn-sm" onClick={async()=>{await api.updateUser(u.id,{role:'admin'});toast.show('Promoted');load()}}>→Admin</button>}
          {u.role==='admin'&&u.username!=='admin'&&<button className="btn btn-secondary btn-sm" onClick={async()=>{await api.updateUser(u.id,{role:'reporter'});toast.show('Demoted');load()}}>→Reporter</button>}
          {u.username!=='admin'&&<button className="btn btn-danger btn-sm" onClick={async()=>{if(window.confirm(`Deactivate ${u.username}?`)){await api.deleteUser(u.id);toast.show('Deactivated');load()}}}>Deactivate</button>}
        </div></td></tr>)}
    </tbody></table></div>}
    {show&&<UserModal onClose={()=>setShow(false)} onDone={()=>{setShow(false);toast.show('User created');load()}}/>}
  </div>);
}

function UserModal({onClose,onDone}) {
  const [f,setF]=useState({username:'',password:'',email:'',role:'reporter'});const [sv,setSv]=useState(false);
  const go=async()=>{if(!f.username||!f.password)return;setSv(true);try{await api.createUser(f);onDone()}catch(e){alert(e.response?.data?.detail||'Failed');setSv(false)}};
  return (<div className="modal-overlay" onClick={onClose}><div className="modal" onClick={e=>e.stopPropagation()}>
    <h3>Create User</h3>
    <div className="grid-2"><div className="form-group"><label>Username *</label><input className="form-input" value={f.username} onChange={e=>setF({...f,username:e.target.value})}/></div>
    <div className="form-group"><label>Password *</label><input className="form-input" type="password" value={f.password} onChange={e=>setF({...f,password:e.target.value})}/></div></div>
    <div className="grid-2"><div className="form-group"><label>Email</label><input className="form-input" value={f.email} onChange={e=>setF({...f,email:e.target.value})}/></div>
    <div className="form-group"><label>Role</label><select className="form-select" value={f.role} onChange={e=>setF({...f,role:e.target.value})}><option value="reporter">Reporter</option><option value="admin">Admin</option></select></div></div>
    <div className="modal-actions"><button className="btn btn-secondary" onClick={onClose}>Cancel</button><button className="btn btn-primary" onClick={go} disabled={sv}>{sv?'Creating...':'Create User'}</button></div>
  </div></div>);
}

// ===== SCHEDULER + SETTINGS (compact) =====
function SchedulerPage() {
  const [logs,setLogs]=useState([]);const [ld,setLd]=useState(true);const [fl,setFl]=useState('');const [cfg,setCfg]=useState(null);const toast=useToast();
  const loadLogs=()=>{setLd(true);const p={limit:50};if(fl)p.job_type=fl;api.getSchedulerLogs(p).then(r=>{setLogs(r.data);setLd(false)}).catch(()=>setLd(false))};
  useEffect(()=>{loadLogs()},[fl]);
  useEffect(()=>{api.getSchedulerConfig().then(r=>setCfg(r.data)).catch(()=>{})},[]);
  const trig=async(a)=>{try{const r=await api.triggerAction(a);toast.show(r.data?.message||`${a} triggered!`);setTimeout(loadLogs,2000)}catch(e){toast.show(e.response?.data?.detail||`${a} failed!`)}};
  const toggleFlag=async(field)=>{if(!cfg)return;const v=!cfg[field];try{await api.updateSchedulerConfig({[field]:v});setCfg(p=>({...p,[field]:v}));toast.show(`${field}→${v?'ON':'OFF'}`)}catch{}};

  return (<div><toast.El/>
    <div className="page-header"><h2>Scheduler</h2>
      <div className="btn-group"><button className="btn btn-primary" onClick={()=>trig('trigger_pipeline')}><IC.Play/>Pipeline</button><button className="btn btn-secondary" onClick={()=>trig('trigger_scrape')}>Scrape</button><button className="btn btn-success" onClick={()=>trig('trigger_ai')}>AI</button><button className="btn btn-secondary" onClick={()=>trig('trigger_ranking')}>Rank</button><button className="btn btn-secondary" style={{background:'#1877F2',color:'#fff',border:'none'}} onClick={()=>trig('trigger_social')}>Social</button><button className="btn btn-secondary" style={{background:'#FF9900',color:'#fff',border:'none'}} onClick={()=>trig('trigger_sync')}>AWS</button></div>
    </div>
    {cfg&&<div className="card" style={{marginBottom:20}}><div className="card-header"><h3>Schedule Config</h3></div><div className="table-container"><table><thead><tr><th>Job</th><th>Status</th><th>Minutes</th><th>Toggle</th></tr></thead><tbody>
      {[{l:'Scrape',f:'scrape_enabled',m:'scrape_minutes'},{l:'AI',f:'ai_enabled',m:'ai_minutes'},{l:'Ranking',f:'ranking_enabled',m:'ranking_minutes'},{l:'AWS Sync',f:'aws_sync_enabled',m:'aws_sync_minutes'},{l:'Categories',f:'category_count_enabled',m:'category_minutes'},{l:'Cleanup',f:'cleanup_enabled',m:'cleanup_minutes'}].map(j=>
        <tr key={j.f}><td style={{fontWeight:600}}>{j.l}</td><td><span className={`badge ${cfg[j.f]?'badge-enabled':'badge-disabled'}`}>{cfg[j.f]?'ON':'OFF'}</span></td><td style={{fontFamily:'var(--mono)',fontSize:12}}>{cfg[j.m]}</td><td><button className={`btn btn-sm ${cfg[j.f]?'btn-danger':'btn-success'}`} onClick={()=>toggleFlag(j.f)}>{cfg[j.f]?'Disable':'Enable'}</button></td></tr>)}
    </tbody></table></div></div>}
    <div style={{display:'flex',gap:8,marginBottom:20}}>{['','scrape','ai_process','ranking','cleanup'].map(f=><button key={f} className={`btn btn-sm ${fl===f?'btn-primary':'btn-secondary'}`} onClick={()=>setFl(f)}>{f||'All'}</button>)}<button className="btn btn-sm btn-secondary" onClick={loadLogs} style={{marginLeft:'auto'}}><IC.Ref/></button></div>
    {ld?<div className="loading"><div className="spinner"/></div>:<div className="table-container"><table><thead><tr><th>ID</th><th>Type</th><th>Status</th><th>Count</th><th>Duration</th><th>Started</th></tr></thead><tbody>
      {logs.map(l=><tr key={l.id}><td style={{fontFamily:'var(--mono)',fontSize:12}}>{l.id}</td><td style={{fontWeight:600}}>{l.job_type}</td><td><span className={`badge ${l.status==='completed'?'badge-enabled':l.status==='failed'?'badge-deleted':'badge-paused'}`}>{l.status}</span></td><td>{l.articles_processed}</td><td style={{fontFamily:'var(--mono)',fontSize:12}}>{l.duration_seconds?`${l.duration_seconds.toFixed(1)}s`:'—'}</td><td style={{fontFamily:'var(--mono)',fontSize:11}}>{new Date(l.started_at).toLocaleString()}</td></tr>)}
      {logs.length===0&&<tr><td colSpan="6" className="empty-state">No logs</td></tr>}
    </tbody></table></div>}
  </div>);
}

function SettingsPage() {
  const [cfg,setCfg]=useState(null);const [ld,setLd]=useState(true);const toast=useToast();
  useEffect(()=>{api.getSchedulerConfig().then(r=>{setCfg(r.data);setLd(false)}).catch(()=>setLd(false))},[]);
  if(ld)return <div className="loading"><div className="spinner"/></div>;
  if(!cfg)return <div className="empty-state"><p>Failed to load</p></div>;
  return (<div><toast.El/>
    <div className="page-header"><h2>Platform Settings</h2></div>
    <div className="grid-2">
      <div className="card"><div className="card-header"><h3>AI Config</h3></div><div style={{fontSize:13,lineHeight:2}}>
        <div><strong>Provider Chain:</strong> {cfg.ai_provider_chain.join(' → ')}</div>
        <div><strong>Batch:</strong> {cfg.ai_batch_size} | <strong>Workers:</strong> {cfg.ai_concurrency}</div>
      </div></div>
      <div className="card"><div className="card-header"><h3>Article Flow</h3></div>
        <div style={{display:'flex',gap:8,alignItems:'center',flexWrap:'wrap',padding:8}}>
          {[{f:'P',l:'Pending'},{f:'N',l:'New'},{f:'A',l:'AI Done'},{f:'Y',l:'Top News'}].map((s,i)=>(
            <React.Fragment key={s.f}><div style={{textAlign:'center',padding:8,background:'var(--bg-input)',borderRadius:6,minWidth:80}}><FlagBadge flag={s.f}/><div style={{fontSize:10,marginTop:4}}>{s.l}</div></div>{i<3&&<span style={{color:'var(--text-muted)'}}>→</span>}</React.Fragment>))}
        </div>
        <div style={{fontSize:11,color:'var(--text-muted)',marginTop:8}}>Reporters submit → P (pending) → Admin approves → N → AI → A → Ranking → Y</div>
      </div>
    </div>
    <div className="card" style={{marginTop:20}}><div className="card-header"><h3>Quick Actions</h3></div>
      <div className="btn-group" style={{flexWrap:'wrap'}}>
        <button className="btn btn-primary" onClick={async()=>{try{const r=await api.triggerAction('trigger_pipeline');toast.show(r.data?.message||'Pipeline started')}catch(e){toast.show(e.response?.data?.detail||'Failed')}}}>Full Pipeline</button>
        <button className="btn btn-secondary" onClick={async()=>{try{const r=await api.triggerAction('trigger_scrape');toast.show(r.data?.message||'Scraping')}catch(e){toast.show(e.response?.data?.detail||'Failed')}}}>Scrape All</button>
        <button className="btn btn-success" onClick={async()=>{try{const r=await api.triggerAction('trigger_ai');toast.show(r.data?.message||'AI started')}catch(e){toast.show(e.response?.data?.detail||'Failed')}}}>AI Process</button>
        <button className="btn btn-secondary" onClick={async()=>{try{const r=await api.triggerAction('trigger_ranking');toast.show(r.data?.message||'Ranking')}catch(e){toast.show(e.response?.data?.detail||'Failed')}}}>Update Ranking</button>
        <button className="btn btn-secondary" onClick={async()=>{try{const r=await api.triggerAction('trigger_sync');toast.show(r.data?.message||'Syncing')}catch(e){toast.show(e.response?.data?.detail||'Failed')}}}>AWS Sync</button>
        <button className="btn btn-danger" onClick={async()=>{try{const r=await api.triggerAction('trigger_cleanup');toast.show(r.data?.message||'Cleanup')}catch(e){toast.show(e.response?.data?.detail||'Failed')}}}>Cleanup</button>
      </div>
    </div>
  </div>);
}

// ===== MAIN APP (role-based routing) =====
function AdminShell({auth}) {
  return (<div className="app-layout"><Sidebar onLogout={auth.doLogout}/><div className="main-content"><Routes>
    <Route path="/" element={<DashboardPage/>}/><Route path="/articles" element={<ArticlesPage/>}/>
    <Route path="/pending" element={<PendingApprovalsPage/>}/><Route path="/sources" element={<SourcesPage/>}/>
    <Route path="/top-news" element={<TopNewsPage/>}/><Route path="/categories" element={<CategoriesPage/>}/>
    <Route path="/youtube" element={<YouTubePage/>}/><Route path="/scheduler" element={<SchedulerPage/>}/>
    <Route path="/users" element={<UsersPage/>}/><Route path="/settings" element={<SettingsPage/>}/>
    <Route path="*" element={<Navigate to="/"/>}/>
  </Routes></div></div>);
}

function ReporterShell({auth}) {
  return (<div className="app-layout"><Sidebar onLogout={auth.doLogout}/><div className="main-content"><Routes>
    <Route path="/" element={<ReporterSubmitPage/>}/>
    <Route path="/my-submissions" element={<MySubmissionsPage/>}/>
    <Route path="*" element={<Navigate to="/"/>}/>
  </Routes></div></div>);
}

export default function App() {
  const auth = useAuth();
  return (<AuthContext.Provider value={auth}><BrowserRouter>
    {!auth.isAuthenticated ? <Routes><Route path="*" element={<LoginPage onLogin={auth.doLogin}/>}/></Routes>
    : auth.isAdmin ? <AdminShell auth={auth}/> : <ReporterShell auth={auth}/>}
  </BrowserRouter></AuthContext.Provider>);
}
