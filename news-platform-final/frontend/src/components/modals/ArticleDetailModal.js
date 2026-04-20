import React, { useState } from 'react';
import { FlagBadge } from '../common/Badges';
import { getImg } from '../../constants/news';

export default function ArticleDetailModal({article:a, onClose}) {
  const [lang, setLang] = useState('en');
  if(!a) return null;
  const hasTE = !!(a.telugu_title && a.telugu_content);
  
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" style={{maxWidth:950}} onClick={e=>e.stopPropagation()}>
        <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:12}}>
          <h3>Article #{a.id}</h3>
          <div style={{display:'flex',gap:8,alignItems:'center'}}>
            {hasTE && (
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
          {a.category && <span className="badge badge-new">{a.category}</span>}
          {a.source_name && <span className="badge badge-paused" style={{background:'var(--india-green)',color:'#fff'}}>{a.source_name}</span>}
          {a.submitted_by && <span className="badge badge-paused">by {a.submitted_by}</span>}
          {a.ai_status && <span className="badge" style={{background:a.ai_status==='failed'?'var(--india-red)':'#6200ea',color:'#fff'}}>{a.ai_status.toUpperCase()}</span>}
          {a.ai_error_count > 0 && <span className="badge badge-deleted">ERRORS: {a.ai_error_count}</span>}
          {hasTE && <span className="badge" style={{background:'#FF9900',color:'#fff'}}>TELUGU ✓</span>}
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
            <h4 style={{fontSize:16,marginBottom:10,lineHeight:1.4,color:'var(--accent)'}}
              className={lang==='te'?'telugu-text':''}
              dangerouslySetInnerHTML={{__html:lang==='te'?(a.telugu_title||a.rephrased_title||a.original_title):(a.rephrased_title||a.original_title)}}/>
            <div className={`news-premium-content ${lang==='te'?'telugu-text':''}`} style={{maxHeight:350,overflowY:'auto'}}
              dangerouslySetInnerHTML={{__html:lang==='te'?(a.telugu_content||a.rephrased_content||'Not translated yet'):(a.rephrased_content||'Not processed yet')}}/>
          </div>
        </div>
        {(a.tags||[]).length>0 && <div style={{marginTop:8,display:'flex',gap:4,flexWrap:'wrap'}}>{(a.tags||[]).map(t=><span key={t} className="tag">{t}</span>)}</div>}
      </div>
    </div>
  );
}
