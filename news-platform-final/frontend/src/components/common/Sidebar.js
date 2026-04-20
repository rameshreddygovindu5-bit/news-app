import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuthCtx } from '../../context/AuthContext';
import { IC } from './Icons';

export function Sidebar({onLogout}) {
  const loc = useLocation();
  const {user} = useAuthCtx();
  const isAdmin = user?.role==='admin';

  const adminNav = [
    {p:'/',l:'Dashboard',i:IC.Dash},
    {p:'/articles',l:'Articles',i:IC.Doc},
    {p:'/pending',l:'Pending Approval',i:IC.Check},
    {p:'/sources',l:'Sources',i:IC.Globe},
    {p:'/top-news',l:'Top 100 News',i:IC.Star},
    {p:'/categories',l:'Categories',i:IC.List},
    {p:'/youtube',l:'YouTube Import',i:IC.YT},
    {p:'/scheduler',l:'Scheduler',i:IC.Clock},
    {p:'/users',l:'Users',i:IC.Users},
    {p:'/polls',l:'Polls',i:IC.List},
    {p:'/surveys',l:'Surveys',i:IC.List},
    {p:'/wishes',l:'Wishes',i:IC.Gift},
    {p:'/settings',l:'Settings',i:IC.Gear},
  ];

  const reporterNav = [
    {p:'/',l:'Submit Article',i:IC.Send},
    {p:'/my-submissions',l:'My Submissions',i:IC.Doc},
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
